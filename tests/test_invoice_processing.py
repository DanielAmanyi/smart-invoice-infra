import pytest
import json
import boto3
from moto import mock_s3, mock_dynamodb, mock_textract
from unittest.mock import patch, MagicMock
import sys
import os

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'inference_handler'))

from handler import lambda_handler, convert_floats_to_decimal
from error_handler import ValidationError, InvoiceProcessingError
from retry_handler import retry_with_backoff, RetryableError

class TestInvoiceProcessing:
    """Test suite for invoice processing functionality"""
    
    @mock_s3
    @mock_dynamodb
    def test_lambda_handler_success(self):
        """Test successful invoice processing"""
        # Setup mock AWS services
        s3 = boto3.client('s3', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create test bucket and table
        bucket_name = 'test-invoice-bucket'
        table_name = 'test-invoice-table'
        
        s3.create_bucket(Bucket=bucket_name)
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'invoice_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'invoice_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Upload test file
        test_content = b"Test PDF content"
        s3.put_object(Bucket=bucket_name, Key='test-invoice.pdf', Body=test_content)
        
        # Set environment variables
        os.environ['BUCKET_NAME'] = bucket_name
        os.environ['DDB_TABLE'] = table_name
        
        # Create test event
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': bucket_name},
                    'object': {'key': 'test-invoice.pdf'}
                }
            }]
        }
        
        # Mock the OCR and AI functions
        with patch('handler.extract_text_from_s3') as mock_ocr, \
             patch('handler.infer_invoice_data') as mock_ai:
            
            mock_ocr.return_value = {
                'raw_text': 'ACME Corp Invoice #123 Amount: $100.00',
                'key_value_pairs': {'Invoice': '123', 'Amount': '$100.00'},
                'confidence_scores': {'overall': 95.0}
            }
            
            mock_ai.return_value = {
                'vendor': 'ACME Corp',
                'amount': 100.00,
                'date': '2024-01-15',
                'invoice_number': '123',
                'currency': 'USD',
                'extraction_method': 'hybrid_ai_rules',
                'confidence': 'high'
            }
            
            # Execute lambda handler
            result = lambda_handler(event, {})
            
            # Assertions
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert 'invoice_id' in response_body
            assert response_body['vendor'] == 'ACME Corp'
            assert response_body['amount'] == 100.00
            assert response_body['extraction_method'] == 'hybrid_ai_rules'
    
    def test_unsupported_file_type(self):
        """Test handling of unsupported file types"""
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test-file.txt'}
                }
            }]
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'Unsupported file type' in response_body['error']
    
    @patch('handler.extract_text_from_s3')
    def test_textract_error_handling(self, mock_extract):
        """Test handling of Textract errors"""
        from botocore.exceptions import ClientError
        
        # Mock Textract error
        mock_extract.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnsupportedDocumentException',
                    'Message': 'Document format not supported'
                }
            },
            operation_name='AnalyzeDocument'
        )
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test-invoice.pdf'}
                }
            }]
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 500
        response_body = json.loads(result['body'])
        assert 'error' in response_body
    
    def test_convert_floats_to_decimal(self):
        """Test float to Decimal conversion for DynamoDB"""
        test_data = {
            'amount': 123.45,
            'tax': 12.34,
            'nested': {
                'value': 67.89,
                'list': [1.23, 4.56]
            },
            'string_value': 'test',
            'int_value': 42
        }
        
        result = convert_floats_to_decimal(test_data)
        
        from decimal import Decimal
        assert isinstance(result['amount'], Decimal)
        assert isinstance(result['tax'], Decimal)
        assert isinstance(result['nested']['value'], Decimal)
        assert isinstance(result['nested']['list'][0], Decimal)
        assert result['string_value'] == 'test'
        assert result['int_value'] == 42

class TestRetryLogic:
    """Test suite for retry functionality"""
    
    def test_retry_success_on_first_attempt(self):
        """Test that successful functions don't retry"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_with_retryable_error(self):
        """Test retry behavior with retryable errors"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary failure")
            return "success"
        
        result = failing_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhaustion(self):
        """Test that retries are exhausted and exception is raised"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")
        
        with pytest.raises(RetryableError):
            always_failing_function()
        
        assert call_count == 3  # Initial attempt + 2 retries
    
    def test_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retries"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def non_retryable_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            non_retryable_function()
        
        assert call_count == 1  # No retries

class TestErrorHandling:
    """Test suite for error handling functionality"""
    
    def test_validation_error(self):
        """Test validation error creation"""
        error = ValidationError("Invalid input")
        
        assert str(error) == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.retryable == False
    
    def test_invoice_processing_error(self):
        """Test custom invoice processing error"""
        error = InvoiceProcessingError(
            "Processing failed", 
            error_code="PROCESSING_ERROR", 
            retryable=True
        )
        
        assert str(error) == "Processing failed"
        assert error.error_code == "PROCESSING_ERROR"
        assert error.retryable == True

class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    @mock_s3
    @mock_dynamodb
    @patch('boto3.client')
    def test_end_to_end_processing(self, mock_boto_client):
        """Test complete end-to-end invoice processing"""
        # Setup mocks
        mock_textract = MagicMock()
        mock_bedrock = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'textract':
                return mock_textract
            elif service_name == 'bedrock-runtime':
                return mock_bedrock
            else:
                return boto3.client(service_name, **kwargs)
        
        mock_boto_client.side_effect = mock_client
        
        # Mock Textract response
        mock_textract.analyze_document.return_value = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'ACME Corporation',
                    'Confidence': 95.0
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Invoice #INV-001',
                    'Confidence': 98.0
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Amount: $250.00',
                    'Confidence': 99.0
                }
            ]
        }
        
        # Mock Bedrock response
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock()
        }
        
        # Setup AWS resources
        s3 = boto3.client('s3', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        bucket_name = 'integration-test-bucket'
        table_name = 'integration-test-table'
        
        s3.create_bucket(Bucket=bucket_name)
        
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'invoice_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'invoice_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Upload test file
        s3.put_object(
            Bucket=bucket_name, 
            Key='integration-test.pdf', 
            Body=b"Mock PDF content"
        )
        
        # Set environment variables
        os.environ['BUCKET_NAME'] = bucket_name
        os.environ['DDB_TABLE'] = table_name
        
        # Create test event
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': bucket_name},
                    'object': {'key': 'integration-test.pdf'}
                }
            }]
        }
        
        # Execute the handler
        result = lambda_handler(event, {})
        
        # Verify results
        assert result['statusCode'] == 200
        
        # Verify data was saved to DynamoDB
        response = table.scan()
        assert len(response['Items']) == 1
        
        saved_item = response['Items'][0]
        assert 'invoice_id' in saved_item
        assert saved_item['s3_key'] == 'integration-test.pdf'
        assert saved_item['s3_bucket'] == bucket_name

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

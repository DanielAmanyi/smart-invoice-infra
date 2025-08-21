import pytest
import os
import boto3
from moto import mock_s3, mock_dynamodb, mock_textract

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """Create a mocked S3 client."""
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture(scope="function")
def dynamodb_resource(aws_credentials):
    """Create a mocked DynamoDB resource."""
    with mock_dynamodb():
        yield boto3.resource("dynamodb", region_name="us-east-1")

@pytest.fixture(scope="function")
def textract_client(aws_credentials):
    """Create a mocked Textract client."""
    with mock_textract():
        yield boto3.client("textract", region_name="us-east-1")

@pytest.fixture
def sample_invoice_event():
    """Sample S3 event for invoice processing."""
    return {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-invoice-bucket'},
                'object': {'key': 'sample-invoice.pdf'}
            }
        }]
    }

@pytest.fixture
def sample_textract_response():
    """Sample Textract response."""
    return {
        'Blocks': [
            {
                'BlockType': 'LINE',
                'Text': 'ACME Corporation',
                'Confidence': 95.0,
                'Id': '1'
            },
            {
                'BlockType': 'LINE',
                'Text': 'Invoice Number: INV-2024-001',
                'Confidence': 98.0,
                'Id': '2'
            },
            {
                'BlockType': 'LINE',
                'Text': 'Date: 2024-01-15',
                'Confidence': 97.0,
                'Id': '3'
            },
            {
                'BlockType': 'LINE',
                'Text': 'Amount: $1,250.00',
                'Confidence': 99.0,
                'Id': '4'
            },
            {
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['KEY'],
                'Text': 'Invoice Number:',
                'Id': '5',
                'Relationships': [{'Type': 'VALUE', 'Ids': ['6']}]
            },
            {
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['VALUE'],
                'Text': 'INV-2024-001',
                'Id': '6'
            }
        ]
    }

@pytest.fixture
def sample_bedrock_response():
    """Sample Bedrock response."""
    return {
        'vendor': 'ACME Corporation',
        'amount': 1250.00,
        'date': '2024-01-15',
        'invoice_number': 'INV-2024-001',
        'tax_amount': 125.00,
        'currency': 'USD',
        'line_items': [
            {'description': 'Professional Services', 'amount': 1125.00},
            {'description': 'Tax', 'amount': 125.00}
        ],
        'confidence': 'high',
        'extraction_method': 'hybrid_ai_rules'
    }

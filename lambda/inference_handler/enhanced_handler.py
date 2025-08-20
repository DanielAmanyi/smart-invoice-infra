import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

from ocr_extract import extract_text_from_s3
from model_helpers import infer_invoice_data

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['DDB_TABLE']
DLQ_URL = os.environ.get('DLQ_URL')

class InvoiceProcessingError(Exception):
    """Custom exception for invoice processing errors"""
    pass

def lambda_handler(event, context):
    """
    Enhanced Lambda handler with comprehensive error handling
    """
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing invoice: s3://{bucket}/{key}")
        
        # Validate file type
        if not key.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            raise InvoiceProcessingError(f"Unsupported file type: {key}")
        
        # Process invoice with retry logic
        result = process_invoice_with_retry(bucket, key, max_retries=3)
        
        logger.info(f"Successfully processed invoice: {result['invoice_id']}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Inference complete", 
                "result": result
            })
        }

    except InvoiceProcessingError as e:
        logger.error(f"Invoice processing error: {str(e)}")
        send_to_dlq(event, str(e))
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Processing error: {str(e)}"})
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        send_to_dlq(event, str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal processing error"})
        }

def process_invoice_with_retry(bucket: str, key: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Process invoice with retry logic
    """
    for attempt in range(max_retries):
        try:
            # 1. Extract text from the uploaded invoice
            invoice_text = extract_text_from_s3(bucket, key)
            
            if not invoice_text or len(invoice_text.strip()) < 10:
                raise InvoiceProcessingError("Insufficient text extracted from invoice")
            
            # 2. Perform inference
            result = infer_invoice_data(invoice_text)
            
            # 3. Validate inference results
            validate_inference_result(result)
            
            # 4. Write result to DynamoDB
            item = {
                "invoice_id": str(uuid.uuid4()),
                "s3_key": key,
                "processed_at": datetime.utcnow().isoformat(),
                "processing_attempts": attempt + 1,
                **result
            }
            
            save_to_dynamodb(item)
            return item
            
        except ClientError as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise InvoiceProcessingError(f"Failed after {max_retries} attempts: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise

def validate_inference_result(result: Dict[str, Any]) -> None:
    """
    Validate inference results
    """
    required_fields = ['vendor', 'amount', 'date']
    for field in required_fields:
        if field not in result or not result[field]:
            raise InvoiceProcessingError(f"Missing required field: {field}")

def save_to_dynamodb(item: Dict[str, Any]) -> None:
    """
    Save item to DynamoDB with error handling
    """
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=item)
        logger.info(f"Saved item to DynamoDB: {item['invoice_id']}")
    except ClientError as e:
        raise InvoiceProcessingError(f"Failed to save to DynamoDB: {str(e)}")

def send_to_dlq(event: Dict[str, Any], error_message: str) -> None:
    """
    Send failed event to Dead Letter Queue
    """
    if not DLQ_URL:
        logger.warning("DLQ_URL not configured, skipping DLQ send")
        return
    
    try:
        message_body = {
            "original_event": event,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        sqs.send_message(
            QueueUrl=DLQ_URL,
            MessageBody=json.dumps(message_body)
        )
        logger.info("Sent failed event to DLQ")
    except Exception as e:
        logger.error(f"Failed to send to DLQ: {str(e)}")

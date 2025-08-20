import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ocr_extract import extract_text_from_s3
from model_helpers import infer_invoice_data

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['DDB_TABLE']

def lambda_handler(event, context):
    """
    Process uploaded invoice with real OCR and AI extraction
    """
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing invoice: s3://{bucket}/{key}")
        
        # Validate file type
        supported_extensions = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp')
        if not key.lower().endswith(supported_extensions):
            logger.warning(f"Unsupported file type: {key}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unsupported file type. Supported: {supported_extensions}"})
            }
        
        # 1. Extract text and structured data using AWS Textract
        logger.info("Starting OCR extraction with Textract...")
        extracted_data = extract_text_from_s3(bucket, key)
        
        # Log extraction results
        text_length = len(extracted_data.get('raw_text', ''))
        kv_pairs_count = len(extracted_data.get('key_value_pairs', {}))
        logger.info(f"Textract extracted {text_length} characters, {kv_pairs_count} key-value pairs")
        
        # 2. Perform AI inference to extract structured invoice data
        logger.info("Starting AI inference...")
        inference_result = infer_invoice_data(extracted_data)
        
        # 3. Prepare final result
        invoice_id = str(uuid.uuid4())
        final_item = {
            "invoice_id": invoice_id,
            "s3_key": key,
            "s3_bucket": bucket,
            "processed_at": datetime.utcnow().isoformat(),
            "file_type": key.split('.')[-1].lower(),
            
            # Extracted invoice data
            "vendor": inference_result.get('vendor', 'Unknown'),
            "amount": inference_result.get('amount', 0.0),
            "date": inference_result.get('date'),
            "invoice_number": inference_result.get('invoice_number'),
            "tax_amount": inference_result.get('tax_amount', 0.0),
            "currency": inference_result.get('currency', 'USD'),
            "line_items": inference_result.get('line_items', []),
            
            # Metadata
            "extraction_method": inference_result.get('extraction_method', 'unknown'),
            "confidence": inference_result.get('confidence', 'medium'),
            "textract_confidence": inference_result.get('textract_confidence', 0.0),
            "text_length": inference_result.get('text_length', 0),
            
            # Raw data (for debugging/reprocessing)
            "raw_text_preview": extracted_data.get('raw_text', '')[:500],  # First 500 chars
            "key_value_pairs": extracted_data.get('key_value_pairs', {}),
        }
        
        # 4. Save to DynamoDB
        logger.info(f"Saving results to DynamoDB table: {TABLE_NAME}")
        table = dynamodb.Table(TABLE_NAME)
        
        # Convert float values to Decimal for DynamoDB
        final_item = convert_floats_to_decimal(final_item)
        
        table.put_item(Item=final_item)
        
        logger.info(f"Successfully processed invoice {invoice_id}: vendor={final_item['vendor']}, amount={final_item['amount']}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Invoice processing complete",
                "invoice_id": invoice_id,
                "vendor": str(final_item['vendor']),
                "amount": float(final_item['amount']),
                "extraction_method": final_item['extraction_method']
            }, default=str)
        }

    except ValueError as e:
        # Handle validation errors (unsupported formats, etc.)
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error processing invoice: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal processing error",
                "details": str(e)
            })
        }

def convert_floats_to_decimal(obj):
    """
    Convert float values to Decimal for DynamoDB compatibility
    """
    from decimal import Decimal
    
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

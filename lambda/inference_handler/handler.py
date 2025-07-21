import json
import boto3
import os
import uuid
from datetime import datetime

from ocr_extract import extract_text_from_s3
from model_helpers import infer_invoice_data

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['DDB_TABLE']

def lambda_handler(event, context):
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # 1. Extract text from the uploaded invoice
        invoice_text = extract_text_from_s3(bucket, key)

        # 2. Perform inference (mock or real logic)
        result = infer_invoice_data(invoice_text)

        # 3. Write result to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        item = {
            "invoice_id": str(uuid.uuid4()),
            "s3_key": key,
            "processed_at": datetime.utcnow().isoformat(),
            **result
        }
        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Inference complete", "result": item})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

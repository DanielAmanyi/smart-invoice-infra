import json
import boto3
import base64
import uuid
import os
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    try:
        # Expecting a JSON payload with base64 file content and filename
        body = json.loads(event['body'])
        file_content = base64.b64decode(body['file_base64'])
        original_filename = body.get('filename', f'invoice-{uuid.uuid4()}.pdf')

        # Generate S3 key
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        s3_key = f"invoices/{timestamp}-{uuid.uuid4()}-{original_filename}"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType="application/pdf"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Upload successful",
                "s3_key": s3_key
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }

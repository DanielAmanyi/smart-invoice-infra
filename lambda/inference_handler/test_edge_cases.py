import pytest
import handler
import os

os.environ['BUCKET_NAME'] = 'test-bucket'
os.environ['DDB_TABLE'] = 'test-table'

def test_lambda_handler_missing_record():
    event = {}
    result = handler.lambda_handler(event, None)
    assert result['statusCode'] == 400

def test_lambda_handler_invalid_s3_key(monkeypatch):
    monkeypatch.setattr(handler, 'extract_text_from_s3', lambda bucket, key: None)
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'invalid-key'}
            }
        }]
    }
    result = handler.lambda_handler(event, None)
    assert result['statusCode'] == 400

import pytest
import handler
import os
import base64

os.environ['BUCKET_NAME'] = 'test-bucket'

def test_lambda_handler_missing_body():
    event = {}
    result = handler.lambda_handler(event, None)
    assert result['statusCode'] == 400

def test_lambda_handler_invalid_base64():
    event = {
        'body': '{"file_base64": "not_base64", "filename": "test.pdf"}'
    }
    result = handler.lambda_handler(event, None)
    assert result['statusCode'] == 400

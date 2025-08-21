import logging
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from retry_handler import NonRetryableError, RetryableError

logger = logging.getLogger(__name__)

class InvoiceProcessingError(Exception):
    """Base exception for invoice processing errors"""
    def __init__(self, message: str, error_code: str = None, retryable: bool = False):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable

class TextractError(InvoiceProcessingError):
    """Textract-specific processing error"""
    pass

class BedrockError(InvoiceProcessingError):
    """Bedrock-specific processing error"""
    pass

class ValidationError(InvoiceProcessingError):
    """Input validation error"""
    def __init__(self, message: str):
        super().__init__(message, error_code="VALIDATION_ERROR", retryable=False)

def handle_textract_error(error: Exception) -> Dict[str, Any]:
    """
    Handle Textract-specific errors and return structured error info
    """
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', '')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        error_mapping = {
            'UnsupportedDocumentException': {
                'user_message': 'Document format not supported. Please use PDF, PNG, JPG, TIFF, or BMP.',
                'error_code': 'UNSUPPORTED_FORMAT',
                'retryable': False,
                'http_status': 400
            },
            'DocumentTooLargeException': {
                'user_message': 'Document is too large. Maximum size is 10MB for synchronous processing.',
                'error_code': 'DOCUMENT_TOO_LARGE',
                'retryable': False,
                'http_status': 400
            },
            'BadDocumentException': {
                'user_message': 'Document appears to be corrupted or unreadable.',
                'error_code': 'CORRUPTED_DOCUMENT',
                'retryable': False,
                'http_status': 400
            },
            'ThrottlingException': {
                'user_message': 'Service is temporarily busy. Please try again in a few moments.',
                'error_code': 'RATE_LIMIT_EXCEEDED',
                'retryable': True,
                'http_status': 429
            },
            'InternalServerError': {
                'user_message': 'Textract service is temporarily unavailable.',
                'error_code': 'SERVICE_UNAVAILABLE',
                'retryable': True,
                'http_status': 503
            },
            'AccessDeniedException': {
                'user_message': 'Insufficient permissions to process document.',
                'error_code': 'ACCESS_DENIED',
                'retryable': False,
                'http_status': 403
            }
        }
        
        if error_code in error_mapping:
            error_info = error_mapping[error_code]
            logger.error(f"Textract error {error_code}: {error_message}")
            
            # Raise appropriate exception for retry logic
            if error_info['retryable']:
                raise RetryableError(error_info['user_message'])
            else:
                raise NonRetryableError(error_info['user_message'])
        
        # Unknown Textract error
        logger.error(f"Unknown Textract error {error_code}: {error_message}")
        return {
            'error_code': 'TEXTRACT_ERROR',
            'user_message': 'Document processing failed due to an unexpected error.',
            'retryable': True,
            'http_status': 500,
            'technical_details': error_message
        }
    
    # Non-ClientError exceptions
    logger.error(f"Unexpected Textract error: {str(error)}")
    return {
        'error_code': 'TEXTRACT_UNEXPECTED',
        'user_message': 'An unexpected error occurred during document processing.',
        'retryable': False,
        'http_status': 500,
        'technical_details': str(error)
    }

def handle_bedrock_error(error: Exception) -> Dict[str, Any]:
    """
    Handle Bedrock-specific errors and return structured error info
    """
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', '')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        error_mapping = {
            'ValidationException': {
                'user_message': 'Invalid request format for AI processing.',
                'error_code': 'INVALID_AI_REQUEST',
                'retryable': False,
                'http_status': 400
            },
            'ThrottlingException': {
                'user_message': 'AI service is temporarily busy. Please try again.',
                'error_code': 'AI_RATE_LIMIT',
                'retryable': True,
                'http_status': 429
            },
            'ModelNotReadyException': {
                'user_message': 'AI model is not available. Please try again later.',
                'error_code': 'MODEL_UNAVAILABLE',
                'retryable': True,
                'http_status': 503
            },
            'AccessDeniedException': {
                'user_message': 'AI service access not configured properly.',
                'error_code': 'AI_ACCESS_DENIED',
                'retryable': False,
                'http_status': 403
            },
            'ServiceQuotaExceededException': {
                'user_message': 'AI service quota exceeded. Please try again later.',
                'error_code': 'AI_QUOTA_EXCEEDED',
                'retryable': True,
                'http_status': 429
            }
        }
        
        if error_code in error_mapping:
            error_info = error_mapping[error_code]
            logger.error(f"Bedrock error {error_code}: {error_message}")
            
            # Raise appropriate exception for retry logic
            if error_info['retryable']:
                raise RetryableError(error_info['user_message'])
            else:
                raise NonRetryableError(error_info['user_message'])
        
        # Unknown Bedrock error
        logger.error(f"Unknown Bedrock error {error_code}: {error_message}")
        return {
            'error_code': 'BEDROCK_ERROR',
            'user_message': 'AI processing failed due to an unexpected error.',
            'retryable': True,
            'http_status': 500,
            'technical_details': error_message
        }
    
    # Non-ClientError exceptions
    logger.error(f"Unexpected Bedrock error: {str(error)}")
    return {
        'error_code': 'BEDROCK_UNEXPECTED',
        'user_message': 'An unexpected error occurred during AI processing.',
        'retryable': False,
        'http_status': 500,
        'technical_details': str(error)
    }

def handle_dynamodb_error(error: Exception) -> Dict[str, Any]:
    """
    Handle DynamoDB-specific errors and return structured error info
    """
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', '')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        error_mapping = {
            'ProvisionedThroughputExceededException': {
                'user_message': 'Database is temporarily busy. Please try again.',
                'error_code': 'DATABASE_BUSY',
                'retryable': True,
                'http_status': 429
            },
            'ValidationException': {
                'user_message': 'Invalid data format for storage.',
                'error_code': 'INVALID_DATA_FORMAT',
                'retryable': False,
                'http_status': 400
            },
            'ResourceNotFoundException': {
                'user_message': 'Database table not found.',
                'error_code': 'TABLE_NOT_FOUND',
                'retryable': False,
                'http_status': 404
            },
            'AccessDeniedException': {
                'user_message': 'Insufficient permissions to save data.',
                'error_code': 'DATABASE_ACCESS_DENIED',
                'retryable': False,
                'http_status': 403
            }
        }
        
        if error_code in error_mapping:
            error_info = error_mapping[error_code]
            logger.error(f"DynamoDB error {error_code}: {error_message}")
            
            # Raise appropriate exception for retry logic
            if error_info['retryable']:
                raise RetryableError(error_info['user_message'])
            else:
                raise NonRetryableError(error_info['user_message'])
        
        # Unknown DynamoDB error
        logger.error(f"Unknown DynamoDB error {error_code}: {error_message}")
        return {
            'error_code': 'DYNAMODB_ERROR',
            'user_message': 'Failed to save processing results.',
            'retryable': True,
            'http_status': 500,
            'technical_details': error_message
        }
    
    # Non-ClientError exceptions
    logger.error(f"Unexpected DynamoDB error: {str(error)}")
    return {
        'error_code': 'DYNAMODB_UNEXPECTED',
        'user_message': 'An unexpected error occurred while saving data.',
        'retryable': False,
        'http_status': 500,
        'technical_details': str(error)
    }

def validate_file_input(bucket: str, key: str) -> None:
    """
    Validate file input parameters
    """
    if not bucket or not key:
        raise ValidationError("Missing bucket or key parameter")
    
    # Check file extension
    supported_extensions = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp')
    if not key.lower().endswith(supported_extensions):
        raise ValidationError(
            f"Unsupported file type. Supported formats: {', '.join(supported_extensions)}"
        )
    
    # Check for suspicious file paths
    if '..' in key or key.startswith('/'):
        raise ValidationError("Invalid file path")

def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """
    Create a standardized error response
    """
    if isinstance(error, InvoiceProcessingError):
        return {
            'statusCode': 400 if not error.retryable else 500,
            'body': {
                'error': {
                    'code': error.error_code,
                    'message': str(error),
                    'retryable': error.retryable,
                    'request_id': request_id
                }
            }
        }
    
    # Generic error
    logger.error(f"Unhandled error: {str(error)}")
    return {
        'statusCode': 500,
        'body': {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'retryable': False,
                'request_id': request_id
            }
        }
    }

import time
import logging
from functools import wraps
from typing import Callable, Any, Optional, List
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Exception that indicates an operation should be retried"""
    pass

class NonRetryableError(Exception):
    """Exception that indicates an operation should not be retried"""
    pass

def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[type]] = None
):
    """
    Decorator that implements exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retryable_exceptions: List of exception types that should trigger retries
    """
    if retryable_exceptions is None:
        retryable_exceptions = [RetryableError, ClientError]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this is a retryable error
                    if not _is_retryable_error(e, retryable_exceptions):
                        logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                        raise e
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts: {str(e)}")
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} of {func.__name__} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

def _is_retryable_error(error: Exception, retryable_exceptions: List[type]) -> bool:
    """
    Determine if an error should trigger a retry
    """
    # Check if it's explicitly non-retryable
    if isinstance(error, NonRetryableError):
        return False
    
    # Check if it's in the retryable exceptions list
    for exc_type in retryable_exceptions:
        if isinstance(error, exc_type):
            # For AWS ClientError, check specific error codes
            if isinstance(error, ClientError):
                return _is_retryable_aws_error(error)
            return True
    
    return False

def _is_retryable_aws_error(error: ClientError) -> bool:
    """
    Determine if an AWS ClientError should be retried
    """
    error_code = error.response.get('Error', {}).get('Code', '')
    
    # Retryable AWS error codes
    retryable_codes = {
        'ThrottlingException',
        'ProvisionedThroughputExceededException',
        'RequestLimitExceeded',
        'ServiceUnavailable',
        'InternalServerError',
        'InternalError',
        'ServiceException',
        'SlowDown',
        'TooManyRequestsException'
    }
    
    # Non-retryable AWS error codes
    non_retryable_codes = {
        'ValidationException',
        'InvalidParameterException',
        'AccessDeniedException',
        'UnauthorizedOperation',
        'InvalidDocumentException',
        'UnsupportedDocumentException',
        'DocumentTooLargeException',
        'BadDocumentException'
    }
    
    if error_code in non_retryable_codes:
        return False
    
    if error_code in retryable_codes:
        return True
    
    # Default to retryable for 5xx HTTP status codes
    http_status = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
    return 500 <= http_status < 600

# Specific retry decorators for different services
def retry_textract_operation(max_retries: int = 3):
    """Retry decorator specifically for Textract operations"""
    return retry_with_backoff(
        max_retries=max_retries,
        backoff_factor=2.0,
        initial_delay=1.0,
        max_delay=30.0,
        retryable_exceptions=[ClientError, RetryableError]
    )

def retry_bedrock_operation(max_retries: int = 2):
    """Retry decorator specifically for Bedrock operations"""
    return retry_with_backoff(
        max_retries=max_retries,
        backoff_factor=1.5,
        initial_delay=2.0,
        max_delay=20.0,
        retryable_exceptions=[ClientError, RetryableError]
    )

def retry_dynamodb_operation(max_retries: int = 3):
    """Retry decorator specifically for DynamoDB operations"""
    return retry_with_backoff(
        max_retries=max_retries,
        backoff_factor=2.0,
        initial_delay=0.5,
        max_delay=10.0,
        retryable_exceptions=[ClientError, RetryableError]
    )

# Circuit breaker pattern for additional resilience
class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        """
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

# Global circuit breakers for different services
textract_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
bedrock_circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
dynamodb_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=20)

"""
Custom exceptions for Open Reasoning Arena.

This module provides a hierarchy of custom exceptions for better error handling
and consistent error responses throughout the application.
"""

from typing import Optional, Dict, Any


class ORAError(Exception):
    """Base exception for Open Reasoning Arena errors."""
    
    def __init__(self, message: str, code: str = "ERROR", 
                 status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "error": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(ORAError):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class AlreadyExistsError(ORAError):
    """Raised when a resource already exists."""
    
    def __init__(self, resource_type: str, field: str, value: str):
        super().__init__(
            message=f"{resource_type} with {field} '{value}' already exists",
            code="ALREADY_EXISTS",
            status_code=409,
            details={"resource_type": resource_type, "field": field, "value": value}
        )


class ValidationError(ORAError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class LengthValidationError(ValidationError):
    """Raised when input length exceeds maximum."""
    
    def __init__(self, field: str, value: str, max_length: int):
        super().__init__(
            message=f"{field} exceeds maximum length of {max_length} characters",
            field=field,
            value=value[:50] + "..." if len(value) > 50 else value
        )
        self.max_length = max_length


class AuthenticationError(ORAError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=401
        )


class AuthorizationError(ORAError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_FAILED",
            status_code=403
        )


class RateLimitExceededError(ORAError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class DatabaseError(ORAError):
    """Raised when there's a database error."""
    
    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation}
        )


class ConfigurationError(ORAError):
    """Raised when there's a configuration error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class ReputationError(ORAError):
    """Raised when there's a reputation system error."""
    
    def __init__(self, message: str, user_id: Optional[int] = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        super().__init__(
            message=message,
            code="REPUTATION_ERROR",
            status_code=400,
            details=details
        )


class ChallengeError(ORAError):
    """Raised when there's a challenge-related error."""
    
    def __init__(self, message: str, challenge_id: Optional[int] = None):
        details = {}
        if challenge_id:
            details["challenge_id"] = challenge_id
        super().__init__(
            message=message,
            code="CHALLENGE_ERROR",
            status_code=400,
            details=details
        )


class ScoringError(ORAError):
    """Raised when there's a scoring error."""
    
    def __init__(self, message: str, solution_id: Optional[int] = None):
        details = {}
        if solution_id:
            details["solution_id"] = solution_id
        super().__init__(
            message=message,
            code="SCORING_ERROR",
            status_code=400,
            details=details
        )

"""
Custom Exceptions Module for Machina Registry Service

This module defines custom exception classes for the Machina Registry Service,
implementing DevQ.ai's standard error handling patterns with proper error
categorization, logging integration, and HTTP status code mapping.

Features:
- Base exception class with common functionality
- HTTP status code mapping for API responses
- Logfire integration for error tracking
- Domain-specific exception types
- Error context and metadata support
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import logfire


class MachinaException(Exception):
    """
    Base exception class for Machina Registry Service.

    This class provides common functionality for all custom exceptions
    in the Machina Registry Service, including error logging, context
    management, and integration with observability systems.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for API responses
            context: Additional context information for debugging
            cause: Original exception that caused this error (if any)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause

        # Log the exception with Logfire
        self._log_exception()

    def _log_exception(self):
        """Log the exception with Logfire for observability."""
        logfire.error(
            f"MachinaException: {self.message}",
            error_code=self.error_code,
            exception_type=self.__class__.__name__,
            context=self.context,
            cause=str(self.cause) if self.cause else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Returns:
            Dict containing error information suitable for JSON responses
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "type": self.__class__.__name__,
            "context": self.context
        }


class ValidationError(MachinaException):
    """Exception raised when data validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context=context,
            **kwargs
        )


class NotFoundError(MachinaException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        identifier: Any,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"{resource_type} with identifier '{identifier}' not found"

        context = kwargs.get("context", {})
        context.update({
            "resource_type": resource_type,
            "identifier": str(identifier)
        })

        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            context=context,
            **kwargs
        )


class ConflictError(MachinaException):
    """Exception raised when a resource conflict occurs."""

    def __init__(
        self,
        resource_type: str,
        identifier: Any,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"{resource_type} with identifier '{identifier}' already exists"

        context = kwargs.get("context", {})
        context.update({
            "resource_type": resource_type,
            "identifier": str(identifier)
        })

        super().__init__(
            message=message,
            error_code="CONFLICT",
            context=context,
            **kwargs
        )


class DatabaseError(MachinaException):
    """Exception raised when database operations fail."""

    def __init__(
        self,
        operation: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Database operation '{operation}' failed"

        context = kwargs.get("context", {})
        context["operation"] = operation

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            context=context,
            **kwargs
        )


class CacheError(MachinaException):
    """Exception raised when cache operations fail."""

    def __init__(
        self,
        operation: str,
        key: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Cache operation '{operation}' failed"
            if key:
                message += f" for key '{key}'"

        context = kwargs.get("context", {})
        context["operation"] = operation
        if key:
            context["key"] = key

        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            context=context,
            **kwargs
        )


class ExternalServiceError(MachinaException):
    """Exception raised when external service calls fail."""

    def __init__(
        self,
        service_name: str,
        operation: str,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"External service '{service_name}' operation '{operation}' failed"
            if status_code:
                message += f" with status code {status_code}"

        context = kwargs.get("context", {})
        context.update({
            "service_name": service_name,
            "operation": operation
        })
        if status_code:
            context["status_code"] = status_code

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            context=context,
            **kwargs
        )


class ConfigurationError(MachinaException):
    """Exception raised when configuration is invalid or missing."""

    def __init__(
        self,
        setting_name: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Configuration error for setting '{setting_name}'"

        context = kwargs.get("context", {})
        context["setting_name"] = setting_name

        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            context=context,
            **kwargs
        )


class AuthenticationError(MachinaException):
    """Exception raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )


class AuthorizationError(MachinaException):
    """Exception raised when authorization fails."""

    def __init__(
        self,
        resource: str,
        action: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Access denied for action '{action}' on resource '{resource}'"

        context = kwargs.get("context", {})
        context.update({
            "resource": resource,
            "action": action
        })

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            context=context,
            **kwargs
        )


class RateLimitError(MachinaException):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        limit: int,
        window: int,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Rate limit exceeded: {limit} requests per {window} seconds"

        context = kwargs.get("context", {})
        context.update({
            "limit": limit,
            "window": window
        })

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            context=context,
            **kwargs
        )


class MCPError(MachinaException):
    """Exception raised when MCP protocol operations fail."""

    def __init__(
        self,
        tool_name: str,
        operation: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"MCP tool '{tool_name}' operation '{operation}' failed"

        context = kwargs.get("context", {})
        context.update({
            "tool_name": tool_name,
            "operation": operation
        })

        super().__init__(
            message=message,
            error_code="MCP_ERROR",
            context=context,
            **kwargs
        )


# HTTP Status Code Mapping
EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    CacheError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    MCPError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    MachinaException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status_code(exception: MachinaException) -> int:
    """
    Get the appropriate HTTP status code for a MachinaException.

    Args:
        exception: The exception to get the status code for

    Returns:
        HTTP status code integer
    """
    return EXCEPTION_STATUS_MAP.get(
        type(exception),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def create_http_exception(exception: MachinaException) -> HTTPException:
    """
    Convert a MachinaException to a FastAPI HTTPException.

    Args:
        exception: The MachinaException to convert

    Returns:
        HTTPException ready for FastAPI to handle
    """
    return HTTPException(
        status_code=get_http_status_code(exception),
        detail=exception.to_dict()
    )


def handle_exception(exception: Exception) -> MachinaException:
    """
    Convert any exception to a MachinaException for consistent handling.

    Args:
        exception: The exception to handle

    Returns:
        MachinaException or subclass
    """
    if isinstance(exception, MachinaException):
        return exception

    # Handle common exception types
    if isinstance(exception, ValueError):
        return ValidationError(
            message=str(exception),
            cause=exception
        )
    elif isinstance(exception, KeyError):
        return NotFoundError(
            resource_type="Key",
            identifier=str(exception),
            cause=exception
        )
    elif isinstance(exception, ConnectionError):
        return ExternalServiceError(
            service_name="Unknown",
            operation="Connection",
            message=str(exception),
            cause=exception
        )
    else:
        # Generic wrapper for unknown exceptions
        return MachinaException(
            message=f"Unexpected error: {str(exception)}",
            error_code="UNKNOWN_ERROR",
            context={"original_type": type(exception).__name__},
            cause=exception
        )

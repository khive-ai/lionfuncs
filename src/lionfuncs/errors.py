"""Custom error types for the lionfuncs package."""

__all__ = [
    "LionError",
    "LionFileError",
    "LionNetworkError",
    "APIClientError",
    "APIConnectionError",
    "APITimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "ResourceNotFoundError",
    "ServerError",
    "CircuitBreakerOpenError",
    "LionConcurrencyError",
    "QueueStateError",
    "LionSDKError",
]


class LionError(Exception):
    """Base exception for all lionfuncs errors."""

    pass


class LionFileError(LionError):
    """For file system operation errors."""

    pass


class LionNetworkError(LionError):
    """For network operation errors (e.g., connection issues, non-HTTP errors)."""

    pass


class APIClientError(LionNetworkError):
    """Base for HTTP client errors from AsyncAPIClient."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_content: str | bytes | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_content = response_content

    def __str__(self) -> str:
        base_str = super().__str__()
        if self.status_code is not None:
            return f"{base_str} (Status Code: {self.status_code})"
        return base_str


class APIConnectionError(APIClientError):
    """Raised when the client cannot connect to the server."""

    pass


class APITimeoutError(APIClientError):
    """Raised when a request times out."""

    pass


class RateLimitError(APIClientError):
    """Raised for 429 status codes, indicating rate limiting."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(APIClientError):
    """Raised for 401/403 status codes, indicating authentication/authorization issues."""

    pass


class ResourceNotFoundError(APIClientError):
    """Raised for 404 status codes."""

    pass


class ServerError(APIClientError):
    """Raised for 5xx status codes."""

    pass


class CircuitBreakerOpenError(LionNetworkError):
    """Raised when an operation is blocked by an open circuit breaker."""

    def __init__(self, message: str, *, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after

    def __str__(self) -> str:
        base_str = super().__str__()
        if self.retry_after is not None:
            return f"{base_str} (Retry After: {self.retry_after:.2f}s)"
        return base_str


class LionConcurrencyError(LionError):
    """For concurrency primitive errors."""

    pass


class QueueStateError(LionConcurrencyError):
    """Raised for invalid operations on a queue given its current state."""

    def __init__(self, message: str, *, current_state: str | None = None):
        super().__init__(message)
        self.current_state = current_state

    def __str__(self) -> str:
        base_str = super().__str__()
        if self.current_state is not None:
            return f"{base_str} (Current State: {self.current_state})"
        return base_str


class LionSDKError(LionError):
    """
    Base for errors originating from SDK interactions.
    Specific SDK errors should inherit from this.
    e.g., OpenAISDKError(LionSDKError)
    """

    def __init__(self, message: str, *, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception

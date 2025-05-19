import pytest

from lionfuncs import errors


def test_lion_error_base():
    """Tests that LionError can be raised and caught."""
    with pytest.raises(errors.LionError, match="Base lion error"):
        raise errors.LionError("Base lion error")


@pytest.mark.parametrize(
    "error_class, message_prefix, base_class",
    [
        (errors.LionFileError, "File error", errors.LionError),
        (errors.LionNetworkError, "Network error", errors.LionError),
        (errors.APIClientError, "API client error", errors.LionNetworkError),
        (errors.APIConnectionError, "API connection error", errors.APIClientError),
        (errors.APITimeoutError, "API timeout error", errors.APIClientError),
        (errors.RateLimitError, "Rate limit exceeded", errors.APIClientError),
        (errors.AuthenticationError, "Auth error", errors.APIClientError),
        (errors.ResourceNotFoundError, "Not found", errors.APIClientError),
        (errors.ServerError, "Server error", errors.APIClientError),
        (
            errors.CircuitBreakerOpenError,
            "Circuit breaker open",
            errors.LionNetworkError,
        ),
        (errors.LionConcurrencyError, "Concurrency error", errors.LionError),
        (errors.QueueStateError, "Queue state error", errors.LionConcurrencyError),
        (errors.LionSDKError, "SDK error", errors.LionError),
    ],
)
def test_specific_lion_errors(error_class, message_prefix, base_class):
    """Tests specific LionError subclasses for basic raising, catching, and inheritance."""
    message = f"{message_prefix} occurred"

    # For errors that take specific constructor args beyond message
    if error_class in [
        errors.APIClientError,
        errors.APIConnectionError,
        errors.APITimeoutError,
        errors.AuthenticationError,
        errors.ResourceNotFoundError,
        errors.ServerError,
    ]:
        with pytest.raises(error_class, match=message) as exc_info:
            raise error_class(message, status_code=500)
        assert isinstance(exc_info.value, base_class)
        assert exc_info.value.status_code == 500
        assert str(exc_info.value) == f"{message} (Status Code: 500)"
    elif error_class is errors.RateLimitError:
        with pytest.raises(error_class, match=message) as exc_info:
            raise error_class(message, status_code=429, retry_after=60)
        assert isinstance(exc_info.value, base_class)
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60
        assert str(exc_info.value) == f"{message} (Status Code: 429)"
    elif error_class is errors.LionSDKError:
        original_exc = ValueError("Original SDK issue")
        with pytest.raises(error_class, match=message) as exc_info:
            raise error_class(message, original_exception=original_exc)
        assert isinstance(exc_info.value, base_class)
        assert exc_info.value.original_exception is original_exc
    else:  # For errors that only take a message
        with pytest.raises(error_class, match=message) as exc_info:
            raise error_class(message)
        assert isinstance(exc_info.value, base_class)
        assert str(exc_info.value) == message


def test_api_client_error_str_no_status_code():
    """Tests APIClientError __str__ when status_code is None."""
    err = errors.APIClientError("Generic API error")
    assert str(err) == "Generic API error"
    assert err.status_code is None


def test_api_client_error_with_response_content():
    """Tests APIClientError stores response_content."""
    content = b"Error details"
    err = errors.APIClientError(
        "Error with content", status_code=500, response_content=content
    )
    assert err.response_content == content


# Example of a more specific SDK error (conceptual, as per TDS)
class OpenAISDKError(errors.LionSDKError):
    """Specific error for OpenAI SDK issues."""

    pass


def test_custom_sdk_error():
    """Tests that a custom SDK error can be defined and used."""
    original_exc = TypeError("OpenAI type issue")
    message = "OpenAI specific SDK error"
    with pytest.raises(OpenAISDKError, match=message) as exc_info:
        raise OpenAISDKError(message, original_exception=original_exc)
    assert isinstance(exc_info.value, errors.LionSDKError)
    assert exc_info.value.original_exception is original_exc

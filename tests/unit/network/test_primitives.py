"""
Unit tests for the network primitives module.
"""

import pytest
import time
from unittest.mock import AsyncMock

from pydantic import BaseModel

from lionfuncs.network.primitives import (
    AdaptiveRateLimiter,
    Endpoint,
    EndpointConfig,
    EndpointRateLimiter,
    HeaderFactory,
    TokenBucketRateLimiter,
    match_endpoint,
)


class TestHeaderFactory:
    """Tests for the HeaderFactory class."""

    def test_get_content_type_header(self):
        """Test get_content_type_header method."""
        headers = HeaderFactory.get_content_type_header()
        assert headers == {"Content-Type": "application/json"}
        
        headers = HeaderFactory.get_content_type_header("text/plain")
        assert headers == {"Content-Type": "text/plain"}

    def test_get_bearer_auth_header(self):
        """Test get_bearer_auth_header method."""
        headers = HeaderFactory.get_bearer_auth_header("test_api_key")
        assert headers == {"Authorization": "Bearer test_api_key"}

    def test_get_x_api_key_header(self):
        """Test get_x_api_key_header method."""
        headers = HeaderFactory.get_x_api_key_header("test_api_key")
        assert headers == {"x-api-key": "test_api_key"}

    def test_get_header_bearer(self):
        """Test get_header method with bearer auth."""
        headers = HeaderFactory.get_header(
            auth_type="bearer",
            content_type="application/json",
            api_key="test_api_key",
        )
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
        }

    def test_get_header_x_api_key(self):
        """Test get_header method with x-api-key auth."""
        headers = HeaderFactory.get_header(
            auth_type="x-api-key",
            content_type="application/json",
            api_key="test_api_key",
        )
        assert headers == {
            "Content-Type": "application/json",
            "x-api-key": "test_api_key",
        }

    def test_get_header_with_default_headers(self):
        """Test get_header method with default headers."""
        headers = HeaderFactory.get_header(
            auth_type="bearer",
            content_type="application/json",
            api_key="test_api_key",
            default_headers={"X-Custom": "custom_value"},
        )
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
            "X-Custom": "custom_value",
        }

    def test_get_header_missing_api_key(self):
        """Test get_header method with missing API key."""
        with pytest.raises(ValueError) as excinfo:
            HeaderFactory.get_header(
                auth_type="bearer",
                content_type="application/json",
                api_key=None,
            )
        assert "API key is required" in str(excinfo.value)

    def test_get_header_unsupported_auth_type(self):
        """Test get_header method with unsupported auth type."""
        with pytest.raises(ValueError) as excinfo:
            HeaderFactory.get_header(
                auth_type="unsupported",  # type: ignore
                content_type="application/json",
                api_key="test_api_key",
            )
        assert "Unsupported auth type" in str(excinfo.value)


class TestEndpointConfig:
    """Tests for the EndpointConfig class."""

    def test_endpoint_config_init(self):
        """Test EndpointConfig initialization."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="test_provider",
            endpoint="test/endpoint",
        )
        
        assert config.name == "test_endpoint"
        assert config.provider == "test_provider"
        assert config.transport_type == "http"
        assert config.base_url is None
        assert config.endpoint == "test/endpoint"
        assert config.endpoint_params is None
        assert config.method == "POST"
        assert config.params == {}
        assert config.content_type == "application/json"
        assert config.auth_type == "bearer"
        assert config.default_headers == {}
        assert config.api_key is None
        assert config.timeout == 300
        assert config.max_retries == 3
        assert config.kwargs == {}
        assert config.client_kwargs == {}

    def test_endpoint_config_full_url_without_params(self):
        """Test full_url property without endpoint params."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="test_provider",
            base_url="https://api.example.com",
            endpoint="test/endpoint",
        )
        
        assert config.full_url == "https://api.example.com/test/endpoint"

    def test_endpoint_config_full_url_with_params(self):
        """Test full_url property with endpoint params."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="test_provider",
            base_url="https://api.example.com",
            endpoint="test/{param1}/endpoint/{param2}",
            endpoint_params=["param1", "param2"],
            params={"param1": "value1", "param2": "value2"},
        )
        
        assert config.full_url == "https://api.example.com/test/value1/endpoint/value2"

    def test_endpoint_config_update(self):
        """Test update method."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="test_provider",
            endpoint="test/endpoint",
        )
        
        config.update(
            name="updated_endpoint",
            base_url="https://api.example.com",
            custom_param="custom_value",
        )
        
        assert config.name == "updated_endpoint"
        assert config.base_url == "https://api.example.com"
        assert config.kwargs["custom_param"] == "custom_value"


class TestEndpoint:
    """Tests for the Endpoint class."""

    def test_endpoint_init_with_dict(self):
        """Test Endpoint initialization with dict config."""
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
            }
        )
        
        assert isinstance(endpoint.config, EndpointConfig)
        assert endpoint.config.name == "test_endpoint"
        assert endpoint.config.provider == "test_provider"
        assert endpoint.config.endpoint == "test/endpoint"

    def test_endpoint_init_with_endpoint_config(self):
        """Test Endpoint initialization with EndpointConfig."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="test_provider",
            endpoint="test/endpoint",
        )
        
        endpoint = Endpoint(config=config)
        
        assert isinstance(endpoint.config, EndpointConfig)
        assert endpoint.config.name == "test_endpoint"
        assert endpoint.config.provider == "test_provider"
        assert endpoint.config.endpoint == "test/endpoint"
        
        # Should be a copy, not the same instance
        assert endpoint.config is not config

    def test_endpoint_init_with_kwargs(self):
        """Test Endpoint initialization with kwargs."""
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
            },
            base_url="https://api.example.com",
            api_key="test_api_key",
        )
        
        assert endpoint.config.base_url == "https://api.example.com"
        assert endpoint.config.api_key == "test_api_key"

    def test_endpoint_create_payload_with_dict(self):
        """Test create_payload method with dict request."""
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
                "api_key": "test_api_key",
            }
        )
        
        request = {"param1": "value1", "param2": "value2"}
        payload, headers = endpoint.create_payload(request)
        
        assert payload == {"param1": "value1", "param2": "value2"}
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
        }

    def test_endpoint_create_payload_with_model(self):
        """Test create_payload method with BaseModel request."""
        class TestModel(BaseModel):
            param1: str
            param2: str
        
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
                "api_key": "test_api_key",
            }
        )
        
        request = TestModel(param1="value1", param2="value2")
        payload, headers = endpoint.create_payload(request)
        
        assert payload == {"param1": "value1", "param2": "value2"}
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
        }

    def test_endpoint_create_payload_with_extra_headers(self):
        """Test create_payload method with extra headers."""
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
                "api_key": "test_api_key",
            }
        )
        
        request = {"param1": "value1"}
        extra_headers = {"X-Custom": "custom_value"}
        payload, headers = endpoint.create_payload(request, extra_headers=extra_headers)
        
        assert payload == {"param1": "value1"}
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
            "X-Custom": "custom_value",
        }

    def test_endpoint_create_payload_with_kwargs(self):
        """Test create_payload method with kwargs."""
        endpoint = Endpoint(
            config={
                "name": "test_endpoint",
                "provider": "test_provider",
                "endpoint": "test/endpoint",
                "api_key": "test_api_key",
            }
        )
        
        request = {"param1": "value1"}
        payload, headers = endpoint.create_payload(
            request,
            param2="value2",
            param3="value3",
        )
        
        assert payload == {
            "param1": "value1",
            "param2": "value2",
            "param3": "value3",
        }
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_api_key",
        }


def test_match_endpoint():
    """Test match_endpoint function."""
    endpoint = match_endpoint(
        provider="test_provider",
        endpoint="test/endpoint",
        base_url="https://api.example.com",
    )
    
    assert isinstance(endpoint, Endpoint)
    assert endpoint.config.name == "test_provider_test/endpoint"
    assert endpoint.config.provider == "test_provider"
    assert endpoint.config.endpoint == "test/endpoint"
    assert endpoint.config.base_url == "https://api.example.com"


class TestTokenBucketRateLimiter:
    """Tests for the TokenBucketRateLimiter class."""

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_init(self):
        """Test TokenBucketRateLimiter initialization."""
        limiter = TokenBucketRateLimiter(rate=10.0, period=1.0)
        
        assert limiter.rate == 10.0
        assert limiter.period == 1.0
        assert limiter.max_tokens == 10.0
        assert limiter.tokens == 10.0
        
        # Test with custom max_tokens and initial_tokens
        limiter = TokenBucketRateLimiter(
            rate=10.0,
            period=1.0,
            max_tokens=20.0,
            initial_tokens=5.0,
        )
        
        assert limiter.rate == 10.0
        assert limiter.period == 1.0
        assert limiter.max_tokens == 20.0
        assert limiter.tokens == 5.0

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_refill(self):
        """Test _refill method."""
        limiter = TokenBucketRateLimiter(rate=10.0, period=1.0, initial_tokens=0.0)
        
        # Manually set last_refill to simulate elapsed time
        limiter.last_refill = time.monotonic() - 0.5  # 0.5 seconds ago
        
        await limiter._refill()
        
        # Should have refilled 5 tokens (0.5 seconds * 10 tokens/second)
        assert limiter.tokens == pytest.approx(5.0, abs=0.01)
        
        # Refill again immediately should not add tokens
        old_tokens = limiter.tokens
        await limiter._refill()
        assert limiter.tokens == pytest.approx(old_tokens, abs=0.01)

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_acquire_available(self):
        """Test acquire method with available tokens."""
        limiter = TokenBucketRateLimiter(rate=10.0, period=1.0)
        
        # Acquire 5 tokens
        wait_time = await limiter.acquire(5.0)
        
        assert wait_time == 0.0  # No wait time
        assert limiter.tokens == 5.0  # 10 - 5 = 5 tokens left

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_acquire_not_available(self):
        """Test acquire method with not enough tokens."""
        limiter = TokenBucketRateLimiter(rate=10.0, period=1.0, initial_tokens=5.0)
        
        # Try to acquire 10 tokens
        wait_time = await limiter.acquire(10.0)
        
        assert wait_time > 0.0  # Should have wait time
        assert wait_time == pytest.approx(0.5, abs=0.01)  # (10 - 5) / 10 = 0.5 seconds

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_execute(self):
        """Test execute method."""
        limiter = TokenBucketRateLimiter(rate=10.0, period=1.0)
        
        # Create a mock async function
        mock_func = AsyncMock(return_value="success")
        
        # Execute with default token cost
        result = await limiter.execute(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        assert limiter.tokens == pytest.approx(9.0, abs=0.01)  # 10 - 1 = 9 tokens left
        
        # Execute with custom token cost
        result = await limiter.execute(
            mock_func,
            "arg2",
            kwarg2="value2",
            tokens=2.0,
        )
        
        assert result == "success"
        assert mock_func.call_count == 2
        assert limiter.tokens == pytest.approx(7.0, abs=0.02)  # 9 - 2 = 7 tokens left


class TestEndpointRateLimiter:
    """Tests for the EndpointRateLimiter class."""

    @pytest.mark.asyncio
    async def test_endpoint_rate_limiter_init(self):
        """Test EndpointRateLimiter initialization."""
        limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
        
        assert limiter.default_rate == 10.0
        assert limiter.default_period == 1.0
        assert limiter.limiters == {}

    @pytest.mark.asyncio
    async def test_endpoint_rate_limiter_get_limiter(self):
        """Test get_limiter method."""
        limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
        
        # Get limiter for an endpoint
        endpoint_limiter = limiter.get_limiter("test/endpoint")
        
        assert isinstance(endpoint_limiter, TokenBucketRateLimiter)
        assert endpoint_limiter.rate == 10.0
        assert endpoint_limiter.period == 1.0
        assert "test/endpoint" in limiter.limiters
        
        # Get the same limiter again
        endpoint_limiter2 = limiter.get_limiter("test/endpoint")
        
        assert endpoint_limiter2 is endpoint_limiter

    @pytest.mark.asyncio
    async def test_endpoint_rate_limiter_execute(self):
        """Test execute method."""
        limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
        
        # Create a mock async function
        mock_func = AsyncMock(return_value="success")
        
        # Execute for an endpoint
        result = await limiter.execute(
            "test/endpoint",
            mock_func,
            "arg1",
            kwarg1="value1",
        )
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        
        # The endpoint limiter should have been created and used
        assert "test/endpoint" in limiter.limiters
        endpoint_limiter = limiter.limiters["test/endpoint"]
        assert endpoint_limiter.tokens == 9.0  # 10 - 1 = 9 tokens left

    @pytest.mark.asyncio
    async def test_endpoint_rate_limiter_update_rate_limit(self):
        """Test update_rate_limit method."""
        limiter = EndpointRateLimiter(default_rate=10.0, default_period=1.0)
        
        # Get limiter for an endpoint
        endpoint_limiter = limiter.get_limiter("test/endpoint")
        
        # Update rate limit
        await limiter.update_rate_limit(
            "test/endpoint",
            rate=20.0,
            period=2.0,
            max_tokens=30.0,
        )
        
        assert endpoint_limiter.rate == 20.0
        assert endpoint_limiter.period == 2.0
        assert endpoint_limiter.max_tokens == 30.0
        
        # Update with reset_tokens
        await limiter.update_rate_limit(
            "test/endpoint",
            reset_tokens=True,
        )
        
        assert endpoint_limiter.tokens == endpoint_limiter.max_tokens
        
        # Update with rate reduction
        endpoint_limiter.tokens = 10.0
        await limiter.update_rate_limit(
            "test/endpoint",
            rate=10.0,  # Half the current rate
        )
        
        assert endpoint_limiter.tokens == 5.0  # Tokens should be reduced proportionally


class TestAdaptiveRateLimiter:
    """Tests for the AdaptiveRateLimiter class."""

    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_init(self):
        """Test AdaptiveRateLimiter initialization."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            initial_period=1.0,
            min_rate=1.0,
            safety_factor=0.9,
        )
        
        assert limiter.rate == 10.0
        assert limiter.period == 1.0
        assert limiter.min_rate == 1.0
        assert limiter.safety_factor == 0.9

    def test_adaptive_rate_limiter_update_from_headers(self):
        """Test update_from_headers method."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0, min_rate=0.1)  # Set min_rate lower than expected rate
        
        # Test with X-RateLimit headers
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "50",
            "X-RateLimit-Reset": "60",
        }
        
        limiter.update_from_headers(headers)
        
        # New rate should be (50 / 60) * 0.9 = 0.75
        assert limiter.rate == 0.75
        
        # Test with minimum rate
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "5",
            "X-RateLimit-Reset": "60",
        }
        
        limiter.update_from_headers(headers)
        
        # New rate would be (5 / 60) * 0.9 = 0.075, which is less than min_rate of 0.1
        assert limiter.rate == 0.1
        
        # Test with Retry-After header
        headers = {
            "Retry-After": "30",
        }
        
        limiter.update_from_headers(headers)
        
        # New rate would be (0 / 30) * 0.9 = 0, but min_rate is 0.1
        assert limiter.rate == 0.1
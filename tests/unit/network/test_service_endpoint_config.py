"""
Unit tests for the ServiceEndpointConfig model.
"""

import pytest

from lionfuncs.network.primitives import (
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
)


class TestServiceEndpointConfig:
    """Tests for the ServiceEndpointConfig model."""

    def test_http_transport_config_valid(self):
        """Test that a valid HTTP transport config passes validation."""
        config = ServiceEndpointConfig(
            name="test_http",
            transport_type="http",
            base_url="https://api.example.com",
            http_config=HttpTransportConfig(),
        )

        assert config.name == "test_http"
        assert config.transport_type == "http"
        assert config.base_url == "https://api.example.com"
        assert config.http_config is not None
        assert config.http_config.method == "POST"  # Default method
        assert config.sdk_config is None
        assert config.timeout == 60.0  # Default timeout
        assert config.default_headers == {}  # Default empty headers
        assert config.client_kwargs == {}  # Default empty kwargs
        assert config.default_request_kwargs == {}  # Default empty request kwargs

    def test_http_transport_config_missing_base_url(self):
        """Test that HTTP transport config without base_url fails validation."""
        with pytest.raises(
            ValueError, match="base_url must be provided for HTTP transport type"
        ):
            ServiceEndpointConfig(
                name="test_http",
                transport_type="http",
                http_config=HttpTransportConfig(),
            )

    def test_sdk_transport_config_valid(self):
        """Test that a valid SDK transport config passes validation."""
        config = ServiceEndpointConfig(
            name="test_sdk",
            transport_type="sdk",
            api_key="test_api_key",
            sdk_config=SdkTransportConfig(sdk_provider_name="openai"),
        )

        assert config.name == "test_sdk"
        assert config.transport_type == "sdk"
        assert config.api_key == "test_api_key"
        assert config.sdk_config is not None
        assert config.sdk_config.sdk_provider_name == "openai"
        assert config.sdk_config.default_sdk_method_name is None
        assert config.http_config is None
        assert config.timeout == 60.0  # Default timeout
        assert config.default_headers == {}  # Default empty headers
        assert config.client_kwargs == {}  # Default empty kwargs
        assert config.default_request_kwargs == {}  # Default empty request kwargs

    def test_sdk_transport_config_missing_sdk_config(self):
        """Test that SDK transport config without sdk_config fails validation."""
        with pytest.raises(
            ValueError, match="sdk_config must be provided for SDK transport type"
        ):
            ServiceEndpointConfig(
                name="test_sdk", transport_type="sdk", api_key="test_api_key"
            )

    def test_sdk_transport_config_with_default_method(self):
        """Test SDK transport config with default_sdk_method_name."""
        config = ServiceEndpointConfig(
            name="test_sdk",
            transport_type="sdk",
            api_key="test_api_key",
            sdk_config=SdkTransportConfig(
                sdk_provider_name="openai",
                default_sdk_method_name="chat.completions.create",
            ),
        )

        assert config.sdk_config.default_sdk_method_name == "chat.completions.create"

    def test_with_custom_timeout(self):
        """Test config with custom timeout."""
        config = ServiceEndpointConfig(
            name="test_http",
            transport_type="http",
            base_url="https://api.example.com",
            timeout=120.0,
        )

        assert config.timeout == 120.0

    def test_with_custom_headers(self):
        """Test config with custom headers."""
        custom_headers = {"X-Custom-Header": "value"}
        config = ServiceEndpointConfig(
            name="test_http",
            transport_type="http",
            base_url="https://api.example.com",
            default_headers=custom_headers,
        )

        assert config.default_headers == custom_headers

    def test_with_client_kwargs(self):
        """Test config with client_kwargs."""
        constructor_kwargs = {"follow_redirects": True}
        config = ServiceEndpointConfig(
            name="test_http",
            transport_type="http",
            base_url="https://api.example.com",
            client_kwargs=constructor_kwargs,
        )

        assert config.client_kwargs == constructor_kwargs

    def test_with_default_request_kwargs(self):
        """Test config with default_request_kwargs."""
        request_kwargs = {"model": "gpt-4"}
        config = ServiceEndpointConfig(
            name="test_http",
            transport_type="http",
            base_url="https://api.example.com",
            default_request_kwargs=request_kwargs,
        )

        assert config.default_request_kwargs == request_kwargs

    def test_invalid_transport_type(self):
        """Test that an invalid transport_type fails validation."""
        with pytest.raises(ValueError):  # Pydantic V2 validates at init time
            # We need to use a different approach since Pydantic V2 validates at init time
            ServiceEndpointConfig(
                name="test_invalid",
                transport_type="invalid",  # Not "http" or "sdk"
                base_url="https://api.example.com",
            )

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):  # Changed from ValidationError to ValueError
            # We need to use a different approach since Pydantic V2 validates at init time
            # Create a dict with extra fields
            config_dict = {
                "name": "test_http",
                "transport_type": "http",
                "base_url": "https://api.example.com",
                "invalid_field": "value",  # This field is not defined in the model
            }
            # Pass the dict to the model constructor
            ServiceEndpointConfig(**config_dict)

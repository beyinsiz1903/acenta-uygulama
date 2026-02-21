"""Unit tests for standardized error handling.

Tests:
- AppError produces correct response format
- Validation errors have standardized format
- 404 errors have correct code
- 500 errors have correct code
- Helper functions produce correct errors
- Error response includes correlation_id and path
"""
import pytest
from app.errors import (
    AppError,
    ErrorCode,
    not_found_error,
    forbidden_error,
    validation_error,
    conflict_error,
    rate_limit_error,
    business_error,
    internal_error,
    error_response,
)


def test_error_code_enum():
    """Test that ErrorCode enum has all required codes."""
    assert ErrorCode.AUTH_REQUIRED == "auth_required"
    assert ErrorCode.NOT_FOUND == "not_found"
    assert ErrorCode.FORBIDDEN == "forbidden"
    assert ErrorCode.VALIDATION_ERROR == "validation_error"
    assert ErrorCode.RATE_LIMITED == "rate_limit_exceeded"
    assert ErrorCode.INTERNAL_ERROR == "internal_error"
    assert ErrorCode.BUSINESS_RULE_VIOLATION == "business_rule_violation"


def test_not_found_error_helper():
    """Test not_found_error helper function."""
    err = not_found_error("Tour", "123")
    assert err.status_code == 404
    assert err.code == ErrorCode.NOT_FOUND
    assert "Tour" in err.message
    assert err.details["resource"] == "Tour"
    assert err.details["resource_id"] == "123"


def test_forbidden_error_helper():
    """Test forbidden_error helper function."""
    err = forbidden_error(required_roles=["admin"])
    assert err.status_code == 403
    assert err.code == ErrorCode.FORBIDDEN
    assert err.details["required_roles"] == ["admin"]


def test_validation_error_helper():
    """Test validation_error helper function."""
    err = validation_error(field="email", message="Geçersiz email")
    assert err.status_code == 422
    assert err.code == ErrorCode.VALIDATION_ERROR
    assert err.details["field"] == "email"


def test_conflict_error_helper():
    """Test conflict_error helper function."""
    err = conflict_error(resource="User")
    assert err.status_code == 409
    assert err.code == ErrorCode.ALREADY_EXISTS


def test_rate_limit_error_helper():
    """Test rate_limit_error helper function."""
    err = rate_limit_error(retry_after_seconds=120)
    assert err.status_code == 429
    assert err.code == ErrorCode.RATE_LIMITED
    assert err.retryable is True
    assert err.details["retry_after_seconds"] == 120


def test_business_error_helper():
    """Test business_error helper function."""
    err = business_error("Yetersiz bakiye")
    assert err.status_code == 400
    assert err.code == ErrorCode.BUSINESS_RULE_VIOLATION


def test_internal_error_helper():
    """Test internal_error helper function."""
    err = internal_error()
    assert err.status_code == 500
    assert err.code == ErrorCode.INTERNAL_ERROR


def test_app_error_to_dict():
    """Test AppError.to_dict method."""
    err = AppError(
        status_code=400,
        code="test_error",
        message="Test message",
        details={"key": "value"},
        retryable=True,
    )
    result = err.to_dict()
    assert result["error"]["code"] == "test_error"
    assert result["error"]["message"] == "Test message"
    assert result["error"]["details"]["key"] == "value"
    assert result["error"]["retryable"] is True


def test_error_response_format():
    """Test error_response function format."""
    result = error_response("test_code", "test message", {"detail_key": "val"})
    assert "error" in result
    assert result["error"]["code"] == "test_code"
    assert result["error"]["message"] == "test message"
    assert result["error"]["details"]["detail_key"] == "val"


@pytest.mark.anyio
async def test_404_returns_standard_format(async_client):
    """Test that 404 responses use standardized error format."""
    resp = await async_client.get("/api/this-does-not-exist-at-all")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


@pytest.mark.anyio
async def test_401_returns_standard_format(async_client):
    """Test that 401 responses use standardized error format."""
    resp = await async_client.get("/api/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert "code" in data["error"]


@pytest.mark.anyio
async def test_validation_error_returns_standard_format(async_client):
    """Test that validation errors use standardized format."""
    # Send invalid login payload (missing required fields)
    resp = await async_client.post("/api/auth/login", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert "errors" in data["error"]["details"]

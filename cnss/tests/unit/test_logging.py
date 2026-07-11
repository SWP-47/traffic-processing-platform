# ==============================================================================
# CnSS Logging and Compatibility Patch Unit Tests
# Validates custom TokenMaskingFilter security sanitization logic
# and the python 3.13 LogRecord monkey patch for formatting coercion.
# ==============================================================================

import logging

import pytest

from core.logging import TokenMaskingFilter, setup_logging


def test_token_masking_filter_message_redaction():
    """
    Architecture §5.3: Ensure TokenMaskingFilter intercepts log records
    and replaces sensitive token parameters in the log msg string.
    """
    filt = TokenMaskingFilter()

    # 1. URL with token as first param
    record = logging.LogRecord(
        "test",
        logging.INFO,
        "src",
        10,
        "GET /api/v1/auth/refresh?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        (),
        None,
    )
    assert filt.filter(record)
    assert record.msg == "GET /api/v1/auth/refresh?token=[REDACTED]"

    # 2. URL with token as subsequent param
    record2 = logging.LogRecord(
        "test", logging.INFO, "src", 10, "GET /api/v1/channels?active=true&token=abcdef123", (), None
    )
    assert filt.filter(record2)
    assert record2.msg == "GET /api/v1/channels?active=true&token=[REDACTED]"

    # 3. URL without token parameter (should not change)
    msg_no_token = "GET /api/v1/channels?active=true"
    record3 = logging.LogRecord("test", logging.INFO, "src", 10, msg_no_token, (), None)
    assert filt.filter(record3)
    assert record3.msg == msg_no_token


def test_token_masking_filter_args_redaction():
    """
    Architecture §5.3: Verify TokenMaskingFilter handles tuple and dict args formatting.
    """
    filt = TokenMaskingFilter()

    # Log record with tuple args containing token string
    record_tuple = logging.LogRecord("test", logging.INFO, "src", 10, "Access token: %s", ("?token=eyJhbGciOi",), None)
    assert filt.filter(record_tuple)
    assert record_tuple.args == ("?token=[REDACTED]",)

    # Log record with dict args containing token string
    record_dict = logging.LogRecord("test", logging.INFO, "src", 10, "User %(user)s accessed with %(token)s", (), None)
    record_dict.args = {"user": "test-user", "token": "?token=abcdefg"}
    assert filt.filter(record_dict)
    assert record_dict.args == {"user": "test-user", "token": "?token=[REDACTED]"}


def test_logging_patch_format_coercion():
    """
    Ensure the Python logging monkey patch for format string type coercion (TypeError in 3.13+)
    intercepts integer formatting TypeError and successfully coerces string parameters to integers.
    """
    # Create a dummy LogRecord with a format mismatch (%d formatting a string)
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="src.py",
        lineno=42,
        msg="Format error number: %d",
        args=("123",),  # String instead of int
        exc_info=None,
    )

    # Calling getMessage should pass without raise, converting '123' to 123
    msg = record.getMessage()
    assert msg == "Format error number: 123"
    assert record.args == (123,)


def test_logging_patch_unrelated_type_error_propagation():
    """
    Ensure the patched LogRecord.getMessage raises TypeError if the error is unrelated
    to integer formatting (e.g. incompatible arguments or other TypeErrors).
    """
    # Format string type mismatch of float conversion or complex type
    with pytest.raises(TypeError) as exc:
        record2 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="src.py",
            lineno=42,
            msg="Expected float: %f",
            args=("not-a-float",),  # Should raise TypeError: %f format: a real number is required, not str
            exc_info=None,
        )
        record2.getMessage()
    assert exc.value is not None


def test_logging_patch_conversion_failure():
    """
    Verify that if a string argument cannot be coerced to an integer (ValueError is raised),
    the patch keeps the original value and allows getMessage to raise the expected TypeError.
    """
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="src.py",
        lineno=42,
        msg="Format error: %d",
        args=("not-an-integer",),
        exc_info=None,
    )
    with pytest.raises(TypeError):
        record.getMessage()


def test_setup_logging_runs():
    """
    Verify setup_logging functions cleanly without raising exceptions.
    """
    setup_logging()

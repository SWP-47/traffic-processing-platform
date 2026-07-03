# ==============================================================================
# Python Logging Compatibility Patch
# Patches logging.LogRecord.getMessage to tolerate string arguments for %d/%x formats.
# This is a workaround for libraries (passlib, uvicorn) that pass strings
# instead of numbers, which causes TypeError in Python 3.13+.
# ==============================================================================

import logging
import sys
from typing import Any


def _install_logging_patch() -> None:
    """
    Monkey-patches logging.LogRecord.getMessage to coerce strings to numbers
    for integer format specifiers (%d, %x, %o, %i, %u).
    """
    if sys.version_info < (3, 13):
        return  # No patch needed for older Python versions

    # Save the original getMessage method
    original_get_message = logging.LogRecord.getMessage

    def _patched_get_message(self: logging.LogRecord) -> str:
        """
        Wrapped getMessage method that catches TypeError from %d/%x formatting
        and coerces string arguments to integers before retrying.
        """
        try:
            return original_get_message(self)
        except TypeError as e:
            # Only patch known format errors
            error_msg = str(e)
            if "format:" not in error_msg:
                raise

            # Check if it's an integer format error (%d, %x, %o, %i, %u)
            if "integer" not in error_msg and "real number" not in error_msg:
                raise

            # Coerce string arguments to integers where possible
            if isinstance(self.args, tuple):
                new_args: list[Any] = []
                for arg in self.args:
                    if isinstance(arg, str):
                        try:
                            # Try to convert to int
                            new_args.append(int(arg))
                        except (ValueError, TypeError):
                            # If conversion fails, keep original value
                            new_args.append(int(arg))
                    else:
                        new_args.append(arg)
                self.args = tuple(new_args)

            # Retry formatting with corrected arguments
            return original_get_message(self)

    # Apply the patch to the instance method
    setattr(logging.LogRecord, "getMessage", _patched_get_message)


# Auto-install on import
_install_logging_patch()

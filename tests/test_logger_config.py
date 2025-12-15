"""
Tests for setup_logger in logger_config.

Author: Emily Amies
Group: 4

Covers validation of:
- logger name
- stream and file logging levels
- maxBytes argument
- backupCount argument
"""

import pytest

from parkVar.utils import logger_config as log_setup


class TestSetupLoggerValidation:
    """Tests for setup_logger"""

    def test_name_must_be_string(self):
        """setup_logger raises TypeError if name is not a string."""

        # Name must strictly be a string
        with pytest.raises(TypeError):
            log_setup.setup_logger(name=123)

        with pytest.raises(TypeError):
            log_setup.setup_logger(name=None)

    @pytest.mark.parametrize("stream_level", ["abc", None, 15, -1, 999])
    def test_invalid_stream_levels(self, stream_level):
        """setup_logger raises ValueError for invalid stream_level values."""

        # Stream level must be one of the valid logging levels
        with pytest.raises(ValueError):
            log_setup.setup_logger(name="x", stream_level=stream_level)

    @pytest.mark.parametrize("file_level", ["abc", None, 17, -20, 123])
    def test_invalid_file_levels(self, file_level):
        """setup_logger raises ValueError for invalid file_level values."""
        # File level must be one of the valid logging levels
        with pytest.raises(ValueError):
            log_setup.setup_logger(name="x", file_level=file_level)

    @pytest.mark.parametrize("maxbytes", ["abc", None, 0, -1, -500])
    def test_invalid_maxbytes(self, maxbytes):
        """setup_logger raises ValueError when maxBytes is not a positive
        integer."""
        # maxBytes must be a positive integer
        with pytest.raises(ValueError):
            log_setup.setup_logger(name="x", maxBytes=maxbytes)

    @pytest.mark.parametrize("backupcount", ["abc", None, -1, -3])
    def test_invalid_backupcount(self, backupcount):
        """setup_logger raises ValueError when backupCount is negative or
        invalid."""

        # backupCount must be a non negative integer
        with pytest.raises(ValueError):
            log_setup.setup_logger(name="x", backupCount=backupcount)

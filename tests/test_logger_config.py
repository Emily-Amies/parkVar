import pytest
from parkVar.utils import logger_config as log_setup

class TestSetupLoggerValidation:

    def test_name_must_be_string(self):
        # Name must strictly be a string
        with pytest.raises(TypeError):
            log_setup.setup_logger(name=123)

        with pytest.raises(TypeError):
            log_setup.setup_logger(name=None)

    @pytest.mark.parametrize('stream_level', ['abc', None, 15, -1, 999])
    def test_invalid_stream_levels(self, stream_level):
        # Stream level must be one of the valid logging levels
        with pytest.raises(ValueError):
            log_setup.setup_logger(name='x', stream_level=stream_level)

    @pytest.mark.parametrize('file_level', ['abc', None, 17, -20, 123])
    def test_invalid_file_levels(self, file_level):
        # File level must be one of the valid logging levels
        with pytest.raises(ValueError):
            log_setup.setup_logger(name='x', file_level=file_level)

    @pytest.mark.parametrize('maxbytes', ['abc', None, 0, -1, -500])
    def test_invalid_maxbytes(self, maxbytes):
        # maxBytes must be a positive integer
        with pytest.raises(ValueError):
            log_setup.setup_logger(name='x', maxBytes=maxbytes)

    @pytest.mark.parametrize('backupcount', ['abc', None, -1, -3])
    def test_invalid_backupcount(self, backupcount):
        # backupCount must be a non negative integer
        with pytest.raises(ValueError):
            log_setup.setup_logger(name='x', backupCount=backupcount)
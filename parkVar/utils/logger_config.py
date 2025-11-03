import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name, 
                 level = 10,
                 maxBytes = 500000,
                 backupCount = 2):
    '''
    Creates and congifures a logger. 
    Formats output and sets level (default = INFO).
    Writes to stderr and a rotating log file.

    Parameters
    -----------
    name: str 
        Name for the logger
    level: int, optional 
        Minimum level of output. 
            50 = CRITICAL
            40 = ERROR
            30 = WARNING
            20 = INFO
            10 = DEBUG
            0  = NOTSET
    maxBytes: int, optional
        Maximum file size for rotating file.
    backupCount: int, optional 
        Maximum number of backup log files.

    Returns
    ----------
    logging.logger
        Configured logger object.
    '''

    # Check parameters
    valid_levels = {50, 40, 30, 20, 10, 0}

    if not isinstance(name, str):
        raise TypeError('name must be a string')

    if level not in valid_levels:
        raise ValueError(f'level must be one of {sorted(valid_levels)}, got {level}')

    if not isinstance(maxBytes, int) or maxBytes <= 0:
        raise ValueError('maxBytes must be a positive integer')

    if not isinstance(backupCount, int) or backupCount < 0:
        raise ValueError('backupCount must be a non-negative integer')
    
    # Path to the logs directory
    log_dir = str(Path(__file__).resolve().parent.parent.parent) + '/logs/'
    log_file = f'{log_dir}/{name}.log'
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Add stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Add file handler
    file_handler = RotatingFileHandler(filename = log_file,
                                       maxBytes = maxBytes,  # 500 KB
                                       backupCount = backupCount)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger('parkVar_logger')

"""
Logging configuration for the parkVar application.

This module provides a helper to create a logger with:
- a rotating file handler
- a stream (stderr) handler
- consistent formatting across all modules

The default logger created at import time is `parkVar_logger`.

Author: Emily Amies
Group: 4

Notes:
- Log files are stored in the project-level 'logs' directory.
- Rotation behaviour is controlled using maxBytes and backupCount.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name, file_level=10, stream_level=10, maxBytes=500000, backupCount=2
):
    """
    Create and configure a logger with rotating file output and stderr output.

    Parameters
    ----------
    name : str
        Name for the logger (also used as the logfile name).
    file_level : int, optional
        Logging threshold for the file handler.
    stream_level : int, optional
        Logging threshold for the stream handler.
    maxBytes : int, optional
        Maximum size (bytes) before log rotation occurs.
    backupCount : int, optional
        Number of rotated log files to keep.

    Returns
    -------
    logging.Logger
        Configured logger instance.

    Raises
    ------
    TypeError
        If `name` is not a string.
    ValueError
        If provided levels or parameters are invalid.
    """

    # Check parameters
    valid_levels = {50, 40, 30, 20, 10, 0}

    if not isinstance(name, str):
        raise TypeError("name must be a string")

    for level in (stream_level, file_level):
        if level not in valid_levels:
            raise ValueError(
                f"level must be one of {sorted(valid_levels)}, got {level}"
            )

    if not isinstance(maxBytes, int) or maxBytes <= 0:
        raise ValueError("maxBytes must be a positive integer")

    if not isinstance(backupCount, int) or backupCount < 0:
        raise ValueError("backupCount must be a non-negative integer")

    # Path to the logs directory
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = f"{log_dir}/{name}.log"

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(file_level)

    # Add stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Add file handler
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=maxBytes,  # 500 KB
        backupCount=backupCount,
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger("parkVar_logger",file_level=20, stream_level=30)

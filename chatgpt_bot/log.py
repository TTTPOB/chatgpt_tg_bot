import logging
from sys import stderr

level = "INFO"

def get_logger() -> logging.Logger:
    logger = logging.getLogger(__package__)
    handler = logging.StreamHandler(stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger

level_map = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL, 
}

__all__ = ["get_logger", "level"]
import logging
from sys import stderr

def get_logger(name: str, output_level: str):
    # set up a logger which output to stderr
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(stderr)
    handler.setLevel(output_level.upper())

    formartter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formartter)
    logger.addHandler(handler)
    return logger

def log(level: str, message: str, logger: logging.Logger):
    if level == "debug":
        logger.debug(message)
    elif level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    elif level == "critical":
        logger.critical(message)
    else:
        print(message, file=stderr)
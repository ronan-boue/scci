import os
import sys
import logging

LOGGING_FORMAT = '%(asctime)s %(levelname)7s [%(filename)20s:%(lineno)4s - %(name)s.%(funcName)s()] %(message)s'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', logging.INFO)
LOGGING_FILENAME = 'app.log'
LOGGING_STDOUT = True

LOGGING_FILENAME = os.getenv('LOGGING_FILENAME', LOGGING_FILENAME)

if len(LOGGING_FILENAME) > 0:
    logging.basicConfig(filename=LOGGING_FILENAME, datefmt=DATE_FORMAT,
                        filemode='a', format=LOGGING_FORMAT, force=False)
else:
    logging.basicConfig(format=LOGGING_FORMAT, datefmt=DATE_FORMAT, force=False)

# -------------------------------------------------------------------------------------------------
#
def get_logger(name, level=LOGGING_LEVEL):
    logger = logging.getLogger(name)
    if LOGGING_STDOUT:
        logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(level)
    return logger

# -------------------------------------------------------------------------------------------------
#
def set_log_filename(filename):
    global LOGGING_FILENAME
    LOGGING_FILENAME = filename
    logging.basicConfig(filename=LOGGING_FILENAME, datefmt=DATE_FORMAT,
                        filemode='a', format=LOGGING_FORMAT, force=True)

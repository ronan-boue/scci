'''
This app is used to test call to direct method on ZEPPELIN module.
'''
# Do this first !
import sys
import os

# Add parent directory to Python path to resolve imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.logger import get_logger, set_log_filename, LOGGING_LEVEL
import time

LOGGING_FILENAME = 'test-c2e.log'
set_log_filename(LOGGING_FILENAME)
logger = get_logger('Publisher', LOGGING_LEVEL)


os.environ["CONFIG_FILENAME"] = "../../config/test/test-zeppelin-v3.json"
os.environ["IOTHUB_CONNECTION_STRING"] = "HostName=iotrcidev01.azure-devices.net;SharedAccessKeyName=testCloud2Device;SharedAccessKey=E7UF2WUysOOkd1E5NK9Noe3hzCH6Tet3uAIoTLOFQ5U="

from zeppelin import Zeppelin

# -----------------------------------------------------------------------------
#
def main():
    try:


        z = Zeppelin()
        if not z.init():
            exit(1)

        z.start()
        time.sleep(0)


    except Exception as e:
        logger.error(str(e))

# -----------------------------------------------------------------------------
#
if __name__ == '__main__':
    main()

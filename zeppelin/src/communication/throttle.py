import time
from threading import Lock
from utils.logger import get_logger

logger = get_logger('Throttle')

# -----------------------------------------------------------------------------
#
class Throttle:
	# -------------------------------------------------------------------------
	#
    def __init__(self, max_msg_sec = 10, sleep_sec = 1.0) -> None:
        self.max_msg_sec = max_msg_sec
        self.sleep_sec = sleep_sec
        self._counter = 0
        self._last_time = int(time.time())
        self._mutex = Lock()

    # -------------------------------------------------------------------------
    def set_max_msg_sec(self, max_msg_sec):
        try:
            logger.info(f'Set max_msg_sec({max_msg_sec})')
            self._mutex.acquire()
            self.max_msg_sec = max_msg_sec

        finally:
            self._mutex.release()

    # -------------------------------------------------------------------------
    def set_sleep_sec(self, sleep_sec):
        try:
            logger.info(f'Set sleep_sec({sleep_sec})')
            self._mutex.acquire()
            self.sleep_sec = sleep_sec

        finally:
            self._mutex.release()

    # -------------------------------------------------------------------------
    def throttle(self) -> bool:
        try:
            self._mutex.acquire()

            now = int(time.time())

            if now != self._last_time:
                self._counter = 1
                self._last_time = now
                return False

            self._counter += 1

            if self._counter < self.max_msg_sec:
                return False

            logger.warning(f'Throttle: Sleeping for {self.sleep_sec} seconds. counter({self._counter}) max_msg_sec({self.max_msg_sec})')
            time.sleep(self.sleep_sec)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

        finally:
            self._mutex.release()

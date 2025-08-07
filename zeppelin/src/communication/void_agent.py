import os

from .communication_interface import CommunicationInterface
from .throttle import Throttle

# -----------------------------------------------------------------------------
#
class VoidAgent(CommunicationInterface, Throttle):

    # -------------------------------------------------------------------------
    #
    def publish(self, topic, payload) -> bool:
        return True

    # -------------------------------------------------------------------------
    #
    def start_listening(self, topic, queue) -> bool :
        return True

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        pass

    # -------------------------------------------------------------------------
    #
    def set_metrics(self, metrics):
        pass

    # -------------------------------------------------------------------------
    #
    def set_max_msg_sec(self, max_msg_sec):
        Throttle.set_max_msg_sec(self, max_msg_sec)

    # -------------------------------------------------------------------------
    #
    def set_sleep_sec(self, sleep_sec):
        Throttle.set_sleep_sec(self, sleep_sec)

	# -------------------------------------------------------------------------
	#
    def get_device_id(self):
        try:
            return os.getenv('IOTEDGE_DEVICEID', '')
        except Exception as ex:
            return ''


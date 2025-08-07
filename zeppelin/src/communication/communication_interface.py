from abc import ABC, abstractmethod

from utils.logger import get_logger

logger = get_logger('CommunicationInterface')

# -------------------------------------------------------------------------------------------------
#
class ConnectionException(Exception):
    pass

# -----------------------------------------------------------------------------
#
class CommunicationInterface(ABC):
    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def publish(self, topic, payload) -> bool:
        pass

    # -------------------------------------------------------------------------
    # Set topic to None if you need to listen on all topics
    @abstractmethod
    def start_listening(self, topic, queue) -> bool:
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def disconnect(self):
        pass

    # -------------------------------------------------------------------------
    # Override this method to handle the task in the derived class
    # This method is called in the main thread and should not block
    def handle_task(self):
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def set_metrics(self, metrics):
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def get_device_id(self):
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def set_max_msg_sec(self, max_msg_sec):
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def set_sleep_sec(self, sleep_sec):
        pass
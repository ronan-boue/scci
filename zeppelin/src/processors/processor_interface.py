from abc import ABC, abstractmethod

# -----------------------------------------------------------------------------
#
class ProcessorInterface(ABC):
    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def init(self, config, source, metrics) -> bool:
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def assess(self) -> bool:
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def validate(self) -> bool:
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def normalize(self) -> bool:
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def get_device_model(self):
        pass

    # -------------------------------------------------------------------------
    #
    @abstractmethod
    def get_data(self):
        pass

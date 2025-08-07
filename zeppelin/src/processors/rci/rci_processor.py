from utils.logger import get_logger, LOGGING_LEVEL
from ..base_processor import BaseProcessor

logger = get_logger("RCIProcessor", LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class RCIProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics) -> bool:
        self.values = None

        if not BaseProcessor.init(self, config, source, metrics):
            return False

        logger.debug("RCIProcessor initialized")

        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_rci_message_total.inc()

            # RCI messages don't have a CloudEvent, so, don't try to check it

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def validate(self) -> bool:
        try:
            if not BaseProcessor.validate(self):
                return False

            valid = True
            if type(self.data) is not dict:
                logger.error("RCI data is not a dictionary")
                valid = False
            else:
                for key, value in self.data.items():
                    if not type(value) in [float, int]:
                        logger.error(f"RCI data({key}) is not a number: value({value})")
                        # valid = False
                        self.metrics.rx_message_invalid.inc()

            return valid

        except Exception as ex:
            logger.error(ex)
            return False

from utils.logger import get_logger, LOGGING_LEVEL
from .base_processor import BaseProcessor

logger = get_logger('EgaugeProcessor', LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class EgaugeProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, source, metrics):
            return False
        logger.debug('EgaugeProcessor initialized')
        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_egauge_message_total.inc()

            if not BaseProcessor.assess(self):
                return False

            self.device_model = 'egauge'

            logger.info(f'device_model({self.device_model})')

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

            device = self.data.get('device', None)
            if device == None:
                logger.error(f'invalid device({device})')
                return False

            self.values = self.data.get('values', None)
            if self.values == None:
                logger.error(f'invalid values({self.values})')
                return False

            if not BaseProcessor.check_values(self, self.values):
                return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def normalize(self) -> bool:
        return BaseProcessor.normalize(self)

    # -------------------------------------------------------------------------
    #
    def get_data(self):
        return BaseProcessor.get_data(self)


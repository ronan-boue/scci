from utils.logger import get_logger, LOGGING_LEVEL
from ..base_processor import BaseProcessor

logger = get_logger("IBRProcessor", LOGGING_LEVEL)

VALID_DATA_TYPES = [
    "ca.qc.hydro.iot.ibr.egauge",
    "ca.qc.hydro.iot.ibr.insighthome",
    "ca.qc.hydro.iot.ibr.predictivecontrol",
    "ca.qc.hydro.iot.ibr.outage",
    "ca.qc.hydro.iot.ibr.drift",
    "ca.qc.hydro.iot.ibr.optimize",
]

# -----------------------------------------------------------------------------
#
class IBRProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, source, metrics):
            return False
        logger.debug("IBRProcessor initialized")
        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_ibr_message_total.inc()

            if not BaseProcessor.assess(self):
                return False

            self.data_type = self.payload.get("type", None)

            if self.data_type == None or self.data_type not in VALID_DATA_TYPES:
                logger.error(f"invalid data type({self.data_type})")
                return False

            if 'egauge' in self.data_type:
                self.device_model = 'eGauge'
            elif 'insighthome' in self.data_type:
                self.device_model = 'InsightHome'
            else:
                self.device_model = ''

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

    # -------------------------------------------------------------------------
    #
    def _get_cloud_event(self, cloud_event, data) -> object:
        try:
            cloud_event = BaseProcessor._get_cloud_event(self, cloud_event, data)

            cloud_event['type'] = self.payload.get('type', cloud_event['type'])

            return cloud_event

        except Exception as ex:
            logger.error(ex)
            return cloud_event


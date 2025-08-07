import copy
from utils.logger import get_logger, LOGGING_LEVEL
from ..base_processor import BaseProcessor

logger = get_logger('GDPProcessor', LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class GDPProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, source, metrics):
            return False
        logger.debug('GDPProcessor initialized')
        return True

    # -------------------------------------------------------------------------
    # Process received message from broker
    def _on_message_received(self, message) -> None:
        try:
            self.payload = message["payload"]
            payload_size = message["size"]

            if (payload_size > self.max_payload_size_bytes and self.max_payload_size_bytes > 0):
                src_topic = message["topic"]
                logger.error(
                    f"payload size({payload_size}) exceeds max_payload_size_bytes({self.max_payload_size_bytes}) from topic({src_topic}) payload(%.300s)",
                    self.payload,
                )
                self.metrics.rx_message_invalid.inc()
                self.metrics.rx_message_over_size.inc()
                return

            self.compressed =  self.payload.get('compressed', False)
            self.is_base64 = 'data_base64' in self.payload

            if not self.assess():
                self.metrics.rx_message_invalid.inc()
                return

            if not self.validate():
                self.metrics.rx_message_invalid.inc()
                return False

            if not self.normalize():
                self.metrics.rx_message_invalid.inc()
                return False

            # we publish original data without the provided cloud_event
            payload = copy.deepcopy(self.payload)
            pub_data = payload.get("data", None)

            if pub_data != None:
                self.metrics.rx_message_valid.inc()

                if self._publish_payload(self.dest_topic, pub_data):
                    self.metrics.tx_message_total.inc()

            else:
                self.metrics.rx_message_error.inc()

        except Exception as ex:
            self.metrics.rx_message_error.inc()
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def _publish_payload(self, topic, data) -> bool:
        try:

            logger.info(f"topic({topic}) payload({data})")

            self.dst_broker.publish(topic, data, retain = True)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_gdp_message_total.inc()

            return BaseProcessor.assess(self)

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def validate(self) -> bool:
        try:
            return BaseProcessor.validate(self)

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


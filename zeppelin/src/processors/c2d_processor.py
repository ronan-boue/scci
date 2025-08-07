import copy

from utils.logger import get_logger, LOGGING_LEVEL
from .base_processor import BaseProcessor
from metrics import Metrics

logger = get_logger("C2DProcessor", LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class C2DProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics: Metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, source, metrics):
            return False
        logger.debug("C2DProcessor initialized")
        return True

    # -------------------------------------------------------------------------
    # Process received message from broker
    def _on_message_received(self, message) -> None:
        try:
            self.payload = message["payload"]
            payload_size = message["size"]
            props = message.get("props", None)
            topic = message.get("topic", None)

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

            if props != None:
                logger.info(f"props({props})")

            if not self.assess():
                self.metrics.rx_message_invalid.inc()
                return

            if not self.validate():
                self.metrics.rx_message_invalid.inc()
                return False

            if not self.normalize():
                self.metrics.rx_message_invalid.inc()
                return False

            # we publish original data with the provided cloud_event
            pub_data = copy.deepcopy(self.payload)

            dest_topic = self.dest_topic

            # Overwrite default dest topic with provided topic
            if props != None and 'dest_topic' in props:
                dest_topic = props['dest_topic']

            # Overwrite dest topic with provided topic in cloud event if available
            if 'dest_topic' in self.payload:
                dt = self.payload.get('dest_topic', None)
                if dt != None and len(dt) > 0:
                    dest_topic = dt

            if pub_data != None and dest_topic != None and len(dest_topic) > 0:
                self.metrics.rx_message_valid.inc()

                if self._publish_payload(dest_topic, pub_data):
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

            logger.info(f"topic({topic}) payload(%.300s)", data)

            self.dst_broker.publish(topic, data)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_c2d_message_total.inc()

            if not BaseProcessor.assess(self):
                return False

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

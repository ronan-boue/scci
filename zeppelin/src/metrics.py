'''
Expose Prometheus metrics from Zeppelin module
'''

from threading import Thread, Lock
from prometheus_client import Counter, Info

from utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('Metrics', LOGGING_LEVEL)


# -----------------------------------------------------------------------------
# Call inc_counter() to increment the counter
# inc_counter() is thread safe
class Metrics:

    # -------------------------------------------------------------------------
    #
    def __init__(self):
        logger.info("constructor called")

        self.mutex = Lock()

        self.version = Info('zeppelin_version', 'Zeppelin version information')
        self.rx_message_total = Counter('zeppelin_rx_message_total', 'Total received message from Broker')
        self.rx_message_over_size = Counter('zeppelin_rx_message_over_size', 'Total received message with payload size exceeding maximum size from Broker')
        self.rx_message_discarded = Counter('zeppelin_rx_message_discarded', 'Total received message discarded from Broker')
        self.rx_message_error = Counter('zeppelin_rx_message_error', 'Total received message with processing error from Broker')
        self.rx_message_valid = Counter('zeppelin_rx_message_valid', 'Total received message valid from Broker')
        self.rx_message_invalid = Counter('zeppelin_rx_message_invalid', 'Total received message invalid from Broker')
        self.tx_message_total = Counter('zeppelin_tx_message_total', 'Total sent message to Broker')
        self.throttle_total = Counter('zeppelin_throttle_total', 'Total throttle applied to received message from Broker')
        self.rx_zigbee_message_total = Counter('zeppelin_rx_zigbee_message_total', 'Total Zigbee received message from Broker')
        self.rx_egauge_message_total = Counter('zeppelin_rx_egauge_message_total', 'Total eGauge received message from Broker')
        self.rx_c2d_message_total = Counter('zeppelin_rx_c2d_message_total', 'Total Cloud to Device received message from Broker')
        self.rx_gdp_message_total = Counter('zeppelin_rx_gdp_message_total', 'Total GDP received message from Broker')
        self.rx_ibr_message_total = Counter('zeppelin_rx_ibr_message_total', 'Total IBR received message from Broker')
        self.rx_rci_message_total = Counter('zeppelin_rx_rci_message_total', 'Total RCI received message from Broker')
        self.tx_cmd_message_total = Counter('zeppelin_tx_cmd_message_total', 'Total Cloud to Edge (direct method) transmitted message')
        self.rx_cmd_message_total = Counter('zeppelin_rx_cmd_message_total', 'Total Cloud to Edge (direct method) received message')
        self.rx_generic_message_total = Counter('zeppelin_rx_generic_message_total', 'Total generic received message from Broker')

    # -------------------------------------------------------------------------
    # May not be required since the doc of prometheus_client says it is thread safe
    def inc_counter(self, name):
        try:
            self.mutex.acquire()

            if name == 'rx_message_total':
                self.rx_message_total.inc()
            elif name == 'rx_message_over_size':
                self.rx_message_over_size.inc()
            elif name == 'rx_message_discarded':
                self.rx_message_discarded.inc()
            elif name == 'rx_message_error':
                self.rx_message_error.inc()
            elif name == 'rx_message_valid':
                self.rx_message_valid.inc()
            elif name == 'rx_message_invalid':
                self.rx_message_invalid.inc()
            elif name == 'tx_message_total':
                self.tx_message_total.inc()
            elif name == 'throttle_total':
                self.throttle_total.inc()
            elif name == 'rx_zigbee_message_total':
                self.rx_zigbee_message_total.inc()
            elif name == 'rx_egauge_message_total':
                self.rx_egauge_message_total.inc()
            else:
                logger.error(f'invalid counter name({name})')

        except Exception as ex:
            logger.error(ex)

        finally:
            self.mutex.release()


'''
pip install prometheus_client==0.20.0

Metric Types: https://prometheus.io/docs/concepts/metric_types/

Default Prometheus port is 8000. You can change it by setting the environment variable PROMETHEUS_PORT.

'''
import logging
import os
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

DEFAULT_PORT = int(os.getenv('PROMETHEUS_PORT', 8000))

# -----------------------------------------------------------------------------
#
class PrometheusServer:
    # -----------------------------------------------------------------------------
    #
    def __init__(self, port=DEFAULT_PORT):
        self.port = port

    # -----------------------------------------------------------------------------
    #
    def init(self):
        try:
            return True

        except Exception as e:
            logger.error(e)
            return False

    # -----------------------------------------------------------------------------
    #
    def start(self):
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus server started on port {self.port}")
            return True

        except Exception as e:
            logger.error(e)
            return False

"""
IoTEdgeAgent
pip install azure-iot-device

ATTENTION:
----------
IoTHubModuleClient a une dépendance sur paho-mqtt < 2.00
IMPORTANT: Il n'est pas possible d'avoir plus d'un client IoTHubModuleClient par application (process).

Ce module est utilisé pour transmettre des messages entre le edge et le cloud.
Pour recevoir des messages du cloud, vous devez activer la fonctionnalité DirectMethod avec les attributs suivant.
"iotedge": {
    "enable_direct_method": true,
    "direct_method_name": "publish"
}
"direct_method_name" doit être le même que le nom de la méthode directe configurée dans IoTHubAgent.

"""
import datetime
import json
import os
import time
import copy
from threading import Lock

from azure.iot.device import IoTHubModuleClient, Message, MethodResponse, MethodRequest
from .communication_interface import CommunicationInterface, ConnectionException
from .throttle import Throttle
from utils.logger import get_logger
from metrics import Metrics

logger = get_logger('IoTEdgeAgent')

CONNECT_MAX_RETRY = 10
CONNECT_INTERVAL = 5.0


# -----------------------------------------------------------------------------
# WARNING: This class is almost a singleton. IoTHubModuleClient cannot handle more than one instance per process.
class IoTEdgeAgent(CommunicationInterface, Throttle):
    # Static variables
    _client = None
    _connected = False
    _connecting = False
    _enable_direct_method = False
    _method_name = None
    # Mapping for topic/queue (hash)
    _topics = {}
    # Mapping for direct method name/queue (hash)
    _methods = {}
    _mutex = Lock()
    _queue = None # default queue
    _topic = None

	# -------------------------------------------------------------------------
	#
    def __init__(self, config:dict = {}):
        Throttle.__init__(self, 10, 1)
        self._metrics = None
        self._direct_method_name = None

        enable_direct_method = config.get("enable_direct_method", False)
        if enable_direct_method:
            direct_method_name = config.get("direct_method_name", None)
            if direct_method_name == None:
                logger.error("direct_method_name attribute not defined")
            else:
                logger.info(f"Direct method enabled with direct_method_name({direct_method_name})")
                self.enable_direct_method(direct_method_name)

        retry = 0
        connected = self._connect()

        while not connected and retry < CONNECT_MAX_RETRY:
            time.sleep(CONNECT_INTERVAL)
            retry += 1
            logger.info(f'connect retry({retry})')
            connected = self._connect()

        if not connected:
            raise ConnectionException('Cannot connect to IoT Edge Hub!')

    # -------------------------------------------------------------------------
    #
    def enable_direct_method(self, method_name):
        if method_name == None:
            logger.error("method_name cannot be None")
            raise Exception("method_name cannot be None")
        IoTEdgeAgent._enable_direct_method = True
        IoTEdgeAgent._method_name = method_name
        self._direct_method_name = method_name

    # -------------------------------------------------------------------------
    #
    def disable_direct_method(self):
        IoTEdgeAgent._enable_direct_method = False

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        try:
            IoTEdgeAgent._mutex.acquire()
            if IoTEdgeAgent._connected or IoTEdgeAgent._client.connected:
                IoTEdgeAgent._connected = False
                IoTEdgeAgent._client.disconnect()
        except Exception as ex:
            logger.error(ex)
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def publish(self, topic, payload) -> bool:

        try:
            IoTEdgeAgent._mutex.acquire()

            if not IoTEdgeAgent._connected:
                logger.warning("Not connected to Iot Edge!")
                return False

            if not type(payload) is str:
                data = json.dumps(payload, ensure_ascii=False)
            else:
                data = payload

            logger.info("Sending message to topic(%s) data(%.150s)...", topic, data)

            msg = Message(data, message_id=None, content_encoding='utf-8', content_type='application/json', output_name=topic)

            IoTEdgeAgent._client.send_message_to_output(message=msg, output_name=topic)

            return True

        except Exception as ex:
            logger.error(ex)
            return False
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def start_listening(self, topic, queue) -> bool:
        try:
            IoTEdgeAgent._mutex.acquire()

            if IoTEdgeAgent._client == None:
                logger.error("Not connected to Iot Edge!")
                return False

            logger.info(f'Listening on topic {topic}')
            IoTEdgeAgent._topic = topic
            IoTEdgeAgent._queue = queue

            if type(topic) is str:
                IoTEdgeAgent._topics[topic] = queue
            elif type(topic) is list:
                for item in topic:
                    if type(item) is str:
                        IoTEdgeAgent._topics[item] = queue
                    elif type(item) is tuple:
                        IoTEdgeAgent._topics[item[0]] = queue
            elif type(topic) is tuple:
                IoTEdgeAgent._topics[topic[0]] = queue

            IoTEdgeAgent._client.on_message_received = self._on_message

            if self._direct_method_name != None:
                IoTEdgeAgent._methods[self._direct_method_name] = queue
                logger.info(f"Direct method {self._direct_method_name} associated with queue")

            return True

        except Exception as ex:
            logger.error(ex)
            return False
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def _connect(self) -> bool:
        try:
            IoTEdgeAgent._mutex.acquire()

            if IoTEdgeAgent._connecting:
                logger.warning("Already connecting to Iot Edge!")
                return True

            if IoTEdgeAgent._connected and IoTEdgeAgent._client != None:
                if IoTEdgeAgent._client.connected:
                    logger.warning("Already connected to Iot Edge!")
                    return True

                IoTEdgeAgent._client.disconnect()
                IoTEdgeAgent._client = None
                IoTEdgeAgent._connected = False

            IoTEdgeAgent._client = IoTHubModuleClient.create_from_edge_environment()
            IoTEdgeAgent._client.on_connection_state_change = IoTEdgeAgent._on_connection_state_change
            IoTEdgeAgent._client.on_background_exception = IoTEdgeAgent._on_background_exception
            IoTEdgeAgent._connecting = True
            IoTEdgeAgent._client.connect()

            return True

        except Exception as ex:
            logger.error(ex)
            IoTEdgeAgent._connected = False
            return False
        finally:
            IoTEdgeAgent._mutex.release()


	# -------------------------------------------------------------------------
	#
    @staticmethod
    def _on_background_exception():
        logger.error(f"Iot Edge exception!")

	# -------------------------------------------------------------------------
	#
    @staticmethod
    def _on_connection_state_change():
        try:
            IoTEdgeAgent._mutex.acquire()

            if IoTEdgeAgent._client.connected:
                logger.warning("Iot Edge connected!")
                IoTEdgeAgent._connected = True

                if not IoTEdgeAgent._connecting:
                    logger.error("Iot Edge connection state changed but not connecting!")

                IoTEdgeAgent._connecting = False

                # Allays enable direct method handler. The request could be configured in the second pipeline (or later).
                IoTEdgeAgent._client.on_method_request_received = IoTEdgeAgent._on_method_request_handler
                if IoTEdgeAgent._enable_direct_method:
                    logger.info("IoTEdgeAgent._client.on_method_request_received = IoTEdgeAgent._on_method_request_handler configured")
            else:
                logger.warning("Iot Edge disconnected!")
                IoTEdgeAgent._connected = False
                IoTEdgeAgent._connecting = False

        except Exception as ex:
            logger.error(ex)
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    @staticmethod
    def _on_method_request_handler(method_request: MethodRequest):
        try:
            IoTEdgeAgent._mutex.acquire()
            logger.info(f"Received method request({method_request.name}) request_id({method_request.request_id}) payload({method_request.payload})")

            resp_status = 200
            resp_payload = {"Response": "Message received with success by Zeppelin"}

            queue = None
            if method_request.name in IoTEdgeAgent._methods:
                queue = IoTEdgeAgent._methods[method_request.name]
            elif method_request.name == IoTEdgeAgent._method_name and IoTEdgeAgent._queue != None:
                queue = IoTEdgeAgent._queue

            if queue != None:
                if method_request.payload != None:
                    msg = {}
                    if type(method_request.payload) is str:
                        msg['payload'] = json.loads(method_request.payload)
                        msg['size'] = len(method_request.payload)
                    else:
                        msg['payload'] = copy.deepcopy(method_request.payload)
                        msg['size'] = len(json.dumps(method_request.payload))
                    msg['topic'] = method_request.name
                    msg['dt'] = datetime.datetime.now()

                    IoTEdgeAgent._queue.put(msg)
                else:
                    resp_status = 400
                    resp_payload = {"Error": "Invalid payload"}
            else:
                resp_status = 400
                resp_payload = {f"Error": "Invalid method {method_request.name}"}

            logger.info(f"Sending method response({method_request.name}) request_id({method_request.request_id}) status({resp_status}) payload({resp_payload})")
            method_response = MethodResponse(method_request.request_id, resp_status, resp_payload)
            IoTEdgeAgent._client.send_method_response(method_response)

        except Exception as ex:
            logger.error(ex)
            try:
                resp_status = 500
                resp_payload = {"Exception": str(ex)}
                method_response = MethodResponse(method_request.request_id, resp_status, resp_payload)
                IoTEdgeAgent._client.send_method_response(method_response)
            except Exception as ex:
                logger.error(ex)
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def _on_message(self, message: Message):
        try:
            IoTEdgeAgent._mutex.acquire()

            queue = None
            topic = message.input_name
            logger.info(f'Received message from topic({topic})')

            if IoTEdgeAgent._topics != None:
                for key in IoTEdgeAgent._topics:
                    if key == topic:
                        queue = IoTEdgeAgent._topics[key]
                        break

            if queue == None:
                logger.warning(f'discard message from topic({topic})')
                return

            payload = message.data.decode('utf8')

            msg = {}
            msg['payload'] = json.loads(payload)
            msg['topic'] = topic
            msg['size'] = len(payload)
            msg['dt'] = datetime.datetime.now()

            queue.put(msg)

            if self.throttle() and self._metrics != None:
                self._metrics.inc_counter('throttle_total')

        except Exception as ex:
            logger.error(ex)
        finally:
            IoTEdgeAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def get_device_id(self) -> str:
        try:
            return os.getenv('IOTEDGE_DEVICEID', '')
        except Exception as ex:
            logger.error(ex)
            return ''

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
    def set_metrics(self, metrics: Metrics):
        self._metrics = metrics
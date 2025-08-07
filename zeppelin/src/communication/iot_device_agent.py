'''
pip install azure-iot-device
Vous avez besoin de python 3.11+ pour utiliser tomllib

Utilisez ce module pour recevoir des messages depuis le cloud (c2d)

IoTHubDeviceClient se connecte directement à Azure IoT Hub et a besoin d'une connection string.
Nous utilisons le fichier /etc/aziot/config.toml pour la connection string.
Le fichier devrait être exposé au conteneur via un volume.
Le nom de la localisation devrait être exposé via une variable d'environnement qui se nomme: AZIOT_CONFIG_PATH
Ex: AZIOT_CONFIG_PATH=/aziot_config.toml
Dans ce cas, faire un bind: -v /etc/aziot/config.toml:/aziot_config.toml

Le concept de topic (output_name) ne s'applique pas pour ces messages.
Utilisez custom_properties pour simuler des topics.
properties = {'src_app': 'GDP-MANAGER', 'src_topic': 'GDP', 'dest_broker': 'MOSQUITTO-MQTT', 'dest_topic': 'GDP'}
properties = {'src_app': 'WEATHER-MANAGER', 'src_topic': 'WEATHER-FORECAST', 'dest_broker': 'EDGE-MQTT', 'dest_topic': 'WEATHER-FORECAST'}

Message doc: https://learn.microsoft.com/en-us/python/api/azure-iot-device/azure.iot.device.message?view=azure-python

Doc:
https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d
https://learn.microsoft.com/en-us/azure/iot-hub/how-to-cloud-to-device-messaging?pivots=programming-language-python

'''
import datetime
import json
import os
import time

from threading import Lock

from azure.iot.device import IoTHubDeviceClient, Message
from .communication_interface import CommunicationInterface, ConnectionException
from .throttle import Throttle
from utils.logger import get_logger
from metrics import Metrics

logger = get_logger('IoTDeviceAgent')

AZIOT_CONFIG_PATH = os.getenv('AZIOT_CONFIG_PATH', '/aziot_config.toml')
DEFAULT_SOURCE_TOPIC = 'none'
CONNECT_MAX_RETRY = 10
CONNECT_INTERVAL = 5.0

# -----------------------------------------------------------------------------
# WARNING: This class is almost a singleton.
class IoTDeviceAgent(CommunicationInterface, Throttle):
    # Static variables
    _client = None
    _connected = False
    # Mapping for topic/queue (hash)
    _topics = {}
    _mutex = Lock()
    _connection_string = None

	# -------------------------------------------------------------------------
	#
    def __init__(self):
        Throttle.__init__(self, 10, 1)
        self._metrics = None

        retry = 0
        connected = self._connect()

        while not connected and retry < CONNECT_MAX_RETRY:
            time.sleep(CONNECT_INTERVAL)
            retry += 1
            logger.info(f'connect retry({retry})')
            connected = self._connect()

        if not connected:
            raise ConnectionException('Cannot connect to IoT Hub!')

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        try:
            IoTDeviceAgent._mutex.acquire()
            if IoTDeviceAgent._connected or IoTDeviceAgent._client.connected:
                IoTDeviceAgent._connected = False
                IoTDeviceAgent._client.disconnect()
        except Exception as ex:
            logger.error(ex)
        finally:
            IoTDeviceAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def publish(self, topic, payload) -> bool:

        try:
            IoTDeviceAgent._mutex.acquire()

            if not IoTDeviceAgent._connected:
                logger.warning("Not connected to Iot Edge!")
                return False

            if not type(payload) is str:
                data = json.dumps(payload, ensure_ascii=False)
            else:
                data = payload

            logger.info("Sending message to topic(%s) data(%.150s)...", topic, data)

            msg = Message(data, message_id=None, content_encoding='utf-8', content_type='application/json', output_name=topic)

            IoTDeviceAgent._client.send_message(msg)

            return True

        except Exception as ex:
            logger.error(ex)
            return False
        finally:
            IoTDeviceAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def start_listening(self, topic, queue) -> bool:
        try:
            IoTDeviceAgent._mutex.acquire()

            if IoTDeviceAgent._client == None:
                logger.error("Not connected to Iot Edge!")
                return False

            if topic == None or len(topic) == 0:
                topic = 'none'

            logger.info(f'Listening on topic {topic}')
            self._topic = topic
            self._queue = queue

            if type(topic) is str:
                IoTDeviceAgent._topics[topic] = queue
            elif type(topic) is list:
                for item in topic:
                    if type(item) is str:
                        IoTDeviceAgent._topics[item] = queue
                    elif type(item) is tuple:
                        IoTDeviceAgent._topics[item[0]] = queue
            elif type(topic) is tuple:
                IoTDeviceAgent._topics[topic[0]] = queue

            IoTDeviceAgent._client.on_message_received = self._on_message

            return True

        except Exception as ex:
            logger.error(ex)
            return False
        finally:
            IoTDeviceAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def _get_connection_string(self) -> str:
        try:
            import tomllib # require python 3.11 +

            if IoTDeviceAgent._connection_string == None:

                logger.info(f'Loading connection string from {AZIOT_CONFIG_PATH}')

                with open(AZIOT_CONFIG_PATH, 'rb') as file:
                    data = tomllib.load(file)
                    c = data.get('provisioning', {})
                    IoTDeviceAgent._connection_string = c.get('connection_string', '')

            return IoTDeviceAgent._connection_string

        except Exception as ex:
            logger.error(ex)
            return ''

	# -------------------------------------------------------------------------
	#
    def _connect(self) -> bool:
        try:
            IoTDeviceAgent._mutex.acquire()

            if IoTDeviceAgent._connected and IoTDeviceAgent._client != None:
                if IoTDeviceAgent._client.connected:
                    logger.warning("Already connected to Iot Hub!")
                    return True

                IoTDeviceAgent._client.disconnect()
                IoTDeviceAgent._client = None
                IoTDeviceAgent._connected = False

            cs = self._get_connection_string()
            if cs == None or cs == '':
                logger.error("No connection string! Did you set AZIOT_CONFIG_PATH?")
                return False

            IoTDeviceAgent._client = IoTHubDeviceClient.create_from_connection_string(cs)
            IoTDeviceAgent._client.on_connection_state_change = IoTDeviceAgent._on_connection_state_change
            IoTDeviceAgent._client.on_background_exception = IoTDeviceAgent._on_background_exception
            IoTDeviceAgent._client.connect()

            return True

        except Exception as ex:
            logger.error(ex)
            IoTDeviceAgent._client = None
            IoTDeviceAgent._connected = False
            return False
        finally:
            IoTDeviceAgent._mutex.release()


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
            IoTDeviceAgent._mutex.acquire()
            if IoTDeviceAgent._client.connected:
                logger.warning("Iot Device connected!")
                IoTDeviceAgent._connected = True
            else:
                logger.warning("Iot Device disconnected!")
                IoTDeviceAgent._connected = False
        except Exception as ex:
            logger.error(ex)
        finally:
            IoTDeviceAgent._mutex.release()

	# -------------------------------------------------------------------------
	#
    def _on_message(self, message: Message):
        global DEFAULT_SOURCE_TOPIC
        try:
            IoTDeviceAgent._mutex.acquire()

            queue = None
            topic = message.input_name
            props = message.custom_properties

            if topic == None or len(topic) == 0:
                topic = DEFAULT_SOURCE_TOPIC

            if props != None and type(props) is dict:
                if 'src_topic' in props:
                    topic = props['src_topic']

            logger.info(f'Received message from topic({topic})')

            if IoTDeviceAgent._topics != None:
                for key in IoTDeviceAgent._topics:
                    if key == topic:
                        queue = IoTDeviceAgent._topics[key]
                        break

            if queue == None:
                logger.warning(f'no destination queue found. discard message topic({topic}) props({props})')
                return

            payload = message.data.decode('utf8')

            try:
                json_payload = json.loads(payload)
            except Exception as ex:
                logger.error(ex)
                logger.warning(f'invalid json payload({payload})')
                json_payload = payload

            msg = {}
            msg['payload'] = json_payload
            msg['topic'] = topic
            msg['size'] = len(payload)
            msg['dt'] = datetime.datetime.now()
            msg['props'] = props

            queue.put(msg)

            if self.throttle() and self._metrics != None:
                self._metrics.inc_counter('throttle_total')

        except Exception as ex:
            logger.error(ex)
        finally:
            IoTDeviceAgent._mutex.release()

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
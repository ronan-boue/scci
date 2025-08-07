"""
pip3 install paho-mqtt

Pour activer l'identification par username/password, il faut ajouter les 2 attibutes dans le fichier de configuration de Zeppelin pour le client MQTT:
"mqtt": {
    "host": "127.0.0.1",
    "port": 1883,
    "id": "zeppelin_gen_src",
    "username": "mqtt_user",
    "password": "mqtt_password",
    "keepalive": 60,
    "qos": 1
}

Pour activer la sécurité TLS, il faut ajouter l'attribut ca_certs (au minimum) dans le fichier de configuration de Zeppelin pour le client MQTT:
"mqtt": {
    "host": "127.0.0.1",
    "port": 1883,
    "id": "zeppelin_gen_src",
    "username": "mqtt_user",
    "password": "mqtt_password",
    "ca_certs": "/config/certs/ca.crt",
    "keepalive": 60,
    "qos": 1
}

Vous pouvez aussi ajouter le certificat du client dans le fichier de configuration de Zeppelin pour le client MQTT avec certfile et keyfile:
"mqtt": {
    "host": "127.0.0.1",
    "port": 1883,
    "id": "zeppelin_gen_src",
    "username": "mqtt_user",
    "password": "mqtt_password",
    "ca_certs": "/config/certs/ca.crt",
    "certfile": "/config/certs/client.crt",
    "keyfile": "/config/certs/client.key",
    "cert_reqs": "CERT_REQUIRED",
    "keepalive": 60,
    "qos": 1
}
"""

import os
import time
import ssl
from threading import Thread, Lock
import datetime
import json
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessageInfo

from .communication_interface import CommunicationInterface, ConnectionException
from .throttle import Throttle
from utils.logger import get_logger
from metrics import Metrics

logger = get_logger("MqttAgent")

CONNECT_MAX_RETRY = 10
CONNECT_INTERVAL = 5.0


# -----------------------------------------------------------------------------
#
class MqttAgent(CommunicationInterface, Throttle):

    # -------------------------------------------------------------------------
    #
    def __init__(
        self,
        id=None,
        host="127.0.0.1",
        port=1883,
        keepalive=60,
        retain=False,
        qos=0,
        username=None,
        password=None,
        ca_certs=None,
        certfile=None,
        keyfile=None,
        cert_reqs=ssl.CERT_NONE,
        ciphers=None,
        insecure=True,
    ):
        Throttle.__init__(self, 10, 1)
        # initialize agent variables
        self.mutex = Lock()
        self._metrics = None
        self.client = None
        self.id = id
        self.hostname = host
        self.port = port
        self.keepalive = keepalive
        self.retain = retain
        self.qos = qos
        self.username = username
        self.password = password
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        self.cert_reqs = cert_reqs
        self.ciphers = ciphers
        self.insecure = insecure
        self.topic = None
        self.connected = False
        self.subscribed = False

        retry = 0
        self.connected = self._connect()

        while not self.connected and retry < CONNECT_MAX_RETRY:
            time.sleep(CONNECT_INTERVAL)
            retry += 1
            logger.info(f"connect retry({retry})")
            self.connected = self._connect()

        if not self.connected:
            raise ConnectionException("Cannot connect to MQTT Broker!")

    # -------------------------------------------------------------------------
    #
    def _connect(self) -> bool:
        try:
            self.mutex.acquire()

            logger.info(f"id({self.id}) connecting to broker({self.hostname}:{self.port}) keepalive({self.keepalive})")

            if self.client != None:
                self.client.disconnect()
                self.client = None
                self.connected = False
                time.sleep(CONNECT_INTERVAL)

            self.client = mqtt.Client(client_id=self.id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_subscribe = self._on_subscribe
            self.client.on_message = self._on_message

            if self.username is not None and self.password is not None:
                self.client.username_pw_set(self.username, self.password)

            if self.ca_certs is not None:
                self.client.tls_set(
                    ca_certs=self.ca_certs,
                    certfile=self.certfile,
                    keyfile=self.keyfile,
                    cert_reqs=self.cert_reqs,
                    ciphers=self.ciphers,
                    tls_version=ssl.PROTOCOL_TLSv1_2,
                )
                self.client.tls_insecure_set(self.insecure)

            self.client.connect(self.hostname, port=self.port, keepalive=self.keepalive)

            logger.info(f"id({self.id}) connected to broker({self.hostname}:{self.port}); loop_start()")
            self.client.loop_start()

            return True

        except Exception as ex:
            logger.error(ex)
            return False

        finally:
            self.mutex.release()

    # -------------------------------------------------------------------------
    #
    def _reconnect(self) -> bool:
        try:
            logger.warning(f"id({self.id}) reconnecting to broker({self.hostname}:{self.port})")

            retry = 0
            self.connected = self._connect()

            while not self.connected:
                time.sleep(CONNECT_INTERVAL)
                retry += 1
                logger.info(f"connect retry({retry})")
                self.connected = self._connect()

            if self.connected:
                if self.subscribed:
                    self.client.subscribe(self.topic)
                    logger.info(f"id({self.id}) Listening on topic {self.topic}")

            return self.connected

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        self.client.disconnect()
        self.connected = False

    # -------------------------------------------------------------------------
    # Set topic to None if you need to listen on all topics
    def start_listening(self, topic, queue) -> bool:
        try:
            self.mutex.acquire()

            if self.client == None:
                logger.error("client is None")
                return False

            if topic == None:
                topic = "#"

            if type(topic) is str:
                topic = [(topic, self.qos)]
            elif type(topic) is list:
                _topics = []

                for item in topic:
                    if type(item) is str:
                        _topics.append((item, self.qos))
                    else:
                        _topics.append(item)
                topic = _topics

            self.topic = topic

            logger.info(f"id({self.id}) Listening on topic {self.topic}")

            self.queue = queue
            self.client.subscribe(self.topic)
            self.subscribed = True

            return True

        except Exception as ex:
            logger.error(ex)
            return False

        finally:
            self.mutex.release()

    # -------------------------------------------------------------------------
    #
    def publish(self, topic, payload, retain=None, qos=None) -> bool:
        try:
            self.mutex.acquire()

            if self.client == None or not self.connected:
                logger.error(f"id({self.id}) not connected")
                return False

            if retain == None:
                retain = self.retain

            if qos == None:
                qos = self.qos

            if not type(payload) is str:
                data = json.dumps(payload, ensure_ascii=False)
            else:
                data = payload

            logger.info(f"id({self.id}) Tx msg to ({topic}): %.300s...", data)

            res: MQTTMessageInfo = self.client.publish(topic, data, retain=retain, qos=qos)

            if res.is_published() or res.rc == 0:
                logger.info(f"id({self.id}) Message({res.mid}) sent to ({topic})")
                return True

            logger.error(f"id({self.id}) Message({res.mid}) not sent to ({topic}) rc({res.rc})")

            return False

        except Exception as ex:
            logger.error(ex)
            return False

        finally:
            self.mutex.release()

    # -------------------------------------------------------------------------
    #
    def _on_connect(self, client, userdata, flags, reason_code):
        try:
            self.mutex.acquire()
            logger.info(f"id({self.id}) connected; reason_code({reason_code})")

            if reason_code != mqtt.CONNACK_ACCEPTED:
                logger.error(f"id({self.id}) connection failed with reason_code({reason_code})")

                self.connected = False

                if reason_code == mqtt.CONNACK_REFUSED_PROTOCOL_VERSION:
                    logger.error("Connection refused: unacceptable protocol version")
                elif reason_code == mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED:
                    logger.error("Connection refused: identifier rejected")
                elif reason_code == mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:
                    logger.error("Connection refused: server unavailable")
                elif reason_code == mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD:
                    logger.error("Connection refused: bad username or password")
                elif reason_code == mqtt.CONNACK_REFUSED_NOT_AUTHORIZED:
                    logger.error("Connection refused: not authorized")

                return

            if not self.connected:
                self.connected = True

        except Exception as ex:
            logger.error(ex)

        finally:
            self.mutex.release()

    # -------------------------------------------------------------------------
    #
    def _on_disconnect(self, client, userdata, flags, rc=0):
        try:
            self.mutex.acquire()
            logger.warning(f"id({self.id}) disconnected")

            if self.connected:
                self.connected = False
                Thread(target=self._reconnect).start()

        except Exception as ex:
            logger.error(ex)

        finally:
            self.mutex.release()

    # -------------------------------------------------------------------------
    #
    def _on_subscribe(self, client, userdata, mid, reason_code_list):
        try:
            logger.info(
                f"id({self.id}) Broker granted the following QoS({reason_code_list[0]}) for topic({self.topic})"
            )

        except Exception as ex:
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def _on_message(self, client, userdata, message):
        try:
            logger.info(f"Rx msg from topic({message.topic}): %.300s ...", message.payload.decode("utf8"))

            payload = message.payload.decode("utf8")
            msg = {}
            msg["topic"] = message.topic
            msg["payload"] = json.loads(payload)
            msg["size"] = len(payload)
            msg["dt"] = datetime.datetime.now()

            self.queue.put(msg)

            if self.throttle() and self._metrics != None:
                self._metrics.inc_counter("throttle_total")

        except Exception as ex:
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def get_device_id(self):
        try:
            return os.getenv("IOTEDGE_DEVICEID", "")
        except Exception as ex:
            logger.error(ex)
            return ""

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

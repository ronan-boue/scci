"""
pip install azure-iot-hub
Utilisez ce module pour transmettre des messages depuis le cloud vers le edge (c2d) en utilisant le service IoT Hub et Direct Method.

IoTHubClient se connecte directement à Azure IoT Hub et a besoin d'une connection string.
La connection string est lue depuis la variable d'environnement IOTHUB_CONNECTION_STRING.
Pour connaitre la connection string, allez dans le portail Azure, sélectionnez votre IoT Hub, puis sélectionnez "Shared access policies" dans le menu de gauche.
Ajoutez une nouvelle clé de sécurité avec les droits "Service Connect".
Cliquez sur la clé de sécurité que vous venez de créer et copiez la connection string.

Le nom de la methode est défini dans le fichier de configuration et doit être le même que celui défini dans
la configuration du module IoTEdgeAgent.

"""

import datetime
import uuid
import os
import time
from threading import Thread, Lock

from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod, CloudToDeviceMethodResult

from .communication_interface import CommunicationInterface, ConnectionException
from .throttle import Throttle
from utils.logger import get_logger
from metrics import Metrics

logger = get_logger("IoTHubAgent")

IOTHUB_CONNECTION_STR = os.getenv("IOTHUB_CONNECTION_STRING")
MODULE_ID = os.getenv("MODULE_ID", "zeppelin")

CONNECT_MAX_RETRY = 10
CONNECT_INTERVAL_SEC = 5.0
CONNECTION_TIMEOUT_SEC = 15
RESPONSE_TIMEOUT_SEC = 30


# -----------------------------------------------------------------------------
#
class IoTHubAgent(CommunicationInterface, Throttle):

    # -------------------------------------------------------------------------
    #
    def __init__(self, config: dict):
        global CONNECT_MAX_RETRY, CONNECT_INTERVAL_SEC, IOTHUB_CONNECTION_STR
        """
        Expected config values:
            direct_method_name
            connection_timeout_sec=CONNECTION_TIMEOUT_SEC
            response_timeout_sec=RESPONSE_TIMEOUT_SEC
            max_execution_time_sec=MAX_EXECUTION_TIME_SEC
        """

        Throttle.__init__(self, 10, 1)
        Thread.__init__(self)

        logger.info(f"config({config})")

        self._method_name = config.get("direct_method_name", None)
        if self._method_name == None:
            logger.error(f"direct_method_name not defined in config({config})")
            raise Exception("direct_method_name not defined in config")

        self._default_device_id = config.get("default_device_id", None)
        self._module_id = config.get("module_id", MODULE_ID)
        self._connection_timeout_sec = float(config.get("connection_timeout_sec", CONNECTION_TIMEOUT_SEC))
        self._response_timeout_sec = float(config.get("response_timeout_sec", RESPONSE_TIMEOUT_SEC))
        self._metrics = None
        self._iothub_manager = None
        self._connected = False

        logger.info(
            f"method_name({self._method_name}) connection_timeout_sec({self._connection_timeout_sec}) response_timeout_sec({self._response_timeout_sec})"
        )

        if IOTHUB_CONNECTION_STR == None or len(IOTHUB_CONNECTION_STR) == 0:
            logger.error("IOTHUB_CONNECTION_STRING not defined")
            raise Exception("IOTHUB_CONNECTION_STRING not defined")

        retry = 0
        self._connected = self._connect()

        while not self._connected and retry < CONNECT_MAX_RETRY:
            time.sleep(CONNECT_INTERVAL_SEC)
            retry += 1
            logger.info(f"connect retry({retry})")
            self._connected = self._connect()

        if not self._connected:
            raise ConnectionException("Cannot connect to IoT Hub!")

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        try:
            self._iothub_manager = None
        except Exception as ex:
            logger.error(ex)

    # -------------------------------------------------------------------------
    # topic: device id to send the message to
    # payload: json object (dict) to send to the method
    def publish(self, topic, payload) -> bool:

        try:
            if not self._connected or self._iothub_manager == None:
                logger.error("Not connected to IoT Hub")
                return False

            device_id = self._default_device_id
            if topic != None and len(topic) > 0:
                device_id = topic

            logger.info(
                f"publish to device({device_id}) module_id({self._module_id}) method({self._method_name}) payload({payload})"
            )

            request: CloudToDeviceMethod = self._create_method_request(payload)

            result: CloudToDeviceMethodResult = self._iothub_manager.invoke_device_module_method(
                device_id=device_id, module_id=self._module_id, direct_method_request=request
            )

            logger.info(f"Result status({result.status}) payload({result.payload})")

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    # Not supported in IoT Hub
    def start_listening(self, topic, queue) -> bool:
        logger.error("start_listening not supported in IoT Hub")
        return False

    # -------------------------------------------------------------------------
    #
    def _connect(self) -> bool:
        global IOTHUB_CONNECTION_STR
        try:
            self._iothub_manager = IoTHubRegistryManager.from_connection_string(IOTHUB_CONNECTION_STR)
            self._connected = self._iothub_manager != None
            return self._connected

        except Exception as ex:
            logger.error(ex)
            self._iothub_manager = None
            self._connected = False
            return False

    # -------------------------------------------------------------------------
    #
    def _create_method_request(self, payload: dict) -> CloudToDeviceMethod | None:
        try:
            request = CloudToDeviceMethod(
                method_name=self._method_name,
                payload=payload,
                response_timeout_in_seconds=self._response_timeout_sec,
                connect_timeout_in_seconds=self._connection_timeout_sec,
            )

            return request

        except Exception as ex:
            logger.error(ex)
            return None

    # -------------------------------------------------------------------------
    #
    def get_device_id(self) -> str:
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

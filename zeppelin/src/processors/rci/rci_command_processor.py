"""
    RCICommandProcessor: RCI Command Processor
    This module process incoming messages from a source, validate the content and forward the message to a destination.
    It is used in the cloud in order to forward command message to IoT Hub and in the edge to forward command message to MQTT broker.
    In the cloud, the module will get the destination topic (that is a device_id) from an attribute in the cloud event (usualy "device_id").
    The cloud event attribute name is defined in the configuration file.
    The IoTHubAgent.publish(topic, payload) method will be used to send the message to the IoT Hub and the topic parameter is used as the destination device_id..
    In the edge, the module will get the destination topic from the configuration file.

    Explained in a different way:
    If the pipeline configuration has a "device_id_attribute_name" attribute, the module will use the value of this attribute as the cloud event attribute for the destination device_id (topic).
    If there is no "device_id_attribute_name" attribute in the pipeline configuration, the module will use the default topic from the pipeline.destination_broker.
"""
from utils.logger import get_logger, LOGGING_LEVEL
from ..base_processor import BaseProcessor

logger = get_logger("RCICommandProcessor", LOGGING_LEVEL)

"""
    You can override the default data types in the configuration file with the pipeline attribute: data_types
"""
VALID_DATA_TYPES = [
    "ca.qc.hydro.iot.rci.command"
]

# -----------------------------------------------------------------------------
#
class RCICommandProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, pipeline, metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, pipeline, metrics):
            return False

        self._dest_device_id = None
        self._device_id_attribute_name = pipeline.get("device_id_attribute_name", None)

        self._data_types = VALID_DATA_TYPES
        data_types = pipeline.get("data_types", None)
        if data_types != None:
            if type(data_types) != list:
                logger.error(f"invalid data_types({data_types})")
                return False
            self._data_types = []
            for data_type in data_types:
                if type(data_type) != str:
                    logger.error(f"invalid data_type({data_type})")
                    return False
                if len(data_type) == 0:
                    logger.error(f"invalid data_type({data_type})")
                    return False
                self._data_types.append(data_type)

        logger.debug(f"RCICommandProcessor initialized device_id_attribute_name({self._device_id_attribute_name}) data_types({self._data_types})")

        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            if self._device_id_attribute_name != None:
                self.metrics.tx_cmd_message_total.inc()
            else:
                self.metrics.rx_cmd_message_total.inc()

            if not BaseProcessor.assess(self):
                return False

            self.data_type = self.payload.get("type", None)

            if self.data_type == None or self.data_type not in self._data_types:
                logger.error(f"invalid data type({self.data_type})")
                return False

            self.device_model = ""

            if self._device_id_attribute_name != None:
                self._dest_device_id = self.payload.get(self._device_id_attribute_name, None)

                if type(self._dest_device_id) != str:
                    logger.error(f"invalid device_id({self._dest_device_id})")
                    self._dest_device_id = None
                    return False
                elif len(self._dest_device_id) == 0:
                    logger.error(f"invalid device_id({self._dest_device_id})")
                    self._dest_device_id = None
                    return False
            else:
                self._dest_device_id = None

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
    def get_destination_topic(self) -> str:
        try:
            if self._dest_device_id != None:
                return self._dest_device_id

            return BaseProcessor.get_destination_topic(self)

        except Exception as ex:
            logger.error(ex)
            return None

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


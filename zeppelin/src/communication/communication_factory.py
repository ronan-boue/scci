from .mqtt_agent import MqttAgent
from .iot_edge_agent import IoTEdgeAgent
from .iot_device_agent import IoTDeviceAgent
from.iot_hub_agent import IoTHubAgent
from .void_agent import VoidAgent
from utils.logger import get_logger

logger = get_logger('CommunicationFactory')

# -------------------------------------------------------------------------------------------------
#
class CommunicationFactory:

    """
    Factory class to create communication agents based on the provided configuration.
    The factory method `get_client` takes a configuration dictionary and returns an instance of the appropriate communication agent class.
    The supported classes are IoTEdgeAgent, IoTDeviceAgent, IoTHubAgent, MqttAgent, and VoidAgent.
    The configuration dictionary must contain a 'class' key that specifies the desired agent class.
    Class keys are:
        - IoTEdge
        - IoTDevice
        - IoTHub
        - MQTT
        - Void
    """

    # -------------------------------------------------------------------------------------------------
    #
    @staticmethod
    def get_client(config):
        try:
            agent = None
            logger.info(config)

            dest_class = config.get('class')

            if dest_class == None:
                logger.error('destination class not defined')
                return None

            d_class = dest_class.strip().upper().replace(' ', '').replace('-', '').replace('_', '')
            logger.info(f'class({d_class})')

            if d_class == 'IOTEDGE':
                iotedge_config = config.get('iotedge', {})
                if iotedge_config == None or not type(iotedge_config) is dict:
                    logger.error('iotedge configuration not defined or invalid')
                    return None

                agent = IoTEdgeAgent(iotedge_config)

            elif d_class == 'IOTDEVICE':
                agent = IoTDeviceAgent()

            elif d_class == 'IOTHUB':
                iothub_config = config.get('iothub', None)
                if iothub_config == None or not type(iothub_config) is dict:
                    logger.error('iothub configuration not defined or invalid')
                    return None

                agent = IoTHubAgent(iothub_config)

            elif d_class == 'MQTT':
                mqtt_config = config.get('mqtt', None)
                if mqtt_config == None or not type(mqtt_config) is dict:
                    logger.error('mqtt configuration not defined')
                    return None

                logger.info(f"mqtt({mqtt_config})")

                agent = MqttAgent(**mqtt_config)

            elif d_class == 'VOID':
                agent = VoidAgent()

            else:
                logger.error(f"Insupported destination class({dest_class})")

            if agent != None:
                agent.set_max_msg_sec(config.get('throttle_max_message_sec', 10))
                agent.set_sleep_sec(config.get('throttle_sleep_sec', 1.0))

            return agent

        except Exception as ex:
            logger.error(ex)
            return None

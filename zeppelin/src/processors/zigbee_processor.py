from utils.logger import get_logger, LOGGING_LEVEL
from .base_processor import BaseProcessor

logger = get_logger('ZigbeeProcessor', LOGGING_LEVEL)



# -----------------------------------------------------------------------------
#
class ZigbeeProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def __init__(self):
        self.device_model = ''
        self.device_config = None
        self.data_fields = None
        BaseProcessor.__init__(self)
        logger.info("constructor called")

    # -------------------------------------------------------------------------
    #
    def init(self, config, source, metrics) -> bool:
        if not BaseProcessor.init(self, config, source, metrics):
            return False
        logger.debug('ZigbeeProcessor initialized')
        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_zigbee_message_total.inc()

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

            # get device model
            device = self.data.get('device', None)
            subject = self.payload.get('subject', None)

            if subject == None or len(subject) == 0 and device != None and type(device) == dict:
                subject = device.get('model', None)

            if subject == None or len(subject) == 0:
                logger.error(f'invalid subject({subject}). Subject must contain device model.')
                return False

            self.device_model = subject.upper()

            logger.info(f'device_model({self.device_model})')

            if self.config == None:
                logger.error(f'invalid config({self.config})')
                return False

            # get device configuration
            devices = self.config.get('devices', None)

            if devices == None:
                logger.error(f'devices not defined in config')
                return False

            dconfig = devices.get(self.device_model, None)

            if dconfig == None:
                logger.error(f'unknown device model({self.device_model})')
                return False

            self.device_config = dconfig
            logger.debug(f'device_config({self.device_config})')

            data_fields = self.config.get('data_fields', None)
            if data_fields == None or type(data_fields) != list:
                logger.error(f'data_fields not defined in config')
                return False

            self.data_fields = data_fields

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def normalize(self) -> bool:
        try:
            if not BaseProcessor.normalize(self):
                return False

            # build normalized data payload
            data = {}
            data['device'] = self.data.get('device', None)
            values = []

            for item in self.device_config:
                field = item.get('field', None)

                if not field in self.data:
                    mandatory = item.get('mandatory', True)

                    if mandatory:
                        logger.error(f'field({field}) not defined in data({self.data}) for self.device_model({self.device_model})')
                        return False

                    logger.warning(f'field({field}) not defined in data({self.data}) for self.device_model({self.device_model})')
                    continue

                value = {}
                value['value'] = self.data.get(field, None)

                for df in self.data_fields:
                    value[df] = item.get(df, None)

                values.append(value)

            data['values'] = values
            self.data = data

            return BaseProcessor.check_values(self, values)

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def get_data(self):
        return BaseProcessor.get_data(self)

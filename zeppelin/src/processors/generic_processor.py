"""
This is a generic processor for handling data from various sources.
You can use this processor to process data that does not fit into specific categories like Egauge, Zigbee, etc.
Generic data is expected to be in a CloudEvent format.

You can validate cloudevent.type by providing the attibute data_types in the pipeline configuration.
data_types is an array of strings.

You can validate the data payload by providing a json schema in the pipeline json_schema attribute.

If you need to populate some CloudEvent attributes from the source CloudEvent, add a pipeline attribute called `populate_ce_attributes`.
pipeline.populate_ce_attributes is an array of strings that contains the CloudEvent attributes to populate.

"""
from utils.logger import get_logger, LOGGING_LEVEL
from .base_processor import BaseProcessor

logger = get_logger('GenericProcessor', LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class GenericProcessor(BaseProcessor):

    # -------------------------------------------------------------------------
    #
    def init(self, config, pipeline, metrics) -> bool:
        self.values = None
        if not BaseProcessor.init(self, config, pipeline, metrics):
            return False

        self._populate_ce_attributes = pipeline.get("populate_ce_attributes", None)
        self._data_types = None
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

        logger.debug('GenericProcessor initialized')
        return True

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            self.metrics.rx_generic_message_total.inc()

            if not BaseProcessor.assess(self):
                return False

            if self._data_types is not None:
                self.data_type = self.payload.get("type", None)

                if self.data_type == None or self.data_type not in self._data_types:
                    logger.error(f"invalid data type({self.data_type})")
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

    # -------------------------------------------------------------------------
    #
    def _get_cloud_event(self, cloud_event, data) -> object:
        try:
            cloud_event = BaseProcessor._get_cloud_event(self, cloud_event, data)

            if self._populate_ce_attributes == None:
                return cloud_event

            for attr in self._populate_ce_attributes:
                if attr in self.payload:
                    cloud_event[attr] = self.payload[attr]
                else:
                    logger.warning(f"attribute({attr}) not found in payload, skipping population")

            return cloud_event

        except Exception as ex:
            logger.error(ex)
            return cloud_event

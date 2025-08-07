'''
JSON SCHEMA DOC
https://json-schema.org/overview/what-is-jsonschema

JSON FILE TO SCHEMA
https://json-to-schema.itential.io/
'''

import copy
import json
import time
import datetime
import uuid
from threading import Thread, Lock
from queue import SimpleQueue

from utils.logger import get_logger, LOGGING_LEVEL
from .processor_interface import ProcessorInterface
from .rules_processor import RulesProcessor
from communication.communication_factory import CommunicationFactory
from jsonschema import validate
from metrics import Metrics


logger = get_logger('BaseProcessor', LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class BaseProcessor(ProcessorInterface, RulesProcessor, Thread):

    # -------------------------------------------------------------------------
    #
    def __init__(self):
        Thread.__init__(self)

        self.config = {}
        self.running = False
        self.interval_sec = 0.1
        self.max_payload_size_bytes = 0
        self.mutex = Lock()
        self.name = ''
        self.device_model = ''
        self.device_id = ''
        self.pipeline = {}
        self.schema = None
        self.rules = {}
        self.src_broker_config = None
        self.dst_broker_config = None
        self.metrics:Metrics = None
        self.queue = SimpleQueue()
        self.src_broker = None
        self.dst_broker = None
        self.topics = []
        self.dest_topic = None
        self.cloud_event = {}
        self.payload = None
        self.data = None
        self.source_topic = None # last message source topic
        self.compressed = False
        self.is_base64 = False
        self.src_has_cloud_event = True # Controlled with source broker config (has_cloud_event)

    # -------------------------------------------------------------------------
    # config = zeppelin global config file
    # pipeline = pipeline object from pipelines[]
    #
    def init(self, config, pipeline, metrics:Metrics) -> bool:
        try:
            self.pipeline = pipeline
            self.metrics = metrics

            if not self._load_config(config, pipeline):
                return False

            RulesProcessor.init(self, self.rules)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    # config = zeppelin global config file
    # pipeline = pipeline object from pipelines[]
    #
    def _load_config(self, config, pipeline) -> bool:
        try:
            if not type(config) is dict:
                logger.error(f'invalid config({config})')
                return False

            if not type(pipeline) is dict:
                logger.error(f'invalid pipeline({pipeline})')
                return False

            logger.info(f'pipeline({pipeline})')

            self.interval_sec = pipeline.get('thread_interval_sec', self.interval_sec)
            self.max_payload_size_bytes = int(pipeline.get('max_payload_size_bytes', self.max_payload_size_bytes))

            global_validation_rules = config.get('global_validation_rules', None)
            if global_validation_rules == None or not type(global_validation_rules) is dict:
                logger.error(f'invalid global_validation_rules({global_validation_rules})')
                return False

            apply_global_validation_rules = pipeline.get('apply_global_validation_rules', False)
            validation_rules = pipeline.get('validation_rules', {})

            if apply_global_validation_rules and global_validation_rules != None:
                validation_rules = validation_rules | global_validation_rules
            elif global_validation_rules != None:
                units = global_validation_rules.get('units', None)
                if units != None:
                    validation_rules['units'] = units

            self.rules = validation_rules

            self.src_broker_config = pipeline.get('source_broker', None)
            if self.src_broker_config == None or not type (self.src_broker_config) is dict:
                logger.error(f'invalid src broker({self.src_broker_config})')
                return False

            self.src_has_cloud_event = self.src_broker_config.get('has_cloud_event', True)
            if not self.src_has_cloud_event:
                logger.warning(f'source broker({self.src_broker_config}) does not have cloud event')

            self.dst_broker_config = pipeline.get('destination_broker', None)
            if self.dst_broker_config == None or not type (self.dst_broker_config) is dict:
                logger.error(f'invalid dst broker({self.dst_broker_config})')
                return False

            self.name = pipeline.get('name', '')

            topic = self.src_broker_config.get('topic', None)
            if topic != None and len(topic) > 0:
                self.topics.append(topic)

            self.dest_topic = self.dst_broker_config.get('topic', None)

            self.schema = None
            json_schema = pipeline.get('json_schema', None)

            if json_schema != None:
                if len(json_schema) == 0:
                    logger.warning(f'no json_schema file provided')
                else:
                    logger.info(f'json_schema({json_schema})')

                    with open(json_schema) as f:
                        self.schema = json.load(f)

            if self.schema == None:
                logger.warning('no schema')

            config_filename = pipeline.get('config', None)

            if config_filename != None and len(config_filename) > 0:
                logger.info(f'config_filename({config_filename})')

                with open(config_filename) as f:
                    config_data = json.load(f)

                if not type(config_data) is dict:
                    logger.error(f'invalid config_data({config_data})')
                    return False

                self.config = config_data

            self.cloud_event = pipeline.get('cloud_event', self.cloud_event)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def _open_broker(self) -> bool:
        try:
            self.src_broker = CommunicationFactory.get_client(self.src_broker_config)

            if self.src_broker == None:
                logger.error(f'cannot create pipeline broker agent from configuration({self.src_broker_config})')
                return False

            self.device_id = self.src_broker.get_device_id()
            logger.info(f'device_id({self.device_id})')
            self.src_broker.set_metrics(self.metrics)

            self.dst_broker = CommunicationFactory.get_client(self.dst_broker_config)

            if self.dst_broker == None:
                logger.error(f'cannot create destination broker agent from configuration({self.dst_broker_config})')
                return False

            self.src_broker.start_listening(self.topics, self.queue)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def _close_broker(self) -> None:
        try:

            if self.src_broker != None:
                self.src_broker.disconnect()
                self.src_broker = None

            if self.dst_broker != None:
                self.dst_broker.disconnect()
                self.dst_broker = None


        except Exception as ex:
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def run(self):
        try:
            self.running = True
            logger.info(f'{self.name} thread started')

            if not self._open_broker():
                self.running = False
                logger.error(f'cannot open broker')
                return

            while self.running:

                try:
                    self._handle_queue()

                    if self.src_broker != None:
                        self.src_broker.handle_task()

                    if self.dst_broker != None:
                        self.dst_broker.handle_task()

                    if self.interval_sec > 0:
                        time.sleep(self.interval_sec)

                except Exception as ex:
                    logger.error(ex)

            # Disconnect from message broker
            self._close_broker()

            logger.info(f'{self.name} thread stopped')

        except Exception as ex:
            self.running = False
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def stop(self):
        try:
            logger.info(f'{self.name} thread stop requested')

            self.mutex.acquire()

            if self.running:
                self.running = False
                return True

            return False

        except Exception as ex:
            logger.error(ex)
            return False

        finally:
            self.mutex.release()

	# -------------------------------------------------------------------------
	# Process received message from broker
    def _handle_queue(self):
        try:

            while not self.queue.empty():
                msg = self.queue.get(block = False)

                if msg == None:
                    return

                self.metrics.rx_message_total.inc()

                self.payload = None
                self.data = None
                self.compressed = False

                self._on_message_received(msg)

        except Exception as ex:
            logger.error(ex)
            return

	# -------------------------------------------------------------------------
	# Process received message from broker
    def _on_message_received(self, message) -> None:
        try:
            self.payload = message['payload']
            payload_size = message['size']
            self.source_topic = message['topic']

            if payload_size > self.max_payload_size_bytes and self.max_payload_size_bytes > 0:
                logger.error(f'payload size({payload_size}) exceeds max_payload_size_bytes({self.max_payload_size_bytes}) from topic({self.source_topic}) payload(%.300s)', self.payload)
                self.metrics.rx_message_invalid.inc()
                self.metrics.rx_message_over_size.inc()
                return

            cloud_event = copy.deepcopy(self.cloud_event)
            if self.src_has_cloud_event:
                cloud_event['source'] = self.payload.get('source', None)
                cloud_event['compressed'] = self.payload.get('compressed', False)
                self.compressed =  self.payload.get('compressed', False)
                self.is_base64 = 'data_base64' in self.payload
            else:
                source = cloud_event.get("source", None)
                if source == None or len(source) == 0:
                    cloud_event['source'] = self.device_id
                self.compressed =  False
                self.is_base64 = False

            if not self.assess():
                self.metrics.rx_message_invalid.inc()
                return

            if not self.validate():
                self.metrics.rx_message_invalid.inc()
                return False

            if not self.normalize():
                self.metrics.rx_message_invalid.inc()
                return False

            cloud_event['device_model'] = self.device_model

            pub_data = self.get_data()

            if pub_data != None:
                self.metrics.rx_message_valid.inc()

                if self._publish_payload(self.get_destination_topic(), pub_data, cloud_event):
                    self.metrics.tx_message_total.inc()

            else:
                self.metrics.rx_message_error.inc()

        except Exception as ex:
            self.metrics.rx_message_error.inc()
            logger.error(ex)

    # -------------------------------------------------------------------------
    #
    def get_destination_topic(self) -> str:
        try:
            if self.dest_topic == None or len(self.dest_topic) == 0:
                logger.error(f'invalid destination topic({self.dest_topic})')
                return None

            return self.dest_topic

        except Exception as ex:
            logger.error(ex)
            return None

    # -------------------------------------------------------------------------
    #
    def _publish_payload(self, topic, data, cloud_event) -> bool:
        try:

            payload = self._get_cloud_event(cloud_event, data)

            if payload == None:
                return False

            logger.info(f'topic({topic}) payload(%.300s)', payload)
            logger.debug(f'data({data})')

            self.dst_broker.publish(topic, payload)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def _get_cloud_event(self, cloud_event, data) -> object:
        try:

            data_label = 'data_base64' if self.is_base64 else 'data'

            cloud_event['time'] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            cloud_event['id'] = str(uuid.uuid4())
            cloud_event[data_label] = data

            return cloud_event

        except Exception as ex:
            logger.error(ex)
            return cloud_event

    # -------------------------------------------------------------------------
    #
    def assess(self) -> bool:
        try:
            return self.check_cloud_event()

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def validate(self) -> bool:
        try:
            if not self.check_schema():
                return False

            if self.src_has_cloud_event:
                if self.is_base64:
                    self.data = copy.deepcopy(self.payload.get('data_base64', None))
                else:
                    self.data = copy.deepcopy(self.payload.get('data', None))
            else:
                self.data = copy.deepcopy(self.payload)

            if self.data == None:
                logger.error('no data')
                return False

            if self.src_has_cloud_event:
                datacontenttype = self.payload.get('datacontenttype', None)
                if datacontenttype == None:
                    logger.error(f'invalid datacontenttype({datacontenttype})')
                    return False

                if (self.compressed or self.is_base64) and type(self.data) is not str:
                    logger.error(f'compressed/base64 data but data field is not a string. data({self.data})')
                    return False

                if 'application/json' in datacontenttype:
                    if not self.compressed and not self.is_base64 and type(self.data) is not dict:
                        logger.error(f'invalid data({self.data})')
                        return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def normalize(self) -> bool:
        return True

    # -------------------------------------------------------------------------
    #
    def get_data(self):
        return self.data

    # -------------------------------------------------------------------------
    #
    def get_device_model(self):
        return self.device_model

    # -------------------------------------------------------------------------
    #
    def check_cloud_event(self) -> bool:
        try:
            if not self.src_has_cloud_event:
                return True

            spec_version = self.payload.get('specversion', None)

            if spec_version == None:
                logger.error(f'invalid payload. specversion is not defined')
                return False

            if not spec_version in ['1.0']:
                logger.error(f'invalid specversion({spec_version})')
                return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def check_schema(self) -> bool:
        try:
            if self.schema == None:
                logger.info('no schema')
                return True

            validate(instance = self.payload, schema = self.schema)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    # Validate value based on value_type
    # Validate unit
    def check_values(self, values) -> bool:
        try:

            for item in values:
                value = item.get('value', None)
                value_type = item.get('value_type', None)

                if value == None or value_type == None:
                    logger.error(f'invalid value({value}) or value_type({value_type})')
                    return False

                vtype = type(value)
                if value_type == 'string' and vtype != str:
                    logger.error(f'invalid value({value}) vtype({vtype}) for value_type({value_type})')
                    return False

                if (value_type == 'int' or value_type == 'uint') and vtype != int:
                    logger.error(f'invalid value({value}) vtype({vtype}) for value_type({value_type})')
                    return False

                if value_type == 'float' and vtype != float and vtype != int:
                    logger.error(f'invalid value({value}) vtype({vtype}) for value_type({value_type})')
                    return False

                unit = item.get('unit', None)
                if unit == None:
                    logger.error(f'invalid unit({unit})')
                    return False

                units = self.get_units()
                if units == None:
                    logger.warning(f'invalid units({units})')
                else:
                    unit = unit.lower()
                    if len(unit) > 0 and not unit in units:
                        logger.error(f'invalid unit({unit}) not listed in units({units})')
                        return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

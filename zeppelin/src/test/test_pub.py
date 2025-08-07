'''
This app is used to publish test data to the MQTT broker from file received in the blob storage (saved by Azure IoT Hub).
The app expect to have one record by row in the file.
Only the "Body" field is published to the MQTT broker.
'''
# Do this first !
import sys
import os

# Add parent directory to Python path to resolve imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.logger import get_logger, set_log_filename, LOGGING_LEVEL
LOGGING_FILENAME = 'test-pub.log'
set_log_filename(LOGGING_FILENAME)
logger = get_logger('Publisher', LOGGING_LEVEL)

import os
from os.path import isfile
import json
import argparse

from utils.tools import Tools
from communication.communication_factory import CommunicationFactory

CONFIG_FILENAME = '/config/test/test-zeppelin-v2.json'
CONFIG_FILENAME = os.getenv('CONFIG_FILENAME', CONFIG_FILENAME)

CET_EGAUGE = 'ca.qc.hydro.iot.egauge'
CET_ZIGBEE = 'ca.qc.hydro.iot.zigbee'

CLOUD_EVENT_TYPE = None

# -----------------------------------------------------------------------------
#
class Publisher():

    # -------------------------------------------------------------------------
    #
    def __init__(self):

        logger.info("constructor called")

        self.config = {}
        self.pipeline = None
        self.broker_config = {}
        self.broker = None
        self.topic = None

    # -------------------------------------------------------------------------
    #
    def init(self, name: str) -> bool:
        try:
            if not self.load_config(name):
                return False

            self.broker = CommunicationFactory.get_client(self.broker_config)

            if self.broker == None:
                logger.error(f'cannot create broker agent from configuration({self.broker_config})')
                return False

            self.device_id = self.broker.get_device_id()

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def load_config(self, name) -> bool:
        try:

            with open(CONFIG_FILENAME) as f:
                config = json.load(f)

            if not type(config) is dict:
                logger.error(f'invalid config({config})')
                return False

            self.config = config
            self.pipeline = None
            pipelines = config.get('pipelines', [])

            name = name.lower()

            for pipeline in pipelines:
                sname = pipeline.get('name', '').lower()
                if sname == name:
                    self.pipeline = pipeline
                    break

            if self.pipeline == None:
                logger.error(f'pipeline name({name}) not found')
                return False

            sclass = self.pipeline.get('class', None)
            if sclass == None:
                logger.error(f'invalid pipeline class({sclass})')
                return False

            if sclass == 'zigbee':
                CLOUD_EVENT_TYPE = CET_ZIGBEE
            elif sclass == 'egauge':
                CLOUD_EVENT_TYPE = CET_EGAUGE
            else:
                logger.error(f'invalid pipeline class({sclass})')
                return False

            self.broker_config = self.pipeline.get('source_broker', None)
            if self.broker_config == None or not type (self.broker_config) is dict:
                logger.error(f'invalid broker({self.broker_config})')
                return False

            id = self.broker_config['mqtt']['id']

            self.broker_config['mqtt']['id'] = id + '_test_pub'

            self.topic = self.broker_config.get('topic', None)
            if self.topic == None:
                logger.error(f'invalid topic({self.topic})')
                return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False


    # -------------------------------------------------------------------------
    #
    def publish_file(self, filename) -> bool:
        try:

            with open(filename) as f:
                for line in f:
                    data = json.loads(line)
                    if not type(data) is dict:
                        logger.error(f'invalid data({data})')
                        return False

                    body = data.get('Body', None)
                    if body == None:
                        logger.error(f'invalid data({data})')
                        return False

                    ce_type = body.get('type', None)

                    if CLOUD_EVENT_TYPE != None and CLOUD_EVENT_TYPE != ce_type:
                        continue

                    self.broker.publish(self.topic, body)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

# -----------------------------------------------------------------------------
#
def main():
    try:

        parser = argparse.ArgumentParser(description='Publish test data to the MQTT broker to test Zeppelin module.')
        parser.add_argument('-f', '--file', help='file to publish', required=True)
        parser.add_argument('-n', '--name', help='pipeline name', required=True)
        args = parser.parse_args()
        filename = args.file
        name = args.name

        if filename == None:
            logger.error('file not provided')
            exit(1)

        if not isfile(filename):
            logger.error(f'file({filename}) not found')
            exit(2)

        pub = Publisher()
        if not pub.init(name):
            exit(1)

        pub.publish_file(filename)

    except Exception as e:
        logger.error(str(e))

# -----------------------------------------------------------------------------
#
if __name__ == '__main__':
    main()

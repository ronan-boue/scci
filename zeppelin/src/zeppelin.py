'''
zeppelin: Zone d’Examen et de Préparation des Publications pour l’Extraction et la Légitimation des Informations Normalisées.

Ce module est responsable de faire la validation et la normalisation des données.
Il est capable de recevoir des messages de différents topics, de les valider et de les normaliser avant de les publier sur un autre topic.
Il supporte les broker de Mosquitto (MQTT) et de Azure IoT EdgeHub. Il contient aussi un processeur pour lire les messages en provenance du cloud Azure.
La liste des sources et des destinations (pipelines) est définie dans le fichier de configuration zeppelin.json.

Plusieur métriques sont exposées par ce module via Prometheus.

'''
import os
import json
import time
from prometheus.prometheus import PrometheusServer

from utils.logger import get_logger, LOGGING_LEVEL
from utils.config_manager import ConfigManager
from processors.processor_factory import ProcessorFactory
from metrics import Metrics
from _version import __version__

CONFIG_FILENAME = '/config/zeppelin.json'
CHECK_CONFIG_INTERVAL_SEC = 10

CONFIG_FILENAME = os.getenv('CONFIG_FILENAME', CONFIG_FILENAME)

prometheus_metrics = Metrics()

logger = get_logger('Zeppelin', LOGGING_LEVEL)
logger.info(f'Zeppelin version({__version__})')

# -----------------------------------------------------------------------------
#
class Zeppelin:

    # -------------------------------------------------------------------------
    #
    def __init__(self):
        logger.info("constructor called")

        self.config = {}
        self.pipelines = []
        self.processors = []
        self.metrics = prometheus_metrics

    # -------------------------------------------------------------------------
    #
    def init(self) -> bool:
        try:
            if not self._load_config():
                return False

            if not self._init_processors():
                return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def start(self) -> bool:
        try:
            logger.info('Zeppelin starting processors')
            result = True

            for proc in self.processors:
                proc.start()

            logger.info('Zeppelin all processors started')

            return result

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def stop(self) -> bool:
        try:
            logger.info('Zeppelin stopping processors')

            for proc in self.processors:
                proc.stop()
                proc.join()

            logger.info('Zeppelin all processors stopped')

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def _load_config(self) -> bool:
        try:

            with open(CONFIG_FILENAME) as f:
                config = json.load(f)

            if not type(config) is dict:
                logger.error(f'invalid config({config})')
                return False

            self.config = config
            version = self.config.get('version', '')
            version_date = self.config.get('version_date', '')

            self.metrics.version.info({'version': version, 'version_date': version_date, 'module': 'zeppelin'})
            logger.info(f'version({version}) version_date({version_date})')

            self.pipelines = None
            if 'pipelines' in config:
                self.pipelines = config.get('pipelines', None)
            elif 'sources' in config:   # la premiere version de zeppelin.json utilisait 'sources' au lieu de 'pipelines'
                self.pipelines = config.get('sources', None)

            if self.pipelines == None or not type(self.pipelines) is list or len(self.pipelines) == 0:
                logger.error(f'invalid pipelines({self.pipelines})')
                return False

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def _init_processors(self) -> bool:
        try:

            for source in self.pipelines:

                sclass = source['class']
                name = source['name']
                proc = ProcessorFactory.get_processor(sclass)

                if proc == None:
                    logger.error(f'invalid source class({sclass}) name({name})')
                    return False

                if not proc.init(self.config, source, self.metrics):
                    logger.error(f'processor init failed for class({sclass}) name({name})')
                    return False

                self.processors.append(proc)

            return True

        except Exception as ex:
            logger.error(ex)
            return False

# -----------------------------------------------------------------------------
# Build a list of files to monitor for changes
def get_monitoring_files():
    try:
        files = [CONFIG_FILENAME]

        with open(CONFIG_FILENAME) as f:
            config = json.load(f)

        if not type(config) is dict:
            logger.error(f'invalid config({config})')
            return files

        pipelines = None
        if 'pipelines' in config:
            pipelines = config.get('pipelines', None)
        elif 'sources' in config:   # la premiere version de zeppelin.json utilisait 'sources' au lieu de 'pipelines'
            pipelines = config.get('sources', None)


        if pipelines == None or not type(pipelines) is list or len(pipelines) == 0:
            logger.error(f'invalid pipelines({pipelines})')
            return files

        for pipeline in pipelines:
            json_schema = pipeline.get('json_schema', None)
            if json_schema != None and len(json_schema):
                files.append(json_schema)

            source_config_filename = pipeline.get('config', None)
            if source_config_filename != None and len(source_config_filename) > 0:
                files.append(source_config_filename)

        return files

    except Exception as e:
        logger.error(str(e))
        return files


# -----------------------------------------------------------------------------
#
def main():
    try:
        # Check if the configuration file exists
        if not os.path.isfile(CONFIG_FILENAME):
            logger.error(f'config file({CONFIG_FILENAME}) not found')
            exit(1)

        # Monitor our configuration files for changes
        config_manager = ConfigManager()
        files = get_monitoring_files()
        for file in files:
            config_manager.add(file)

        # Expose some metrics with Prometheus
        prometheus = PrometheusServer()
        if not prometheus.init():
            logger.error('Prometheus server init failed')
            exit(1)

        if not prometheus.start():
            logger.error('Prometheus server start failed')
            exit(1)

        # Instantiate our Zeppelin module
        z = Zeppelin()
        if not z.init():
            exit(2)

        if not z.start():
            exit(3)

        while True:
            if config_manager.is_modified():
                logger.info('config file modified')
                z.stop()

                z = Zeppelin()
                if not z.init():
                    exit(2)

                if not z.start():
                    exit(3)

            time.sleep(CHECK_CONFIG_INTERVAL_SEC)

    except Exception as e:
        logger.error(str(e))

# -----------------------------------------------------------------------------
#
if __name__ == '__main__':
    main()

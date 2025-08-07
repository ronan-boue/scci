from .generic_processor import GenericProcessor
from .egauge_processor import EgaugeProcessor
from .zigbee_processor import ZigbeeProcessor
from .ibr.gdp_processor import GDPProcessor
from .ibr.ibr_processor import IBRProcessor
from .rci.rci_processor import RCIProcessor
from .c2d_processor import C2DProcessor
from .rci.rci_processor import RCIProcessor
from .rci.rci_command_processor import RCICommandProcessor
from .processor_interface import ProcessorInterface

from utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('ProcessorFactory', LOGGING_LEVEL)

# -----------------------------------------------------------------------------
#
class ProcessorFactory:
    # -------------------------------------------------------------------------
    #
    @staticmethod
    def get_processor(sclass) -> ProcessorInterface:

        sclass = sclass.strip().lower()

        if sclass == 'generic':
            return GenericProcessor()
        elif sclass == 'egauge':
            return EgaugeProcessor()
        elif sclass == 'zigbee':
            return ZigbeeProcessor()
        elif sclass == 'gdp':
            return GDPProcessor()
        elif sclass == 'ibr':
            return IBRProcessor()
        elif sclass == 'cloud2device':
            return C2DProcessor()
        elif sclass == 'rci':
            return RCIProcessor()
        elif sclass == 'rci_command':
            return RCICommandProcessor()
        else:
            logger.error(f'invalid class({sclass})')
            return None


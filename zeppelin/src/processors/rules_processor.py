from utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('RulesProcessor', LOGGING_LEVEL)


# -----------------------------------------------------------------------------
#
class RulesProcessor():

    # -------------------------------------------------------------------------
    #
    def init(self, rules):
        self.rules = rules

    # -------------------------------------------------------------------------
    #
    def check_value(self, value, unit) -> bool:
        try:
            if self.rules == None:
                logger.error(f'invalid rules({self.rules})')
                return False

            if len(self.rules) == 0:
                return True

            if value == None or unit == None or len(unit) == 0:
                return True

            # TODO: check value and unit

            return True

        except Exception as ex:
            logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    #
    def get_units(self):
        return self.rules.get('units', None)

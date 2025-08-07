'''
Load config file
Detect changes in config file (based on file size and timestamp)
'''
import os
from .logger import get_logger

# ---------------------------------------------------------------------------------
#
class ConfigManager:

    # -----------------------------------------------------------------------------
    #
    class ConfigFile:

        # -------------------------------------------------------------------------
        #
        def __init__(self, file_name):
            self.logger = get_logger('ConfigFile')
            self.logger.info(f'file_name({file_name})')

            self.file_name = file_name
            self.size = -1
            self.timestamp = 0
            self.stat()

        # -------------------------------------------------------------------------
        #
        def stat(self):
            try:
                self.size = os.path.getsize(self.file_name)
                self.timestamp = os.path.getmtime(self.file_name)

                return True

            except Exception as ex:
                self.logger.error(ex)
                return False

        # -------------------------------------------------------------------------
        #
        def is_modified(self):
            try:
                size = self.size
                timestamp = self.timestamp
                self.stat()

                if size != self.size or timestamp != self.timestamp:
                    self.logger.info(f'file_name({self.file_name}) modification detected')
                    return True

                return False

            except Exception as ex:
                self.logger.error(ex)
                return False
            
    # -------------------------------------------------------------------------
    #
    def __init__(self):
        self.logger = get_logger('ConfigManager')
        self.logger.info('constructor called')
        self.config_files = []

    # -------------------------------------------------------------------------
    #
    def add(self, file_name):
        try:
            self.logger.info(f'file_name({file_name})')

            file = ConfigManager.ConfigFile(file_name)
            self.config_files.append(file)

        except Exception as ex:
            self.logger.error(ex)
        
    # -------------------------------------------------------------------------
    # Return True if any file in the list was modified since the last verification
    def is_modified(self):
        try:
            res = False

            for file in self.config_files:
                if file.is_modified():
                    res = True

            return res

        except Exception as ex:
            self.logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    # Return a list of file name that was modified since the last verification
    def get_modified(self):
        try:
            res = []

            for file in self.config_files:
                if file.is_modified():
                    res.append(file.file_name)

            return res

        except Exception as ex:
            self.logger.error(ex)
            return None

import json
import os
import re
from .logger import get_logger

# DATA_ID_PATTERN = r'\[.*\w-.*\w\]'
# DATA_ID_PATTERN = r'\[.*\w\..*\w\]'
DATA_ID_PATTERN = r'\[.*\w\]'

# -------------------------------------------------------------------------------------------------
#
class Tools:
    logger = get_logger('Tools')

    # -------------------------------------------------------------------------------------------------
    #
    @staticmethod
    def load_json(filename):
        try:
            Tools.logger.info(filename)
            data = None

            if os.path.isfile(filename):
                with open(filename) as f:
                    data = json.load(f)
            else:
                Tools.logger.warn(
                    'filename({}) does not exists'.format(filename))

            return data

        except Exception as ex:
            Tools.logger.error(ex)
            return None

    # -------------------------------------------------------------------------------------------------
    #
    @staticmethod
    def save_json(filename, data):
        try:
            Tools.logger.info(filename)

            with open(filename, 'w') as f:
                json.dump(data, f, ensure_ascii=True, indent=4)

            return True

        except Exception as ex:
            Tools.logger.error(ex)
            return False

    # -------------------------------------------------------------------------
    # usage: list_files('my/folder', '.json')
    @staticmethod
    def list_files(dir_path, ext):

        try:
            # list to store file name
            files = []

            # Iterate directory
            for file in os.listdir(dir_path):
                if file.endswith(ext):
                    files.append(file)

            return files

        except Exception as ex:
            Tools.logger.error(ex)
            return []

    # -------------------------------------------------------------------------
    # Extract Data ID from string. Data ID is a standardized string that uniquely identify data.
    # Data ID is expected to be within backets []
    # Ex: [LAL-W], [L1-V], [EPOCH-MS]
    # Return Data ID without brackets if a Data ID is found in the string
    # Return None if no Data ID is found or an exception occur
    @staticmethod
    def get_data_id(text, pattern = DATA_ID_PATTERN):

        try:
            x = re.search(pattern, text)

            if x == None:
                return None
            
            return text[x.start()+1 : x.end()-1]

        except Exception as ex:
            Tools.logger.error(ex)
            return None


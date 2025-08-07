"""
SyncIoT is a Python script that listens to events from Azure IoT Hub and stores them in a PostgreSQL database.
It uses the Azure IoT Hub client to subscribe to events and the PostgreSQL client to insert data into the database.
The script is designed to run as a background thread and can be configured using a JSON file.

Secrets are managed using environment variables (until Azure Key Vault is available).
    AZURE_IOTHUB_CONNECTION_STRING
    AZURE_IOTHUB_CONSUMER_GROUP
    AZURE_POSTGRESQL_HOST
    AZURE_POSTGRESQL_PORT
    AZURE_POSTGRESQL_DATABASE
    AZURE_POSTGRESQL_USERNAME
    AZURE_POSTGRESQL_PASSWORD

The script also includes a configuration file (synciot.json) that defines the routes for the events and the tables in the PostgreSQL database.
To create a different configuration, copy the synciot.json file and modify it as needed.
There should be one configuration file per IoT Hub.
You can provide the configuration file path using the environment variable SYNCIOT_CONFIG_FILENAME.

"""
import os
import json
import time
import queue
import threading
import datetime
import requests

from services.azure_iot_hub_client import AzureIoTHubClient
from services.postgres_client import PostgresClient

from metrics import Metrics
from tools.logger import get_logger
from _version import __version__

logger = get_logger("SyncIoT")
logger.info(f'SyncIoT version({__version__})')

SYNCIOT_CONFIG_FILENAME = "./config/synciot.json"
SYNCIOT_CONFIG_FILENAME = os.getenv("SYNCIOT_CONFIG_FILENAME", SYNCIOT_CONFIG_FILENAME)
CONFIG_TABLE = os.getenv("CONFIG_TABLE", "public.synciot_config")
CONFIG_KEY = os.getenv("CONFIG_KEY", "synciot_config")
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", 900))
UPDATE_CONFIG_INTERVAL_SEC = int(os.getenv("UPDATE_CONFIG_INTERVAL_SEC", 300))
BACKLOG_INTERVAL_SEC = int(os.getenv("BACKLOG_INTERVAL_SEC", 30))
DEFAULT_ACTION = "insert"
CLOUD_HOSTED_DABATASE=False

# -----------------------------------------------------------------------------
#
class SyncIoT:

    # -------------------------------------------------------------------------
    #
    def __init__(self):
        self.iot_hub_client = AzureIoTHubClient()
        self.postgres_client = PostgresClient()
        self.queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.config = None
        self.config_table = CONFIG_TABLE
        self.config_key = CONFIG_KEY
        self.update_config_interval_sec = UPDATE_CONFIG_INTERVAL_SEC
        self.last_config_data_update_sec = 0
        self.last_config_update = 0
        self.config_data = {"timestamp": 0} # Last timestamp of IoT Hub received data
        self.metrics = Metrics()
        self.total_events = self.metrics.add_counter("total_events")
        self.last_event_time: datetime.datetime = None

    # -------------------------------------------------------------------------
    #
    def init(self) -> bool:
        try:
            with open(SYNCIOT_CONFIG_FILENAME, "r") as f:
                self.config = json.load(f)

            if self.config == None:
                logger.error(f"Failed to load configuration from {SYNCIOT_CONFIG_FILENAME}")
                return False

            self.iothub = self.config.get("iothub")
            if CLOUD_HOSTED_DABATASE:
                self.postgresql = self.config.get("postgresql")
            else:
                self.postgresql = self.config.get("postgresql_local")
            
            self.routes = self.config.get("routes")

            if self.iothub == None or self.postgresql == None or self.routes == None:
                logger.error(f"Failed to load configuration from {SYNCIOT_CONFIG_FILENAME}")
                return False

            self.config_data["timestamp"] = int(time.time())
            self.config_table = self.postgresql.get("config_table", self.config_table)
            self.config_key = self.postgresql.get("config_key", self.config_key)
            self.update_config_interval_sec = self.postgresql.get("update_config_interval_sec", self.update_config_interval_sec)
            logger.info(f"config_table({self.config_table}) config_key({self.config_key}) update_config_interval_sec({self.update_config_interval_sec})")

            if not self._update_secrets():
                logger.error(f"Failed to update secrets")
                return False

            # Initialize IoT Hub client
            if not self.iot_hub_client.init(connection_string=self.iothub.get("connection_string"), consumer_group=self.iothub.get("consumer_group")):
                logger.error(f"Failed to initialize IoT Hub client")
                return False

            if not self.postgres_client.connect(self.postgresql):
                logger.error(f"Failed to initialize PostgreSQL client and connect to database")
                return False

            if not self.load_config_data():
                logger.error(f"Failed to load configuration data from PostgreSQL database")
                return False

            return True
        except Exception as e:
            logger.error(f"Failed to initialize SyncIoT: {e}")
            return False

    # -------------------------------------------------------------------------
    #
    def _update_secrets(self) -> bool:
        """
        Update secrets from Azure Key Vault.
        This function is a placeholder and should be implemented to update secrets from Azure Key Vault.

        Until Azure Key Vault is available, secrets are stored in environment variables.

        IoT Hub Connection String is stored in self.iothub from:
            1. Azure Key Vault
            2. Environment variable

        PostgreSQL username and password are stored in self.postgresql from:
            1. Azure Key Vault
            2. Environment variable
        """
        try:
            result = True

            conn_string = os.getenv("AZURE_IOTHUB_CONNECTION_STRING", None)
            if conn_string is not None:
                self.iothub["connection_string"] = conn_string
                logger.info(f"Updated IoT Hub connection string from environment variable (AZURE_IOTHUB_CONNECTION_STRING)")
            else:
                logger.error(f"Failed to update IoT Hub connection string from environment variable (AZURE_IOTHUB_CONNECTION_STRING)")
                result = False

            consumer_group = os.getenv("AZURE_IOTHUB_CONSUMER_GROUP", None)
            if consumer_group is not None:
                self.iothub["consumer_group"] = consumer_group
                logger.info(f"Updated IoT Hub consumer group from environment variable (AZURE_IOTHUB_CONSUMER_GROUP)")

            host = os.getenv("AZURE_POSTGRESQL_HOST", None)
            if host is not None:
                self.postgresql["host"] = host
                logger.info(f"Updated PostgreSQL host from environment variable (AZURE_POSTGRESQL_HOST)")

            port = os.getenv("AZURE_POSTGRESQL_PORT", None)
            if port is not None:
                self.postgresql["port"] = int(port)
                logger.info(f"Updated PostgreSQL port from environment variable (AZURE_POSTGRESQL_PORT)")

            database = os.getenv("AZURE_POSTGRESQL_DATABASE", None)
            if database is not None:
                self.postgresql["database"] = database
                logger.info(f"Updated PostgreSQL database from environment variable (AZURE_POSTGRESQL_DATABASE)")

            username = os.getenv("AZURE_POSTGRESQL_USERNAME", None)
            if username is not None:
                self.postgresql["user"] = username
                logger.info(f"Updated PostgreSQL username from environment variable (AZURE_POSTGRESQL_USERNAME)")
            else:
                logger.error(f"Failed to update PostgreSQL username from environment variable (AZURE_POSTGRESQL_USERNAME)")
                result = False

            password = os.getenv("AZURE_POSTGRESQL_PASSWORD", None)
            if password is not None:
                self.postgresql["password"] = password
                logger.info(f"Updated PostgreSQL password from environment variable (AZURE_POSTGRESQL_PASSWORD)")
            else:
                logger.error(f"Failed to update PostgreSQL password from environment variable (AZURE_POSTGRESQL_PASSWORD)")
                result = False
            
            sslmode = os.getenv("AZURE_POSTGRESQL_SSLMODE", None)
            if sslmode is not None:
                self.postgresql["sslmode"] = sslmode
                logger.info(f"Updated PostgreSQL sslmode from environment variable (AZURE_POSTGRESQL_SSLMODE)")
            else:
                logger.error(f"Failed to update PostgreSQL sslmode from environment variable (AZURE_POSTGRESQL_SSLMODE)")
                result = False

            return result

        except Exception as e:
            logger.error(f"Failed to update secrets: {e}")
            return False



    # -------------------------------------------------------------------------
    #
    def start_thread(self) -> None:
        try:
            logger.info("Starting SyncIoT thread...")
            thread = threading.Thread(target=self.run, daemon=True)
            thread.start()
            logger.info("SyncIoT thread started.")

        except Exception as e:
            logger.error(f"Failed to run SyncIoT in thread: {e}")

    # -------------------------------------------------------------------------
    #
    def get_event_count(self) -> int:
        return self.total_events.get_value()

    # -------------------------------------------------------------------------
    #
    def get_last_event_time(self) -> str:
        if self.last_event_time is None:
            return "No events received yet"
        return self.last_event_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    # -------------------------------------------------------------------------
    #
    def send_to_zeppelin(data):
        try:
            url = "http://zeppelin:8001/process"
            response = requests.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to send data to Zeppelin: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error communicating with Zeppelin: {e}")
            return None
        
    # -------------------------------------------------------------------------
    #
    def run(self) -> None:
        try:
            logger.info("Starting SyncIoT...")

            start_position_epoch = self.config_data.get("timestamp", 0)
            if start_position_epoch == 0:
                start_position_epoch = int(time.time()) - BACKLOG_INTERVAL_SEC

            start_position = datetime.datetime.fromtimestamp(start_position_epoch)

            logger.info(f"Starting SyncIoT from position datetime({start_position}) epoch({start_position_epoch})")

            self.iot_hub_client.subscribe_to_events(self.queue, start_position)

            logger.info("Event listening started.")

            while True:
                while not self.queue.empty():
                    event = self.queue.get(block=False)
                    if event:
                        self.total_events.inc()
                        self._handle_event(event)
                    else:
                        logger.warning("Received None event")
                    self.queue.task_done()

                # Update the configuration data in PostgreSQL database after a few events
                if self.total_events.get_value() > 10:
                    self.save_config_data()

                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.warning("Message listening stopped.")
        except Exception as e:
            logger.error(f"Failed to run SyncIoT: {e}")
            self.iot_hub_client.disconnect()

    # -------------------------------------------------------------------------
    #
    def _handle_event(self, event) -> None:
        try:
            """
            Handle the event received from Azure IoT Hub.
            This function processes the event and stores it in the PostgreSQL database.
            event is expected to be a CloudEvent
            """
            if event is None:
                logger.warning("Received None event")
                return

            ce = json.loads(event)

            if ce is None:
                logger.warning("Received invalid event")
                return

            data = ce.get("data")
            if data is None:
                logger.warning("Received event does not contain 'data' field")
                return

            uuid = ce.get("id", None)
            if uuid is None or len(uuid) == 0:
                logger.warning("Received event does not contain 'id' field")
                return

            device = ce.get("source")
            if device is None or len(device) == 0:
                logger.warning("Received event does not contain 'source' field")
                return

            try:
                tm = ce.get("time", None)
                if tm != None:
                    self.last_event_time = datetime.datetime.fromisoformat(tm)
            except Exception as e:
                logger.error(f"Failed to parse event time: {e} ce({ce})")
                self.last_event_time = None

            sdata = json.dumps(data)
            logger.info(f"Rx device {device} data: {sdata:.100}")

            now = int(time.time())

            table, action = self.get_table(ce)
            if table is None or action is None:
                logger.warning(f"Received event does not match any route: {event}")
                return

            if action == "insert":
                if not self.postgres_client.insert_data_with_uuid(table, device, uuid, now, event):
                    logger.error(f"Failed to insert data into PostgreSQL database table({table}) device({device}) uuid({uuid}) event({event})")
                    exit(1)
            else:
                logger.error(f"Unknown action '{action}' for table '{table}'")

            count = self.total_events.get_value()
            if count > 0 and count % 50 == 0:
                logger.info(f"Processed {count} events")
                self.save_config_data()

        except Exception as e:
            logger.error(f"{e}")

    # -------------------------------------------------------------------------
    #
    def get_table(self, cloud_event) -> tuple [str, str]:
        """
        Get the table name and action based on routes defined in the configuration file.
        The table name is used to store the data in the PostgreSQL database.
        The action is used to determine the type of operation to perform on the database.
        """
        try:
            schema = self.postgresql.get("default_schema")
            table = self.postgresql.get("default_table")
            table = f"{schema}.{table}"
            action = DEFAULT_ACTION

            route = self.get_route(cloud_event)

            if route != None:
                schema = route.get("schema", schema)
                table = route.get("table", table)
                table = f"{schema}.{table}"
                action = route.get("action", action)

        except Exception as e:
            logger.error(f"Failed to get table name and action: {e}")

        finally:
            return table, action

    # -------------------------------------------------------------------------
    #
    def get_route(self, cloud_event) -> dict:
        """
        Get the route based on the event type and source.
        The route is used to determine the table name and action to perform on the database.
        """
        try:
            for route in self.routes:
                filters = route.get("filters")

                if filters is None:
                    logger.error(f"Route {route} does not contain filters")
                    continue

                match = True
                for filter in filters:
                    attr = filter.get("attribute", None)
                    value = filter.get("value", None)

                    if attr == None or value == None or cloud_event.get(attr, None) != value:
                        match = False
                        break

                if match:
                    return route

            return None

        except Exception as e:
            logger.error(f"Failed to get route: {e}")
            return None

    # -------------------------------------------------------------------------
    #
    @staticmethod
    def epoch_to_iso8601(epoch_time: int) -> str:
        """
        Convert epoch time to ISO 8601 format.
        """
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch_time)) + "Z"

    # -------------------------------------------------------------------------
    #
    def load_config_data(self) -> bool:
        """
        Read config data from PostgreSQL database.
        """
        try:
            result = self.postgres_client.read_config(self.config_table, self.config_key)
            if result is None or len(result) == 0:
                logger.warning(f"Failed to load configuration data from PostgreSQL database table({self.config_table}) key({self.config_key})")
                return self.save_config_data(force=True)

            data = result[1]
            if data is None:
                logger.error(f"Failed to load configuration data from PostgreSQL database")
                return False

            if type(data) is str:
                data = json.loads(data)

            if data is None:
                logger.error(f"Failed to load configuration data from PostgreSQL database")
                return False

            self.config_data = data

            logger.info(f"Loaded configuration data({self.config_data}) from PostgreSQL database table({self.config_table}) key({self.config_key})")
            self.last_config_data_update_sec = int(time.time())

            return True

        except Exception as e:
            logger.error(f"Failed to get route: {e}")
            return False


    # -------------------------------------------------------------------------
    #
    def save_config_data(self, force = False) -> bool:
        """
        Save config data to PostgreSQL database.
        """
        try:
            now = int(time.time())
            if now - self.last_config_data_update_sec < self.update_config_interval_sec and not force:
                return True

            self.last_config_data_update_sec = now

            if self.last_event_time != None:
                self.config_data["timestamp"] = int(self.last_event_time.timestamp()) - BACKLOG_INTERVAL_SEC
            else:
                self.config_data["timestamp"] = now - BACKLOG_INTERVAL_SEC

            return self.postgres_client.upsert_config(self.config_table, self.config_key, json.dumps(self.config_data))

        except Exception as e:
            logger.error(f"Failed to get route: {e}")
            return False

# -----------------------------------------------------------------------------
#
def test_config():
    try:
        print("Starting SyncIoT test configuration...")
        logger.info("Starting SyncIoT...")
        synciot = SyncIoT()

        if not synciot.init():
            logger.error("Failed to initialize SyncIoT")
            return

        time.sleep(10)
        if not synciot.save_config_data(force=True):
            logger.error("Failed to save configuration data to PostgreSQL database")

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
        # Clean up resources
        synciot.stop_thread()  # Assuming SyncIoT has a stop_thread method
        print("SyncIoT thread stopped.")

    finally:
        logger.info("SyncIoT finished successfully.")

# -----------------------------------------------------------------------------
#
def main():
    try:
        print("Starting SyncIoT...")
        logger.info("Starting SyncIoT...")
        synciot = SyncIoT()

        if not synciot.init():
            logger.error("Failed to initialize SyncIoT")
            return

        synciot.run()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
        # Clean up resources
        synciot.stop_thread()  # Assuming SyncIoT has a stop_thread method
        print("SyncIoT thread stopped.")

    finally:
        logger.info("SyncIoT finished successfully.")

# -----------------------------------------------------------------------------
#
if __name__ == "__main__":
    main()
    # test_config()
"""
https://learn.microsoft.com/en-us/python/api/azure-eventhub/azure.eventhub.eventhubconsumerclient?view=azure-python#azure-eventhub-eventhubconsumerclient-receive

Partition ownership changes frequently
https://learn.microsoft.com/en-us/azure/developer/java/sdk/troubleshooting-messaging-event-hubs-processor

https://learn.microsoft.com/en-us/answers/questions/1184327/how-to-fix-azure-eventhub-exceptions-authenticatio

TODO: Store credentials (the connection string) in Azure Key Vault

In Shared access policies, add a new access policy:
    name: subscriber
    permissions: Registry Read, Service Connect

In Built-in endpoints, Event Hub compatible endpoint,
    select the Shared Access Policy: subscriber
    copy Event Hub-compatible endpoint (the connection string starting with Endpoint=sb://iothub-ns)

"""
import sys
import os
import threading
from azure.eventhub import EventHubConsumerClient

# Add the parent directory to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.logger import get_logger

logger = get_logger("IoTHub")

# -----------------------------------------------------------------------------
#
class AzureIoTHubClient:
    # -------------------------------------------------------------------------
    #
    def __init__(self):
        self.queue = None

    # -------------------------------------------------------------------------
    #
    def init(self, connection_string, consumer_group = "$Default") -> bool:
        """
        Initialize the Azure IoT Hub client with the provided connection string.
        """
        try:
            self.client = EventHubConsumerClient.from_connection_string(conn_str=connection_string, consumer_group=consumer_group)
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Azure IoT Hub client: {e}")
            return False

    # -------------------------------------------------------------------------
    #
    def subscribe_to_events(self, queue, start_position="@latest"):
        """
        Subscribe to device-to-cloud messages.
        """
        try:
            logger.info(f"Listening for events from Azure IoT Hub with start_position({start_position})")

            self.queue = queue
            self.start_position = start_position
            threading.Thread(target=self._listen, daemon=True).start()
            logger.info("Event listening started.")

        except Exception as e:
            logger.error(f"Error while receiving messages: {e}")

    # -------------------------------------------------------------------------
    #
    def _listen(self):
        """
        Start listening for events from the Azure IoT Hub.
        """
        try:
            logger.info(f"Start receive event with start_position({self.start_position})")

            self.client.receive_batch(
                on_event_batch=self.on_event_batch,
                starting_position=self.start_position
            )

        except Exception as e:
            logger.error(f"Error while receiving messages: {e}")

    # -------------------------------------------------------------------------
    #
    def on_event(self, partition_context, event):
        """
        Receive and process events from the Azure IoT Hub.
        """
        try:
            if event is None:
                return

            self.queue.put(event.body_as_str())
            # print(f"Partition: {partition_context.partition_id}")
            # print(f"Partition: {partition_context.consumer_group}")
            # print(f"Partition: {partition_context.eventhub_name}")
            # print(f"Partition: {partition_context.fully_qualified_namespace}")
        except Exception as e:
            logger.error(f"Error while receiving event: {e}")

    # -------------------------------------------------------------------------
    #
    def on_event_batch(self, partition_context, events):
        """
        Receive and process events from the Azure IoT Hub.
        """
        try:
            if events is None:
                return

            logger.info("Rx Events count({})".format(len(events)))

            for event in events:
                if event is None:
                    continue
                self.queue.put(event.body_as_str())

            # print(f"Partition: {partition_context.partition_id}")
            # print(f"Partition: {partition_context.consumer_group}")
            # print(f"Partition: {partition_context.eventhub_name}")
            # print(f"Partition: {partition_context.fully_qualified_namespace}")
        except Exception as e:
            logger.error(f"Error while receiving event: {e}")

    # -------------------------------------------------------------------------
    #
    def disconnect(self):
        """
        Disconnect from the Azure IoT Hub.
        """
        try:
            self.client.close()
            logger.info("Disconnected from Azure IoT Hub.")
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")

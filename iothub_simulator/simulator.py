import os
import time
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential

# On utilise les chaînes de connexion Event Hub au sein de l'IoT Hub (onglet "Point de terminaison prédéfinis")
AZURE_EVENT_HUB_CONNECTION_STRING = os.getenv("AZURE_IOTHUB_CONNECTION_STRING", "Endpoint=sb://iothub-ns-iotretlabc-55367731-fba84cf20d.servicebus.windows.net/;SharedAccessKeyName=iothubowner;SharedAccessKey=AlrE5vpZtQGB+lIA5/yQso/Az0gB8nqZTAIoTAFyMnE=;EntityPath=iotretlabca296f")
EVENT_HUB_NAME = os.getenv("EVENT_HUB_NAME", "iotretlabca296f")

# Création du client Event Hub Producer
producer = EventHubProducerClient.from_connection_string(
    conn_str=AZURE_EVENT_HUB_CONNECTION_STRING,
    eventhub_name=EVENT_HUB_NAME,
    credential=DefaultAzureCredential()
)

def send_hello_world_message():
    """Envoie un message 'Hello World' à Event Hub."""
    try:
        with producer:
            event_data_batch = producer.create_batch()
            event_data_batch.add(EventData("Hello SCCI"))
            producer.send_batch(event_data_batch)
            print("Message envoyé : Hello SCCI")
    except Exception as e:
        print(f"Erreur lors de l'envoi du message : {e}")

print("Démarrage du simulateur... Envoi d'un message toutes les 5 secondes.")

try:
    while True:
        send_hello_world_message()
        time.sleep(5)
except KeyboardInterrupt:
    print("\nArrêt du simulateur.")
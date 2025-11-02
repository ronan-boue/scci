Commentaires globals: 

Quel est, et ou est la demande de cette documentation ?

Commentaires spécifiques:

Le ticket Jira INNOC-3199 mention qu'il s'agit de document Zeppelin dans le Confluence d'Infra IoT, n'est-ce pas plutôt Zeppelin pour SCCI ?

Dans la section Prérequis, expliquer quels sont les problématiques réseaux d'installation de paquet et ce que résout Fiddler

Dans la section Prérequis, Pourquoi installer SyncIoT ?

Dans la section Prérequis, on pointe sur les sources du module Zeppelin ici (https://PlateformeDEV-LTE@dev.azure.com/PlateformeDEV-LTE/PEPC/_git/zeppelin) et il y a aussi ce lien que Jean-François Gauthier a fait (https://git.hydro.qc.ca/projects/RET-I/repos/zeppelin). Quel est le lien qui pointe vers la bonne source de code ?

Dans la section 1, on parle de données Serial comme type de Pipeline. Il faut documenter le pourquoi de ce nouveau type de Pipeline. Est-ce ce que le chercheur Juan Carlos a énoncé ?

Dans la section 1, il faudrait expliquer brievement la structure de Zeppelin qui est un modèle de pipelines (chaque pipeline contient 2 connecteurs; une source et une destination) et de processeurs. Et que ZEPPELIN contient 4 types de connecteurs; Cloud-to-Device (iot_device_agent.py); class=iotdevice, Cloud-to-Edge (iot_hub_agent.py); class=iothub, Azure IoT Edge Hub (iot_edge_agent.py); class=iotedge et Mosquitto MQTT (mqtt_agent.py); class=mqtt.

Dans la section 1.4.1, il faut expliquer ce à quoi sert un fichier schema et le lien avec le fichier du pipeline config/zeppelin-serial.json

Dans la section 1.5.1, il faut documenter ce que fait src/utils/serial_parser.py et où il s'intègre dans l'architecture logiciel de Zeppelin.

Globalement, il faut mettre au début de cette documentation un schéma d'architecture logiciel de Zeppelin dans ce contexte d'ingestion de donnée de type serial. Voici un exemple de schéma : 
ZEPPELIN 

Dans la section 1.5.2, même commentaires que 8 pour examples/serial_integration.py.

Dans la section 1.6 Démarrage de Zeppelin, on démarre Zeppelin directement dans un shell. Pourquoi ce Zeppelin n'est-il pas containeurisé comme l'utilisation normal de Zeppelin dans un environnement Azure IoT ?

Dans la section 1.6, qu'arrive-t-il avec l'ingestion des données simulées ? Où vont-elles ? Est-ce que ça fonctionne ?

Dans la section 1.7 Surveillance er débogage, où vont les logs ?

Dans la section 1.10 Dépannage, on mentionne "Consultez les logs"; où sont ces logs ?

Dans la section 1.10.2, on donne des exemples de commandes utils pour mosquitto. Où est installé mosquitto ?

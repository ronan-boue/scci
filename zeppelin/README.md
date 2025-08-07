# Introduction
Project: PEPC (Programme d'établissement des profils de consommation) <br /><br />
This module (zeppelin) assess, validate and normalize data before publishing data to consumers. <br />
En français, ZEPPELIN: Zone d’Examen et de Préparation des Publications pour l’Extraction et la Légitimation des Informations Normalisées. <br /><br />

ZEPPELIN est structuré selon un modèle de pipelines et de processor. <br />
Chaque pipeline contient 2 connecteurs: une source et une destination. <br />
Le processor jour un rôle de validation et de transformation (au besoin). <br /><br />

ZEPPELIN contient 4 types de connecteurs. <br />
1.	Cloud-to-Device (iot_device_agent.py); class=iotdevice
2.	Cloud-to-Edge (iot_hub_agent.py); class=iothub
3.	Azure IoT Edge Hub (iot_edge_agent.py); class=iotedge
4.	Mosquitto MQTT (mqtt_agent.py); class=mqtt

<br />

## Configuration
La configuration est entièrement dynamique. <br />
Voir le fichier /config/zeppelin.json pour un exemple de configuration. <br />
Il y a des exemples de configuration dans le répertoire /config/exemples. <br />

## Cloud-to-Device
Le connecteur IoTDeviceAgent se présente comme un device au IoT Hub et utilise la Connection String du fichier /etc/aziot/config.toml pour se connecter au IoT Hub. Voir les détails dans le fichier iot_device_agent.py.<br />
Ce connecteur ne retourne aucune confirmation à la source. Il n'est pas 100% fiable. Pour plus de fiabilité, il est préférable d'utiliser le connecteur IoTHubAgent. <br />
Le rôle du processor C2DProcessor est essentielement un rôle de routeur entre le IoT Hub du cloud et le IoT Edge Hub dans la passerelle.
<br />
Les messages en provenance du cloud doivent être traités dans un processor séparé. <br />
Les messages en provenance du cloud doivent comprendre une propriété "dest_topic=c2d-xyz", où "c2d-xyz" est le nom d'un topic unique référencé dans une route du Deployement-Template. <br />
Voici l'exemple d'une route pour un message de GDP: <br />
    "route": "FROM /messages/modules/zeppelin/outputs/c2d-gdp INTO BrokeredEndpoint(\"/modules/zeppelin/inputs/gdp\")" <br />
<br />
## Cloud-to-Edge
Le connecteur IoTHubAgent est conçu pour être utilisé dans le Cloud ou bien On-Premise. Il est utilisé pour transmettre des messages au Edge. Pour ce faire, le connecteur IoTEdgeAgent (dans le Edge) doit exposé un Callback de type DirectMethod (voir le fichier iot_edge_agent.py pour plus de détails). <br />
Voir le fichier iot_hub_agent.py pour connaitre les détails de configuration du connecteur IoTHubAgent.<br />
Il est impératif que les deux connecteurs soit configurés avec le même nom de DirectMethod, sans quoi les messages seront rejetés.<br />
Par défaut, les messages sont transmis au module Zeppelin. Le nom du module peut être modifié avec la variable d'environnement MODULE_ID. <br />
Chaque message est transmit à une Edge spécifique (DEVICE_ID). Le processeur doit donc connaitre le destinataire. Dans le cas du processeur de commande du projet SCCI (RCI), le nom du Edge (DEVICE_ID) est fournit par la source via un attribut dans l'entête du message (CloudEvent).

## MQTT
Nous ne pouvons pas utiliser la version 2.x de paho-mqtt à cause de azure-iot-device:<br />
    azure-iot-device 2.14.0 depends on paho-mqtt<2.0.0 and >=1.6.1<br />
<br />

# Getting Started
TODO: Guide users through getting your code up and running on their own system. In this section you can talk about:
1.	Clone this repo
2.	Software dependencies: Docker Desktop
3.	Latest releases: see docker/readme.txt


# Build and Test
## Build
From git-bash run: scripts/build.sh <br />
## Docker / Release
Read docker/readme.txt <br />

# Contribute

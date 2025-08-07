### Documentation : Déploiement Local de la Stack SCCI avec Docker-Compose

#### **Introduction**
Cette documentation explique comment déployer localement l'environnement complet de la stack SCCI en utilisant `docker-compose`. Cet environnement permet de valider la connectivité avec IoTHub, tester les connecteurs MQTT, et valider les notebooks Zeppelin sans dépendre des services cloud ou des VMs Azure. L'objectif est de permettre aux développeurs d'itérer rapidement et de corriger les problèmes localement.

---

### **Prérequis**

1. **Logiciels nécessaires :**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop) (avec Docker Compose intégré).
   - Git pour cloner le dépôt.

2. **Ports requis :**
   Assurez-vous que les ports suivants sont libres sur votre machine :
   - **IoT Hub simulé** : `5671`, `8883`, `443`.
   - **PostgreSQL** : `5432`.
   - **Zeppelin** : `8080`.
   - **MQTT Broker (Mosquitto)** : `1883`.

3. **Cloner le Dépôt :**
   Clonez le dépôt contenant le projet SCCI :
   ```bash
   git clone <URL_DU_DEPOT>
   cd <REPERTOIRE_DU_DEPOT>
   ```

---

### **Structure des Services**

Le fichier 

docker-compose.yml

 inclut les services suivants :
1. **IoT Hub Simulé** : Simule Azure IoT Hub pour recevoir des messages télémétriques.
2. **PostgreSQL** : Base de données pour stocker les données télémétriques (locale ou hébergée sur Azure).
3. **Zeppelin** : Interface pour valider les notebooks et visualiser les données.
4. **Mosquitto** : Broker MQTT pour tester les connecteurs MQTT.
5. **SyncIoT** : Application principale pour synchroniser les données IoT.

---

### **Structure du Répertoire**
Assurez-vous que la structure de votre projet ressemble à ceci :
```
/SCCI
  ├── docker-compose.yml
  ├── config/
  │   ├── mosquitto.conf
  │   ├── synciot.json
  ├── iothub_simulator/
  │   ├── docker/
  │   │   ├── Dockerfile
  │   ├── simulator.py
  │   ├── requirements.txt
  ├── zeppelin/
  │   ├── docker/
  │   │   ├── Dockerfile.test.v2.amd64
  │   ├── config/
  │   │   ├── zeppelin.json
  ├── synciot/
  │   ├── src/
  │   │   ├── synciot.py
  │   │   ├── services/
  │   │   │   ├── azure_iot_hub_client.py
  │   │   │   ├── postgres_client.py
  │   │   ├── tools/
  │   │   │   ├── logger.py
  │   │   ├── metrics.py
  │   │   ├── _version.py
  ├── README.md
```

### **Fichier 

docker-compose.yml

**

Voici un exemple de fichier 

docker-compose.yml

 configuré pour la stack SCCI :

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:latest
    container_name: postgres
    environment:
      POSTGRES_USER: ${POSTGRESQL_USERNAME}
      POSTGRES_PASSWORD: ${POSTGRESQL_PASSWORD}
      POSTGRES_DB: ${POSTGRESQL_DATABASE}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: scci_mosquitto
    ports:
      - "1883:1883"
    volumes:
      - ./config/mosquitto.conf:/mosquitto/config/mosquitto.conf

  iothub_simulator:
    build:
      context: ./iothub_simulator
      dockerfile: docker/Dockerfile
    container_name: scci_iothub_simulator
    ports:
      - "5671:5671"
      - "8883:8883"
      - "443:443"
    environment:
      IOTHUB_CONNECTION_STRING: ${AZURE_IOTHUB_CONNECTION_STRING}

  synciot:
    build:
      context: .
      dockerfile: docker/Dockerfile.webapp.amd64
    container_name: synciot
    environment:
      AZURE_IOTHUB_CONNECTION_STRING: ${AZURE_IOTHUB_CONNECTION_STRING}
      AZURE_IOTHUB_CONSUMER_GROUP: ${AZURE_IOTHUB_CONSUMER_GROUP}
      AZURE_POSTGRESQL_HOST: ${AZURE_POSTGRESQL_HOST}
      AZURE_POSTGRESQL_PORT: 5432
      AZURE_POSTGRESQL_DATABASE: ${AZURE_POSTGRESQL_DATABASE}
      AZURE_POSTGRESQL_USERNAME: ${AZURE_POSTGRESQL_USERNAME}
      AZURE_POSTGRESQL_PASSWORD: ${AZURE_POSTGRESQL_PASSWORD}
      AZURE_POSTGRESQL_SSLMODE: ${AZURE_POSTGRESQL_SSLMODE}
      SYNCIOT_CONFIG_FILENAME: ${SYNCIOT_CONFIG_FILENAME}
    depends_on:
      - postgres
      - iothub_simulator
    ports:
      - "8000:8000"
    volumes:
      - ./config/synciot.json:/config/synciot.json
      - ./src:/app

  zeppelin:
    build:
      context: ./zeppelin
      dockerfile: docker/Dockerfile.test.v2.amd64
    container_name: zeppelin
    environment:
      CONFIG_FILENAME: /config/zeppelin.json
    ports:
      - "8001:8001"
    volumes:
      - ./zeppelin:/app
      - ./config:/config

volumes:
  postgres_data:
```

---

### **Fichier `Dockerfile` pour 

iothub_simulator

**

Créez un fichier `Dockerfile` dans le répertoire 

iothub_simulator

 avec le contenu suivant :

```dockerfile
FROM artifactory.hydro.qc.ca/dockerhub-docker-remote/python:3.12.1-slim-bullseye

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY simulator.py /app/simulator.py
COPY requirements.txt /app/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 5671 8883 443

CMD ["python3", "simulator.py"]
```

---

### **Fichier 

requirements.txt

 pour 

iothub_simulator

**

Ajoutez un fichier 

requirements.txt

 dans le répertoire 

iothub_simulator

 avec le contenu suivant :

```
azure-eventhub==5.11.0
```

---

### **Basculer entre une Base PostgreSQL Locale et Azure**

Le comportement de SyncIoT peut être configuré pour utiliser une base PostgreSQL locale ou une base hébergée sur Azure. Cela est contrôlé par la variable `CLOUD_HOSTED_DATABASE` dans le fichier synciot.py.

1. **Base Locale** :
   - Assurez-vous que `CLOUD_HOSTED_DATABASE` est défini sur `False` dans le fichier synciot.py :
     ```python
     CLOUD_HOSTED_DABATASE = False
     ```
   - Dans ce mode, SyncIoT utilisera les paramètres définis dans la section `postgresql_local` du fichier synciot.json.

2. **Base Hébergée sur Azure** :
   - Définissez `CLOUD_HOSTED_DATABASE` sur `True` dans le fichier synciot.py :
     ```python
     CLOUD_HOSTED_DABATASE = True
     ```
   - Dans ce mode, SyncIoT utilisera les paramètres définis dans la section `postgresql_azure` du fichier synciot.json.
  
---

### **Étapes pour Déployer et Tester**

1. **Construire et Lancer les Conteneurs**
   Exécutez la commande suivante pour démarrer tous les services :
   ```bash
   docker-compose up --build
   ```

2. **Vérifier les Services**
   - PostgreSQL : Accessible sur `localhost:5432`.
   - Mosquitto : Accessible sur `localhost:1883`.
   - Zeppelin : Accessible sur `http://localhost:8080`.
   - IoT Hub Simulé : Simule les connexions IoT Hub.

3. **Tester la Connectivité**
   - **Envoyer un message IoT Hub** :
     Le simulateur envoie automatiquement un message "Hello IoT Hub!" toutes les 5 secondes. Consultez les logs du conteneur `scci_iothub_simulator` pour vérifier :
     ```bash
     docker logs -f scci_iothub_simulator
     ```

4. **Valider les Données**
   - Connectez-vous à PostgreSQL pour vérifier que les messages sont bien insérés dans la base de données :
     ```bash
     docker exec -it scci_postgres psql -U synciot_user -d synciot_db
     SELECT * FROM rci_capteurs.rci_lost;
     ```
   - Ouvrez Zeppelin sur `http://localhost:8080` et exécutez un notebook pour visualiser les données.

---

### **Test de Bout en Bout**

1. **Hello World Télémétrie**
   - Vérifiez que le simulateur envoie des messages à IoT Hub.
   - Confirmez que SyncIoT traite les messages et les insère dans PostgreSQL.
   - Visualisez les données dans Zeppelin.

2. **Logs**
   Consultez les logs des conteneurs pour valider le bon fonctionnement de chaque service :
   ```bash
   docker logs <nom_du_conteneur>
   ```

---

### **Conclusion**

Cette procédure permet de déployer localement un environnement complet pour valider la stack SCCI. Elle offre un moyen rapide et efficace de tester les fonctionnalités sans dépendre des services cloud.
# Documentation d'intégration de Zeppelin - Traitement de données Serial

## 1. Vue d'ensemble

Zeppelin est un système de normalisation et de validation de données conçu pour traiter différents types de messages IoT. Cette documentation présente l'intégration complète pour traiter des données arrivant au format Serial via terminal.

**Exemple de donnée traitée :**
```
PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL
```

## 2. Architecture du système

Zeppelin utilise une architecture basée sur des pipelines où chaque pipeline traite un type de données spécifique :
- **Source** : Point d'entrée des données (MQTT, IoT Edge, IoT Device, etc.)
- **Processeur** : Logique de traitement et validation
- **Destination** : Point de sortie des données normalisées
- **Schéma JSON** : Définit la structure attendue des données

## 3. Installation et configuration

### 3.1 Prérequis
```powershell
# Installation des dépendances
pip install -r requirements.txt
```

### 3.2 Structure des fichiers pour l'exemple Serial

Nous allons créer :
1. Un schéma JSON pour valider les données Serial
2. Une configuration de pipeline
3. Un processeur personnalisé (optionnel)

## 4. Configuration détaillée pour données Serial

### 4.1 Création du schéma JSON

**Fichier : `config/schemas/serial-schema.json`**
```json
{
    "$id": "serial-schema",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "specversion": {
            "type": "string",
            "default": "1.0"
        },
        "type": {
            "type": "string",
            "default": "ca.hydroquebec.serial.data"
        },
        "time": {
            "type": "string",
            "format": "date-time"
        },
        "id": {
            "type": "string",
            "format": "uuid"
        },
        "source": {
            "type": "string"
        },
        "datacontenttype": {
            "type": "string",
            "default": "application/json; charset=utf-8"
        },
        "data": {
            "type": "object",
            "properties": {
                "PROP1": {
                    "type": "number",
                    "description": "Propriété numérique 1"
                },
                "PROP2": {
                    "type": "integer",
                    "description": "Propriété entière 2"
                },
                "PROP3": {
                    "type": "number",
                    "description": "Propriété numérique 3"
                },
                "PROP4": {
                    "type": "string",
                    "description": "Propriété texte 4"
                }
            },
            "required": ["PROP1", "PROP2", "PROP3", "PROP4"]
        }
    },
    "required": ["specversion", "type", "time", "id", "source", "data"]
}
```

### 4.2 Configuration du pipeline

**Fichier : `config/zeppelin-serial.json`**
```json
{
    "version": "0.2",
    "version_date": "2025-09-04",
    "main_thread_interval_sec": 0.1,
    "pipelines": [
        {
            "name": "SerialData",
            "class": "generic",
            "json_schema": "/config/schemas/serial-schema.json",
            "config": "",
            "apply_global_validation_rules": true,
            "validation_rules": {
                "max_prop1_value": 100.0,
                "min_prop2_value": 0
            },
            "max_payload_size_bytes": 1024,
            "thread_interval_sec": 0.1,
            "data_types": ["ca.hydroquebec.serial.data"],
            "source_broker": {
                "class": "mqtt",
                "topic": "serial/input",
                "mqtt": {
                    "host": "localhost",
                    "port": 1883,
                    "id": "zeppelin_serial_src",
                    "keepalive": 60,
                    "qos": 1
                },
                "throttle_max_message_sec": 10,
                "throttle_sleep_sec": 1.0
            },
            "destination_broker": {
                "class": "mqtt",
                "topic": "serial/output",
                "mqtt": {
                    "host": "localhost",
                    "port": 1883,
                    "id": "zeppelin_serial_dest",
                    "keepalive": 60,
                    "qos": 1
                }
            }
        }
    ]
}
```

## 5. Traitement des données Serial

### 5.1 Fonction de parsing des données Serial

**Fichier : `src/utils/serial_parser.py`**
```python
import json
import uuid
from datetime import datetime, timezone
from utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('SerialParser', LOGGING_LEVEL)

def parse_serial_line(line: str, source_id: str = "serial-device") -> dict:
    """
    Parse une ligne Serial au format: PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL
    Retourne un CloudEvent formaté
    """
    try:
        parts = line.strip().split()
        if len(parts) % 2 != 0:
            raise ValueError(f"Nombre impair d'éléments dans la ligne: {line}")
        
        # Extraction des propriétés
        data = {}
        for i in range(0, len(parts), 2):
            key = parts[i]
            value = parts[i + 1]
            
            # Conversion automatique des types selon la clé
            if key == "PROP1" or key == "PROP3":
                data[key] = float(value)
            elif key == "PROP2":
                data[key] = int(value)
            else:
                data[key] = value
        
        # Création du CloudEvent
        cloud_event = {
            "specversion": "1.0",
            "type": "ca.hydroquebec.serial.data",
            "time": datetime.now(timezone.utc).isoformat(),
            "id": str(uuid.uuid4()),
            "source": source_id,
            "datacontenttype": "application/json; charset=utf-8",
            "data": data
        }
        
        logger.debug(f"Parsed serial line: {json.dumps(cloud_event, indent=2)}")
        return cloud_event
        
    except Exception as e:
        logger.error(f"Erreur lors du parsing de la ligne Serial '{line}': {e}")
        raise

def validate_serial_data(data: dict) -> bool:
    """
    Valide les données Serial selon des règles métier
    """
    try:
        serial_data = data.get('data', {})
        
        # Validation des valeurs
        if 'PROP1' in serial_data and serial_data['PROP1'] < 0:
            logger.warning(f"PROP1 négative détectée: {serial_data['PROP1']}")
            return False
            
        if 'PROP2' in serial_data and serial_data['PROP2'] > 1000:
            logger.warning(f"PROP2 trop élevée détectée: {serial_data['PROP2']}")
            return False
            
        if 'PROP4' in serial_data and serial_data['PROP4'] not in ['NORMAL', 'WARNING', 'ERROR']:
            logger.warning(f"PROP4 invalide détectée: {serial_data['PROP4']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {e}")
        return False
```

### 5.2 Script d'intégration principal

**Fichier : `examples/serial_integration.py`**
```python
#!/usr/bin/env python3
"""
Exemple d'intégration de Zeppelin pour traiter des données Serial
"""

import json
import time
import serial
import paho.mqtt.client as mqtt
from src.utils.serial_parser import parse_serial_line, validate_serial_data
from src.utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('SerialIntegration', LOGGING_LEVEL)

class SerialToZeppelin:
    def __init__(self, serial_port='COM3', baud_rate=9600, mqtt_host='localhost', mqtt_port=1883):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.serial_connection = None
        self.mqtt_client = None
        
    def init_serial(self):
        """Initialise la connexion série"""
        try:
            self.serial_connection = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            logger.info(f"Connexion série initialisée sur {self.serial_port} à {self.baud_rate} bauds")
            return True
        except Exception as e:
            logger.error(f"Erreur initialisation série: {e}")
            return False
            
    def init_mqtt(self):
        """Initialise la connexion MQTT"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connexion MQTT initialisée sur {self.mqtt_host}:{self.mqtt_port}")
            return True
        except Exception as e:
            logger.error(f"Erreur initialisation MQTT: {e}")
            return False
    
    def process_serial_data(self):
        """Traite les données Serial en continu"""
        try:
            while True:
                if self.serial_connection.in_waiting > 0:
                    # Lecture de la ligne série
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"Ligne reçue: {line}")
                        
                        # Parsing de la ligne
                        cloud_event = parse_serial_line(line, f"serial-{self.serial_port}")
                        
                        # Validation
                        if validate_serial_data(cloud_event):
                            # Envoi vers Zeppelin via MQTT
                            self.send_to_zeppelin(cloud_event)
                        else:
                            logger.warning(f"Données invalides ignorées: {line}")
                
                time.sleep(0.1)  # Petite pause pour éviter la surcharge CPU
                
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur durant le traitement: {e}")
    
    def send_to_zeppelin(self, cloud_event):
        """Envoie les données vers Zeppelin via MQTT"""
        try:
            topic = "serial/input"
            payload = json.dumps(cloud_event)
            self.mqtt_client.publish(topic, payload)
            logger.debug(f"Données envoyées vers Zeppelin sur le topic '{topic}'")
        except Exception as e:
            logger.error(f"Erreur envoi MQTT: {e}")
    
    def close(self):
        """Ferme les connexions"""
        if self.serial_connection:
            self.serial_connection.close()
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

# Exemple d'utilisation en mode test (sans port série)
def test_mode():
    """Mode test sans port série physique"""
    try:
        # Simulation de données Serial
        test_lines = [
            "PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL",
            "PROP1 25.3 PROP2 180 PROP3 172.45 PROP4 WARNING",
            "PROP1 19.8 PROP2 290 PROP3 165.22 PROP4 NORMAL"
        ]
        
        # Initialisation MQTT
        mqtt_client = mqtt.Client()
        mqtt_client.connect('localhost', 1883, 60)
        mqtt_client.loop_start()
        
        for line in test_lines:
            print(f"Traitement de: {line}")
            
            # Parsing
            cloud_event = parse_serial_line(line, "serial-test")
            print(f"CloudEvent généré: {json.dumps(cloud_event, indent=2)}")
            
            # Validation
            if validate_serial_data(cloud_event):
                # Envoi vers Zeppelin
                topic = "serial/input"
                payload = json.dumps(cloud_event)
                mqtt_client.publish(topic, payload)
                print(f"Envoyé vers Zeppelin sur le topic '{topic}'")
            
            time.sleep(2)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
    except Exception as e:
        logger.error(f"Erreur en mode test: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Mode test activé")
        test_mode()
    else:
        # Mode production avec port série
        integrator = SerialToZeppelin()
        if integrator.init_serial() and integrator.init_mqtt():
            try:
                integrator.process_serial_data()
            finally:
                integrator.close()
```

## 6. Démarrage et utilisation

### 6.1 Démarrage de Zeppelin avec la configuration Serial

```powershell
# Définir le fichier de configuration
$env:CONFIG_FILENAME = "c:\path\to\zeppelin\config\zeppelin-serial.json"

# Démarrer Zeppelin
cd c:\path\to\zeppelin
python src\zeppelin.py
```

### 6.2 Test avec données simulées

```powershell
# Test sans port série physique
python examples\serial_integration.py --test
```

### 6.3 Démarrage avec port série réel

```powershell
# Adapter le port série dans le script
python examples\serial_integration.py
```

## 7. Surveillance et débogage

### 7.1 Logs

Les logs sont configurés dans `src/utils/logger.py`. Pour activer le mode debug :
```python
from src.utils.logger import get_logger
logger = get_logger('MonModule', 'DEBUG')
```

### 7.2 Métriques Prometheus

Zeppelin expose des métriques Prometheus par défaut :
- Nombre de messages traités
- Erreurs de validation
- Performance des processeurs

Accès : `http://localhost:9090/metrics`

### 7.3 Validation des données

Vérifiez que les données respectent le schéma :
```powershell
# Voir les logs de validation
tail -f logs/zeppelin.log | grep "validation"
```

## 8. Personnalisation avancée

### 8.1 Ajout de règles de validation personnalisées

Modifiez le fichier de configuration `zeppelin-serial.json` :
```json
"validation_rules": {
    "max_prop1_value": 100.0,
    "min_prop2_value": 0,
    "allowed_prop4_values": ["NORMAL", "WARNING", "ERROR", "CRITICAL"]
}
```

### 8.2 Création d'un processeur personnalisé

Si le processeur générique ne suffit pas, créez `src/processors/serial_processor.py` :
```python
from .base_processor import BaseProcessor
from utils.logger import get_logger, LOGGING_LEVEL

logger = get_logger('SerialProcessor', LOGGING_LEVEL)

class SerialProcessor(BaseProcessor):
    def init(self, config, pipeline, metrics):
        if not BaseProcessor.init(self, config, pipeline, metrics):
            return False
        # Initialisation spécifique au Serial
        return True
    
    def process_message(self, message):
        # Logique de traitement spécifique
        return BaseProcessor.process_message(self, message)
```

## 9. Exemples de données

### 9.1 Données d'entrée (Serial)
```
PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL
```

### 9.2 Données de sortie (CloudEvent normalisé)
```json
{
    "specversion": "1.0",
    "type": "ca.hydroquebec.serial.data",
    "time": "2025-09-04T14:30:00.123456+00:00",
    "id": "12345678-1234-1234-1234-123456789abc",
    "source": "serial-COM3",
    "datacontenttype": "application/json; charset=utf-8",
    "data": {
        "PROP1": 21.5,
        "PROP2": 235,
        "PROP3": 168.11,
        "PROP4": "NORMAL"
    }
}
```

## 10. Dépannage

### 10.1 Problèmes courants

**Erreur de connexion série :**
- Vérifiez le port COM et les droits d'accès
- Testez avec un autre terminal série

**Erreur de validation JSON :**
- Vérifiez que le schéma correspond aux données
- Consultez les logs pour les détails de l'erreur

**Problème MQTT :**
- Vérifiez que le broker MQTT est démarré
- Testez la connectivité avec `mosquitto_pub/sub`

### 10.2 Commands utiles

```powershell
# Tester la connexion MQTT
mosquitto_pub -h localhost -t "serial/input" -m '{"test": "message"}'

# Écouter les messages de sortie
mosquitto_sub -h localhost -t "serial/output"

# Vérifier les logs Zeppelin
Get-Content -Path "logs\zeppelin.log" -Wait
```

## 11. Conclusion

Cette documentation couvre l'intégration complète de Zeppelin pour traiter des données Serial. Le système est modulaire et extensible, permettant d'adapter facilement le traitement à d'autres formats de données.

Pour des besoins spécifiques, n'hésitez pas à personnaliser les schémas, les règles de validation et les processeurs selon vos exigences métier.

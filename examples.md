# Guide Pas à Pas : Intégration Zeppelin pour données Serial

Ce guide fournit toutes les commandes PowerShell nécessaires pour installer, configurer, tester et démarrer l'intégration Zeppelin pour le traitement de données Serial sur Windows.

## Table des matières

1. [Prérequis](#prérequis)
2. [Installation initiale](#installation-initiale)
3. [Configuration de l'environnement](#configuration-de-lenvironnement)
4. [Création des fichiers de configuration](#création-des-fichiers-de-configuration)
5. [Installation de Mosquitto MQTT](#installation-de-mosquitto-mqtt)
6. [Test en mode simulation](#test-en-mode-simulation)
7. [Démarrage de Zeppelin](#démarrage-de-zeppelin)
8. [Vérification et surveillance](#vérification-et-surveillance)
9. [Mode production avec port série](#mode-production-avec-port-série)
10. [Dépannage](#dépannage)

---

## Prérequis

### 1. Vérifier Python

```powershell
# Vérifier la version de Python (doit être 3.8+)
python --version

# Si Python n'est pas installé, télécharger depuis python.org
# Recommandé : Python 3.10 ou 3.11
```

### 2. Vérifier Git (optionnel)

```powershell
# Vérifier si Git est installé
git --version
```

### 3. Cloner ou télécharger les projets

```powershell
# Naviguer vers votre répertoire de travail
cd "c:\Users\$env:USERNAME\Documents\Environments\HydroQuebec\Clients - LTE"

# Créer le dossier SCCI si nécessaire
New-Item -ItemType Directory -Force -Path ".\scci"
cd scci

# Les projets zeppelin et synciot doivent être présents
# Si vous avez accès Git, clonez-les :
# git clone https://git.hydro.qc.ca/projects/RCI-I/repos/zeppelin
# git clone https://git.hydro.qc.ca/projects/RCI-I/repos/synciot
```

---

## Installation initiale

### 1. Créer un environnement virtuel Python (recommandé)

```powershell
# Naviguer vers le dossier zeppelin
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Note : Si vous avez une erreur "execution of scripts is disabled", exécutez :
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Installer les dépendances Python

```powershell
# Avec l'environnement virtuel activé
pip install --upgrade pip

# Installer les dépendances de Zeppelin
pip install -r requirements.txt

# Vérifier l'installation
pip list
```

### 3. Installer les dépendances supplémentaires pour Serial

```powershell
# Installer pyserial pour la communication série
pip install pyserial

# Installer paho-mqtt si pas déjà présent
pip install paho-mqtt==1.6.1
```

---

## Configuration de l'environnement

### 1. Créer la structure de dossiers

```powershell
# Depuis le dossier zeppelin
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"

# Créer les dossiers nécessaires
New-Item -ItemType Directory -Force -Path ".\config\schemas"
New-Item -ItemType Directory -Force -Path ".\examples"
New-Item -ItemType Directory -Force -Path ".\logs"
New-Item -ItemType Directory -Force -Path ".\src\utils"
```

### 2. Définir les variables d'environnement

```powershell
# Définir le chemin de configuration pour Zeppelin
$env:CONFIG_FILENAME = "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin\config\zeppelin-serial.json"

# Vérifier
Write-Host "CONFIG_FILENAME = $env:CONFIG_FILENAME"

# Pour rendre permanent (optionnel), ajouter au profil PowerShell
# notepad $PROFILE
# Puis ajouter la ligne : $env:CONFIG_FILENAME = "..."
```

---

## Création des fichiers de configuration

### 1. Créer le schéma JSON pour Serial

```powershell
# Créer le fichier de schéma
$schemaContent = @'
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
                    "description": "Propriété texte 4",
                    "enum": ["NORMAL", "WARNING", "ERROR", "CRITICAL"]
                }
            },
            "required": ["PROP1", "PROP2", "PROP3", "PROP4"]
        }
    },
    "required": ["specversion", "type", "time", "id", "source", "data"]
}
'@

$schemaContent | Out-File -FilePath ".\config\schemas\serial-schema.json" -Encoding UTF8
Write-Host "✓ Fichier schema créé : config\schemas\serial-schema.json"
```

### 2. Créer la configuration du pipeline Serial

```powershell
$pipelineConfig = @'
{
    "version": "0.2",
    "version_date": "2025-11-03",
    "main_thread_interval_sec": 0.1,
    "pipelines": [
        {
            "name": "SerialData",
            "class": "generic",
            "json_schema": "config/schemas/serial-schema.json",
            "config": "",
            "apply_global_validation_rules": true,
            "validation_rules": {
                "max_prop1_value": 100.0,
                "min_prop2_value": 0,
                "max_prop2_value": 1000
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
                    "username": "",
                    "password": "",
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
                    "username": "",
                    "password": "",
                    "qos": 1
                }
            }
        }
    ]
}
'@

$pipelineConfig | Out-File -FilePath ".\config\zeppelin-serial.json" -Encoding UTF8
Write-Host "✓ Fichier pipeline créé : config\zeppelin-serial.json"
```

### 3. Créer le parser Serial (si absent)

```powershell
$parserContent = @'
"""
Module de parsing pour données Serial
Transforme des lignes texte en CloudEvents JSON
"""
import json
import uuid
from datetime import datetime, timezone
from ..utils.logger import get_logger

logger = get_logger('SerialParser', 'INFO')

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
            
        if 'PROP4' in serial_data and serial_data['PROP4'] not in ['NORMAL', 'WARNING', 'ERROR', 'CRITICAL']:
            logger.warning(f"PROP4 invalide détectée: {serial_data['PROP4']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {e}")
        return False
'@

# Créer le fichier uniquement s'il n'existe pas
if (-not (Test-Path ".\src\utils\serial_parser.py")) {
    $parserContent | Out-File -FilePath ".\src\utils\serial_parser.py" -Encoding UTF8
    Write-Host "✓ Fichier parser créé : src\utils\serial_parser.py"
} else {
    Write-Host "⚠ Fichier src\utils\serial_parser.py existe déjà, non modifié"
}
```

### 4. Créer le script d'intégration Serial-to-MQTT

```powershell
$integrationScript = @'
#!/usr/bin/env python3
"""
Exemple d'intégration de Zeppelin pour traiter des données Serial
Bridge entre port série et MQTT
"""
import json
import time
import sys
import os

# Ajouter le dossier src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Serial port features disabled.")

import paho.mqtt.client as mqtt

# Import du parser (ajuster selon votre structure)
try:
    from utils.serial_parser import parse_serial_line, validate_serial_data
except ImportError:
    print("Error: Cannot import serial_parser. Check your file structure.")
    sys.exit(1)

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
        if not SERIAL_AVAILABLE:
            print("Error: pyserial not installed")
            return False
            
        try:
            self.serial_connection = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            print(f"✓ Connexion série initialisée sur {self.serial_port} à {self.baud_rate} bauds")
            return True
        except Exception as e:
            print(f"✗ Erreur initialisation série: {e}")
            return False
    
    def init_mqtt(self):
        """Initialise la connexion MQTT"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            print(f"✓ Connexion MQTT initialisée sur {self.mqtt_host}:{self.mqtt_port}")
            return True
        except Exception as e:
            print(f"✗ Erreur initialisation MQTT: {e}")
            return False
    
    def process_serial_data(self):
        """Traite les données Serial en continu"""
        try:
            print("Démarrage de la lecture série... (Ctrl+C pour arrêter)")
            while True:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        print(f"Reçu: {line}")
                        cloud_event = parse_serial_line(line, f"serial-{self.serial_port}")
                        if validate_serial_data(cloud_event):
                            self.send_to_zeppelin(cloud_event)
                        else:
                            print("⚠ Données invalides, non envoyées")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n✓ Arrêt demandé par l'utilisateur")
        except Exception as e:
            print(f"✗ Erreur durant le traitement: {e}")
    
    def send_to_zeppelin(self, cloud_event):
        """Envoie les données vers Zeppelin via MQTT"""
        try:
            topic = "serial/input"
            payload = json.dumps(cloud_event)
            self.mqtt_client.publish(topic, payload)
            print(f"→ Envoyé vers Zeppelin (topic: {topic})")
        except Exception as e:
            print(f"✗ Erreur envoi MQTT: {e}")
    
    def close(self):
        """Ferme les connexions"""
        if self.serial_connection:
            self.serial_connection.close()
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def test_mode():
    """Mode test sans port série physique"""
    print("=" * 60)
    print("MODE TEST : Simulation de données Serial")
    print("=" * 60)
    
    try:
        # Simulation de données Serial
        test_lines = [
            "PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL",
            "PROP1 25.3 PROP2 180 PROP3 172.45 PROP4 WARNING",
            "PROP1 19.8 PROP2 290 PROP3 165.22 PROP4 NORMAL",
            "PROP1 30.2 PROP2 450 PROP3 170.00 PROP4 CRITICAL"
        ]
        
        # Initialisation MQTT
        mqtt_client = mqtt.Client()
        mqtt_client.connect('localhost', 1883, 60)
        mqtt_client.loop_start()
        print("✓ Connexion MQTT établie")
        
        for i, line in enumerate(test_lines, 1):
            print(f"\n[Test {i}/{len(test_lines)}] Traitement de: {line}")
            
            # Parsing
            cloud_event = parse_serial_line(line, "serial-test")
            print(f"✓ CloudEvent généré (id: {cloud_event['id'][:8]}...)")
            
            # Validation
            if validate_serial_data(cloud_event):
                # Envoi vers Zeppelin
                topic = "serial/input"
                payload = json.dumps(cloud_event)
                mqtt_client.publish(topic, payload)
                print(f"→ Envoyé vers Zeppelin (topic: {topic})")
            else:
                print("⚠ Validation échouée, message non envoyé")
            
            time.sleep(2)
        
        print("\n" + "=" * 60)
        print("✓ Test terminé avec succès")
        print("=" * 60)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
    except Exception as e:
        print(f"✗ Erreur en mode test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_mode()
    else:
        # Mode production avec port série
        print("Mode production - Port série requis")
        print("Usage: python serial_integration.py [--test]")
        print("  --test : Mode simulation sans port série")
        print()
        
        integrator = SerialToZeppelin()
        if integrator.init_serial() and integrator.init_mqtt():
            try:
                integrator.process_serial_data()
            finally:
                integrator.close()
        else:
            print("\n✗ Impossible de démarrer. Vérifiez votre configuration.")
            sys.exit(1)
'@

$integrationScript | Out-File -FilePath ".\examples\serial_integration.py" -Encoding UTF8
Write-Host "✓ Script d'intégration créé : examples\serial_integration.py"
```

---

## Installation de Mosquitto MQTT

### Option 1 : Installation via Windows Installer (Recommandé)

```powershell
# Télécharger Mosquitto depuis https://mosquitto.org/download/
# Installer manuellement, puis ajouter au PATH

# Vérifier l'installation
mosquitto -h

# Démarrer le broker Mosquitto
mosquitto -v -c "C:\Program Files\mosquitto\mosquitto.conf"
```

### Option 2 : Utiliser Docker (Plus simple)

```powershell
# Vérifier que Docker est installé
docker --version

# Démarrer un container Mosquitto
docker run -d `
  --name mosquitto-scci `
  -p 1883:1883 `
  -p 9001:9001 `
  eclipse-mosquitto

# Vérifier que le container fonctionne
docker ps

# Voir les logs du broker
docker logs -f mosquitto-scci

# Arrêter le broker
# docker stop mosquitto-scci

# Redémarrer le broker
# docker start mosquitto-scci
```

### Tester la connexion MQTT (optionnel)

```powershell
# Si mosquitto_pub/sub sont installés
mosquitto_sub -h localhost -t "serial/#" -v

# Dans un autre terminal PowerShell
mosquitto_pub -h localhost -t "serial/test" -m "Hello MQTT"
```

---

## Test en mode simulation

### 1. Démarrer Mosquitto (dans un terminal séparé)

```powershell
# Option Docker
docker start mosquitto-scci

# OU Option installé
mosquitto -v
```

### 2. Activer l'environnement virtuel

```powershell
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"
.\venv\Scripts\Activate.ps1
```

### 3. Lancer le test de simulation

```powershell
# Exécuter le script en mode test
python .\examples\serial_integration.py --test

# Vous devriez voir :
# ============================================================
# MODE TEST : Simulation de données Serial
# ============================================================
# ✓ Connexion MQTT établie
# [Test 1/4] Traitement de: PROP1 21.5 PROP2 235...
# ✓ CloudEvent généré...
# → Envoyé vers Zeppelin (topic: serial/input)
# ...
```

### 4. Surveiller les messages MQTT (dans un autre terminal)

```powershell
# Si mosquitto_sub est installé
mosquitto_sub -h localhost -t "serial/input" -v

# OU utiliser un client MQTT GUI comme MQTT Explorer
# Télécharger depuis : http://mqtt-explorer.com/
```

---

## Démarrage de Zeppelin

### 1. Vérifier la configuration

```powershell
# Vérifier que la variable d'environnement est définie
echo $env:CONFIG_FILENAME

# Si non définie, la définir
$env:CONFIG_FILENAME = "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin\config\zeppelin-serial.json"
```

### 2. Démarrer Zeppelin

```powershell
# Depuis le dossier zeppelin avec l'environnement virtuel activé
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"
.\venv\Scripts\Activate.ps1

# Démarrer Zeppelin
python .\src\zeppelin.py

# Vous devriez voir :
# INFO - Zeppelin starting...
# INFO - Loading configuration from: ...
# INFO - Pipeline 'SerialData' initialized
# INFO - MQTT connection established
# INFO - Prometheus metrics exposed on port 9090
```

### 3. Tester le flux complet (dans des terminaux séparés)

**Terminal 1 : Mosquitto**
```powershell
docker start mosquitto-scci
```

**Terminal 2 : Zeppelin**
```powershell
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"
.\venv\Scripts\Activate.ps1
$env:CONFIG_FILENAME = ".\config\zeppelin-serial.json"
python .\src\zeppelin.py
```

**Terminal 3 : Test simulé**
```powershell
cd "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"
.\venv\Scripts\Activate.ps1
python .\examples\serial_integration.py --test
```

**Terminal 4 : Surveillance sortie**
```powershell
# Surveiller les messages de sortie
mosquitto_sub -h localhost -t "serial/output" -v
```

---

## Vérification et surveillance

### 1. Vérifier les logs Zeppelin

```powershell
# Voir les logs en temps réel
Get-Content -Path ".\logs\zeppelin.log" -Wait -Tail 50

# Filtrer les erreurs
Get-Content -Path ".\logs\zeppelin.log" | Select-String -Pattern "ERROR"

# Filtrer les validations
Get-Content -Path ".\logs\zeppelin.log" | Select-String -Pattern "validation"
```

### 2. Vérifier les métriques Prometheus

```powershell
# Ouvrir le navigateur sur l'endpoint des métriques
Start-Process "http://localhost:9090/metrics"

# OU avec curl/Invoke-WebRequest
Invoke-WebRequest -Uri "http://localhost:9090/metrics" | Select-Object -ExpandProperty Content
```

### 3. Vérifier les processus en cours

```powershell
# Vérifier que Zeppelin tourne
Get-Process python

# Vérifier que Mosquitto tourne (Docker)
docker ps | Select-String mosquitto

# Vérifier les ports ouverts
netstat -an | Select-String "1883"  # MQTT
netstat -an | Select-String "9090"  # Prometheus
```

---

## Mode production avec port série

### 1. Identifier votre port série

```powershell
# Lister les ports COM disponibles
[System.IO.Ports.SerialPort]::getportnames()

# OU avec mode.com
mode
```

### 2. Adapter le script

```powershell
# Éditer le script pour spécifier le bon port
notepad .\examples\serial_integration.py

# Modifier la ligne :
# SerialToZeppelin(serial_port='COM3', baud_rate=9600, ...)
# Remplacer COM3 par votre port (ex: COM5)
```

### 3. Lancer en mode production

```powershell
# Démarrer le pont série-MQTT
python .\examples\serial_integration.py

# Le script va attendre des données sur le port série
# et les transmettre automatiquement à Zeppelin via MQTT
```

---

## Dépannage

### Problème : "Execution of scripts is disabled"

```powershell
# Autoriser l'exécution de scripts PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problème : Module Python introuvable

```powershell
# Vérifier que l'environnement virtuel est activé
# Le prompt doit afficher (venv)

# Réactiver si nécessaire
.\venv\Scripts\Activate.ps1

# Réinstaller les dépendances
pip install -r requirements.txt
```

### Problème : Connexion MQTT échoue

```powershell
# Vérifier que Mosquitto tourne
docker ps
# OU
Get-Process mosquitto

# Tester la connectivité
Test-NetConnection -ComputerName localhost -Port 1883

# Redémarrer Mosquitto
docker restart mosquitto-scci
```

### Problème : Port série occupé

```powershell
# Lister les processus utilisant les ports COM
Get-Process | Where-Object {$_.MainWindowTitle -like "*COM*"}

# Fermer les applications qui utilisent le port série
# (Arduino IDE, PuTTY, etc.)
```

### Problème : Zeppelin ne démarre pas

```powershell
# Vérifier la variable CONFIG_FILENAME
echo $env:CONFIG_FILENAME

# Vérifier que le fichier existe
Test-Path $env:CONFIG_FILENAME

# Vérifier la syntaxe JSON
Get-Content $env:CONFIG_FILENAME | ConvertFrom-Json

# Voir les erreurs détaillées
python .\src\zeppelin.py 2>&1 | Tee-Object -FilePath ".\logs\startup-errors.log"
```

### Problème : Aucune donnée dans les logs

```powershell
# Vérifier que le dossier logs existe
New-Item -ItemType Directory -Force -Path ".\logs"

# Vérifier le niveau de log dans src/utils/logger.py
notepad .\src\utils\logger.py
# Changer LOGGING_LEVEL = 'DEBUG'

# Redémarrer Zeppelin
```

### Problème : Messages rejetés par le schéma

```powershell
# Voir les erreurs de validation dans les logs
Get-Content -Path ".\logs\zeppelin.log" | Select-String -Pattern "schema|validation" -Context 2

# Tester manuellement le schéma avec un message
python -c "import json, jsonschema; schema = json.load(open('config/schemas/serial-schema.json')); message = {'specversion':'1.0','type':'ca.hydroquebec.serial.data','time':'2025-11-03T10:00:00Z','id':'test-123','source':'test','data':{'PROP1':21.5,'PROP2':235,'PROP3':168.11,'PROP4':'NORMAL'}}; jsonschema.validate(message, schema); print('✓ Valid')"
```

---

## Commandes utiles de maintenance

### Arrêter tous les services

```powershell
# Arrêter Zeppelin (Ctrl+C dans le terminal)

# Arrêter Mosquitto Docker
docker stop mosquitto-scci

# Arrêter le script d'intégration (Ctrl+C)
```

### Nettoyer les logs

```powershell
# Archiver les vieux logs
$date = Get-Date -Format "yyyy-MM-dd"
Compress-Archive -Path ".\logs\*.log" -DestinationPath ".\logs\archive-$date.zip"
Remove-Item ".\logs\*.log"
```

### Mettre à jour les dépendances

```powershell
# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Mettre à jour pip
pip install --upgrade pip

# Mettre à jour les packages
pip install --upgrade -r requirements.txt

# Voir les packages obsolètes
pip list --outdated
```

### Sauvegarder la configuration

```powershell
# Créer une sauvegarde de la config
$date = Get-Date -Format "yyyy-MM-dd-HHmm"
Copy-Item -Path ".\config" -Destination ".\config-backup-$date" -Recurse
Write-Host "✓ Backup créé : config-backup-$date"
```

---

## Scripts PowerShell utiles

### Script de démarrage complet

Créer un fichier `start-zeppelin-serial.ps1` :

```powershell
# start-zeppelin-serial.ps1
# Script de démarrage automatique pour Zeppelin Serial

$ErrorActionPreference = "Stop"

Write-Host "=" * 60
Write-Host "Démarrage de l'environnement Zeppelin Serial"
Write-Host "=" * 60

# 1. Démarrer Mosquitto
Write-Host "`n[1/4] Démarrage de Mosquitto MQTT..."
docker start mosquitto-scci
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Mosquitto n'est pas démarré, tentative de création..."
    docker run -d --name mosquitto-scci -p 1883:1883 eclipse-mosquitto
}
Write-Host "✓ Mosquitto démarré"

# 2. Activer l'environnement virtuel
Write-Host "`n[2/4] Activation de l'environnement virtuel..."
Set-Location "c:\Users\ronan\Documents\Environments\HydroQuebec\Clients - LTE\scci\zeppelin"
.\venv\Scripts\Activate.ps1
Write-Host "✓ Environnement virtuel activé"

# 3. Définir la configuration
Write-Host "`n[3/4] Configuration de l'environnement..."
$env:CONFIG_FILENAME = ".\config\zeppelin-serial.json"
Write-Host "✓ CONFIG_FILENAME défini : $env:CONFIG_FILENAME"

# 4. Instructions finales
Write-Host "`n[4/4] Prêt à démarrer"
Write-Host "`nCommandes disponibles :"
Write-Host "  python .\src\zeppelin.py                          # Démarrer Zeppelin"
Write-Host "  python .\examples\serial_integration.py --test    # Test simulation"
Write-Host "  python .\examples\serial_integration.py           # Mode production"
Write-Host "`n" + "=" * 60
```

Exécuter le script :

```powershell
.\start-zeppelin-serial.ps1
```

---

## Références rapides

### Ports utilisés

- **1883** : MQTT Mosquitto
- **9090** : Métriques Prometheus de Zeppelin

### Fichiers importants

- `config/zeppelin-serial.json` : Configuration du pipeline
- `config/schemas/serial-schema.json` : Schéma de validation
- `examples/serial_integration.py` : Script pont série-MQTT
- `src/zeppelin.py` : Application principale
- `logs/zeppelin.log` : Logs de l'application

### Topics MQTT

- `serial/input` : Entrée des données Serial vers Zeppelin
- `serial/output` : Sortie des données normalisées par Zeppelin

---

**Documentation créée le 3 novembre 2025**  
**Version : 1.0**

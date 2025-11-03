Prérequis
Afin de résoudre les problématiques réseau d’installation de paquets, installer Fiddler en suivant la procédure : 

Télécharger également localement les contenus de synciot et zeppelin :

https://git.hydro.qc.ca/projects/RCI-I/repos/synciot/browse

https://PlateformeDEV-LTE@dev.azure.com/PlateformeDEV-LTE/PEPC/_git/zeppelin

 

1. Documentation d'intégration de Zeppelin - Traitement de données Serial
1.1. Vue d'ensemble
Zeppelin est un système de normalisation et de validation de données conçu pour traiter différents types de messages IoT. Cette documentation présente l'intégration complète pour traiter des données arrivant au format Serial via terminal.

Exemple de donnée traitée :



PROP1 21.5 PROP2 235 PROP3 168.11 PROP4 NORMAL
1.2. Architecture du système
Zeppelin utilise une architecture basée sur des pipelines où chaque pipeline traite un type de données spécifique :
## Objectif et portée

Ce document décrit l'intégration conjointe des deux projets présents dans ce dépôt : SyncIoT (dossier `synciot/`) et Zeppelin (dossier `zeppelin/`). Il explique pourquoi et comment démarrer, configurer, tester et dépanner le traitement de données de type "Serial" (lignes textuelles transmises par port série ou simulées) vers le pipeline de normalisation Zeppelin.

Public visé : équipes d'intégration/devops et développeurs qui doivent déployer ou tester l'ingestion Serial pour SCCI.

Remarque sur la source du code
- Le dépôt local `synciot/` contient le projet SyncIoT.
- Le dépôt local `zeppelin/` contient le projet Zeppelin (l'implémentation utilisée pour SCCI). Si vous recherchez les sources distantes, les liens historiques possibles sont :
  - https://git.hydro.qc.ca/projects/RCI-I/repos/synciot (SyncIoT mirror)
  - https://PlateformeDEV-LTE@dev.azure.com/PlateformeDEV-LTE/PEPC/_git/zeppelin (Zeppelin mirror)


## Pourquoi installer Fiddler et SyncIoT ? (Prérequis réseau)

- Fiddler : utile si vous rencontrez des restrictions réseau lors de l'installation de paquets Python (accès npm/pip restreint via proxy interne). Fiddler peut aider à diagnostiquer les interceptions TLS et les proxys. Installez-le uniquement si vous avez des erreurs réseau et suivez la politique de sécurité de votre entreprise.
- SyncIoT : certaines fonctionnalités de tests et d'outils d'embarquement (scripts, exemples) se trouvent dans le projet `synciot/`. Installez ou clonez `synciot/` localement pour accéder aux scripts d'intégration et aux configurations réutilisées.

Installation minimale (Python) :

```powershell
# depuis le dossier concerné (ex. zeppelin/ ou synciot/)
python -m pip install -r requirements.txt
```


## Vue d'ensemble : pourquoi le type de pipeline "Serial" ?

Contexte : certains équipements industriels ou bancs d'essai envoient des lignes de texte via port série (ou un service série encodé sur TCP) dans un format simple clé valeur. L'objectif est d'ingérer ces lignes, de les normaliser en CloudEvent JSON et de les faire passer dans la chaîne de validation/normalisation existante de Zeppelin.

Raisons du nouveau type :
- Permet de définir un schéma JSON clair (validation statique)
- Permet d'appliquer des règles métiers spécifiques (règles de seuil, types, valeurs autorisées)
- Réutilise le framework de connecteurs de Zeppelin (source -> processeur -> destination)

## Architecture logicielle (simplifiée)

Voici un schéma texte montrant les composants et leur rôle :

ZEPPELIN (processus)
  ├─ pipelines (config/zeppelin-*.json)
  │   ├─ source_broker (ex: mqtt, iothub, iotedge)
  │   ├─ processors (src/processors/, ex : generic_processor.py)
  │   └─ destination_broker
  ├─ utils (src/utils/)  <-- comportent le parser série
  │   └─ serial_parser.py
  └─ prometheus / logging

Flux d'une donnée Serial simulée/physique :
  Serial device / simulator -> Serial-to-MQTT (examples/serial_integration.py) -> topic MQTT (serial/input) -> Zeppelin source (mqtt agent) -> pipeline Generic -> validation via json_schema -> destination (serial/output ou autre)

Fichiers clés et rôle
- `zeppelin/config/zeppelin-serial.json` : exemple de pipeline Serial
- `zeppelin/config/schemas/serial-schema.json` : schéma JSON attendu
- `zeppelin/src/utils/serial_parser.py` : transforme une ligne Serial en CloudEvent JSON
- `zeppelin/examples/serial_integration.py` : connecteur test/simulateur série -> publie sur MQTT
- `synciot/` : contient outils et scripts complémentaires (si utilisés)

## Schéma JSON et lien avec la config du pipeline

Le schéma JSON (ex. `config/schemas/serial-schema.json`) définit la structure d'un CloudEvent attendu par le pipeline (champs `specversion`, `type`, `time`, `id`, `source`, `data`, ...). Dans la configuration du pipeline (`config/zeppelin-serial.json`) vous référencez ce schéma via la clé `json_schema`. Zeppelin valide chaque événement entrant contre ce schéma si `apply_global_validation_rules` est activé.

Extrait d'intention :
- `json_schema`: chemin relatif/absolu vers le fichier de schema
- `data_types`: liste des types CloudEvent attendus (ex. `ca.hydroquebec.serial.data`)

## src/utils/serial_parser.py — rôle et intégration

But : parser une ligne au format "KEY value KEY2 value2 ..." et produire un CloudEvent JSON.

Comportement principal :
- Scinde la ligne en paires clé/valeur.
- Convertit automatiquement certains champs (ex. `PROP1` et `PROP3` en float, `PROP2` en int).
- Compose un objet CloudEvent avec un `id` UUID et un `time` en UTC.
- Logge les erreurs et l'événement parse en debug.

Où il s'intègre :
- Utilisé par des scripts d'intégration (ex. `examples/serial_integration.py`) pour publier les CloudEvents sur le topic d'entrée du pipeline (`serial/input`).

Règles métier/validation complémentaire
- `validate_serial_data()` (dans le même module) applique des règles simples (ex. PROP1 >= 0, PROP2 <= 1000, PROP4 appartient à une liste autorisée). Ces règles sont complémentaires à la validation du schéma JSON.

## examples/serial_integration.py — rôle

Ce script est un pont (bridge) pour :
- lire depuis un port série réel (ex. `COM3`) ou
- simuler des lignes (mode `--test`) et
- publier des CloudEvents JSON sur un broker MQTT (topic `serial/input`).

Utilisation test (PowerShell) :

```powershell
# mode test, sans port série
python .\examples\serial_integration.py --test
```

En production, adaptez `serial_port` et démarrez sans `--test` :

```powershell
python .\examples\serial_integration.py
```

Le script utilise `serial_parser.parse_serial_line()` pour produire l'événement, puis publie via Paho MQTT vers le broker configuré.

## Démarrage de Zeppelin — containerisation vs exécution directe

- Dans ces exemples, Zeppelin est souvent démarré directement en Python (ex. `python src\zeppelin.py`) pour faciliter le développement et le débogage local.
- En production (Azure IoT, edge), on privilégiera la containerisation (images Docker fournies sous `docker/`) et les déploiements orchestrés (IoT Edge modules, Kubernetes, etc.).

Pourquoi exécution directe ici ?
- tests locaux et debugging rapide (log en console/local file)
- facilité d'itération pour adapter le parser/les règles

## Où vont les données simulées ?

- Les données simulées publiées par `examples/serial_integration.py --test` sont envoyées au broker MQTT configuré (par défaut `localhost:1883`, topic `serial/input`).
- Zeppelin (si configuré avec une source MQTT écoutant `serial/input`) va consommer ces messages, les valider, appliquer les processeurs et publier éventuellement un message de sortie sur `serial/output` ou stocker/forwarder vers la destination configurée.

## Logs et surveillance

Emplacement des logs :
- Par défaut, la configuration de log se trouve dans `src/utils/logger.py`. Selon la configuration, les logs peuvent être écrits sur la console et/ou dans un fichier `logs/zeppelin.log` (si configuré).

Activer le debug (exemple) :

```python
from src.utils.logger import get_logger, LOGGING_LEVEL
logger = get_logger('MonModule', 'DEBUG')
```

Pour suivre les logs sous PowerShell :

```powershell
Get-Content -Path ".\logs\zeppelin.log" -Wait
```

Si `logs/zeppelin.log` n'existe pas, vérifiez `src/utils/logger.py` pour la destination exacte et adaptez la configuration (chemin, rotation, niveau).

## Métriques Prometheus

Zeppelin expose des métriques (si activé) sur un endpoint local (ex. `http://localhost:9090/metrics`). Vérifiez la configuration Prometheus dans `src/prometheus/`.

## Mosquitto et broker MQTT

- Le document de test suppose un broker MQTT local (ex. Mosquitto). Mosquitto n'est pas fourni dans ce repo ; il s'agit d'un service externe à installer sur la machine de test ou à exécuter via Docker.
- Sous Windows, vous pouvez installer Mosquitto via son installeur officiel ou exécuter un container Docker :

```powershell
# Docker (exemple)
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto
```

Commandes utiles pour tester la connectivité MQTT (si mosquitto_pub/sub sont installés) :

```powershell
mosquitto_pub -h localhost -t "serial/input" -m '{"test":"message"}'
mosquitto_sub -h localhost -t "serial/output"
```

Si mosquitto n'est pas installé localement, utilisez le client Paho MQTT (ex. `examples/serial_integration.py`) pour publier/écouter.

## Dépannage (où regarder et étapes rapides)

1) Erreurs d'installation pip : vérifier la connectivité réseau, proxy, ou utiliser Fiddler pour diagnostiquer.
2) Erreurs MQTT : s'assurer que le broker est démarré et que l'hôte/port sont corrects.
3) Erreurs de validation schema : consulter les logs (niveau DEBUG) pour voir le payload et la raison du rejet.
4) Logs : vérifier `src/utils/logger.py` pour le chemin de sortie des logs (console/file).

Exemples PowerShell pour surveiller les logs :

```powershell
Get-Content -Path ".\logs\zeppelin.log" -Wait
```

## Points demandés par le feedback — réponses rapides

- "Quel est, et où est la demande de cette documentation ?" : Elle documente l'intégration Zeppelin pour l'ingestion Serial dans le contexte SCCI ; la demande est traitée ici pour l'équipe d'Infra IoT / SCCI.
- "Pourquoi installer SyncIoT ?" : pour disposer des scripts d'intégration et exemples complémentaires fournis dans `synciot/` et pour reproduire l'environnement utilisé en production.
- "Quel lien pointe vers la bonne source ?" : vérifier avec l'équipe; le repo local est source de vérité pour cette doc.
- "Pourquoi un nouveau type de Pipeline Serial ?" : cf. section "Pourquoi le type de pipeline 'Serial' ?" ci‑dessus.
- "Où va le parser / serial_parser.py et examples ?" : décrit en sections dédiées ci‑dessus.
- "Pourquoi démarrer direct et pas en conteneur ?" : facilité de développement et debugging ; production → container.
- "Où vont les logs ?" : voir `src/utils/logger.py`; par défaut console et/ou `logs/zeppelin.log` si configuré.

## Suivi et prochaines étapes

- Vérifier et confirmer le lien de code officiel auprès du responsable du projet.
- (Optionnel) Ajouter un diagramme visuel (PNG/SVG) dans `doc/` pour la documentation finale.
- (Optionnel) Ajouter un fichier `examples/README.md` avec commandes pas-à-pas pour Windows et Docker.

---
Résumé des changements : j'ai enrichi le document pour répondre aux points listés dans `feedback.md` : clarifications sur l'objectif, architecture, schéma, parser, exemples d'exécution (PowerShell), logs, mosquitto et notes de déploiement vs développement.
# Écouter les messages de sortie
mosquitto_sub -h localhost -t "serial/output"
# Vérifier les logs Zeppelin
Get-Content -Path "logs\zeppelin.log" -Wait

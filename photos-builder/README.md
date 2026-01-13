# Photo Rebuilder - Azure Function

Cette Azure Function reconstruit automatiquement les photos envoyées par les capteurs IoT en plusieurs blocs via MQTT/IoT Hub.

## 🎯 Fonctionnalités

- ✅ Reconstruction automatique des photos découpées en blocs
- ✅ Support des caméras avant (CAMAV) et arrière (CAMAR)
- ✅ Détection automatique des photos complètes
- ✅ Sauvegarde dans Azure Blob Storage
- ✅ Insertion des métadonnées dans Azure Data Explorer (ADX)
- ✅ Gestion des timeouts (2 minutes par défaut)
- ✅ Tests locaux sans déploiement Azure

## 📋 Format des données

Les capteurs envoient les photos selon ce protocole :

### Message d'initialisation
```json
{
  "data": [
    {"type": "CAMAV_NBBLOC", "val": 156}  // Nombre total de blocs
  ]
}
```

### Messages de blocs
```json
{
  "data": [
    {"type": "CAMAV_BLC", "val": 1},        // Numéro du bloc
    {"type": "CAMAV_SIZ", "val": 512},      // Taille du bloc en bytes
    {"type": "CAMAV_DAT", "val": "base64"}  // Données encodées en base64
  ]
}
```

## 🏗️ Architecture

```
IoT Hub (Event Hub)
       ↓
Azure Function (PhotoRebuilder)
       ├→ Photo State Manager (mémoire)
       ├→ Azure Blob Storage (photos)
       └→ Azure Data Explorer (métadonnées)
```

## 🚀 Déploiement

### Prérequis

- Python 3.9+
- Azure Functions Core Tools
- Un compte Azure avec :
  - IoT Hub
  - Storage Account
  - Azure Data Explorer cluster

### Configuration

1. **Créer un environnement virtuel :**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. **Installer les dépendances :**
```powershell
pip install -r requirements.txt
```

3. **Configurer `local.settings.json` :**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "IoTHubEventHubConnectionString": "Endpoint=sb://...",
    "BLOB_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;...",
    "BLOB_CONTAINER_NAME": "photos",
    "ADX_CLUSTER_URI": "https://yourcluster.kusto.windows.net",
    "ADX_DATABASE": "IoTData",
    "ADX_TABLE": "Photos",
    "ADX_CLIENT_ID": "your-app-id",
    "ADX_CLIENT_SECRET": "your-app-secret",
    "ADX_TENANT_ID": "your-tenant-id",
    "PHOTO_TIMEOUT_MINUTES": "2"
  }
}
```

4. **Créer l'App Registration Azure AD (pour ADX) :**
```powershell
az ad sp create-for-rbac --name "photo-rebuilder-sp"
```

5. **Donner les permissions ADX :**
```kql
.add database IoTData ingestors ('aadapp=<CLIENT_ID>;<TENANT_ID>')
```

### Déploiement dans Azure

```powershell
# Se connecter à Azure
az login

# Créer une Function App
az functionapp create `
  --resource-group YourResourceGroup `
  --consumption-plan-location eastus `
  --runtime python `
  --runtime-version 3.9 `
  --functions-version 4 `
  --name photo-rebuilder-func `
  --storage-account yourstorageaccount

# Déployer le code
func azure functionapp publish photo-rebuilder-func

# Configurer les variables d'environnement
az functionapp config appsettings set `
  --name photo-rebuilder-func `
  --resource-group YourResourceGroup `
  --settings @appsettings.json
```

## 🧪 Tests locaux

### Test avec les données d'exemple

Le script `test_local.py` permet de tester la reconstruction sans déployer sur Azure :

```powershell
# Test avec le fichier d'exemple
python test_local.py "39 (1).json"
```

**Résultat attendu :**
```
Chargement des messages depuis: 39 (1).json
301 messages chargés

[0] Init CAMAV: 156 blocs à 2025-11-06 19:39:07.633000+00:00
[1] Bloc CAMAV 1 ajouté (512 bytes)
[2] Bloc CAMAV 2 ajouté (512 bytes)
...
[156] Bloc CAMAV 156 ajouté (253 bytes)

✓ Photo CAMAV complète!
  → Fichier sauvegardé: test_output\77CA3DF2F6BADB7C_CAMAV_20251106_193907.jpg
  → Taille: 79876 bytes
  → Blocs: 156/156

============================================================
Traitement terminé:
  - Messages traités: 301
  - Photos complétées: 2
  - Fichiers sauvegardés dans: C:\...\test_output
============================================================
```

Les photos reconstruites sont sauvegardées dans `test_output/` et peuvent être ouvertes avec n'importe quel visualiseur d'images.

### Test de l'upload Blob Storage (optionnel)

```powershell
# Définir la connexion storage
$env:BLOB_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# Tester l'upload
python -c "
from shared.blob_storage import BlobStorageClient
from datetime import datetime

client = BlobStorageClient()
with open('test_output/photo.jpg', 'rb') as f:
    url = client.upload_photo('TEST_DEVICE', 'CAMAV', datetime.utcnow(), f.read())
    print(f'Photo uploadée: {url}')
"
```

### Test de l'insertion ADX (optionnel)

```powershell
# Définir les variables ADX
$env:ADX_CLUSTER_URI="https://yourcluster.kusto.windows.net"
$env:ADX_DATABASE="IoTData"
$env:ADX_CLIENT_ID="..."
$env:ADX_CLIENT_SECRET="..."
$env:ADX_TENANT_ID="..."

# Tester l'insertion
python -c "
from shared.adx_client import ADXClient
from datetime import datetime

client = ADXClient()
success = client.insert_photo_record(
    'TEST_DEVICE', 'CAMAV', datetime.utcnow(),
    'https://storage.blob.core.windows.net/photos/test.jpg',
    156, 79876
)
print(f'Insertion: {\"Succès\" if success else \"Échec\"}')
"
```

## 📊 Monitoring

### Requêtes ADX utiles

```kql
// Photos récentes
Photos
| where IngestionTime > ago(24h)
| order by Timestamp desc

// Statistiques par device
Photos
| summarize 
    PhotoCount = count(),
    AvgFileSize = avg(FileSize),
    AvgBlocks = avg(TotalBlocks)
  by DeviceId, CameraType

// Photos par heure
Photos
| where Timestamp > ago(7d)
| summarize count() by bin(Timestamp, 1h)
| render timechart
```

### Logs de la Function App

```powershell
# Afficher les logs en temps réel
func azure functionapp logstream photo-rebuilder-func
```

## 🔧 Troubleshooting

### La photo n'est pas complète

- Vérifier que tous les blocs arrivent dans la fenêtre de 2 minutes
- Augmenter `PHOTO_TIMEOUT_MINUTES` si nécessaire
- Vérifier les logs pour les erreurs de parsing

### Erreur Blob Storage

- Vérifier `BLOB_STORAGE_CONNECTION_STRING`
- Vérifier que le conteneur existe ou que la fonction a les droits de le créer
- Vérifier les quotas du Storage Account

### Erreur ADX

- Vérifier les credentials (CLIENT_ID, SECRET, TENANT_ID)
- Vérifier les permissions : `.show database IoTData principals`
- Vérifier que la table existe : `.show tables`

## 📝 Structure du projet

```
photos-builder/
├── PhotoRebuilder/          # Azure Function
│   ├── __init__.py          # Code principal
│   └── function.json        # Configuration trigger
├── shared/                  # Modules partagés
│   ├── photo_state.py       # Gestion de l'état
│   ├── blob_storage.py      # Client Blob Storage
│   └── adx_client.py        # Client ADX
├── test_output/             # Photos reconstruites localement
├── test_local.py            # Script de test
├── requirements.txt         # Dépendances Python
├── host.json               # Configuration Functions
├── local.settings.json     # Variables d'environnement
└── README.md               # Ce fichier
```

## 📄 Licence

MIT

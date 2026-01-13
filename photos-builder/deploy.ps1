# Scripts PowerShell pour le déploiement et la gestion
# Utilisez ces commandes pour déployer et tester la solution

# ============================================================
# INSTALLATION ET CONFIGURATION INITIALE
# ============================================================

# 1. Créer et activer l'environnement virtuel
function Setup-Environment {
    Write-Host "🔧 Configuration de l'environnement..." -ForegroundColor Cyan
    
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    pip install azure-functions-core-tools
    
    Write-Host "✅ Environnement configuré!" -ForegroundColor Green
}

# 2. Test local simple
function Test-Local {
    Write-Host "🧪 Test local de reconstruction..." -ForegroundColor Cyan
    
    .venv\Scripts\Activate.ps1
    python test_local.py "39 (1).json"
    
    Write-Host "`n📁 Vérifiez les photos dans: test_output/" -ForegroundColor Yellow
}

# ============================================================
# CRÉATION DES RESSOURCES AZURE
# ============================================================

# 3. Créer les ressources Azure
function Create-AzureResources {
    param(
        [string]$ResourceGroup = "rg-photos-iot",
        [string]$Location = "eastus",
        [string]$StorageAccount = "stphotosiot$(Get-Random -Maximum 9999)",
        [string]$FunctionApp = "func-photos-rebuilder",
        [string]$IoTHub = "iothub-photos",
        [string]$ADXCluster = "adxphotos"
    )
    
    Write-Host "🏗️  Création des ressources Azure..." -ForegroundColor Cyan
    
    # Resource Group
    Write-Host "`n📦 Création du Resource Group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location
    
    # Storage Account
    Write-Host "`n💾 Création du Storage Account..." -ForegroundColor Yellow
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS
    
    $storageConnection = az storage account show-connection-string `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --query connectionString -o tsv
    
    # Créer le conteneur photos
    az storage container create `
        --name photos `
        --connection-string $storageConnection
    
    # IoT Hub
    Write-Host "`n🌐 Création de l'IoT Hub..." -ForegroundColor Yellow
    az iot hub create `
        --name $IoTHub `
        --resource-group $ResourceGroup `
        --sku S1 `
        --location $Location
    
    # Event Hub Connection (built-in endpoint)
    $eventHubConnection = az iot hub connection-string show `
        --hub-name $IoTHub `
        --policy-name service `
        --query connectionString -o tsv
    
    # Function App
    Write-Host "`n⚡ Création de la Function App..." -ForegroundColor Yellow
    az functionapp create `
        --name $FunctionApp `
        --resource-group $ResourceGroup `
        --consumption-plan-location $Location `
        --runtime python `
        --runtime-version 3.9 `
        --functions-version 4 `
        --storage-account $StorageAccount
    
    # ADX Cluster (optionnel - coûteux)
    Write-Host "`n📊 Pour ADX, créez manuellement via le portail Azure" -ForegroundColor Yellow
    Write-Host "    ou utilisez: az kusto cluster create" -ForegroundColor Gray
    
    # Sauvegarder les informations
    @{
        ResourceGroup = $ResourceGroup
        StorageAccount = $StorageAccount
        StorageConnection = $storageConnection
        IoTHub = $IoTHub
        EventHubConnection = $eventHubConnection
        FunctionApp = $FunctionApp
    } | ConvertTo-Json | Out-File "azure-resources.json"
    
    Write-Host "`n✅ Ressources créées!" -ForegroundColor Green
    Write-Host "📝 Informations sauvegardées dans: azure-resources.json" -ForegroundColor Cyan
}

# 4. Créer un App Registration pour ADX
function Create-ADXServicePrincipal {
    Write-Host "🔐 Création du Service Principal pour ADX..." -ForegroundColor Cyan
    
    $sp = az ad sp create-for-rbac --name "photo-rebuilder-sp" | ConvertFrom-Json
    
    Write-Host "`n✅ Service Principal créé!" -ForegroundColor Green
    Write-Host "`nSauvegardez ces valeurs:" -ForegroundColor Yellow
    Write-Host "  ADX_CLIENT_ID: $($sp.appId)" -ForegroundColor Cyan
    Write-Host "  ADX_CLIENT_SECRET: $($sp.password)" -ForegroundColor Cyan
    Write-Host "  ADX_TENANT_ID: $($sp.tenant)" -ForegroundColor Cyan
    
    return $sp
}

# 5. Configurer la Function App
function Configure-FunctionApp {
    param(
        [string]$FunctionApp,
        [string]$ResourceGroup,
        [string]$StorageConnection,
        [string]$EventHubConnection,
        [string]$ADXClusterUri,
        [string]$ADXClientId,
        [string]$ADXClientSecret,
        [string]$ADXTenantId
    )
    
    Write-Host "⚙️  Configuration de la Function App..." -ForegroundColor Cyan
    
    az functionapp config appsettings set `
        --name $FunctionApp `
        --resource-group $ResourceGroup `
        --settings `
            "BLOB_STORAGE_CONNECTION_STRING=$StorageConnection" `
            "BLOB_CONTAINER_NAME=photos" `
            "IoTHubEventHubConnectionString=$EventHubConnection" `
            "ADX_CLUSTER_URI=$ADXClusterUri" `
            "ADX_DATABASE=IoTData" `
            "ADX_TABLE=Photos" `
            "ADX_CLIENT_ID=$ADXClientId" `
            "ADX_CLIENT_SECRET=$ADXClientSecret" `
            "ADX_TENANT_ID=$ADXTenantId" `
            "PHOTO_TIMEOUT_MINUTES=2"
    
    Write-Host "✅ Configuration terminée!" -ForegroundColor Green
}

# ============================================================
# DÉPLOIEMENT
# ============================================================

# 6. Déployer la Function
function Deploy-Function {
    param(
        [string]$FunctionApp
    )
    
    Write-Host "🚀 Déploiement de la Function..." -ForegroundColor Cyan
    
    .venv\Scripts\Activate.ps1
    func azure functionapp publish $FunctionApp --python
    
    Write-Host "✅ Déploiement terminé!" -ForegroundColor Green
}

# 7. Setup ADX
function Setup-ADX {
    Write-Host "📊 Configuration d'Azure Data Explorer..." -ForegroundColor Cyan
    
    .venv\Scripts\Activate.ps1
    python setup_adx.py
    
    Write-Host "✅ ADX configuré!" -ForegroundColor Green
}

# ============================================================
# MONITORING ET TROUBLESHOOTING
# ============================================================

# 8. Afficher les logs
function Show-Logs {
    param(
        [string]$FunctionApp
    )
    
    Write-Host "📜 Logs de la Function App..." -ForegroundColor Cyan
    func azure functionapp logstream $FunctionApp
}

# 9. Tester l'upload Blob
function Test-BlobUpload {
    Write-Host "🧪 Test d'upload vers Blob Storage..." -ForegroundColor Cyan
    
    $testPhoto = Get-ChildItem "test_output\*.jpg" | Select-Object -First 1
    
    if ($testPhoto) {
        .venv\Scripts\Activate.ps1
        
        $pythonScript = @"
from shared.blob_storage import BlobStorageClient
from datetime import datetime

client = BlobStorageClient()
with open('$($testPhoto.FullName)', 'rb') as f:
    url = client.upload_photo('TEST_DEVICE', 'CAMAV', datetime.utcnow(), f.read())
    print(f'Photo uploadée: {url}')
"@
        
        python -c $pythonScript
    } else {
        Write-Host "❌ Aucune photo de test trouvée. Exécutez d'abord Test-Local" -ForegroundColor Red
    }
}

# 10. Vérifier les ressources
function Show-Resources {
    param(
        [string]$ResourceGroup = "rg-photos-iot"
    )
    
    Write-Host "📋 Ressources dans $ResourceGroup..." -ForegroundColor Cyan
    az resource list --resource-group $ResourceGroup --output table
}

# ============================================================
# WORKFLOW COMPLET
# ============================================================

function Deploy-Complete {
    Write-Host "🚀 DÉPLOIEMENT COMPLET" -ForegroundColor Magenta
    Write-Host "=" * 60 -ForegroundColor Magenta
    
    # 1. Setup local
    Setup-Environment
    
    # 2. Test local
    Test-Local
    
    Write-Host "`n⏸️  Vérifiez que les photos sont correctement reconstruites." -ForegroundColor Yellow
    $continue = Read-Host "Continuer avec le déploiement Azure? (O/N)"
    
    if ($continue -ne "O") {
        Write-Host "❌ Déploiement annulé" -ForegroundColor Red
        return
    }
    
    # 3. Créer les ressources
    $params = @{
        ResourceGroup = "rg-photos-iot"
        Location = "eastus"
        StorageAccount = "stphotosiot$(Get-Random -Maximum 9999)"
        FunctionApp = "func-photos-rebuilder"
        IoTHub = "iothub-photos"
    }
    
    Create-AzureResources @params
    $resources = Get-Content "azure-resources.json" | ConvertFrom-Json
    
    # 4. Service Principal pour ADX
    Write-Host "`n⚠️  Créez manuellement le cluster ADX dans le portail" -ForegroundColor Yellow
    Write-Host "URL du portail: https://portal.azure.com" -ForegroundColor Cyan
    
    $adxUri = Read-Host "Entrez l'URI du cluster ADX (ex: https://mycluster.eastus.kusto.windows.net)"
    
    $sp = Create-ADXServicePrincipal
    
    # 5. Configurer la Function App
    Configure-FunctionApp `
        -FunctionApp $resources.FunctionApp `
        -ResourceGroup $resources.ResourceGroup `
        -StorageConnection $resources.StorageConnection `
        -EventHubConnection $resources.EventHubConnection `
        -ADXClusterUri $adxUri `
        -ADXClientId $sp.appId `
        -ADXClientSecret $sp.password `
        -ADXTenantId $sp.tenant
    
    # 6. Setup ADX
    Setup-ADX
    
    # 7. Déployer
    Deploy-Function -FunctionApp $resources.FunctionApp
    
    Write-Host "`n✅ DÉPLOIEMENT COMPLET!" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "`n📝 Prochaines étapes:" -ForegroundColor Yellow
    Write-Host "  1. Connectez vos devices à l'IoT Hub: $($resources.IoTHub)" -ForegroundColor Cyan
    Write-Host "  2. Surveillez les logs: Show-Logs -FunctionApp $($resources.FunctionApp)" -ForegroundColor Cyan
    Write-Host "  3. Vérifiez les photos dans le Storage: $($resources.StorageAccount)" -ForegroundColor Cyan
}

# ============================================================
# AFFICHER L'AIDE
# ============================================================

function Show-Help {
    Write-Host "`n🔧 COMMANDES DISPONIBLES" -ForegroundColor Magenta
    Write-Host "=" * 60 -ForegroundColor Magenta
    
    Write-Host "`n📦 Configuration locale:" -ForegroundColor Yellow
    Write-Host "  Setup-Environment          - Configure l'environnement Python"
    Write-Host "  Test-Local                 - Test local avec les données d'exemple"
    
    Write-Host "`n☁️  Ressources Azure:" -ForegroundColor Yellow
    Write-Host "  Create-AzureResources      - Crée toutes les ressources Azure"
    Write-Host "  Create-ADXServicePrincipal - Crée le Service Principal pour ADX"
    Write-Host "  Show-Resources             - Liste les ressources créées"
    
    Write-Host "`n⚙️  Configuration:" -ForegroundColor Yellow
    Write-Host "  Configure-FunctionApp      - Configure les paramètres de la Function"
    Write-Host "  Setup-ADX                  - Configure la base ADX et les tables"
    
    Write-Host "`n🚀 Déploiement:" -ForegroundColor Yellow
    Write-Host "  Deploy-Function            - Déploie le code dans Azure"
    Write-Host "  Deploy-Complete            - Workflow complet de A à Z"
    
    Write-Host "`n📊 Monitoring:" -ForegroundColor Yellow
    Write-Host "  Show-Logs                  - Affiche les logs en temps réel"
    Write-Host "  Test-BlobUpload            - Test l'upload vers Blob Storage"
    
    Write-Host "`n💡 Exemple d'utilisation:" -ForegroundColor Cyan
    Write-Host "  # Déploiement complet automatique"
    Write-Host "  Deploy-Complete"
    Write-Host ""
    Write-Host "  # Ou étape par étape"
    Write-Host "  Setup-Environment"
    Write-Host "  Test-Local"
    Write-Host "  Create-AzureResources -ResourceGroup 'my-rg' -Location 'eastus'"
    Write-Host "  Deploy-Function -FunctionApp 'my-func-app'"
    Write-Host ""
}

# Afficher l'aide au chargement du script
Show-Help

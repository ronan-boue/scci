"""
Script pour créer la table ADX avec le schéma correct.
"""
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
import os


def create_adx_table():
    """Crée la table Photos dans ADX."""
    
    cluster_uri = os.environ.get("ADX_CLUSTER_URI")
    database = os.environ.get("ADX_DATABASE")
    client_id = os.environ.get("ADX_CLIENT_ID")
    client_secret = os.environ.get("ADX_CLIENT_SECRET")
    tenant_id = os.environ.get("ADX_TENANT_ID")
    table_name = os.environ.get("ADX_TABLE", "Photos")
    
    if not all([cluster_uri, database, client_id, client_secret, tenant_id]):
        print("❌ Configuration ADX incomplète")
        print("Variables requises: ADX_CLUSTER_URI, ADX_DATABASE, ADX_CLIENT_ID, ADX_CLIENT_SECRET, ADX_TENANT_ID")
        return False
    
    # Connexion à ADX
    kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
        cluster_uri, client_id, client_secret, tenant_id
    )
    client = KustoClient(kcsb)
    
    print(f"🔗 Connexion à {cluster_uri}")
    print(f"📊 Base de données: {database}")
    print(f"📋 Table: {table_name}")
    
    # Créer la table
    create_table_command = f"""
    .create table {table_name} (
        DeviceId: string,
        CameraType: string,
        Timestamp: datetime,
        BlobUrl: string,
        TotalBlocks: int,
        FileSize: long,
        IngestionTime: datetime
    ) with (folder = "IoT/Photos", docstring = "Photos reconstruites depuis les capteurs IoT")
    """
    
    try:
        print("\n📝 Création de la table...")
        client.execute(database, create_table_command)
        print(f"✅ Table '{table_name}' créée avec succès!")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"ℹ️  La table '{table_name}' existe déjà")
        else:
            print(f"❌ Erreur: {e}")
            return False
    
    # Créer des fonctions d'affichage utiles
    functions = [
        # Fonction pour afficher les photos récentes
        f"""
        .create-or-alter function PhotosRecent(hours:int = 24) {{
            {table_name}
            | where IngestionTime > ago(hours * 1h)
            | order by Timestamp desc
            | project Timestamp, DeviceId, CameraType, FileSize, TotalBlocks, BlobUrl
        }}
        """,
        
        # Fonction pour les statistiques par device
        f"""
        .create-or-alter function PhotosStats() {{
            {table_name}
            | summarize 
                PhotoCount = count(),
                AvgFileSize = avg(FileSize),
                AvgBlocks = avg(TotalBlocks),
                LastPhoto = max(Timestamp)
              by DeviceId, CameraType
            | order by LastPhoto desc
        }}
        """
    ]
    
    print("\n📊 Création des fonctions d'affichage...")
    for func in functions:
        try:
            client.execute(database, func)
            print("  ✅ Fonction créée")
        except Exception as e:
            print(f"  ⚠️  Avertissement: {e}")
    
    # Afficher les permissions
    print("\n🔐 Vérification des permissions...")
    try:
        perms_query = f".show database {database} principals"
        response = client.execute(database, perms_query)
        
        print("\nPrincipaux autorisés:")
        for row in response.primary_results[0]:
            print(f"  - {row['PrincipalDisplayName']} ({row['Role']})")
    except Exception as e:
        print(f"  ⚠️  Impossible de vérifier les permissions: {e}")
    
    print("\n✅ Configuration ADX terminée!")
    print("\n📝 Requêtes utiles:")
    print(f"  - Photos récentes:         PhotosRecent()")
    print(f"  - Statistiques:            PhotosStats()")
    print(f"  - Toutes les photos:       {table_name} | take 100")
    
    return True


if __name__ == "__main__":
    import sys
    success = create_adx_table()
    sys.exit(0 if success else 1)

"""
Module d'insertion dans Azure Data Explorer (ADX).
"""
import logging
import os
from datetime import datetime
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from typing import Optional


class ADXClient:
    """Client pour interagir avec Azure Data Explorer."""
    
    def __init__(self):
        self.cluster_uri = os.environ.get("ADX_CLUSTER_URI")
        self.database = os.environ.get("ADX_DATABASE")
        self.table = os.environ.get("ADX_TABLE", "Photos")
        self.logger = logging.getLogger(__name__)
        
        # Authentification
        client_id = os.environ.get("ADX_CLIENT_ID")
        client_secret = os.environ.get("ADX_CLIENT_SECRET")
        tenant_id = os.environ.get("ADX_TENANT_ID")
        
        if not all([self.cluster_uri, self.database, client_id, client_secret, tenant_id]):
            raise ValueError("Configuration ADX incomplète")
        
        # Construire la chaîne de connexion
        kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
            self.cluster_uri, client_id, client_secret, tenant_id
        )
        
        self.client = KustoClient(kcsb)
        
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Crée la table si elle n'existe pas."""
        create_table_command = f"""
        .create table {self.table} (
            DeviceId: string,
            CameraType: string,
            Timestamp: datetime,
            BlobUrl: string,
            TotalBlocks: int,
            FileSize: long,
            IngestionTime: datetime
        ) with (folder = "IoT/Photos")
        """
        
        try:
            self.client.execute(self.database, create_table_command)
            self.logger.info(f"Table {self.table} créée ou existe déjà")
        except KustoServiceError as e:
            # Ignorer l'erreur si la table existe déjà
            if "already exists" not in str(e).lower():
                self.logger.warning(f"Avertissement lors de la création de la table: {e}")
    
    def insert_photo_record(self, device_id: str, camera_type: str, 
                           timestamp: datetime, blob_url: str, 
                           total_blocks: int, file_size: int) -> bool:
        """
        Insère un enregistrement de photo dans ADX.
        Retourne True si succès, False sinon.
        """
        try:
            # Préparer les données
            ingestion_time = datetime.utcnow()
            
            # Construire la commande d'insertion
            insert_command = f"""
            .ingest inline into table {self.table} <|
            "{device_id}","{camera_type}","{timestamp.isoformat()}","{blob_url}",{total_blocks},{file_size},"{ingestion_time.isoformat()}"
            """
            
            self.client.execute(self.database, insert_command)
            
            self.logger.info(
                f"Enregistrement inséré: Device={device_id}, Camera={camera_type}, "
                f"URL={blob_url}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'insertion dans ADX: {e}")
            return False
    
    def query_recent_photos(self, device_id: Optional[str] = None, 
                           hours: int = 24) -> list:
        """
        Récupère les photos récentes.
        Pour debugging et monitoring.
        """
        try:
            query = f"{self.table} | where IngestionTime > ago({hours}h)"
            
            if device_id:
                query += f" | where DeviceId == '{device_id}'"
            
            query += " | order by Timestamp desc | take 100"
            
            response = self.client.execute(self.database, query)
            return list(response.primary_results[0])
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la requête ADX: {e}")
            return []

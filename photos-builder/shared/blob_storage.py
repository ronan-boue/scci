"""
Module de stockage dans Azure Blob Storage.
"""
import logging
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from typing import Optional


class BlobStorageClient:
    """Client pour interagir avec Azure Blob Storage."""
    
    def __init__(self):
        self.connection_string = os.environ.get("BLOB_STORAGE_CONNECTION_STRING")
        self.container_name = os.environ.get("BLOB_CONTAINER_NAME", "photos")
        self.logger = logging.getLogger(__name__)
        
        if not self.connection_string:
            raise ValueError("BLOB_STORAGE_CONNECTION_STRING non configurée")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Crée le conteneur s'il n'existe pas."""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            if not container_client.exists():
                container_client.create_container()
                self.logger.info(f"Conteneur créé: {self.container_name}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du conteneur: {e}")
    
    def upload_photo(self, device_id: str, camera_type: str, timestamp: datetime, 
                    photo_data: bytes) -> Optional[str]:
        """
        Upload une photo dans Blob Storage.
        Retourne l'URL de la photo si succès, None sinon.
        """
        try:
            # Générer un nom de blob unique
            blob_name = self._generate_blob_name(device_id, camera_type, timestamp)
            
            # Obtenir le client du blob
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload avec métadonnées
            blob_client.upload_blob(
                photo_data,
                overwrite=True,
                content_settings=ContentSettings(content_type='image/jpeg'),
                metadata={
                    'device_id': device_id,
                    'camera_type': camera_type,
                    'timestamp': timestamp.isoformat()
                }
            )
            
            # Retourner l'URL publique
            blob_url = blob_client.url
            self.logger.info(f"Photo uploadée: {blob_url}")
            return blob_url
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'upload: {e}")
            return None
    
    def _generate_blob_name(self, device_id: str, camera_type: str, 
                           timestamp: datetime) -> str:
        """Génère un nom de blob unique et organisé."""
        # Format: device_id/YYYY/MM/DD/camera_type_HHmmss_timestamp.jpg
        date_path = timestamp.strftime("%Y/%m/%d")
        time_str = timestamp.strftime("%H%M%S")
        timestamp_ms = int(timestamp.timestamp() * 1000)
        
        return f"{device_id}/{date_path}/{camera_type}_{time_str}_{timestamp_ms}.jpg"

"""
Module de gestion de l'état des photos en cours de reconstruction.
Stocke les blocs reçus en mémoire jusqu'à ce que la photo soit complète.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading


@dataclass
class PhotoBlock:
    """Représente un bloc de données de photo."""
    block_number: int
    size: int
    data: bytes


@dataclass
class PhotoState:
    """État d'une photo en cours de reconstruction."""
    device_id: str
    camera_type: str  # 'CAMAV' ou 'CAMAR'
    total_blocks: int
    first_timestamp: datetime
    blocks: Dict[int, PhotoBlock] = field(default_factory=dict)
    
    def is_complete(self) -> bool:
        """Vérifie si tous les blocs ont été reçus."""
        return len(self.blocks) == self.total_blocks
    
    def is_expired(self, timeout_minutes: int = 2) -> bool:
        """Vérifie si la photo a expiré (timeout dépassé)."""
        return datetime.utcnow() - self.first_timestamp > timedelta(minutes=timeout_minutes)
    
    def get_sorted_data(self) -> bytes:
        """Retourne les données complètes de la photo triées par numéro de bloc."""
        sorted_blocks = sorted(self.blocks.values(), key=lambda b: b.block_number)
        return b''.join(block.data for block in sorted_blocks)


class PhotoStateManager:
    """Gestionnaire de l'état des photos en cours de reconstruction."""
    
    def __init__(self, timeout_minutes: int = 2):
        self.timeout_minutes = timeout_minutes
        self.photos: Dict[str, PhotoState] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def _get_photo_key(self, device_id: str, camera_type: str, timestamp: datetime) -> str:
        """Génère une clé unique pour identifier une photo."""
        # Grouper les messages dans une fenêtre de 2 minutes
        minute_window = timestamp.replace(second=0, microsecond=0)
        return f"{device_id}_{camera_type}_{minute_window.isoformat()}"
    
    def initialize_photo(self, device_id: str, camera_type: str, total_blocks: int, 
                        timestamp: datetime) -> str:
        """Initialise une nouvelle photo."""
        with self._lock:
            key = self._get_photo_key(device_id, camera_type, timestamp)
            
            if key not in self.photos:
                self.photos[key] = PhotoState(
                    device_id=device_id,
                    camera_type=camera_type,
                    total_blocks=total_blocks,
                    first_timestamp=timestamp
                )
                self.logger.info(f"Photo initialisée: {key} avec {total_blocks} blocs")
            
            return key
    
    def add_block(self, key: str, block_number: int, size: int, data: bytes) -> Optional[PhotoState]:
        """
        Ajoute un bloc à une photo.
        Retourne la PhotoState si la photo est complète, None sinon.
        """
        with self._lock:
            if key not in self.photos:
                self.logger.warning(f"Photo non initialisée: {key}")
                return None
            
            photo = self.photos[key]
            photo.blocks[block_number] = PhotoBlock(block_number, size, data)
            
            self.logger.info(f"Bloc {block_number}/{photo.total_blocks} ajouté pour {key}")
            
            if photo.is_complete():
                self.logger.info(f"Photo complète: {key}")
                return photo
            
            return None
    
    def find_matching_photo(self, device_id: str, camera_type: str, 
                           timestamp: datetime) -> Optional[str]:
        """Trouve une photo correspondante dans la fenêtre de temps."""
        with self._lock:
            # Chercher dans une fenêtre de ±2 minutes
            for delta_minutes in range(-2, 3):
                test_time = timestamp + timedelta(minutes=delta_minutes)
                test_key = self._get_photo_key(device_id, camera_type, test_time)
                
                if test_key in self.photos:
                    return test_key
            
            return None
    
    def remove_photo(self, key: str):
        """Supprime une photo du gestionnaire."""
        with self._lock:
            if key in self.photos:
                del self.photos[key]
                self.logger.info(f"Photo supprimée: {key}")
    
    def cleanup_expired_photos(self):
        """Nettoie les photos expirées."""
        with self._lock:
            expired_keys = [
                key for key, photo in self.photos.items() 
                if photo.is_expired(self.timeout_minutes)
            ]
            
            for key in expired_keys:
                self.logger.warning(f"Photo expirée supprimée: {key}")
                del self.photos[key]
            
            return len(expired_keys)

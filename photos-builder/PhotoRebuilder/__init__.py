"""
Azure Function principale pour reconstruire les photos depuis IoT Hub.
Trigger: Event Hub (IoT Hub)
"""
import azure.functions as func
import json
import base64
import logging
import os
from datetime import datetime
from typing import Optional
from shared.photo_state import PhotoStateManager
from shared.blob_storage import BlobStorageClient
from shared.adx_client import ADXClient


# Instance globale du gestionnaire d'état (persiste entre les invocations)
photo_manager = PhotoStateManager(
    timeout_minutes=int(os.environ.get("PHOTO_TIMEOUT_MINUTES", "2"))
)
blob_client = None
adx_client = None


def initialize_clients():
    """Initialise les clients Azure de manière lazy."""
    global blob_client, adx_client
    
    if blob_client is None:
        blob_client = BlobStorageClient()
    
    if adx_client is None:
        adx_client = ADXClient()


def parse_iot_hub_message(body_bytes: bytes) -> list:
    """
    Parse un message IoT Hub au format nouveau (DCAV/DCAR/BCAV/BCAR).
    Retourne une liste de data_items parsés.
    """
    try:
        data_items = []
        
        # Nouveau format: {"data":[{"type":"DCAV","val":"210"}]} ou
        #                 {"data":[{"type":"BCAV","val":"1 512 <BINARY>"}]}
        
        # Chercher le type de message
        if b'"type":"DCAV"' in body_bytes:
            # Message d'initialisation caméra avant
            match = body_bytes.find(b'"val":"')
            if match != -1:
                val_start = match + 7
                val_end = body_bytes.find(b'"', val_start)
                total_blocks = int(body_bytes[val_start:val_end].decode('ascii'))
                data_items.append({'type': 'DCAV', 'val': total_blocks})
        
        elif b'"type":"DCAR"' in body_bytes:
            # Message d'initialisation caméra arrière
            match = body_bytes.find(b'"val":"')
            if match != -1:
                val_start = match + 7
                val_end = body_bytes.find(b'"', val_start)
                total_blocks = int(body_bytes[val_start:val_end].decode('ascii'))
                data_items.append({'type': 'DCAR', 'val': total_blocks})
        
        elif b'"type":"BCAV"' in body_bytes:
            # Bloc caméra avant: "val":"<numéro> <taille> <BINARY>"
            match = body_bytes.find(b'"val":"')
            if match != -1:
                val_start = match + 7
                
                # Extraire numéro et taille
                space1 = body_bytes.find(b' ', val_start)
                block_number = int(body_bytes[val_start:space1].decode('ascii'))
                
                space2 = body_bytes.find(b' ', space1 + 1)
                block_size = int(body_bytes[space1+1:space2].decode('ascii'))
                
                # Données binaires
                data_start = space2 + 1
                data_bytes = body_bytes[data_start:-3]  # -3 pour enlever "}]}
                
                data_items.append({'type': 'BCAV_BLC', 'val': block_number})
                data_items.append({'type': 'BCAV_SIZ', 'val': block_size})
                data_items.append({'type': 'BCAV_DAT', 'val': data_bytes})
        
        elif b'"type":"BCAR"' in body_bytes:
            # Bloc caméra arrière
            match = body_bytes.find(b'"val":"')
            if match != -1:
                val_start = match + 7
                
                space1 = body_bytes.find(b' ', val_start)
                block_number = int(body_bytes[val_start:space1].decode('ascii'))
                
                space2 = body_bytes.find(b' ', space1 + 1)
                block_size = int(body_bytes[space1+1:space2].decode('ascii'))
                
                data_start = space2 + 1
                data_bytes = body_bytes[data_start:-3]
                
                data_items.append({'type': 'BCAR_BLC', 'val': block_number})
                data_items.append({'type': 'BCAR_SIZ', 'val': block_size})
                data_items.append({'type': 'BCAR_DAT', 'val': data_bytes})
        
        return data_items
        
    except Exception as e:
        logging.error(f"Erreur de parsing du message IoT Hub: {e}")
        return []


def parse_message_body(body_base64: str) -> tuple:
    """
    Parse le body encodé en base64 (pour compatibilité avec les fichiers d'export).
    Cette fonction est utilisée uniquement pour les tests avec des fichiers JSON exportés.
    """
    try:
        body_bytes = base64.b64decode(body_base64)
        return parse_iot_hub_message(body_bytes)
    except Exception as e:
        logging.error(f"Erreur de parsing du body base64: {e}")
        return []


def process_photo_init(device_id: str, camera_type: str, total_blocks: int, 
                       timestamp: datetime) -> str:
    """Traite un message d'initialisation de photo (DCAV/DCAR)."""
    logging.info(
        f"Initialisation photo: Device={device_id}, Camera={camera_type}, "
        f"Blocs={total_blocks}"
    )
    
    return photo_manager.initialize_photo(
        device_id, camera_type, total_blocks, timestamp
    )


def process_photo_block(device_id: str, camera_type: str, block_number: int, 
                       block_size: int, block_data: bytes, timestamp: datetime):
    """Traite un bloc de photo (BCAV/BCAR)."""
    try:
        # Les données sont déjà en bytes bruts
        data_bytes = block_data
        
        logging.info(
            f"Bloc reçu: Device={device_id}, Camera={camera_type}, "
            f"Bloc={block_number}, Taille={len(data_bytes)} bytes"
        )
        
        # Trouver la photo correspondante
        photo_key = photo_manager.find_matching_photo(device_id, camera_type, timestamp)
        
        if not photo_key:
            logging.warning(
                f"Aucune photo initialisée trouvée pour le bloc {block_number}"
            )
            return
        
        # Ajouter le bloc
        completed_photo = photo_manager.add_block(
            photo_key, block_number, block_size, data_bytes
        )
        
        # Si la photo est complète, la sauvegarder
        if completed_photo:
            save_completed_photo(completed_photo, photo_key)
            
    except Exception as e:
        logging.error(f"Erreur lors du traitement du bloc: {e}")


def save_completed_photo(photo_state, photo_key: str):
    """Sauvegarde une photo complète dans Blob Storage et ADX."""
    try:
        initialize_clients()
        
        # Récupérer les données complètes
        photo_data = photo_state.get_sorted_data()
        file_size = len(photo_data)
        
        logging.info(
            f"Photo complète: Device={photo_state.device_id}, "
            f"Camera={photo_state.camera_type}, Taille={file_size} bytes"
        )
        
        # Upload vers Blob Storage
        blob_url = blob_client.upload_photo(
            photo_state.device_id,
            photo_state.camera_type,
            photo_state.first_timestamp,
            photo_data
        )
        
        if not blob_url:
            logging.error("Échec de l'upload dans Blob Storage")
            return
        
        # Insérer dans ADX
        success = adx_client.insert_photo_record(
            photo_state.device_id,
            photo_state.camera_type,
            photo_state.first_timestamp,
            blob_url,
            photo_state.total_blocks,
            file_size
        )
        
        if success:
            logging.info(f"Photo sauvegardée avec succès: {blob_url}")
            # Nettoyer l'état
            photo_manager.remove_photo(photo_key)
        else:
            logging.error("Échec de l'insertion dans ADX")
            
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la photo: {e}")


def main(events: func.EventHubEvent):
    """
    Fonction principale déclenchée par IoT Hub via Event Hub.
    """
    try:
        # Nettoyer les photos expirées périodiquement
        expired_count = photo_manager.cleanup_expired_photos()
        if expired_count > 0:
            logging.info(f"{expired_count} photos expirées nettoyées")
        
        # Traiter chaque événement du batch
        for event in events:
            try:
                # Extraire les propriétés système
                system_properties = event.system_properties
                device_id = system_properties.get(b'iothub-connection-device-id', b'').decode('utf-8')
                enqueued_time = system_properties.get(b'iothub-enqueuedtime')
                
                if isinstance(enqueued_time, bytes):
                    enqueued_time = enqueued_time.decode('utf-8')
                
                # Limiter les microsecondes à 6 chiffres (Python supporte jusqu'à 6 chiffres)
                if '.' in enqueued_time and len(enqueued_time.split('.')[-1]) > 6:
                    parts = enqueued_time.split('.')
                    microseconds = parts[1][:6]  # Garder seulement 6 chiffres
                    # Reconstruire avec le timezone
                    if '+' in parts[1]:
                        tz = parts[1].split('+', 1)[1]
                        enqueued_time = f"{parts[0]}.{microseconds}+{tz}"
                    elif 'Z' in parts[1]:
                        enqueued_time = f"{parts[0]}.{microseconds}Z"
                
                timestamp = datetime.fromisoformat(enqueued_time.replace('Z', '+00:00'))
                
                # Parser le body du message (directement depuis Event Hub, pas de wrapper JSON)
                body_bytes = event.get_body()
                
                # Parser le message IoT Hub
                data = parse_iot_hub_message(body_bytes)
                if not data:
                    logging.warning(f"Aucune donnée parsée pour device {device_id}")
                    continue
                
                # Traiter selon le type de message
                for item in data:
                    msg_type = item.get('type', '')
                    value = item.get('val')
                    
                    # Message d'initialisation DCAV (caméra avant)
                    if msg_type == 'DCAV':
                        process_photo_init(device_id, 'CAMAV', value, timestamp)
                    
                    # Message d'initialisation DCAR (caméra arrière)
                    elif msg_type == 'DCAR':
                        process_photo_init(device_id, 'CAMAR', value, timestamp)
                    
                    # Bloc de données BCAV (caméra avant)
                    elif msg_type == 'BCAV_BLC':
                        block_number = value
                        block_size = next(
                            (d['val'] for d in data if d['type'] == 'BCAV_SIZ'), 0
                        )
                        block_data = next(
                            (d['val'] for d in data if d['type'] == 'BCAV_DAT'), None
                        )
                        
                        if block_data is not None:
                            process_photo_block(
                                device_id, 'CAMAV', block_number, 
                                block_size, block_data, timestamp
                            )
                    
                    # Bloc de données BCAR (caméra arrière)
                    elif msg_type == 'BCAR_BLC':
                        block_number = value
                        block_size = next(
                            (d['val'] for d in data if d['type'] == 'BCAR_SIZ'), 0
                        )
                        block_data = next(
                            (d['val'] for d in data if d['type'] == 'BCAR_DAT'), None
                        )
                        
                        if block_data is not None:
                            process_photo_block(
                                device_id, 'CAMAR', block_number, 
                                block_size, block_data, timestamp
                            )
                
            except Exception as e:
                logging.error(f"Erreur lors du traitement d'un événement: {e}")
                continue
        
    except Exception as e:
        logging.error(f"Erreur critique dans la fonction: {e}")
        raise

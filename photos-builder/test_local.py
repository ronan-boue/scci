"""
Script de test local pour simuler le traitement des messages IoT Hub.
Charge les données depuis le fichier JSON d'exemple et les traite.
"""
import json
import base64
import sys
import os
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from shared.photo_state import PhotoStateManager

# Les clients Azure sont optionnels pour les tests locaux
try:
    from shared.blob_storage import BlobStorageClient
    from shared.adx_client import ADXClient
    AZURE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Clients Azure non disponibles (normal pour test local): {e}")
    AZURE_AVAILABLE = False


class LocalTester:
    """Testeur local pour la fonction Azure."""
    
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.photo_manager = PhotoStateManager(timeout_minutes=2)
        # Pour les tests locaux, on peut simuler les clients
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)
    
    def parse_message(self, msg: dict) -> tuple:
        """Parse un message du fichier JSON."""
        # Extraire les propriétés système
        system_props = msg.get('SystemProperties', {})
        device_id = system_props.get('connectionDeviceId', 'unknown')
        enqueued_time_str = system_props.get('enqueuedTime', '')
        
        # Limiter les microsecondes à 6 chiffres (Python supporte jusqu'à 6 chiffres)
        if '.' in enqueued_time_str:
            parts = enqueued_time_str.split('.')
            if len(parts) == 2:
                # Extraire la partie fractionnaire et le timezone
                frac_and_tz = parts[1]
                if '+' in frac_and_tz or 'Z' in frac_and_tz:
                    # Séparer fraction et timezone
                    for sep in ['+', 'Z']:
                        if sep in frac_and_tz:
                            frac, tz = frac_and_tz.split(sep, 1)
                            # Limiter à 6 chiffres
                            frac = frac[:6]
                            enqueued_time_str = f"{parts[0]}.{frac}{sep}{tz}" if sep != 'Z' else f"{parts[0]}.{frac}Z"
                            break
        
        timestamp = datetime.fromisoformat(enqueued_time_str.replace('Z', '+00:00'))
        
        # Décoder le body
        body_base64 = msg.get('Body', '')
        try:
            body_bytes = base64.b64decode(body_base64)
            
            # Le format contient du JSON avec des bytes bruts pour CAMAV_DAT
            # On doit parser manuellement car les données binaires cassent le JSON standard
            data = self._parse_iot_message(body_bytes)
        except Exception as e:
            print(f"Erreur de parsing: {e}")
            data = []
        
        return device_id, timestamp, data
    
    def _parse_iot_message(self, body_bytes):
        """Parse un message IoT au nouveau format (DCAV/DCAR/BCAV/BCAR)."""
        try:
            data_items = []
            
            # Nouveau format: {"data":[{"type":"DCAV","val":"210"}]} ou
            #                 {"data":[{"type":"BCAV","val":"1 512 <BINARY>"}]}
            
            # Chercher le type de message
            if b'"type":"DCAV"' in body_bytes:
                # Message d'initialisation caméra avant
                # Format: "val":"210"
                match = body_bytes.find(b'"val":"')
                if match != -1:
                    val_start = match + 7  # len(b'"val":"')
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
                # Bloc caméra avant: "val":"1 512 <BINARY>"
                match = body_bytes.find(b'"val":"')
                if match != -1:
                    val_start = match + 7  # Après "val":"
                    # Les données vont jusqu'à "}]} à la fin
                    # Format: "<numéro> <taille> <données_binaires>"
                    
                    # Extraire numéro et taille (ASCII)
                    space1 = body_bytes.find(b' ', val_start)
                    block_number = int(body_bytes[val_start:space1].decode('ascii'))
                    
                    space2 = body_bytes.find(b' ', space1 + 1)
                    block_size = int(body_bytes[space1+1:space2].decode('ascii'))
                    
                    # Les données binaires commencent après le 2e espace
                    data_start = space2 + 1
                    # et vont jusqu'à "}]} (3 bytes avant la fin)
                    data_bytes = body_bytes[data_start:-3]
                    
                    data_items.append({'type': 'BCAV_BLC', 'val': block_number})
                    data_items.append({'type': 'BCAV_SIZ', 'val': block_size})
                    data_items.append({'type': 'BCAV_DAT', 'val': data_bytes})
            
            elif b'"type":"BCAR"' in body_bytes:
                # Bloc caméra arrière: même format
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
            print(f"Erreur _parse_iot_message: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def process_messages(self):
        """Traite tous les messages du fichier."""
        print(f"Chargement des messages depuis: {self.json_file}")
        
        with open(self.json_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Le fichier contient un message par ligne
            messages = [json.loads(line.strip()) for line in content.split('\n') if line.strip()]
        
        print(f"{len(messages)} messages chargés")
        
        photos_completed = []
        
        for idx, msg in enumerate(messages):
            device_id, timestamp, data = self.parse_message(msg)
            
            for item in data:
                msg_type = item.get('type', '')
                value = item.get('val')
                
                # Initialisation DCAV (caméra avant)
                if msg_type == 'DCAV':
                    print(f"\n[{idx}] Init CAMAV: {value} blocs à {timestamp}")
                    photo_key = self.photo_manager.initialize_photo(
                        device_id, 'CAMAV', value, timestamp
                    )
                
                # Bloc BCAV (caméra avant)
                elif msg_type == 'BCAV_BLC':
                    block_number = value
                    block_size = next((d['val'] for d in data if d['type'] == 'BCAV_SIZ'), 0)
                    block_data_raw = next((d['val'] for d in data if d['type'] == 'BCAV_DAT'), None)
                    
                    if block_data_raw is not None:
                        try:
                            data_bytes = block_data_raw if isinstance(block_data_raw, bytes) else block_data_raw.encode('latin-1')
                            
                            photo_key = self.photo_manager.find_matching_photo(
                                device_id, 'CAMAV', timestamp
                            )
                            
                            if photo_key:
                                completed_photo = self.photo_manager.add_block(
                                    photo_key, block_number, block_size, data_bytes
                                )
                                
                                print(f"[{idx}] Bloc CAMAV {block_number} ajouté ({block_size} bytes)")
                                
                                if completed_photo:
                                    print(f"\n✓ Photo CAMAV complète!")
                                    self.save_photo_locally(completed_photo, photo_key)
                                    photos_completed.append(photo_key)
                                    self.photo_manager.remove_photo(photo_key)
                        
                        except Exception as e:
                            print(f"Erreur bloc {block_number}: {e}")
                
                # Initialisation DCAR (caméra arrière)
                elif msg_type == 'DCAR':
                    print(f"\n[{idx}] Init CAMAR: {value} blocs à {timestamp}")
                    photo_key = self.photo_manager.initialize_photo(
                        device_id, 'CAMAR', value, timestamp
                    )
                
                # Bloc BCAR (caméra arrière)
                elif msg_type == 'BCAR_BLC':
                    block_number = value
                    block_size = next((d['val'] for d in data if d['type'] == 'BCAR_SIZ'), 0)
                    block_data_raw = next((d['val'] for d in data if d['type'] == 'BCAR_DAT'), None)
                    
                    if block_data_raw is not None:
                        try:
                            data_bytes = block_data_raw if isinstance(block_data_raw, bytes) else block_data_raw.encode('latin-1')
                            
                            photo_key = self.photo_manager.find_matching_photo(
                                device_id, 'CAMAR', timestamp
                            )
                            
                            if photo_key:
                                completed_photo = self.photo_manager.add_block(
                                    photo_key, block_number, block_size, data_bytes
                                )
                                
                                print(f"[{idx}] Bloc CAMAR {block_number} ajouté ({block_size} bytes)")
                                
                                if completed_photo:
                                    print(f"\n✓ Photo CAMAR complète!")
                                    self.save_photo_locally(completed_photo, photo_key)
                                    photos_completed.append(photo_key)
                                    self.photo_manager.remove_photo(photo_key)
                        
                        except Exception as e:
                            print(f"Erreur bloc {block_number}: {e}")
        
        print(f"\n\n{'='*60}")
        print(f"Traitement terminé:")
        print(f"  - Messages traités: {len(messages)}")
        print(f"  - Photos complétées: {len(photos_completed)}")
        print(f"  - Fichiers sauvegardés dans: {self.output_dir.absolute()}")
        print(f"{'='*60}")
        
        return photos_completed
    
    def save_photo_locally(self, photo_state, photo_key: str):
        """Sauvegarde une photo localement pour test."""
        photo_data = photo_state.get_sorted_data()
        
        # Générer un nom de fichier
        timestamp_str = photo_state.first_timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{photo_state.device_id}_{photo_state.camera_type}_{timestamp_str}.jpg"
        filepath = self.output_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(photo_data)
        
        print(f"  → Fichier sauvegardé: {filepath}")
        print(f"  → Taille: {len(photo_data)} bytes")
        print(f"  → Blocs: {len(photo_state.blocks)}/{photo_state.total_blocks}")


def main():
    """Point d'entrée du script de test."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test local de la fonction Azure')
    parser.add_argument(
        'json_file',
        nargs='?',
        default='39 (1).json',
        help='Fichier JSON contenant les messages IoT Hub (par défaut: 39 (1).json)'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Erreur: Fichier non trouvé: {args.json_file}")
        return 1
    
    tester = LocalTester(args.json_file)
    photos = tester.process_messages()
    
    return 0 if len(photos) > 0 else 1


if __name__ == '__main__':
    sys.exit(main())

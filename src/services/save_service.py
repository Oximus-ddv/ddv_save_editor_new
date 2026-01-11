"""
Save file handling service for DDV Save Editor
"""
import json
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib

from ..models.game_item import SaveData, PlayerInventoryItem, PetData


logger = logging.getLogger(__name__)


class SaveFileService:
    """Service for loading, decrypting, and saving DDV save files"""
    
    def __init__(self, backup_dir: str = "backups", max_backups: int = 10):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.backup_dir.mkdir(exist_ok=True)
        
        # Current loaded save data
        self.current_save_path: Optional[Path] = None
        self.current_save_data: Optional[SaveData] = None
        self.is_encrypted: bool = False
        self.decryption_key: Optional[bytes] = None

    def reparse_from_json(self, json_data: Dict[str, Any]):
        """Re-parse save data from a raw JSON dictionary (e.g. from Full Editor)"""
        if not json_data:
            return
            
        try:
            # Parse the new data
            new_save_data = self._parse_save_data(json_data)
            
            # Update current save data
            self.current_save_data = new_save_data
            
            logger.info("Successfully re-parsed save data from JSON")
            return self.current_save_data
            
        except Exception as e:
            logger.error(f"Error re-parsing save data: {e}")
            # Don't raise, just log, so we don't crash the UI if parsing fails on a partial edit
            return None
    
    def detect_save_file(self) -> Optional[Path]:
        """Auto-detect DDV save file location"""
        try:
            # Common DDV save locations
            possible_paths = [
                Path.home() / "AppData" / "LocalLow" / "Gameloft" / "Disney Dreamlight Valley" / "profile.json",
                Path.home() / "Documents" / "My Games" / "Disney Dreamlight Valley" / "profile.json",
                Path("profile.json"),  # Current directory
            ]
            
            for path in possible_paths:
                if path.exists():
                    logger.info(f"Found save file at: {path}")
                    return path
            
            logger.info("No save file found in common locations")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting save file: {e}")
            return None
    
    def is_file_encrypted(self, file_path: Path) -> bool:
        """Check if a file appears to be encrypted by analyzing entropy"""
        try:
            with open(file_path, 'rb') as f:
                # Read first 1KB to analyze
                data = f.read(1024)
            
            if len(data) < 50:
                return False
            
            # First check if it looks like plain text JSON
            try:
                # Try to decode as UTF-8 and check for JSON start
                text_start = data[:100].decode('utf-8', errors='ignore')
                if text_start.strip().startswith('{') or text_start.strip().startswith('['):
                    logger.info("File appears to be plain JSON")
                    return False
            except:
                pass
            
            # Check if it starts with ZIP signature (compressed but not encrypted)
            if data.startswith(b'PK'):
                logger.info("File appears to be ZIP compressed")
                return False
            
            # Calculate byte frequency entropy
            byte_counts = [0] * 256
            for byte in data:
                byte_counts[byte] += 1
            
            import math
            entropy = 0.0
            data_len = len(data)
            for count in byte_counts:
                if count > 0:
                    frequency = count / data_len
                    entropy -= frequency * math.log2(frequency)
            
            # High entropy (> 7.5) usually indicates encryption
            is_encrypted = entropy > 7.5
            logger.info(f"File entropy: {entropy:.2f}, encrypted: {is_encrypted}")
            return is_encrypted
            
        except Exception as e:
            logger.error(f"Error checking file encryption: {e}")
            return False
    
    def load_save_file(self, file_path: str, decryption_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        Load a save file (encrypted or unencrypted)
        
        Returns:
            (success, message)
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Save file not found: {file_path}")
                return False, f"File not found: {file_path}"
            
            # Log detailed file information
            file_stat = file_path.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            from datetime import datetime
            mod_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            logger.info(f"Loading save file: {file_path.name}")
            logger.info(f"File size: {file_size_mb:.2f} MB")
            logger.info(f"Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Full path: {file_path}")
            
            # Create backup before loading
            self._create_backup(file_path)
            
            # Check if encrypted
            self.is_encrypted = self.is_file_encrypted(file_path)
            logger.info(f"File encryption status: {'Encrypted' if self.is_encrypted else 'Plain text'}")
            
            if self.is_encrypted:
                if not decryption_key:
                    logger.error("Decryption key required but not provided")
                    return False, "Decryption key required for encrypted save file"
                
                logger.info("Attempting to decrypt save file...")
                # Decrypt the file
                decrypted_data = self._decrypt_save_file(file_path, decryption_key)
                if not decrypted_data:
                    logger.error("Decryption failed - invalid key or corrupted file")
                    return False, "Failed to decrypt save file (invalid key?)"
                
                logger.info("Decryption successful, checking compression...")
                # Decompress if needed
                json_data = self._decompress_data(decrypted_data)
                
            else:
                # Read unencrypted file
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # Try decompression first
                json_data = self._decompress_data(data)
                
                # If decompression fails, assume it's plain JSON
                if not json_data:
                    # Try different encodings
                    for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                        try:
                            json_data = data.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # If all encodings fail, use utf-8 with error handling
                        json_data = data.decode('utf-8', errors='replace')
            
            # Parse JSON with detailed error handling
            try:
                save_dict = json.loads(json_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                # Try to provide more helpful error messages
                if "Expecting property name enclosed in double quotes" in str(e):
                    return False, "Save file appears to be corrupted. Try restoring from a backup or using the working copy you mentioned."
                return False, f"Failed to parse save file: {str(e)}"
            
            # Convert to SaveData model
            try:
                self.current_save_data = self._parse_save_data(save_dict)
                self.current_save_path = file_path
            except Exception as e:
                logger.error(f"Error parsing save data: {str(e)}")
                return False, f"Failed to parse save data structure: {str(e)}"
            
            if decryption_key:
                self.decryption_key = self._hex_to_bytes(decryption_key)
            
            logger.info(f"Successfully loaded save file: {file_path}")
            return True, "Save file loaded successfully"
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in save file: {e}"
        except Exception as e:
            logger.error(f"Error loading save file: {e}")
            return False, f"Error loading save file: {e}"
    
    def find_latest_save_file(self, base_path: Optional[str] = None) -> Optional[str]:
        """
        Find the newest 'profile.json' save by file modification time.
        - Searches recursively under the DDV save root
        - Considers only paths under folders starting with 'steam' or 'windows'
        - Break ties by parent folder mtime and prefer folders ending with '_r'
        """
        try:
            if not base_path:
                base_path = Path.home() / "AppData" / "LocalLow" / "Gameloft" / "Disney Dreamlight Valley"
            else:
                base_path = Path(base_path)

            if not base_path.exists():
                logger.warning(f"DDV save directory not found: {base_path}")
                return None

            logger.info(f"Searching for save files in: {base_path}")

            candidates: List[Dict[str, Any]] = []

            for profile_path in base_path.rglob("profile.json"):
                try:
                    folder = profile_path.parent
                    # Identify top-level folder under base_path for filtering
                    try:
                        rel = folder.relative_to(base_path)
                        top_name = rel.parts[0] if rel.parts else folder.name
                    except Exception:
                        top_name = folder.name
                    if not (top_name.startswith('steam') or top_name.startswith('windows')):
                        continue

                    fstat = profile_path.stat()
                    dstat = folder.stat()
                    prefer_remote = 1 if folder.name.endswith('_r') else 0
                    candidates.append({
                        'path': str(profile_path),
                        'folder': folder.name,
                        'modified': fstat.st_mtime,
                        'folder_mtime': dstat.st_mtime,
                        'size': fstat.st_size,
                        'prefer': prefer_remote,
                    })
                except Exception:
                    continue

            if not candidates:
                logger.warning("No save files found in steam/windows folders")
                return None

            # Sort by file mtime desc, then folder mtime desc, then prefer_remote desc
            candidates.sort(key=lambda x: (x['modified'], x['folder_mtime'], x['prefer']), reverse=True)
            latest = candidates[0]

            logger.info(f"Latest save file selected: {latest['folder']}/profile.json")
            logger.info(f"Modified: {datetime.fromtimestamp(latest['modified'])}")
            logger.info(f"Size: {latest['size'] / (1024*1024):.2f} MB")

            return latest['path']

        except Exception as e:
            logger.error(f"Error finding latest save file: {e}")
            return None
    
    def auto_load_latest_save(self, decryption_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        Automatically find and load the latest save file
        """
        logger.info("Starting automatic save file detection...")
        
        latest_save_path = self.find_latest_save_file()
        if not latest_save_path:
            return False, "No save files found in DDV directory"
        
        logger.info(f"Auto-loading: {latest_save_path}")
        return self.load_save_file(latest_save_path, decryption_key)
    
    def save_file(self, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """Save the current save data back to file"""
        try:
            if not self.current_save_data:
                return False, "No save data loaded"
            
            save_path = Path(output_path) if output_path else self.current_save_path
            if not save_path:
                return False, "No save path specified"
            
            # Create backup of original
            if save_path.exists():
                self._create_backup(save_path)
            
            # Convert SaveData back to dictionary
            save_dict = self._save_data_to_dict(self.current_save_data)
            
            # Convert to JSON with proper string key handling
            def convert_keys_to_str(obj):
                if isinstance(obj, dict):
                    return {str(key): convert_keys_to_str(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_keys_to_str(element) for element in obj]
                return obj
            
            # Ensure all dictionary keys are strings
            save_dict = convert_keys_to_str(save_dict)
            
            # Convert to JSON with ensure_ascii=False to handle non-ASCII characters
            json_data = json.dumps(save_dict, separators=(',', ':'), ensure_ascii=False)  # Compact format
            
            if self.is_encrypted and self.decryption_key:
                # Compress and encrypt
                compressed_data = self._compress_data(json_data.encode('utf-8'))
                encrypted_data = self._encrypt_data(compressed_data, self.decryption_key)
                
                with open(save_path, 'wb') as f:
                    f.write(encrypted_data)
            else:
                # Save as plain JSON or compressed
                if self._should_compress(json_data):
                    compressed_data = self._compress_data(json_data.encode('utf-8'))
                    with open(save_path, 'wb') as f:
                        f.write(compressed_data)
                else:
                    with open(save_path, 'w', encoding='utf-8', newline='') as f:
                        f.write(json_data)
            
            logger.info(f"Save file saved successfully: {save_path}")
            return True, "Save file saved successfully"
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, f"Error saving file: {e}"
    
    def _decrypt_save_file(self, file_path: Path, hex_key: str) -> Optional[bytes]:
        """Decrypt an encrypted save file"""
        try:
            key_bytes = self._hex_to_bytes(hex_key)
            
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Try AES ECB mode (common for DDV saves)
            cipher = Cipher(
                algorithms.AES(key_bytes),
                modes.ECB(),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding if present
            if decrypted_data and decrypted_data[-1] < 16:
                padding_len = decrypted_data[-1]
                decrypted_data = decrypted_data[:-padding_len]
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def _encrypt_data(self, data: bytes, key: bytes) -> bytes:
        """Encrypt data using AES ECB"""
        # Add PKCS7 padding
        padding_len = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_len] * padding_len)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.ECB(),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        return encryptor.update(padded_data) + encryptor.finalize()
    
    def _decompress_data(self, data: bytes) -> Optional[str]:
        """Try to decompress data if it's a ZIP file"""
        try:
            # Check if it looks like a ZIP file
            if data.startswith(b'PK'):
                import io
                with zipfile.ZipFile(io.BytesIO(data), 'r') as zip_file:
                    # Get the first file (should be the JSON)
                    names = zip_file.namelist()
                    if names:
                        with zip_file.open(names[0]) as json_file:
                            return json_file.read().decode('utf-8')
            
            # Try gzip decompression
            import gzip
            try:
                return gzip.decompress(data).decode('utf-8')
            except:
                pass
            
            return None
            
        except Exception:
            return None
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using ZIP format"""
        import io
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('profile.json', data)
        
        return buffer.getvalue()
    
    def _should_compress(self, json_data: str) -> bool:
        """Determine if we should compress the save file"""
        # Compress if file is large (>50KB) or if original was compressed
        return len(json_data) > 50000 or self.is_encrypted
    
    def _hex_to_bytes(self, hex_string: str) -> bytes:
        """Convert hex string to bytes"""
        # Remove any whitespace or separators
        hex_clean = hex_string.replace(' ', '').replace('-', '').replace(':', '')
        return bytes.fromhex(hex_clean)
    
    def _parse_save_data(self, save_dict: Dict[str, Any]) -> SaveData:
        """Parse save dictionary into SaveData model"""
        player_data = save_dict.get('Player', {})
        game_info = save_dict.get('GameInfo', {})
        
        # Parse collection sets
        collection_sets = player_data.get('CollectionSets', {})
        
        # Ensure Tools array is preserved
        if 'Tools' not in player_data:
            player_data['Tools'] = []
        
        # Parse currencies
        currencies = player_data.get('CurrencyAmounts', {})
        
        # Parse inventory items from ContainerInventories (Backpack and Storage)
        inventory_items = []
        container_inventories = player_data.get('ContainerInventories', {})
        for inv_id, container in container_inventories.items():
            inventory_list = container.get('Inventory', [])
            for item_data in inventory_list:
                try:
                    item_id = int(item_data.get('ItemID', 0))
                    if item_id == 0:  # Skip empty slots
                        continue
                        
                    amount = item_data.get('Amount', 1)
                    state = item_data.get('State')
                    marker = item_data.get('Marker')
                    
                    inventory_item = PlayerInventoryItem(
                        item_id=item_id,
                        amount=amount,
                        state=state,
                        marker=marker,
                        inventory_id=str(inv_id),
                        source_type="container",
                        raw_data=item_data # Capture all fields
                    )
                    inventory_items.append(inventory_item)
                except (ValueError, TypeError):
                    continue

        # Parse inventory items from ListInventories (Furniture, Clothes, Houses, etc.)
        list_inventories = player_data.get('ListInventories', {})
        for inv_id, container in list_inventories.items():
            inventory_dict = container.get('Inventory', {})
            # List inventory is a dictionary mapping ItemID string to item data
            for item_id_str, item_data in inventory_dict.items():
                try:
                    item_id = int(item_id_str)
                    if item_id == 0:
                        continue

                    # ListInventories items use 'Amount' and usually have a 'Marker'
                    amount = item_data.get('Amount', 1)
                    marker = item_data.get('Marker')

                    inventory_item = PlayerInventoryItem(
                        item_id=item_id,
                        amount=amount,
                        marker=marker,
                        inventory_id=str(inv_id),
                        source_type="list",
                        raw_data=item_data # Capture all fields
                    )
                    inventory_items.append(inventory_item)
                except (ValueError, TypeError):
                    continue
        
        # Parse pets (support newer fields: CustomName, XP)
        pets = []
        pets_data = player_data.get('Pets', [])
        for pet_data in pets_data:
            if isinstance(pet_data, dict) and 'PetItemID' in pet_data:
                pets.append(PetData(
                    pet_item_id=pet_data['PetItemID'],
                    name=pet_data.get('Name'),  # legacy name field
                    custom_name=pet_data.get('CustomName'),
                    friendship_level=pet_data.get('FriendshipLevel'),
                    xp=pet_data.get('XP', pet_data.get('FriendshipXP')),
                    is_following=pet_data.get('IsFollowing', False),
                    last_selfie_date=pet_data.get('LastSelfieDate'),
                    last_petted_date=pet_data.get('LastPettedDate'),
                    granted_inventory_slots=pet_data.get('GrantedInventorySlots', 0),
                    pending_hangout_rewards=pet_data.get('PendingHangoutRewards', []),
                    raw_data=pet_data # Capture all fields
                ))
        
        return SaveData(
            player_name=player_data.get('Name', 'Unknown'),
            player_level=player_data.get('Level', 1),
            star_coins=int(currencies.get('80000000', 0)),
            dreamlight=int(currencies.get('80300000', 0)),
            daisy_coins=int(currencies.get('80000009', 0)),
            mist=int(currencies.get('80000003', 0)),
            pixel_dust=int(currencies.get('80200002', 0)),
            story_book_magic=int(currencies.get('80000010', 0)),
            moonstones=int(currencies.get('80100000', 0)),
            inventory_items=inventory_items,
            pets=pets,
            collection_sets=collection_sets,
            game_version=game_info.get('Version', ''),
            save_version=str(save_dict.get('Version', '')),
            custom_data={'original_save': save_dict}  # Keep original for reference
        )
    
    def _save_data_to_dict(self, save_data: SaveData) -> Dict[str, Any]:
        """Convert SaveData back to dictionary format"""
        # Start with original save data if available
        if 'original_save' in save_data.custom_data:
            save_dict = save_data.custom_data['original_save'].copy()
            
            # Ensure Tools array is preserved from original save
            if 'Player' in save_dict and 'Tools' in save_dict['Player']:
                original_tools = save_dict['Player']['Tools']
            else:
                original_tools = []
        else:
            save_dict = {}
            original_tools = []
        
        # Update player data
        player_data = save_dict.setdefault('Player', {})
        player_data['Name'] = save_data.player_name
        player_data['Level'] = save_data.player_level
        player_data['CollectionSets'] = save_data.collection_sets
        
        # Update currencies
        currencies = player_data.setdefault('CurrencyAmounts', {})
        currencies['80000000'] = save_data.star_coins
        currencies['80300000'] = save_data.dreamlight
        currencies['80000009'] = save_data.daisy_coins
        currencies['80000003'] = save_data.mist
        currencies['80200002'] = save_data.pixel_dust
        currencies['80000010'] = save_data.story_book_magic
        currencies['80100000'] = save_data.moonstones
        
        # Ensure critical unmodeled player fields are preserved if they somehow got lost
        # (Though starting with original_save should have them already)
        if 'original_save' in save_data.custom_data:
            original_player = save_data.custom_data['original_save'].get('Player', {})
            for field in ['Xp', 'NextContainerInventoryID', 'NextListInventoryID', 'NextClothingDesignID']:
                if field in original_player and field not in player_data:
                    player_data[field] = original_player[field]
                elif field in original_player:
                    # Explicitly ensure we don't overwrite with 0 or smaller values if not intended
                    # For now, just ensure they exist. The model doesn't touch them.
                    pass
        
        # Update pets
        pets_list = []
        total_pet_inventory_slots = 0
        for pet in save_data.pets:
            # Start with original pet data if available to preserve unmodeled fields
            pet_dict = pet.raw_data.copy() if pet.raw_data else {}
            pet_dict['PetItemID'] = pet.pet_item_id
            
            # Preserve legacy Name if present; prefer CustomName when available
            if pet.custom_name:
                pet_dict['CustomName'] = pet.custom_name
            if pet.name:
                pet_dict['Name'] = pet.name
            if pet.friendship_level is not None:
                pet_dict['FriendshipLevel'] = pet.friendship_level
            if pet.xp is not None:
                # Update whichever field was present (XP or FriendshipXp)
                if 'FriendshipXp' in pet_dict:
                    pet_dict['FriendshipXp'] = pet.xp
                if 'XP' in pet_dict or 'FriendshipXp' not in pet_dict:
                    pet_dict['XP'] = pet.xp
            if pet.is_following:
                pet_dict['IsFollowing'] = pet.is_following
                total_pet_inventory_slots += pet.granted_inventory_slots # Accumulate granted slots from following pets
            if pet.last_selfie_date is not None:
                pet_dict['LastSelfieDate'] = pet.last_selfie_date
            if pet.last_petted_date is not None:
                pet_dict['LastPettedDate'] = pet.last_petted_date
            if pet.granted_inventory_slots is not None:
                pet_dict['GrantedInventorySlots'] = pet.granted_inventory_slots
            if pet.pending_hangout_rewards is not None:
                pet_dict['PendingHangoutRewards'] = pet.pending_hangout_rewards
            pets_list.append(pet_dict)

        player_data['Pets'] = pets_list
        
        # Calculate expected backpack size based on companions
        base_backpack_size = 42
        expected_backpack_size = base_backpack_size + total_pet_inventory_slots
        
        # Update ContainerInventories
        # We need to preserve the structure (Size, ID, etc.) of existing containers
        original_containers = player_data.get('ContainerInventories', {})
        
        # Group items by their inventory_id
        inventory_groups: Dict[str, List[PlayerInventoryItem]] = {}
        for item in save_data.inventory_items:
            if item.source_type == "container":
                inv_id = str(item.inventory_id or '0') # Default to backpack '0'
                if inv_id not in inventory_groups:
                    inventory_groups[inv_id] = []
                inventory_groups[inv_id].append(item)
            
        # Rebuild each container
        new_containers = original_containers.copy()
        for inv_id, items in inventory_groups.items():
            # Important: Use existing container as base to preserve metadata (ParentItemID, BelongsToPlayer, etc.)
            original_container = new_containers.get(inv_id, {})
            container = original_container.copy()
            
            if inv_id == "0": # Main backpack
                container['Size'] = expected_backpack_size
                container['ExtraBagSpace'] = total_pet_inventory_slots
            
            if not container:
                # Create new container if it doesn't exist (basic structure)
                # For main backpack, use calculated size, otherwise default to items + 10
                size_for_new_container = expected_backpack_size if inv_id == "0" else len(items) + 10 
                container = {'ID': int(inv_id) if inv_id.isdigit() else 0, 'Size': size_for_new_container, 'Inventory': []}
                if inv_id == "0":
                    container['ExtraBagSpace'] = total_pet_inventory_slots
            
            # Update the inventory list
            new_inv_list = []
            for item in items:
                # Start with original item data if available
                item_data = item.raw_data.copy() if item.raw_data else {}
                item_data.update({'ItemID': item.item_id, 'Amount': item.amount})
                
                if item.state is not None:
                    item_data['State'] = item.state
                elif 'State' not in item_data and item.item_id != 0:
                    item_data['State'] = None # Explicit null for state often required
                
                if item.marker:
                    item_data['Marker'] = item.marker
                
                new_inv_list.append(item_data)
            
            # Truncate if too many items for the main backpack
            if inv_id == "0":
                while len(new_inv_list) > expected_backpack_size:
                    new_inv_list.pop()
            
            # Fill remaining slots with empty items if we want to preserve size?
            # For main backpack, use expected_backpack_size, otherwise use container's size
            target_size = expected_backpack_size if inv_id == "0" else container.get('Size', len(new_inv_list))
            
            # Fill the rest with empty items
            while len(new_inv_list) < target_size:
                new_inv_list.append({'ItemID': 0, 'Amount': 0, 'State': None})
                    
            container['Inventory'] = new_inv_list
            new_containers[inv_id] = container
            
        player_data['ContainerInventories'] = new_containers

        # Update ListInventories
        # Rebuild each list inventory from items grouped by inv_id where source_type is 'list'
        original_list_inventories = player_data.get('ListInventories', {})
        new_list_inventories = original_list_inventories.copy()

        # Group list items
        list_groups: Dict[str, List[PlayerInventoryItem]] = {}
        for item in save_data.inventory_items:
            if item.source_type == "list":
                inv_id = str(item.inventory_id or '0')
                if inv_id not in list_groups:
                    list_groups[inv_id] = []
                list_groups[inv_id].append(item)

        for inv_id, items in list_groups.items():
            container = new_list_inventories.get(inv_id, {}).copy()
            if not container:
                # Basic structure for new list container
                container = {'ID': int(inv_id) if inv_id.isdigit() else 0, 'Inventory': {}}
            
            # Rebuild the inventory dictionary
            new_inv_dict = {}
            for item in items:
                # Start with original item data if available
                item_data = item.raw_data.copy() if item.raw_data else {}
                item_data['Amount'] = item.amount
                
                if item.marker:
                    item_data['Marker'] = item.marker
                elif 'Marker' not in item_data:
                    item_data['Marker'] = "ItemMarker_None"
                new_inv_dict[str(item.item_id)] = item_data
            
            container['Inventory'] = new_inv_dict
            new_list_inventories[inv_id] = container

        player_data['ListInventories'] = new_list_inventories
        
        # Update game info
        game_info = save_dict.setdefault('GameInfo', {})
        if save_data.game_version:
            game_info['Version'] = save_data.game_version
        
        if save_data.save_version:
            save_dict['Version'] = save_data.save_version
        
        return save_dict
    
    def _create_backup(self, file_path: Path) -> None:
        """Create a backup of the save file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}_backup{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            
            # Clean up old backups
            self._cleanup_old_backups()
            
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backup files to stay within limit"""
        try:
            backup_files = list(self.backup_dir.glob("*_backup.*"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove files beyond the limit
            for old_backup in backup_files[self.max_backups:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")
    
    def get_backup_list(self) -> List[Dict[str, Any]]:
        """Get list of available backups"""
        backups = []
        try:
            for backup_file in self.backup_dir.glob("*_backup.*"):
                stat = backup_file.stat()
                backups.append({
                    'path': backup_file,
                    'name': backup_file.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting backup list: {e}")
        
        return backups
    
    def restore_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Restore a backup file"""
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                return False, "Backup file not found"
            
            if not self.current_save_path:
                return False, "No current save file to restore to"
            
            # Create backup of current file before restoring
            self._create_backup(self.current_save_path)
            
            # Copy backup to current save location
            shutil.copy2(backup_path, self.current_save_path)
            
            # Reload the restored file
            success, message = self.load_save_file(str(self.current_save_path))
            if success:
                return True, "Backup restored successfully"
            else:
                return False, f"Backup copied but failed to load: {message}"
                
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False, f"Error restoring backup: {e}"

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
            
            # Parse JSON
            save_dict = json.loads(json_data)
            
            # Convert to SaveData model
            self.current_save_data = self._parse_save_data(save_dict)
            self.current_save_path = file_path
            
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
        Automatically find the latest save file by timestamp
        Looks in steam/windows folders for profile.json
        """
        try:
            if not base_path:
                # Default DDV save location
                base_path = Path.home() / "AppData" / "LocalLow" / "Gameloft" / "Disney Dreamlight Valley"
            else:
                base_path = Path(base_path)
            
            if not base_path.exists():
                logger.warning(f"DDV save directory not found: {base_path}")
                return None
            
            logger.info(f"Searching for save files in: {base_path}")
            
            # Find all directories that start with 'steam' or 'windows'
            save_candidates = []
            
            for folder in base_path.iterdir():
                if folder.is_dir() and (folder.name.startswith('steam') or folder.name.startswith('windows')):
                    profile_path = folder / "profile.json"
                    if profile_path.exists():
                        stat = profile_path.stat()
                        save_candidates.append({
                            'path': str(profile_path),
                            'folder': folder.name,
                            'modified': stat.st_mtime,
                            'size': stat.st_size
                        })
                        logger.info(f"Found save file: {folder.name}/profile.json (modified: {datetime.fromtimestamp(stat.st_mtime)})")
            
            if not save_candidates:
                logger.warning("No save files found in steam/windows folders")
                return None
            
            # Sort by modification time (newest first)
            save_candidates.sort(key=lambda x: x['modified'], reverse=True)
            latest_save = save_candidates[0]
            
            logger.info(f"Latest save file selected: {latest_save['folder']}/profile.json")
            logger.info(f"Modified: {datetime.fromtimestamp(latest_save['modified'])}")
            logger.info(f"Size: {latest_save['size'] / (1024*1024):.2f} MB")
            
            return latest_save['path']
            
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
            
            # Convert to JSON
            json_data = json.dumps(save_dict, separators=(',', ':'))  # Compact format
            
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
        
        # Parse currencies
        currencies = player_data.get('CurrencyAmounts', {})
        
        # Parse inventory items
        inventory_items = []
        inventories = player_data.get('ListInventories', {})
        for inv_id, inventory in inventories.items():
            inv_data = inventory.get('Inventory', {})
            for item_id_str, item_data in inv_data.items():
                try:
                    item_id = int(item_id_str)
                    amount = item_data.get('Amount', 1)
                    state = item_data.get('State')
                    
                    inventory_items.append(PlayerInventoryItem(
                        item_id=item_id,
                        amount=amount,
                        state=state,
                        inventory_id=str(inv_id)
                    ))
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
                    is_following=pet_data.get('IsFollowing', False)
                ))
        
        return SaveData(
            player_name=player_data.get('Name', 'Unknown'),
            player_level=player_data.get('Level', 1),
            star_coins=int(currencies.get('80000000', 0)),
            dreamlight=int(currencies.get('80300000', 0)),
            daisy_coins=int(currencies.get('80000009', 0)),
            mist=int(currencies.get('80000003', 0)),
            pixel_dust=int(currencies.get('80200002', 0)),
            inventory_items=inventory_items,
            pets=pets,
            game_version=game_info.get('Version', ''),
            save_version=str(save_dict.get('Version', '')),
            custom_data={'original_save': save_dict}  # Keep original for reference
        )
    
    def _save_data_to_dict(self, save_data: SaveData) -> Dict[str, Any]:
        """Convert SaveData back to dictionary format"""
        # Start with original save data if available
        if 'original_save' in save_data.custom_data:
            save_dict = save_data.custom_data['original_save'].copy()
        else:
            save_dict = {}
        
        # Update player data
        player_data = save_dict.setdefault('Player', {})
        player_data['Name'] = save_data.player_name
        player_data['Level'] = save_data.player_level
        
        # Update currencies
        currencies = player_data.setdefault('CurrencyAmounts', {})
        currencies['80000000'] = save_data.star_coins
        currencies['80300000'] = save_data.dreamlight
        currencies['80000009'] = save_data.daisy_coins
        currencies['80000003'] = save_data.mist
        currencies['80200002'] = save_data.pixel_dust
        
        # Update pets
        pets_list = []
        for pet in save_data.pets:
            pet_dict = {'PetItemID': pet.pet_item_id}
            # Preserve legacy Name if present; prefer CustomName when available
            if pet.custom_name:
                pet_dict['CustomName'] = pet.custom_name
            if pet.name:
                pet_dict['Name'] = pet.name
            if pet.friendship_level is not None:
                pet_dict['FriendshipLevel'] = pet.friendship_level
            if pet.xp is not None:
                pet_dict['XP'] = pet.xp
            if pet.is_following:
                pet_dict['IsFollowing'] = pet.is_following
            pets_list.append(pet_dict)

        player_data['Pets'] = pets_list
        
        # Rebuild inventories from scratch to avoid stale entries
        # Preserve any non-Inventory metadata that might exist on each bucket
        original_inventories: Dict[str, Any] = player_data.get('ListInventories', {}) or {}
        player_data['ListInventories'] = {}
        inventories: Dict[str, Any] = player_data['ListInventories']

        # Group inventory items by their original inventory_id when available
        # Fallback to '1' if not specified
        for inv_item in save_data.inventory_items:
            group_id = inv_item.inventory_id or '1'
            inv_bucket = inventories.setdefault(group_id, {})
            # Copy over non-Inventory fields from the original bucket once
            if '__metadata_copied__' not in inv_bucket:
                original_bucket = original_inventories.get(group_id, {}) or {}
                for key, value in original_bucket.items():
                    if key != 'Inventory' and key not in inv_bucket:
                        inv_bucket[key] = value
                # Mark to avoid re-copy attempts
                inv_bucket['__metadata_copied__'] = True

            group = inv_bucket.setdefault('Inventory', {})
            item_dict = {'Amount': inv_item.amount}
            if inv_item.state:
                item_dict['State'] = inv_item.state
            group[str(inv_item.item_id)] = item_dict

        # Clean internal flags
        for bucket in inventories.values():
            if isinstance(bucket, dict) and '__metadata_copied__' in bucket:
                bucket.pop('__metadata_copied__', None)
        
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

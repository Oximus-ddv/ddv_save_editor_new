"""
Dictionary-based data loading service for DDV Save Editor.

Loads item IDs and names from a folder structure like:
Dict/
  furniture/
    furnitures.json
  pets/
    pets.json
  clothes_tops/
    tops.json

Each JSON file is expected to contain a flat mapping of ID->Name, with optional
line or inline comments using // style. Example:
{
  // Crafting Stations
  "40001121": "Wooden Crafting Station",
  "40001155": "Iron Crafting Station"
}
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, List
import logging
import json
import re

from ..models.game_item import GameItem, ItemCategory, GameDatabase


logger = logging.getLogger(__name__)


import zipfile
import io

class DictDataService:
    """Service for loading game data from a Dict folder or Dict.zip of JSON files."""

    def __init__(self, dict_root: str | Path = "Dict") -> None:
        self.dict_root = Path(dict_root)
        self.zip_path = Path("Dict.zip")
        self._cached_database: Optional[GameDatabase] = None
        self._last_snapshot: Optional[str] = None
        self._id_name_cache: Dict[int, str] = {}

    def load_game_database(self, force_reload: bool = False) -> GameDatabase:
        """Load or reload the game database from the Dict folder or Dict.zip."""
        try:
            # Prefer ZIP if it exists
            if self.zip_path.exists():
                return self._load_from_zip(force_reload)
            
            if not self.dict_root.exists():
                logger.error(f"Dict source not found (tried {self.dict_root} and {self.zip_path})")
                return GameDatabase()

            # Snapshot for change detection (folder mtimes + file names)
            snapshot = self._snapshot()
            if not force_reload and self._cached_database and snapshot == self._last_snapshot:
                logger.info("Using cached database (Dict folder unchanged)")
                return self._cached_database

            db = GameDatabase(source_file=str(self.dict_root))
            self._id_name_cache.clear()

            for subdir in sorted(p for p in self.dict_root.iterdir() if p.is_dir()):
                category = self._map_dir_to_category(subdir.name)
                if not category:
                    continue

                for jf in sorted(subdir.glob("*.json")):
                    items = self._read_id_name_map(jf.read_text(encoding="utf-8"))
                    self._add_items_to_db(db, items, category)

            self._cached_database = db
            self._last_snapshot = snapshot
            logger.info(f"Database loaded successfully: {db.get_stats()}")
            return db
        except Exception as e:
            logger.error(f"Error loading Dict data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return GameDatabase()

    def _load_from_zip(self, force_reload: bool = False) -> GameDatabase:
        """Load game database from Dict.zip."""
        try:
            # Simple version/mtime check for zip
            stat = self.zip_path.stat()
            snapshot = f"zip:{int(stat.st_mtime)}:{stat.st_size}"
            
            if not force_reload and self._cached_database and snapshot == self._last_snapshot:
                return self._cached_database

            db = GameDatabase(source_file=str(self.zip_path))
            self._id_name_cache.clear()

            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                # 1. Load categorized folders first
                all_files = sorted(zf.namelist())
                
                # Normalize paths by stripping the leading "Dict/" directory if present
                normalized_files = [f.removeprefix("Dict/") for f in all_files if f.startswith("Dict/")]
                
                # Filter for JSON files
                json_files = [f for f in normalized_files if f.endswith(".json")]
                
                # Prioritize subdirectories over root files
                folder_files = [f for f in json_files if '/' in f]
                root_files = [f for f in json_files if '/' not in f]

                # Process folder files
                for name in folder_files:
                    path_obj = Path(name)
                    dir_name = path_obj.parent.name
                    category = self._map_dir_to_category(dir_name)
                    
                    try:
                        with zf.open(f"Dict/{name}") as f: # Re-add prefix for reading
                            text = f.read().decode('utf-8', errors='ignore')
                            
                            # Handle furniture sub-categories specially
                            is_quest = "furnituresquest.json" in name.lower()
                            items, metadata = self._read_id_name_map_with_metadata(text)
                            self._add_items_to_db(db, items, category, metadata=metadata, is_quest=is_quest)
                    except Exception as e:
                        logger.warning(f"Error reading {name} from zip: {e}")

                # 2. Process root files (like allknowids.json) last as fallback
                for name in root_files:
                    try:
                        with zf.open(f"Dict/{name}") as f: # Re-add prefix for reading
                            text = f.read().decode('utf-8', errors='ignore')
                            items, _ = self._read_id_name_map_with_metadata(text)
                            # Passing None as category triggers prefix-based guessing
                            self._add_items_to_db(db, items, None)
                    except Exception as e:
                        logger.warning(f"Error reading root file {name} from zip: {e}")

            self._cached_database = db
            self._last_snapshot = snapshot
            logger.info(f"Database loaded from ZIP: {db.get_stats()}")
            return db
        except Exception as e:
            logger.error(f"Error loading from ZIP: {e}")
            return GameDatabase()

    def _guess_category_by_id(self, item_id: int) -> Optional[ItemCategory]:
        """Guess item category based on ID prefix patterns."""
        s = str(item_id)
        if s.startswith('10'): return ItemCategory.MOTIFS
        if s.startswith('11'): return ItemCategory.TOOLS
        if s.startswith('12'): return ItemCategory.PETS
        if s.startswith('14'): return ItemCategory.MAKEUP
        if s.startswith('16'): return ItemCategory.TRIMMING
        if s.startswith('17'): return ItemCategory.NPC_SKINS
        if s.startswith('18'): return ItemCategory.SCRAMBLECOIN
        if s.startswith('19'): return ItemCategory.PHOTO_MODE
        if s.startswith('20'): return ItemCategory.HOUSE_SKINS
        if s.startswith('21'): return ItemCategory.TOOLS # Tool skins
        if s.startswith('30'): return ItemCategory.MATERIALS
        if s.startswith('31'): return ItemCategory.ACTIVITY
        if s.startswith('40'): return ItemCategory.FURNITURE
        if s.startswith('5080'): return ItemCategory.GLIDERS
        if s.startswith('50'): return ItemCategory.CLOTHES_OTHER
        if s.startswith('70'): return ItemCategory.GLIDERS
        return None

    def _add_items_to_db(self, db: GameDatabase, items: Dict[str, str], category: Optional[ItemCategory], metadata: Optional[Dict[str, str]] = None, is_quest: bool = False) -> None:
        metadata = metadata or {}
        for id_str, name in items.items():
            try:
                item_id = int(str(id_str).strip())
                # If category is provided, use it. Otherwise guess from ID.
                item_category = category or self._guess_category_by_id(item_id)
                if not item_category:
                    continue
                
                # Filter out debug items
                name_upper = str(name).upper()
                if "DELETE" in name_upper or "UNRELEASED" in name_upper:
                    continue
                
                # Check ALL collections to avoid duplicates across categories
                existing = None
                for cat in ItemCategory:
                    coll = db.get_collection(cat)
                    if item_id in coll.items:
                        existing = coll.items[item_id]
                        break

                if existing:
                    # If same category, maybe update name if new one is better
                    if existing.category == item_category:
                        if not existing.name.startswith("Item ") and len(str(name)) > len(existing.name):
                            existing.name = str(name)
                            self._id_name_cache[item_id] = str(name)
                        # Update metadata even if item exists
                        if item_id_str := str(item_id):
                            if item_id_str in metadata:
                                existing.sub_category = metadata[item_id_str]
                            if is_quest:
                                existing.is_quest = True
                    # Upgrade priority: allow items to move from 'CLOTHES_OTHER' or 'FURNITURE' to a more specific category
                    elif existing.category in [ItemCategory.CLOTHES_OTHER, ItemCategory.FURNITURE] and item_category not in [ItemCategory.CLOTHES_OTHER, ItemCategory.FURNITURE]:
                        # Remove from old collection
                        old_coll = db.get_collection(existing.category)
                        old_coll.items.pop(item_id, None)
                        
                        # Move to new category
                        existing.category = item_category
                        db.add_item(existing)
                        
                        # Update details
                        if not existing.name.startswith("Item ") and len(str(name)) > len(existing.name):
                            existing.name = str(name)
                            self._id_name_cache[item_id] = str(name)
                        if str(item_id) in metadata:
                            existing.sub_category = metadata[str(item_id)]
                        if is_quest:
                            existing.is_quest = True
                        
                        logger.debug(f"Upgraded item {item_id} from {existing.category} to {item_category}")
                    continue

                item = GameItem(id=item_id, name=str(name), category=item_category)
                if str(item_id) in metadata:
                    item.sub_category = metadata[str(item_id)]
                if is_quest:
                    item.is_quest = True
                
                db.add_item(item)
                self._id_name_cache[item_id] = str(name)
            except Exception:
                continue

    def get_item_name(self, item_id: int) -> str:
        """Fast lookup for item name."""
        if not self._cached_database:
            self.load_game_database()
        return self._id_name_cache.get(item_id, f"Item {item_id}")

    def _snapshot(self) -> str:
        parts: List[str] = []
        try:
            for p in sorted(self.dict_root.rglob("*.json")):
                try:
                    stat = p.stat()
                    parts.append(f"{p.relative_to(self.dict_root)}:{int(stat.st_mtime)}:{stat.st_size}")
                except Exception:
                    continue
        except Exception:
            pass
        return "|".join(parts)

    def _map_dir_to_category(self, dirname: str) -> Optional[ItemCategory]:
        name = dirname.lower().replace(" ", "_").replace("+", "")
        # Direct value match
        for cat in ItemCategory:
            if name == cat.value:
                return cat
        # Partial/heuristic matches
        hints: Dict[ItemCategory, List[str]] = {
            ItemCategory.FURNITURE: ["furniture", "furnitures", "decor", "decoration"],
            ItemCategory.PETS: ["pets", "pet", "companions", "critter", "critters"],
            ItemCategory.CLOTHES_OUTFITS: ["clothes_outfits", "outfits"],
            ItemCategory.CLOTHES_TOPS: ["clothes_tops", "tops", "jackets", "shirts"],
            ItemCategory.CLOTHES_BOTTOMS: ["clothes_bottoms", "bottoms", "skirts", "pants"],
            ItemCategory.CLOTHES_HELMETS: ["clothes_helmets", "helmets", "hair", "hats"],
            ItemCategory.CLOTHES_SHOES: ["clothes_shoes", "shoes", "socks"],
            ItemCategory.CLOTHES_ACCESSORIES: ["clothes_accessories", "accessories", "gloves", "glasses", "bracelets", "earrings", "neckwear"],
            ItemCategory.CLOTHES_OTHER: ["clothes_other", "clothes", "clothing", "fashion"],
            ItemCategory.HOUSE_SKINS: ["house_skins", "houses", "house", "buildings"],
            ItemCategory.HOUSE_WALLPAPER: ["house_wallpaper", "wallpaper"],
            ItemCategory.HOUSE_FLOORS: ["house_floors", "floors"],
            ItemCategory.NPC_HOUSES: ["npc_houses", "npc_house"],
            ItemCategory.NPC_SKINS: ["npc_skins", "skins", "characters"],
            ItemCategory.TOOLS: ["tools", "tool", "equipment"],
            ItemCategory.FOOD: ["food", "meals", "recipes", "ingredients"],
            ItemCategory.MATERIALS: ["materials", "material", "resources", "gems", "ore", "wood", "flowers"],
            ItemCategory.GLIDERS: ["gliders", "glider", "movement"],
            ItemCategory.MOTIFS: ["motifs", "motif", "touch_of_magic", "tom"],
            ItemCategory.MAKEUP: ["makeup", "makeups", "face", "cosmetic"],
            ItemCategory.TRIMMING: ["trimming", "wallpapersfloors", "trim"],
            ItemCategory.ACTIVITY: ["activity", "activities", "containeritems"],
            ItemCategory.SCRAMBLECOIN: ["scramblecoin", "board_games", "game"],
            ItemCategory.AVATAR_FEATURES: ["avatar_features", "avatar"],
            ItemCategory.PHOTO_MODE: ["photo_mode", "photo"],
        }
        for cat, keys in hints.items():
            if any(k in name for k in keys):
                return cat
        return None

    def _read_id_name_map(self, text: str) -> Dict[str, str]:
        """Read a JSON mapping, tolerating // comments and trailing commas."""
        items, _ = self._read_id_name_map_with_metadata(text)
        return items

    def _read_id_name_map_with_metadata(self, text: str) -> tuple[Dict[str, str], Dict[str, str]]:
        """Read a JSON mapping, extracting comments as metadata (sub-categories)."""
        items: Dict[str, str] = {}
        metadata: Dict[str, str] = {}
        
        current_sub_category: Optional[str] = None
        
        # Line-by-line parsing to extract comments and associate them with subsequent items
        # This is more robust for our specialized furniture files
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Check for comment
            if line.startswith('//'):
                cat_name = line[2:].strip()
                if cat_name and not cat_name.startswith('Quest Furniture') and not cat_name.startswith('Quest Companion'):
                    current_sub_category = cat_name
                continue
            
            # Use regex to find "key": "value" pattern (even with inline comments or trailing commas)
            match = re.search(r'"(\d+)":\s*"([^"]+)"', line)
            if match:
                item_id = match.group(1)
                item_name = match.group(2)
                items[item_id] = item_name
                if current_sub_category:
                    metadata[item_id] = current_sub_category
        
        # If the manual parsing failed or found nothing, try standard json load as fallback
        if not items:
            try:
                # Remove comments (line and inline)
                content = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                # Remove trailing commas
                content = re.sub(r', \s*([}\]])', r'\1', content)
                content = re.sub(r',\s*([}\]])', r'\1', content)
                
                data = json.loads(content)
                if isinstance(data, dict):
                    items = {str(k): (v if isinstance(v, str) else str(v)) for k, v in data.items() if k is not None}
            except Exception:
                pass
                
        return items, metadata



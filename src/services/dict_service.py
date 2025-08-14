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


class DictDataService:
    """Service for loading game data from a Dict folder of JSON files."""

    def __init__(self, dict_root: str | Path = "Dict") -> None:
        self.dict_root = Path(dict_root)
        self._cached_database: Optional[GameDatabase] = None
        self._last_snapshot: Optional[str] = None

    def load_game_database(self, force_reload: bool = False) -> GameDatabase:
        """Load or reload the game database from the Dict folder."""
        try:
            if not self.dict_root.exists():
                logger.error(f"Dict folder not found: {self.dict_root}")
                return GameDatabase()

            # Snapshot for change detection (folder mtimes + file names)
            snapshot = self._snapshot()
            if not force_reload and self._cached_database and snapshot == self._last_snapshot:
                logger.info("Using cached database (Dict folder unchanged)")
                return self._cached_database

            db = GameDatabase(source_file=str(self.dict_root))
            load_count: Dict[ItemCategory, int] = {cat: 0 for cat in ItemCategory}

            for subdir in sorted(p for p in self.dict_root.iterdir() if p.is_dir()):
                category = self._map_dir_to_category(subdir.name)
                if not category:
                    logger.warning(f"Unknown category folder: {subdir.name}")
                    continue

                json_files = sorted(subdir.glob("*.json"))
                if not json_files:
                    continue

                for jf in json_files:
                    items = self._read_id_name_map(jf)
                    if not items:
                        continue
                    for id_str, name in items.items():
                        try:
                            item_id = int(str(id_str).strip())
                            item = GameItem(id=item_id, name=str(name), category=category)
                            db.add_item(item)
                            load_count[category] += 1
                        except Exception as e:
                            logger.debug(f"Skip entry {id_str} in {jf}: {e}")

                logger.info(f"Loaded {load_count[category]} items from '{subdir.name}'")

            self._cached_database = db
            self._last_snapshot = snapshot
            logger.info(f"Database loaded successfully: {db.get_stats()}")
            return db
        except Exception as e:
            logger.error(f"Error loading Dict data: {e}")
            return GameDatabase()

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
        name = dirname.lower().replace(" ", "_")
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
            ItemCategory.CLOTHES_OTHER: ["clothes_other", "clothes", "clothing", "fashion", "motif", "motifs"],
            ItemCategory.HOUSE_SKINS: ["house_skins", "houses", "house", "buildings"],
            ItemCategory.HOUSE_WALLPAPER: ["house_wallpaper", "wallpaper"],
            ItemCategory.HOUSE_FLOORS: ["house_floors", "floors"],
            ItemCategory.NPC_HOUSES: ["npc_houses", "npc_house"],
            ItemCategory.NPC_SKINS: ["npc_skins", "skins", "characters"],
            ItemCategory.TOOLS: ["tools", "tool", "equipment"],
            ItemCategory.FOOD: ["food", "meals", "recipes", "ingredients"],
            ItemCategory.MATERIALS: ["materials", "material", "resources", "gems", "ore", "wood", "flowers"],
        }
        for cat, keys in hints.items():
            if any(k in name for k in keys):
                return cat
        return None

    def _read_id_name_map(self, file_path: Path) -> Dict[str, str]:
        """Read a JSON mapping, tolerating // comments and trailing commas."""
        try:
            text = file_path.read_text(encoding="utf-8")
            # Remove // comments (line and inline) and trailing commas
            lines: List[str] = []
            for raw in text.splitlines():
                line = raw
                if '//' in line:
                    line = line.split('//', 1)[0]
                lines.append(line)
            cleaned = "\n".join(lines)
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return {str(k): (v if isinstance(v, str) else str(v)) for k, v in data.items() if k is not None}
            logger.warning(f"File does not contain a JSON object: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {}



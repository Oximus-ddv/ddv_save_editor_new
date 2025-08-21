"""
Augmentation helpers to safely add items to a DDV save dict without overwriting unrelated data.
"""
from __future__ import annotations

import json
import re
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple, Optional
from enum import Enum


# Configure logging to output to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('augmentation.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)


class InventoryType(Enum):
    """Inventory types and their corresponding IDs in the save file"""
    FURNITURE = "0"  # Furniture items
    CLOTHES = "1"    # Clothing items
    ACTIVITY = "2"   # Activity items
    MAKEUP = "3"     # Makeup items
    TRIMMING = "4"   # Trimming/Wallpapers/Floors
    HOUSES = "5"     # Houses
    TOUCHOFMAGIC = "6"  # Touch of Magic decorations
    NPCSKINS = "7"   # NPC skins
    BOARDGAME = "8"  # Board game items
    AVATARFEATURE = "9"  # Avatar features
    PHOTOMODE = "10"  # Photo mode items

    @staticmethod
    def get_inventory_for_id(item_id: int) -> Optional[str]:
        """Determine which inventory an item belongs to based on its ID pattern"""
        id_str = str(item_id)
        logger.info(f"Determining inventory for item ID: {id_str}")
        
        # Special case: Tools (110XXXXXX) should be added to Player.Tools array, not inventory
        if id_str.startswith("110"):
            logger.info(f"[TOOL] Item {id_str} is a tool and should be added to Player.Tools array")
            return None
        
        # Map ID patterns to inventory types
        patterns = {
            # Furniture items (inventory 0)
            "40": "0",   # Furniture
            "20": "0",   # More furniture items
            
            # Clothes (inventory 1)
            "50": "1",   # Clothes
            
            # Activity items (inventory 2)
            # "110": "2",  # Activity items - REMOVED: Tools should go to Player.Tools
            
            # Makeup (inventory 3)
            "140": "3",  # Makeup items
            
            # Trimming/Wallpapers/Floors (inventory 4)
            "16": "4",   # Wallpapers and Floors
            
            # Houses (inventory 5)
            "20": "5",   # Houses
            
            # Touch of Magic (inventory 6)
            "100": "6",  # Touch of Magic decorations
            
            # NPC Skins (inventory 7)
            "170": "7",  # NPC skins
            
            # Board games (inventory 8)
            "180": "8",  # Board game items
            
            # Avatar features (inventory 9)
            "190": "9",  # Avatar features
            
            # Photo mode (inventory 10)
            "200": "10", # Photo mode items
        }
        
        # Try to match the ID pattern
        for pattern, inv_id in patterns.items():
            if id_str.startswith(pattern):
                logger.info(f"[OK] Item {id_str} matches pattern {pattern}, assigned to inventory {inv_id}")
                return inv_id
                
        logger.warning(f"[ERROR] Could not determine inventory for item ID: {id_str}")
        return None


RE_CS_INT_ENTRY = re.compile(r"\{\s*(\d{5,9})\s*,\s*\".*?\"\s*\}")


def parse_ids_from_csharp_dict(cs_path: Path) -> Set[int]:
    logger.info(f"Parsing dictionary file: {cs_path}")
    text = cs_path.read_text(encoding="utf-8", errors="ignore")
    ids: Set[int] = set()
    for m in RE_CS_INT_ENTRY.finditer(text):
        try:
            item_id = int(m.group(1))
            ids.add(item_id)
        except ValueError as e:
            logger.warning(f"Failed to parse item ID from match: {m.group(0)}, error: {e}")
            continue
    logger.info(f"Found {len(ids)} valid item IDs in {cs_path}")
    return ids


def _get_inventory_dict(root: Dict[str, Any], inventory_id: str) -> Dict[str, Any]:
    logger.info(f"Getting inventory dictionary for ID: {inventory_id}")
    player = root.setdefault("Player", {})
    list_inventories = player.setdefault("ListInventories", {})
    inv = list_inventories.setdefault(inventory_id, {})
    inventory = inv.setdefault("Inventory", {})
    return inventory


def add_items_to_inventory(
    inventory: Dict[str, Any],
    item_ids: Iterable[int],
    amount: int,
    mode: str,
) -> Tuple[int, int, int]:
    added = 0
    replaced = 0
    skipped = 0
    
    logger.info(f"Adding items to inventory. Mode: {mode}, Amount: {amount}")
    for item_id in item_ids:
        key = str(item_id)
        if key in inventory:
            if mode == "overwrite":
                old = inventory.get(key)
                new_val = {"Amount": amount}
                if old != new_val:
                    logger.info(f"[REPLACE] Item {key}: {old} -> {new_val}")
                    replaced += 1
                else:
                    logger.info(f"[SKIP] Unchanged item {key}")
                    skipped += 1
                inventory[key] = new_val
            else:
                logger.info(f"[SKIP] Existing item {key} (mode: {mode})")
                skipped += 1
        else:
            logger.info(f"[ADD] New item {key} with amount {amount}")
            inventory[key] = {"Amount": amount}
            added += 1
            
    logger.info(f"Operation complete. Added: {added}, Replaced: {replaced}, Skipped: {skipped}")
    return added, replaced, skipped


def add_specific_tool(save_dict: Dict[str, Any], tool_id: int, current_of_type: bool = False) -> bool:
    """Add a specific tool to the player's inventory"""
    # Get or create Tools list in Player
    player_data = save_dict.setdefault('Player', {})
    tools_list = player_data.setdefault('Tools', [])
    
    # Check if tool already exists
    if not any(tool.get('ToolItemID') == tool_id for tool in tools_list):
        logger.info(f"[TOOL] Adding new tool {tool_id} to Player.Tools array")
        tools_list.append({
            'ToolItemID': tool_id,
            'CurrentOfType': current_of_type
        })
        return True
    logger.info(f"[TOOL] Tool {tool_id} already exists in Player.Tools array")
    return False


def add_basic_tools(save_dict: Dict[str, Any], amount: int = 1) -> Dict[str, Any]:
    """Add a basic set of tools to the player's inventory"""
    # Basic tool IDs
    basic_tools = {
        110000002: "Nefarious Shovel",
        110100002: "Nefarious Fishing Rod",
        110400001: "Nefarious Pickaxe",
        110400004: "Monster Pickaxe",
        110500001: "Nefarious Watering Can",
        110600001: "Nefarious Phone",
        110700007: "Nefarious Hourglass"
    }
    
    # Get or create Tools list in Player
    player_data = save_dict.setdefault('Player', {})
    tools_list = player_data.setdefault('Tools', [])
    
    # Add each tool if not already present
    added_tools = []
    for tool_id, tool_name in basic_tools.items():
        # Check if tool already exists
        if not any(tool.get('ToolItemID') == tool_id for tool in tools_list):
            logger.info(f"[TOOL] Adding new tool {tool_id} ({tool_name}) to Player.Tools array")
            tools_list.append({
                'ToolItemID': tool_id,
                'CurrentOfType': False
            })
            added_tools.append(tool_name)
        else:
            logger.info(f"[TOOL] Tool {tool_id} ({tool_name}) already exists in Player.Tools array")
    
    return {
        'tools_added': len(added_tools),
        'added_tools': added_tools
    }


def augment_save_dict(
    save_dict: Dict[str, Any],
    *,
    items_to_add: Dict[str, bool] = None,  # Dict of item type to bool indicating if it should be added
    inventory_overrides: Dict[str, str] = None,  # Optional inventory ID overrides
    amount: int = 1,
    mode: str = "missing-only",
    dict_paths: Dict[str, Optional[Path]] = None,  # Dict of item type to path of dictionary file
) -> Dict[str, int]:
    """
    Augment a save dict in-place; returns counters per category and total.
    
    Args:
        save_dict: The save dictionary to modify
        items_to_add: Dictionary mapping item types to booleans indicating if they should be added
        inventory_overrides: Optional dictionary to override default inventory IDs
        amount: Amount of each item to add
        mode: Either "missing-only" or "overwrite"
        dict_paths: Dictionary mapping item types to paths of their dictionary files
    """
    if items_to_add is None:
        items_to_add = {}
    if inventory_overrides is None:
        inventory_overrides = {}
    if dict_paths is None:
        dict_paths = {}

    logger.info("[START] Starting save dict augmentation")
    logger.info(f"Items to add: {items_to_add}")
    logger.info(f"Inventory overrides: {inventory_overrides}")
    logger.info(f"Dictionary paths: {dict_paths}")

    summary = {}
    
    # Process each item type
    for inv_type in InventoryType:
        type_name = inv_type.name.lower()
        
        # Skip if not requested
        if not items_to_add.get(type_name, False):
            logger.info(f"[SKIP] {type_name} (not requested)")
            continue
            
        # Get the dictionary path
        dict_path = dict_paths.get(type_name)
        if not dict_path or not dict_path.exists():
            logger.warning(f"[ERROR] Dictionary path for {type_name} not found or invalid: {dict_path}")
            continue
            
        # Get inventory ID (use override if provided)
        inventory_id = inventory_overrides.get(type_name, inv_type.value)
        logger.info(f"[PROCESS] {type_name} items using inventory {inventory_id}")
        
        # Add items
        ids = parse_ids_from_csharp_dict(dict_path)
        inv = _get_inventory_dict(save_dict, inventory_id)
        added, replaced, skipped = add_items_to_inventory(inv, ids, amount, mode)
        
        # Update summary
        summary[f"{type_name}_added"] = added
        summary[f"{type_name}_replaced"] = replaced
        summary[f"{type_name}_skipped"] = skipped
        
        logger.info(f"[COMPLETE] {type_name}: Added {added}, Replaced {replaced}, Skipped {skipped}")

    logger.info("[DONE] Save dict augmentation complete")
    logger.info(f"[SUMMARY] {summary}")
    return summary


def add_item_to_save(
    save_dict: Dict[str, Any],
    item_id: int,
    amount: int = 1,
    inventory_id: Optional[str] = None,
) -> bool:
    """
    Add a single item to the save dict, automatically determining the correct inventory.
    
    Args:
        save_dict: The save dictionary to modify
        item_id: The ID of the item to add
        amount: Amount of the item to add
        inventory_id: Optional override for the inventory ID
    
    Returns:
        bool: True if item was added successfully, False otherwise
    """
    logger.info(f"[START] Adding single item. ID: {item_id}, Amount: {amount}, Override inventory: {inventory_id}")
    
    # Special case: Tools (110XXXXXX) should be added to Player.Tools array
    if str(item_id).startswith("110"):
        logger.info(f"[TOOL] Item {item_id} is a tool, adding to Player.Tools array")
        return add_specific_tool(save_dict, item_id, False)
    
    if inventory_id is None:
        inventory_id = InventoryType.get_inventory_for_id(item_id)
        if inventory_id is None:
            logger.error(f"[ERROR] Could not determine inventory for item {item_id}")
            return False
    
    logger.info(f"[PROCESS] Using inventory {inventory_id} for item {item_id}")
    inv = _get_inventory_dict(save_dict, inventory_id)
    inv[str(item_id)] = {"Amount": amount}
    logger.info(f"[OK] Successfully added item {item_id} to inventory {inventory_id}")
    return True
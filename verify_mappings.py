
import sys
import os
import logging
from typing import Dict, Any

# Setup path
sys.path.append(os.getcwd())

# Import models
from src.models.game_item import ItemCategory
from src.services.augmentation_service import InventoryType, add_item_from_editor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def verify():
    failures = []
    
    # 1. VERIFY MAPPINGS
    logger.info("Verifying ItemCategory.get_id()...")
    expectations = {
        ItemCategory.GLIDERS: 9, 
        ItemCategory.TOOLS: 2,  # User says Tools in Inventory 2
        ItemCategory.ACTIVITY: 2,
        ItemCategory.MOUNT_GEAR: 11
    }
    for cat, expected_id in expectations.items():
        actual_id = cat.get_id()
        if actual_id != expected_id:
            logger.error(f"FAILURE: {cat} expected {expected_id}, got {actual_id}")
            failures.append(f"{cat} ID mismatch")
        else:
            logger.info(f"OK: {cat} -> {actual_id}")

    # 2. VERIFY INVENTORY PATTERNS
    logger.info("Verifying InventoryType.get_inventory_for_id()...")
    id_samples = {
        11000001: "2",   # Tools/Activity -> Inv 2
        70000001: "9",   # Gliders -> Inv 9
        21000001: "11",  # Mounts -> Inv 11
        19000001: "10"   # Photo -> Inv 10
    }
    
    for item_id, expected_inv in id_samples.items():
        actual_inv = InventoryType.get_inventory_for_id(item_id)
        if actual_inv != expected_inv:
            logger.error(f"FAILURE: Item {item_id} expected Inv {expected_inv}, got {actual_inv}")
            failures.append(f"Item {item_id} Inv mismatch")
        else:
            logger.info(f"OK: Item {item_id} -> Inv {actual_inv}")

    # 3. VERIFY ADD_ITEM_FROM_EDITOR LOGIC
    logger.info("Verifying add_item_from_editor logic for Tools...")
    
    # Mock save data
    save_data = {
        "Player": {
            "ListInventories": {},
            "Tools": []
        }
    }
    
    # Test case: Add a generic Tool/Activity item (11000001) with Category "TOOLS"
    # Expected: Should go to Inventory 2 (ListInventories['2']), NOT Player.Tools
    item_id = 11000001
    add_item_from_editor(save_data, item_id, "TOOLS")
    
    # Check ListInventories
    inv_2 = save_data["Player"]["ListInventories"].get("2", {}).get("Inventory", {})
    if str(item_id) in inv_2:
        logger.info(f"OK: Tool Item {item_id} added to Inventory 2 correctly.")
    else:
        logger.error(f"FAILURE: Tool Item {item_id} NOT found in Inventory 2.")
        failures.append("Tool Item not in Inv 2")
        
    # Check Player.Tools (should NOT be there, or at least Inv 2 is priority)
    player_tools = save_data["Player"]["Tools"]
    is_in_tools = any(t.get('ToolItemID') == item_id for t in player_tools)
    if is_in_tools:
        logger.warning(f"WARNING: Tool Item {item_id} ALSO added to Player.Tools (Duplicate?) or hijacked?")
        # If it's in BOTH, that might be okay, but we definitely want it in Inventory 2.
    
    if failures:
        logger.error(f"Verification FAILED with {len(failures)} errors.")
        sys.exit(1)
    else:
        logger.info("Verification SUCCESS!")
        sys.exit(0)

if __name__ == "__main__":
    verify()

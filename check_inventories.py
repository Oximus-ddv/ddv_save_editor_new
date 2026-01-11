import json
import os
import sys

# Define category mapping manually to ensure standalone execution
CATEGORY_IDS = {
    0: "FURNITURE",
    1: "PETS",
    2: "ACTIVITY",
    3: "MAKEUP",
    4: "TRIMMING",
    5: "BUILDING",
    6: "MOTIFS",
    7: "SKIN",
    8: "SCRAMBLECOIN",
    9: "AVATAR_FEATURES",
    10: "PHOTO_MODE",
    11: "MOUNT_GEAR"
}

def check_profile_inventories(file_path):
    print(f"Checking profile: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    player = data.get('Player', {})
    if not player:
        print("Error: 'Player' section not found in JSON.")
        return

    list_inventories = player.get('ListInventories', {})
    if not list_inventories:
        print("Warning: 'ListInventories' is empty or missing.")
        return

    print(f"\nFound {len(list_inventories)} inventories in ListInventories.\n")
    print("-" * 80)
    print(f"{'ID':<5} | {'Category Name':<25} | {'Item Count':<10} | {'Sample Item IDs'}")
    print("-" * 80)

    # Sort by ID for cleaner output
    sorted_ids = sorted(list_inventories.keys(), key=lambda x: int(x) if x.isdigit() else 999999)

    for inv_id_str in sorted_ids:
        try:
            inv_id = int(inv_id_str)
        except ValueError:
            inv_id = -1
            
        category_name = CATEGORY_IDS.get(inv_id, f"UNKNOWN ({inv_id})")
        
        container = list_inventories[inv_id_str]
        inventory = container.get('Inventory', {})
        
        item_count = len(inventory)
        
        # Get up to 5 sample IDs
        sample_ids = list(inventory.keys())[:5]
        samples_str = ", ".join(sample_ids)
        if len(inventory) > 5:
            samples_str += ", ..."
            
        print(f"{inv_id_str:<5} | {category_name:<25} | {item_count:<10} | {samples_str}")

        # specific checks can be added here
        # For example, checking if furniture items (ID 31) look like furniture IDs
        
    print("-" * 80)
    print("\nDetailed Inventory contents have been checked.")

if __name__ == "__main__":
    profile_path = os.path.join("Profiles", "profile.json")
    # Allow command line argument to override
    if len(sys.argv) > 1:
        profile_path = sys.argv[1]
        
    check_profile_inventories(profile_path)

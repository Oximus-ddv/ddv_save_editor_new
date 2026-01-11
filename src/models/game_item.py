"""
Game item data models for DDV Save Editor
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ItemCategory(str, Enum):
    """Available item categories with their numeric IDs"""
    PETS = "pets"  # ID: 1 (or 12 for actual pets?)
    
    # Clothing subcategories (Inventory 1)
    CLOTHES_OUTFITS = "clothes_outfits"
    CLOTHES_TOPS = "clothes_tops"
    CLOTHES_BOTTOMS = "clothes_bottoms"
    CLOTHES_HELMETS = "clothes_helmets"
    CLOTHES_SHOES = "clothes_shoes"
    CLOTHES_ACCESSORIES = "clothes_accessories"
    CLOTHES_OTHER = "clothes_other"
    
    # House subcategories (Inventory 5)
    HOUSE_SKINS = "house_skins"
    HOUSE_WALLPAPER = "house_wallpaper"
    HOUSE_FLOORS = "house_floors"
    NPC_HOUSES = "npc_houses"
    
    # Other categories
    NPC_SKINS = "npc_skins"  # Inventory 7
    FURNITURE = "furniture"  # Inventory 0
    TOOLS = "tools"
    FOOD = "food"
    MATERIALS = "materials"
    
    # New categories
    MOTIFS = "motifs"  # Inventory 6
    GLIDERS = "gliders"  # Inventory 9 (Avatar Features) or 11 (Mount Gear)?
    MAKEUP = "makeup"  # Inventory 3
    TRIMMING = "trimming"  # Inventory 4
    ACTIVITY = "activity"  # Inventory 2
    SCRAMBLECOIN = "scramblecoin"  # Inventory 8
    AVATAR_FEATURES = "avatar_features"  # Inventory 9
    PHOTO_MODE = "photo_mode"  # Inventory 10
    MOUNT_GEAR = "mount_gear" # Inventory 11
    
    def get_id(self) -> int:
        """Get the numeric ID for this category (Inventory ID)"""
        category_ids = {
            "furniture": 0,
            
            # Clothes / Pets (1)
            "pets": 1,
            "clothes_outfits": 1,
            "clothes_tops": 1,
            "clothes_bottoms": 1,
            "clothes_helmets": 1,
            "clothes_shoes": 1,
            "clothes_accessories": 1,
            "clothes_other": 1,
            
            "activity": 2,
            "makeup": 3,
            "trimming": 4,
            
            # Buildings (5)
            "house_skins": 5,
            "npc_houses": 5,
            "house_wallpaper": 5,
            "house_floors": 5,
            
            "motifs": 6,
            "npc_skins": 7,
            "scramblecoin": 8,
            
            # Avatar features (9) matches 70xxxx IDs
            "avatar_features": 9,
            "gliders": 9, # Assuming Gliders (70xxxx) go here. Or do they go to 11?
                         # Analysis showed 11 is 210xxxx. 9 is 70xxxx.
                         # If items are 70xxxx, they MUST return 9.
            
            "photo_mode": 10,
            
            # Mount Gear (11) matches 210xxxx IDs
            "mount_gear": 11,
            
            # Others (Tools/Food/Materials usually NOT in ListInventories)
            # But if forced:
            "tools": 2, # Often with Activity?
            
            # Legacy/Unsure
            "materials": 0, 
            "food": 0
        }
        return category_ids.get(self.value, 0)
    
    @classmethod
    def from_id(cls, id: int) -> Optional["ItemCategory"]:
        """Get a representative category from its numeric Inventory ID"""
        id_to_category = {
            0: cls.FURNITURE,
            1: cls.CLOTHES_TOPS, # Representative for Clothes
            2: cls.ACTIVITY,
            3: cls.MAKEUP,
            4: cls.TRIMMING,
            5: cls.HOUSE_SKINS, # Representative for Buildings
            6: cls.MOTIFS,
            7: cls.NPC_SKINS,
            8: cls.SCRAMBLECOIN,
            9: cls.AVATAR_FEATURES,
            10: cls.PHOTO_MODE,
            11: cls.MOUNT_GEAR,
        }
        return id_to_category.get(id)


class GameItem(BaseModel):
    """Represents a single game item"""
    id: int = Field(..., description="Unique item ID")
    name: str = Field(..., description="Display name of the item")
    category: ItemCategory = Field(..., description="Item category")
    sub_category: Optional[str] = Field(None, description="Item sub-category (e.g. from Dict comments)")
    is_quest: bool = Field(False, description="Whether this is a quest item")
    description: Optional[str] = Field(None, description="Item description")
    image_path: Optional[str] = Field(None, description="Path to item image")
    rarity: Optional[str] = Field(None, description="Item rarity")
    cost: Optional[int] = Field(None, description="Item cost")
    unlocked: Optional[bool] = Field(True, description="Whether item is unlocked")
    max_quantity: Optional[int] = Field(None, description="Maximum recommended quantity (1 for yellow items)")
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Additional custom data")

    @validator('id')
    def validate_id(cls, v):
        if v <= 0:
            raise ValueError('Item ID must be positive')
        return v

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Item name cannot be empty')
        return v.strip()

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.id})"

    def __repr__(self) -> str:
        return f"GameItem(id={self.id}, name='{self.name}', category='{self.category}')"


class PlayerInventoryItem(BaseModel):
    """Represents an item in player's inventory"""
    item_id: int = Field(..., description="Reference to GameItem.id")
    amount: int = Field(1, description="Quantity of the item")
    state: Optional[Any] = Field(None, description="Item state (for some special items)")
    inventory_id: Optional[str] = Field(None, description="Original inventory/group identifier where this item belongs")
    marker: Optional[str] = Field(None, description="Marker for items in ListInventories (e.g. ItemMarker_None)")
    source_type: str = Field("container", description="Source type: 'container' or 'list'")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Original raw data to preserve unmodeled fields")

    @validator('amount')
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v


class PetData(BaseModel):
    """Specific data for pet items"""
    pet_item_id: int = Field(..., description="Pet item ID")
    name: Optional[str] = Field(None, description="Deprecated: Original Name field, kept for backward compatibility")
    custom_name: Optional[str] = Field(None, description="Custom pet name")
    friendship_level: Optional[int] = Field(None, description="Friendship level")
    xp: Optional[int] = Field(None, description="Friendship XP")
    is_following: bool = Field(False, description="Is pet currently following player")
    last_selfie_date: Optional[str] = Field(None, description="Last selfie date")
    last_petted_date: Optional[str] = Field(None, description="Last petted date")
    granted_inventory_slots: int = Field(0, description="Number of inventory slots granted by this pet")
    pending_hangout_rewards: List[Any] = Field(default_factory=list, description="Pending hangout rewards")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Original raw data to preserve unmodeled fields")


class SaveData(BaseModel):
    """Complete save file data structure"""
    player_name: str = Field(..., description="Player character name")
    player_level: int = Field(1, description="Player level")
    
    # Currencies
    star_coins: int = Field(0, description="Star Coins currency")
    dreamlight: int = Field(0, description="Dreamlight currency")
    daisy_coins: int = Field(0, description="Daisy Coins currency")
    mist: int = Field(0, description="Mist currency")
    pixel_dust: int = Field(0, description="Pixel Dust currency")
    story_book_magic: int = Field(0, description="StoryBook Magic currency")
    moonstones: int = Field(0, description="Moonstones currency")
    
    # Inventories
    inventory_items: List[PlayerInventoryItem] = Field(default_factory=list)
    pets: List[PetData] = Field(default_factory=list)
    collection_sets: List[Dict[str, Any]] = Field(default_factory=list, description="Collection sets data")
    
    # Game info
    game_version: Optional[str] = Field(None, description="Game version")
    save_version: Optional[str] = Field(None, description="Save file version")
    
    @validator('game_version', pre=True)
    def convert_game_version(cls, v):
        """Convert game_version to string if it's a number"""
        if v is not None:
            return str(v)
        return v
    
    @validator('save_version', pre=True)
    def convert_save_version(cls, v):
        """Convert save_version to string if it's a number"""
        if v is not None:
            return str(v)
        return v
    
    # Additional data
    custom_data: Dict[str, Any] = Field(default_factory=dict)

    @validator('player_level')
    def validate_level(cls, v):
        if v < 1:
            raise ValueError('Player level must be at least 1')
        return v


class ItemCollection(BaseModel):
    """Collection of items by category"""
    category: ItemCategory
    items: Dict[int, GameItem] = Field(default_factory=dict)
    
    def add_item(self, item: GameItem) -> None:
        """Add an item to the collection"""
        if item.category != self.category:
            raise ValueError(f"Item category {item.category} doesn't match collection category {self.category}")
        self.items[item.id] = item
    
    def get_item(self, item_id: int) -> Optional[GameItem]:
        """Get an item by ID"""
        return self.items.get(item_id)
    
    def remove_item(self, item_id: int) -> bool:
        """Remove an item by ID, returns True if removed"""
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False
    
    def search_items(self, query: str) -> List[GameItem]:
        """Search items by name or description"""
        query_lower = query.lower()
        results = []
        for item in self.items.values():
            if (query_lower in item.name.lower() or 
                (item.description and query_lower in item.description.lower()) or
                str(item.id) == query):
                results.append(item)
        return sorted(results, key=lambda x: x.name)
    
    def get_items_by_rarity(self, rarity: str) -> List[GameItem]:
        """Get all items of a specific rarity"""
        return [item for item in self.items.values() if item.rarity == rarity]
    
    def __len__(self) -> int:
        return len(self.items)
    
    def __iter__(self):
        return iter(self.items.values())


class GameDatabase(BaseModel):
    """Complete game item database"""
    collections: Dict[ItemCategory, ItemCollection] = Field(default_factory=dict)
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    source_file: Optional[str] = Field(None, description="Source Excel file path")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize collections for all categories
        for category in ItemCategory:
            if category not in self.collections:
                self.collections[category] = ItemCollection(category=category)
    
    def get_collection(self, category: ItemCategory) -> ItemCollection:
        """Get items collection for a category"""
        return self.collections[category]
    
    def add_item(self, item: GameItem) -> None:
        """Add an item to the appropriate collection"""
        self.collections[item.category].add_item(item)
    
    def get_item(self, category: ItemCategory, item_id: int) -> Optional[GameItem]:
        """Get a specific item by category and ID"""
        return self.collections[category].get_item(item_id)
    
    def get_item_by_id(self, item_id: int) -> Optional[GameItem]:
        """Get a specific item by ID, searching across all categories."""
        for collection in self.collections.values():
            item = collection.get_item(item_id)
            if item:
                return item
        return None
    
    def search_all_items(self, query: str) -> Dict[ItemCategory, List[GameItem]]:
        """Search across all categories"""
        results = {}
        for category, collection in self.collections.items():
            items = collection.search_items(query)
            if items:
                results[category] = items
        return results
    
    def get_all_categories(self) -> List[ItemCategory]:
        """Get all available categories with items"""
        return [cat for cat, collection in self.collections.items() if len(collection) > 0]
    
    def get_total_items(self) -> int:
        """Get total number of items across all categories"""
        return sum(len(collection) for collection in self.collections.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "total_items": self.get_total_items(),
            "categories": len(self.get_all_categories()),
            "items_by_category": {
                cat.value: len(collection) 
                for cat, collection in self.collections.items() 
                if len(collection) > 0
            },
            "last_updated": self.last_updated,
            "source_file": self.source_file
        }
        return stats

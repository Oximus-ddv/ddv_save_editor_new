"""
Game item data models for DDV Save Editor
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ItemCategory(str, Enum):
    """Available item categories with their numeric IDs"""
    PETS = "pets"  # ID: 1
    
    # Clothing subcategories (10-19)
    CLOTHES_OUTFITS = "clothes_outfits"  # ID: 10
    CLOTHES_TOPS = "clothes_tops"  # ID: 11
    CLOTHES_BOTTOMS = "clothes_bottoms"  # ID: 12
    CLOTHES_HELMETS = "clothes_helmets"  # ID: 13
    CLOTHES_SHOES = "clothes_shoes"  # ID: 14
    CLOTHES_ACCESSORIES = "clothes_accessories"  # ID: 15
    CLOTHES_OTHER = "clothes_other"  # ID: 16
    
    # House subcategories (20-29)
    HOUSE_SKINS = "house_skins"  # ID: 20
    HOUSE_WALLPAPER = "house_wallpaper"  # ID: 21
    HOUSE_FLOORS = "house_floors"  # ID: 22
    NPC_HOUSES = "npc_houses"  # ID: 23
    
    # Other categories (30+)
    NPC_SKINS = "npc_skins"  # ID: 30
    FURNITURE = "furniture"  # ID: 31
    TOOLS = "tools"  # ID: 32
    FOOD = "food"  # ID: 33
    MATERIALS = "materials"  # ID: 34
    
    def get_id(self) -> int:
        """Get the numeric ID for this category"""
        category_ids = {
            "pets": 1,
            "clothes_outfits": 1,
            "clothes_tops": 1,
            "clothes_bottoms": 1,
            "clothes_helmets": 1,
            "clothes_shoes": 1,
            "clothes_accessories": 1,
            "clothes_other": 1,
            "house_skins": 5,
            "house_wallpaper": 2,
            "house_floors": 2,
            "npc_houses": 5,
            "npc_skins": 7,
            "furniture": 31,
            "tools": 32,
            "food": 33,
            "materials": 34
        }
        return category_ids[self.value]
    
    @classmethod
    def from_id(cls, id: int) -> Optional["ItemCategory"]:
        """Get a category from its numeric ID"""
        id_to_category = {
            1: cls.PETS,
            10: cls.CLOTHES_OUTFITS,
            11: cls.CLOTHES_TOPS,
            12: cls.CLOTHES_BOTTOMS,
            13: cls.CLOTHES_HELMETS,
            14: cls.CLOTHES_SHOES,
            15: cls.CLOTHES_ACCESSORIES,
            16: cls.CLOTHES_OTHER,
            20: cls.HOUSE_SKINS,
            21: cls.HOUSE_WALLPAPER,
            22: cls.HOUSE_FLOORS,
            23: cls.NPC_HOUSES,
            30: cls.NPC_SKINS,
            31: cls.FURNITURE,
            32: cls.TOOLS,
            33: cls.FOOD,
            34: cls.MATERIALS
        }
        return id_to_category.get(id)


class GameItem(BaseModel):
    """Represents a single game item"""
    id: int = Field(..., description="Unique item ID")
    name: str = Field(..., description="Display name of the item")
    category: ItemCategory = Field(..., description="Item category")
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
    state: Optional[str] = Field(None, description="Item state (for some special items)")
    inventory_id: Optional[str] = Field(None, description="Original inventory/group identifier where this item belongs")

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
    
    # Inventories
    inventory_items: List[PlayerInventoryItem] = Field(default_factory=list)
    pets: List[PetData] = Field(default_factory=list)
    
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
        """Get a specific item"""
        return self.collections[category].get_item(item_id)
    
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

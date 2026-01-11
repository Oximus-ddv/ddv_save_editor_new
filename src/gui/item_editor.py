"""
Item editor frame for editing game items
"""
from typing import List, Optional, Dict
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, 
    QTreeWidget, QTreeWidgetItem, QPushButton, QLineEdit,
    QMenu, QMessageBox, QInputDialog, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QColor

from ..models.game_item import ItemCategory, ItemCollection, SaveData, PlayerInventoryItem, GameItem, PetData
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.augmentation_service import InventoryType, add_item_from_editor, add_specific_tool
from .pet_editor_dialog import PetEditorDialog
from .hover_preview import HoverPreviewBehavior

logger = logging.getLogger(__name__)


class CustomQTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        try:
            return int(self.text(column)) < int(other.text(column))
        except ValueError:
            return self.text(column) < other.text(column)


class ItemEditorFrame(QWidget):
    """Frame for editing items of a specific category using a split view"""
    data_changed = pyqtSignal()
    
    def __init__(self, parent, category: ItemCategory, collection: ItemCollection, 
                 image_service: ImageService, save_service: SaveFileService):
        super().__init__(parent)
        
        self.category = category
        self.collection = collection
        self.image_service = image_service
        self.save_service = save_service
        self.save_data: Optional[SaveData] = None
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the split view UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter for Left (Dict) and Right (Save)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # --- LEFT PANE: Dictionary ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 2, 5)
        
        # Header with Search
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("<b>Dictionary</b> (Available Items)"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self.filter_dictionary)
        left_header.addWidget(self.search_input)
        left_layout.addLayout(left_header)
        
        # Dictionary Tree
        self.dict_tree = QTreeWidget()
        self.dict_tree.setHeaderLabels(["ID", "Name"])
        self.dict_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.dict_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.dict_tree.setSortingEnabled(True)
        self.dict_tree.header().sectionClicked.connect(lambda col: self._sort_tree(self.dict_tree, col))
        # Enable multi-selection
        from PyQt6.QtWidgets import QAbstractItemView
        self.dict_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.dict_tree.itemDoubleClicked.connect(self.on_dict_item_double_clicked)
        left_layout.addWidget(self.dict_tree)
        
        # Add Button
        add_btn = QPushButton("Add to Save >")
        add_btn.clicked.connect(self.add_selected_item)
        left_layout.addWidget(add_btn)
        
        splitter.addWidget(left_widget)
        
        # --- RIGHT PANE: Save Inventory ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 5, 5, 5)
        
        # Header
        right_header = QHBoxLayout()
        right_header.addWidget(QLabel("<b>Save Inventory</b> (Owned Items)"))
        right_layout.addLayout(right_header)
        
        # Inventory Tree
        self.inv_tree = QTreeWidget()
        self.inv_tree.setHeaderLabels(["ID", "Name", "Amount"])
        self.inv_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.inv_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.inv_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # Enable multi-selection
        self.inv_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.inv_tree.itemDoubleClicked.connect(self.edit_inventory_amount)
        self.inv_tree.setSortingEnabled(True)
        self.inv_tree.header().sectionClicked.connect(lambda col: self._sort_tree(self.inv_tree, col))
        right_layout.addWidget(self.inv_tree)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        
        if self.category == ItemCategory.PETS:
            edit_details_btn = QPushButton("Edit Details")
            edit_details_btn.clicked.connect(self.edit_pet_details)
            actions_layout.addWidget(edit_details_btn)
            
        edit_btn = QPushButton("Edit Amount")
        edit_btn.clicked.connect(self.edit_inventory_amount)
        actions_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_selected_item)
        actions_layout.addWidget(remove_btn)
        
        right_layout.addLayout(actions_layout)
        
        splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (50/50)
        # splitter.setSizes([400, 400])
        
        # Populate Dictionary
        self.populate_dictionary(set())
        
        # Setup Hover Previews
        self.dict_hover = HoverPreviewBehavior(self.dict_tree, self.image_service, 
                                               lambda id, item: self.category)
        self.inv_hover = HoverPreviewBehavior(self.inv_tree, self.image_service, 
                                              lambda id, item: self.category)

    def _sort_tree(self, tree: QTreeWidget, column: int):
        """Sort the tree widget by the given column, handling groups."""
        order = tree.header().sortIndicatorOrder()
        
        # Sort top-level items
        tree.sortItems(column, order)
        
        # Now, sort children of each top-level group
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            if parent and parent.childCount() > 0:
                parent.sortChildren(column, order)

    def populate_dictionary(self, saved_item_ids: set):
        """Populate the dictionary tree with items from the collection, grouping by sub_category if available"""
        self.dict_tree.clear()
        
        # Dictionary to store group parents: {group_name: QTreeWidgetItem}
        groups: Dict[str, CustomQTreeWidgetItem] = {}
        items_without_group = []
        
        # Sort items to preserve some order (e.g. by name)
        sorted_collection = sorted(list(self.collection), key=lambda x: x.name)

        for item in sorted_collection:
            item_id_str = str(item.id) # Define item_id_str here, outside the if blocks

            # If this is a house category, apply specific filtering rules for display
            if self.category in [ItemCategory.HOUSE_SKINS, ItemCategory.HOUSE_WALLPAPER, 
                                 ItemCategory.HOUSE_FLOORS, ItemCategory.NPC_HOUSES]:
                
                is_house_wallpaper = (self.category == ItemCategory.HOUSE_WALLPAPER)
                
                passes_house_filter = False
                if is_house_wallpaper:
                    passes_house_filter = item_id_str.startswith('20') or item_id_str.startswith('160')
                else: # Other house types (SKINS, FLOORS, NPC_HOUSES)
                    passes_house_filter = item_id_str.startswith('20')
                
                if not passes_house_filter:
                    continue # Skip this item if it doesn't pass the house filter

            # Global rule: For non-house categories, exclude items starting with '20'
            elif item_id_str.startswith('20'):
                continue # Skip '20' items from non-house categories

            # If the item passes all relevant filters, create the tree item
            tree_item = CustomQTreeWidgetItem()
            tree_item.setText(0, str(item.id))
            tree_item.setText(1, item.name)
            # Store full item object
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item)

            if item.id in saved_item_ids:
                tree_item.setForeground(1, QColor("green"))
            
            # Grouping logic
            sub_cat = getattr(item, 'sub_category', None)
            if sub_cat:
                if sub_cat not in groups:
                    group_parent = CustomQTreeWidgetItem(self.dict_tree)
                    group_parent.setText(1, sub_cat)
                    # Make group bold
                    font = group_parent.font(1)
                    font.setBold(True)
                    group_parent.setFont(1, font)
                    groups[sub_cat] = group_parent
                
                groups[sub_cat].addChild(tree_item)
            else:
                items_without_group.append(tree_item)
            
        # Add standalone items to the top level
        self.dict_tree.addTopLevelItems(items_without_group)
        
        # Expand all groups by default
        self.dict_tree.expandAll()
        
    def filter_dictionary(self, text: str):
        """Filter dictionary items based on search text, handling hierarchical groups"""
        text = text.lower()
        
        def filter_item(item: QTreeWidgetItem) -> bool:
            # If it's a leaf (an actual game item)
            game_item: Optional[GameItem] = item.data(0, Qt.ItemDataRole.UserRole)
            if game_item:
                match = text in game_item.name.lower() or text in str(game_item.id)
                item.setHidden(not match)
                return match
            
            # If it's a group parent
            visible_children = 0
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    visible_children += 1
            
            # Parent is hidden if it has no visible children and its own name doesn't match
            # But usually we only search within item names/IDs
            group_match = text in item.text(1).lower()
            should_show_parent = visible_children > 0 or group_match
            item.setHidden(not should_show_parent)
            
            # If parent matches but children don't, show all children? 
            # (Standard behavior: if parent matches, show it. If children match, show parent.)
            if group_match:
                for i in range(item.childCount()):
                    item.child(i).setHidden(False)
            
            return should_show_parent

        root = self.dict_tree.invisibleRootItem()
        for i in range(root.childCount()):
            filter_item(root.child(i))

    def load_save_data(self, save_data: SaveData):
        """Load save data into the right pane"""
        self.save_data = save_data
        if self.save_data:
            saved_item_ids = {item.item_id for item in self.save_data.inventory_items}
            self.populate_dictionary(saved_item_ids)
        self.refresh_inventory_tree()

    def _get_backpack_capacity_info(self) -> (int, int):
        """Calculates the expected backpack size and current item count."""
        if not self.save_data:
            return 0, 0

        total_pet_inventory_slots = 0
        for pet in self.save_data.pets:
            if pet.is_following:
                total_pet_inventory_slots += pet.granted_inventory_slots
        
        expected_backpack_size = 42 + total_pet_inventory_slots

        current_backpack_items = [
            item for item in self.save_data.inventory_items
            if item.source_type == 'container' and item.inventory_id == '0' and item.item_id != 0
        ]
        current_item_count = len(current_backpack_items)

        return expected_backpack_size, current_item_count

    def _is_pet_category(self) -> bool:
        """Check if this is the pets/companions category"""
        return self.category == ItemCategory.PETS

    def _is_tool_category(self) -> bool:
        """Check if this is the tools category"""
        return self.category == ItemCategory.TOOLS

    def refresh_inventory_tree(self):
        """Refresh the inventory tree from save data"""
        self.inv_tree.clear()
        if not self.save_data:
            return

        # Handle Pets/Companions specially
        if self._is_pet_category():
            for pet in self.save_data.pets:
                self._add_pet_tree_item(pet)
            return

        # Handle Tools specially
        if self._is_tool_category():
            tools = self.save_data.custom_data.get('original_save', {}).get('Player', {}).get('Tools', [])
            for tool in tools:
                self._add_tool_tree_item(tool)
            return

        items_to_display = []
        for inv_item in self.save_data.inventory_items:
            # Check if this item exists in our collection for the current category
            game_item = self.collection.get_item(inv_item.item_id)
            if game_item and game_item.category == self.category:
                items_to_display.append(inv_item)
            elif self._item_matches_category(str(inv_item.item_id)): # Fallback for items not in collection but match category pattern
                items_to_display.append(inv_item)

        for item in items_to_display:
            self._add_inv_tree_item(item)
        
        logger.info(f"Category {self.category.name}: {len(items_to_display)} items displayed in inventory tree")

    def _add_tool_tree_item(self, tool_data: dict):
        """Helper to add a tool to the inventory tree"""
        tool_id = tool_data.get('ToolItemID')
        if not tool_id:
            return

        name = "Unknown Tool"
        game_item = self.collection.get_item(tool_id)
        if game_item:
            name = game_item.name
        
        tree_item = CustomQTreeWidgetItem(self.inv_tree)
        tree_item.setText(0, str(tool_id))
        tree_item.setText(1, name)
        tree_item.setText(2, "1") # Tools are unique, amount 1
        
        # Store tool data object
        tree_item.setData(0, Qt.ItemDataRole.UserRole, tool_data)

    def _add_pet_tree_item(self, pet):
        """Helper to add a pet to the inventory tree"""
        # Find name from collection
        name = pet.custom_name or "Unknown"
        # Try to find generic name from collection
        for item in self.collection:
            if str(item.id) == str(pet.pet_item_id):
                if not name or name == "Unknown":
                    name = item.name
                else:
                    name = f"{name} ({item.name})" # Show custom name + species
                break
        
        tree_item = CustomQTreeWidgetItem(self.inv_tree)
        tree_item.setText(0, str(pet.pet_item_id))
        tree_item.setText(1, name)
        tree_item.setText(2, "1") # Pets are unique, amount 1
        
        # Store PetData object
        tree_item.setData(0, Qt.ItemDataRole.UserRole, pet)
                
    def _item_matches_category(self, item_id_str: str) -> bool:
        """Check if an item ID pattern matches this category based on DDV's ID scheme"""
        # DDV uses specific ID ranges for different item types
        # Based on observed patterns in Dict files and save data
        
        # Pets/Companions: 12000xxxx
        if self.category == ItemCategory.PETS:
            return item_id_str.startswith('12000') or item_id_str.startswith('12')
        
        # All clothing items: 50xxxxxx or 51xxxxxx
        if self.category in [ItemCategory.CLOTHES_OTHER, ItemCategory.CLOTHES_OUTFITS, 
                             ItemCategory.CLOTHES_TOPS, ItemCategory.CLOTHES_BOTTOMS,
                             ItemCategory.CLOTHES_HELMETS, ItemCategory.CLOTHES_SHOES,
                             ItemCategory.CLOTHES_ACCESSORIES]:
            return item_id_str.startswith('50') or item_id_str.startswith('51')
        
        # Furniture: 30xxxxxx, 31xxxxxx, 40xxxxxx, 41xxxxxx
        if self.category == ItemCategory.FURNITURE:
            return (item_id_str.startswith('30') or item_id_str.startswith('31') or
                    item_id_str.startswith('40') or item_id_str.startswith('41'))
        
        # Gliders: 70xxxxxx
        if self.category == ItemCategory.GLIDERS:
            return item_id_str.startswith('70')
            
        # Avatar Features: 70xxxxxx (same as Gliders?)
        if self.category == ItemCategory.AVATAR_FEATURES:
            return item_id_str.startswith('70')

        # Specific house rules:
        # HOUSE_WALLPAPER allows '20' and '160' (as requested)
        if self.category == ItemCategory.HOUSE_WALLPAPER:
            return item_id_str.startswith('20') or item_id_str.startswith('160')
        
        # Other house types only allow '20'
        if self.category in [ItemCategory.HOUSE_SKINS, ItemCategory.HOUSE_FLOORS, ItemCategory.NPC_HOUSES]:
            return item_id_str.startswith('20')
        
        # Global rule: Prevent '20' items from other inventories (unless handled above)
        if item_id_str.startswith('20'):
            return False # Exclude '20' items from non-house categories
        
        # NPC Skins: 170xxxxxx
        if self.category == ItemCategory.NPC_SKINS:
            return item_id_str.startswith('170')
        
        # Tools: 110xxxxxx or 80xxxxxx
        if self.category == ItemCategory.TOOLS:
            return item_id_str.startswith('110') or item_id_str.startswith('80')
            
        # Activity: 110xxxxxx
        if self.category == ItemCategory.ACTIVITY:
            return item_id_str.startswith('110') or item_id_str.startswith('11')
        
        # Motifs: 100xxxxxx
        if self.category == ItemCategory.MOTIFS:
            return item_id_str.startswith('100')
            
        # Photo Mode: 190xxxxxx
        if self.category == ItemCategory.PHOTO_MODE:
            return item_id_str.startswith('190')
            
        # Mount Gear: 210xxxxxx
        if self.category == ItemCategory.MOUNT_GEAR:
            return item_id_str.startswith('210')
            
        # Scramblecoin: 180xxxxxx
        if self.category == ItemCategory.SCRAMBLECOIN:
            return item_id_str.startswith('180')
            
        # Makeup: 140xxxxxx
        if self.category == ItemCategory.MAKEUP:
            return item_id_str.startswith('140')
            
        # Trimming: 16xxxxxx
        if self.category == ItemCategory.TRIMMING:
            return item_id_str.startswith('16')
        
        # Food: 90xxxxxx (Consumables generally)
        if self.category == ItemCategory.FOOD:
            return item_id_str.startswith('90')
        
        # Materials: Crafting items
        if self.category == ItemCategory.MATERIALS:
            return item_id_str.startswith('10') and not item_id_str.startswith('100') # Avoid Motifs conflict
        
        return False
    
    def _is_pet_category(self) -> bool:
        return self.category == ItemCategory.PETS

    def _is_list_category(self) -> bool:
        """Categories that go into ListInventories (Furniture, Clothes, etc.)"""
        return self.category in [
            ItemCategory.FURNITURE,
            ItemCategory.CLOTHES_OUTFITS,
            ItemCategory.CLOTHES_TOPS,
            ItemCategory.CLOTHES_BOTTOMS,
            ItemCategory.CLOTHES_HELMETS,
            ItemCategory.CLOTHES_SHOES,
            ItemCategory.CLOTHES_ACCESSORIES,
            ItemCategory.CLOTHES_OTHER,
            ItemCategory.GLIDERS,
            ItemCategory.HOUSE_SKINS,
            ItemCategory.HOUSE_WALLPAPER,
            ItemCategory.HOUSE_FLOORS,
            ItemCategory.NPC_SKINS,
            ItemCategory.NPC_HOUSES,
            ItemCategory.MOTIFS,
            ItemCategory.MAKEUP,
            ItemCategory.TRIMMING,
            ItemCategory.PHOTO_MODE
        ]
    
    def _add_inv_tree_item(self, inv_item: PlayerInventoryItem, show_as_unknown: bool = False):
        """Helper to add an item to the inventory tree"""
        # Find name from collection
        name = "Unknown"
        if not show_as_unknown:
            # Since we just need lookup, iterate collection (could be optimized with a dict)
            for item in self.collection:
                if str(item.id) == str(inv_item.item_id):
                    name = item.name
                    break
        else:
            name = f"Unknown Item (ID: {inv_item.item_id})"
        
        tree_item = CustomQTreeWidgetItem(self.inv_tree)
        tree_item.setText(0, str(inv_item.item_id))
        
        display_name = name
        if inv_item.marker == "ItemMarker_IsNew":
            display_name = f"{name} (New)"
            
        tree_item.setText(1, display_name)
        tree_item.setText(2, str(inv_item.amount))
        
        # Store the PlayerInventoryItem object specifically for editing
        tree_item.setData(0, Qt.ItemDataRole.UserRole, inv_item)

    def add_selected_item(self):
        """Add selected item(s) from dictionary to save inventory"""
        if not self.save_data:
            return

        selected_items = self.dict_tree.selectedItems()
        if not selected_items:
            return

        added_count = 0
        for item in selected_items:
            game_item = item.data(0, Qt.ItemDataRole.UserRole)
            # --- NEW CHECK: Prevent adding house items not starting with '20' ---
            if self.category in [ItemCategory.HOUSE_SKINS, ItemCategory.HOUSE_WALLPAPER, 
                                 ItemCategory.HOUSE_FLOORS, ItemCategory.NPC_HOUSES]:
                if not str(game_item.id).startswith('20'):
                    QMessageBox.warning(self, "Cannot Add", f"Item '{game_item.name}' (ID: {game_item.id}) cannot be added to Houses category as it does not start with '20'.")
                    continue # Skip adding this item
            # --- END NEW CHECK ---

            # --- NEW CHECK: Filter items based on category rules before adding ---
            game_item_id_str = str(game_item.id)
            should_add_item = True
            reason = ""

            if self.category in [ItemCategory.HOUSE_SKINS, ItemCategory.HOUSE_WALLPAPER, 
                                 ItemCategory.HOUSE_FLOORS, ItemCategory.NPC_HOUSES]:
                # House categories
                is_house_wallpaper = (self.category == ItemCategory.HOUSE_WALLPAPER)
                
                passes_house_filter = False
                if is_house_wallpaper:
                    passes_house_filter = game_item_id_str.startswith('20') or game_item_id_str.startswith('160')
                else: # Other house types (SKINS, FLOORS, NPC_HOUSES)
                    passes_house_filter = game_item_id_str.startswith('20')
                
                if not passes_house_filter:
                    should_add_item = False
                    reason = f"Item ID {game_item_id_str} does not match the required prefix ('20' or '160' for wallpaper, '20' for others)."
            
            elif game_item_id_str.startswith('20'):
                # For non-house categories, disallow items starting with '20'
                should_add_item = False
                reason = f"Item ID {game_item_id_str} starts with '20' and cannot be added to this category."

            if not should_add_item:
                QMessageBox.warning(self, "Cannot Add", f"Cannot add item '{game_item.name}' (ID: {game_item.id}). Reason: {reason}")
                continue # Skip adding this item
            # --- END NEW CHECK ---

            if self._is_pet_category():
                # Check if pet already exists
                if any(p.pet_item_id == game_item.id for p in self.save_data.pets):
                    continue
                
                # Also update the raw dictionary
                player_data = self.save_data.custom_data['original_save'].setdefault('Player', {})
                pets_list = player_data.setdefault('Pets', [])
                
                # Check if pet already exists in raw data
                if any(p.get('PetItemID') == game_item.id for p in pets_list):
                    continue
                    
                new_pet_dict = {
                    'PetItemID': game_item.id,
                    'FriendshipLevel': 1,
                    'FriendshipXp': 0,
                }
                pets_list.append(new_pet_dict)
                added_count += 1
            elif self._is_tool_category():
                if add_specific_tool(self.save_data.custom_data['original_save'], game_item.id):
                    added_count += 1
            else:
                if add_item_from_editor(self.save_data.custom_data['original_save'], game_item.id, self.category.name):
                    added_count += 1
        
        if added_count > 0:
            self.save_service.reparse_from_json(self.save_data.custom_data['original_save'])
            message = f"Added {added_count} new item(s)."
            if self.category == ItemCategory.TOOLS:
                message = f"{added_count} new tool(s) have been added to your tools list."
            elif self._is_pet_category():
                message = f"{added_count} new companion(s) have been added to your companions list."
            QMessageBox.information(self, "Success", message)

        self.data_changed.emit()
        self.refresh_inventory_tree()
        
    def on_dict_item_double_clicked(self, item, column):
        self.add_selected_item()

    def remove_selected_item(self):
        """Remove selected item(s) from save inventory"""
        if not self.save_data:
            return
            
        selected_items = self.inv_tree.selectedItems()
        if not selected_items:
            return
            
        count = len(selected_items)
        confirm_msg = f"Are you sure you want to remove {count} items?"
        if count == 1:
            inv_item = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            item_id = getattr(inv_item, 'item_id', getattr(inv_item, 'pet_item_id', 'Unknown'))
            confirm_msg = f"Are you sure you want to remove item {item_id}?"

        confirm = QMessageBox.question(
            self, "Confirm Remove",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            removed_count = 0
            for tree_item in selected_items:
                item_data = tree_item.data(0, Qt.ItemDataRole.UserRole)
                
                if self._is_pet_category():
                    if item_data in self.save_data.pets:
                        self.save_data.pets.remove(item_data)
                        removed_count += 1
                else:
                    if item_data in self.save_data.inventory_items:
                        self.save_data.inventory_items.remove(item_data)
                        removed_count += 1
            
            logger.info(f"Removed {removed_count} items")
            self.data_changed.emit()
            self.refresh_inventory_tree()

    def edit_inventory_amount(self):
        """Edit amount of selected inventory item(s)"""
        selected_items = self.inv_tree.selectedItems()
        if not selected_items:
            return
            
        # Filter valid items (pets don't have amounts)
        editable_items = []
        for tree_item in selected_items:
            inv_item = tree_item.data(0, Qt.ItemDataRole.UserRole)
            if not hasattr(inv_item, 'pet_item_id'):
                editable_items.append((tree_item, inv_item))
                
        if not editable_items:
            if any(hasattr(tree_item.data(0, Qt.ItemDataRole.UserRole), 'pet_item_id') for tree_item in selected_items):
                QMessageBox.information(self, "Info", "Pets/Companions do not have an amount.")
            return

        # Use the amount of the first item as default, or 1
        default_val = getattr(editable_items[0][1], 'amount', 1)
        
        prompt = f"Enter amount for {len(editable_items)} items:" if len(editable_items) > 1 else f"Enter amount for item {getattr(editable_items[0][1], 'item_id', '?')}:"

        val, ok = QInputDialog.getInt(
            self, "Edit Amount", 
            prompt,
            value=default_val, min=1, max=9999
        )
        
        if ok:
            count = 0
            for tree_item, inv_item in editable_items:
                inv_item.amount = val
                tree_item.setText(2, str(val))
                count += 1
            
            logger.info(f"Updated amount to {val} for {count} items")
            
    def edit_pet_details(self):
        """Open the pet editor dialog for the selected pet"""
        selected = self.inv_tree.selectedItems()
        if not selected:
            return
            
        tree_item = selected[0]
        pet_data = tree_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Verify it's actually pet data
        if not hasattr(pet_data, 'pet_item_id'):
            return

        # Find GameItem for metadata
        game_item = self.collection.get_item(pet_data.pet_item_id)
        
        dialog = PetEditorDialog(self, pet_data, game_item, self.image_service)
        if dialog.exec():
            # Refresh to show changes (e.g. name change)
            # Better: just update text of current item
            name = pet_data.custom_name or "Unknown"
            if game_item:
                 if not name or name == "Unknown":
                    name = game_item.name
                 else:
                    name = f"{name} ({game_item.name})"
            
            tree_item.setText(1, name)
            self.data_changed.emit()

    def update_save_data(self):
        """Update save data with current values"""
        # Data is updated in-place on the objects, so no extra work needed here normally,
        # unless we were using a disconnected model.
        pass

    def add_all_items(self):
        """Add all items from this category to save"""
        if not self.save_data:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Add All",
            f"This will add {len(self.collection)} items to your save. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        existing_ids = {item.item_id for item in self.save_data.inventory_items}
        
        count = 0
        for game_item in self.collection:
            if game_item.id not in existing_ids:
                inv_id = InventoryType.get_inventory_for_id(game_item.id) or "1"
                self.save_data.inventory_items.append(
                    PlayerInventoryItem(
                        item_id=game_item.id,
                        amount=1,
                        inventory_id=inv_id
                    )
                )
                count += 1
                
        self.data_changed.emit()
        self.refresh_inventory_tree()
        QMessageBox.information(self, "Success", f"Added {count} new items.")

    def clear_all_items(self):
        """Remove all items of this category from save"""
        if not self.save_data:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to remove ALL items of this category from your save?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        valid_ids = {str(item.id) for item in self.collection}
        
        # Filter out items belonging to this category
        self.save_data.inventory_items = [
            item for item in self.save_data.inventory_items
            if str(item.item_id) not in valid_ids
        ]
        
        self.data_changed.emit()
        self.refresh_inventory_tree()
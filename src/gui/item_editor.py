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
from PyQt6.QtGui import QAction, QIcon

from ..models.game_item import ItemCategory, ItemCollection, SaveData, PlayerInventoryItem, GameItem
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.augmentation_service import InventoryType
from .pet_editor_dialog import PetEditorDialog
from .hover_preview import HoverPreviewBehavior

logger = logging.getLogger(__name__)


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
        splitter.setSizes([400, 400])
        
        # Populate Dictionary
        self.populate_dictionary()
        
        # Setup Hover Previews
        self.dict_hover = HoverPreviewBehavior(self.dict_tree, self.image_service, 
                                               lambda id, item: self.category)
        self.inv_hover = HoverPreviewBehavior(self.inv_tree, self.image_service, 
                                              lambda id, item: self.category)

    def populate_dictionary(self):
        """Populate the dictionary tree with items from the collection, grouping by sub_category if available"""
        self.dict_tree.clear()
        
        # Dictionary to store group parents: {group_name: QTreeWidgetItem}
        groups: Dict[str, QTreeWidgetItem] = {}
        items_without_group = []
        
        # Sort items to preserve some order (e.g. by name)
        sorted_collection = sorted(list(self.collection), key=lambda x: x.name)

        for item in sorted_collection:
            tree_item = QTreeWidgetItem()
            tree_item.setText(0, str(item.id))
            tree_item.setText(1, item.name)
            # Store full item object
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
            
            # Grouping logic
            sub_cat = getattr(item, 'sub_category', None)
            if sub_cat:
                if sub_cat not in groups:
                    group_parent = QTreeWidgetItem(self.dict_tree)
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
        self.refresh_inventory_tree()

    def _is_pet_category(self):
        """Check if this is the pets/companions category"""
        return self.category == ItemCategory.PETS

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

        # Determine which items belong to this category
        # Match items by checking if they exist in the Dict collection
        
        # Creating a set of valid IDs for this category for fast lookup
        valid_ids = {str(item.id) for item in self.collection}
        
        # Try to categorize items based on ID prefixes (game's ID scheme)
        matched_items = []
        category_items = []  # Items that match category prefix but not in Dict
        
        for inv_item in self.save_data.inventory_items:
            item_id_str = str(inv_item.item_id)
            
            # Check if this item is in our Dict
            if item_id_str in valid_ids:
                matched_items.append(inv_item)
            else:
                # Check if item might belong to this category based on ID pattern
                if self._item_matches_category(item_id_str):
                    category_items.append(inv_item)
        
        # Add matched items first
        for item in matched_items:
            self._add_inv_tree_item(item)
        
        # Add category items that aren't in Dict as "Unknown"
        for item in category_items:
            self._add_inv_tree_item(item, show_as_unknown=True)
        
        logger.info(f"Category {self.category.name}: {len(matched_items)} matched, {len(category_items)} unknown items")

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
        
        tree_item = QTreeWidgetItem(self.inv_tree)
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
            return item_id_str.startswith('12000')
        
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
        
        # Gliders: 70xxxxxx or 5080xxxx
        if self.category == ItemCategory.GLIDERS:
            return item_id_str.startswith('70') or item_id_str.startswith('5080')

        # House-related: 20xxxxxx, 21xxxxxx, 60xxxxxx
        if self.category in [ItemCategory.HOUSE_SKINS, ItemCategory.HOUSE_WALLPAPER, 
                             ItemCategory.HOUSE_FLOORS, ItemCategory.NPC_HOUSES]:
            return (item_id_str.startswith('20') or item_id_str.startswith('21') or
                    item_id_str.startswith('60'))
        
        # NPC Skins: Often in 70xxxxxx range
        if self.category == ItemCategory.NPC_SKINS:
            return item_id_str.startswith('70')
        
        # Tools: 80xxxxxx
        if self.category == ItemCategory.TOOLS:
            return item_id_str.startswith('80')
        
        # Food: 90xxxxxx
        if self.category == ItemCategory.FOOD:
            return item_id_str.startswith('90')
        
        # Materials: 100xxxxx
        if self.category == ItemCategory.MATERIALS:
            return item_id_str.startswith('100')
        
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
        
        tree_item = QTreeWidgetItem(self.inv_tree)
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
            
        # Collect GameItems from selection (filtering out group headers which have no data)
        game_items: List[GameItem] = []
        for tree_item in selected_items:
            data = tree_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, GameItem):
                game_items.append(data)
                
        if not game_items:
            return

        added_count = 0
        updated_count = 0
        
        # Check which items already exist
        existing_map = {} # item_id -> existing_object
        
        if self._is_pet_category():
            for pet in self.save_data.pets:
                existing_map[pet.pet_item_id] = pet
        else:
            for item in self.save_data.inventory_items:
                existing_map[item.item_id] = item
        
        items_to_add = []
        items_to_update = []
        
        for game_item in game_items:
            if game_item.id in existing_map:
                items_to_update.append((game_item, existing_map[game_item.id]))
            else:
                items_to_add.append(game_item)
                
        # Handle updates (if any)
        if items_to_update:
            should_update = False
            # If only 1 item update, use specific message
            if len(items_to_update) == 1 and len(game_items) == 1:
                item, existing = items_to_update[0]
                reply = QMessageBox.question(
                    self, "Item Exists", 
                    f"{item.name} is already in your inventory. Increase amount?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                should_update = (reply == QMessageBox.StandardButton.Yes)
            else:
                # Bulk update confirmation
                reply = QMessageBox.question(
                    self, "Items Exist", 
                    f"{len(items_to_update)} of the selected items are already in your inventory.\nIncrease amount for these items?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                should_update = (reply == QMessageBox.StandardButton.Yes)
                
            if should_update:
                for game_item, existing_item in items_to_update:
                    if hasattr(existing_item, 'amount'):
                        existing_item.amount += 1
                        updated_count += 1
                        logger.info(f"Increased amount for item {game_item.id}")

        # Handle new items
        for game_item in items_to_add:
            item_id = game_item.id
            
            # Determine inventory ID
            source_type = "list" if self._is_list_category() else "container"
            inventory_id = InventoryType.get_inventory_for_id(item_id)
            if not inventory_id:
                inventory_id = "1" if source_type == "list" else "0"
            
            marker = "ItemMarker_IsNew"
            
            if self._is_pet_category():
                from ..models.game_item import PetData
                new_pet = PetData(
                    pet_item_id=item_id,
                    name=game_item.name,
                    is_following=False
                )
                self.save_data.pets.append(new_pet)
                logger.info(f"Added new pet: {game_item.name} (ID: {item_id})")
            else:
                new_item = PlayerInventoryItem(
                    item_id=item_id,
                    amount=1,
                    inventory_id=inventory_id,
                    source_type=source_type,
                    marker=marker
                )
                self.save_data.inventory_items.append(new_item)
                logger.info(f"Added new item: {game_item.name} (ID: {item_id})")
            
            added_count += 1
            
        self.data_changed.emit()
        self.refresh_inventory_tree()
        
        # Show summary if we did a bulk operation
        if len(game_items) > 1:
            msg = []
            if added_count > 0: msg.append(f"Added {added_count} new items.")
            if updated_count > 0: msg.append(f"Updated {updated_count} existing items.")
            if not msg: msg.append("No changes made.")
            
            # Use status bar for less intrusion, or toast? 
            # MainWindow has status signal but we are in a widget.
            # Just log it or show info if significant.
            if added_count + updated_count > 0:
                logger.info(f"Bulk add complete: {', '.join(msg)}")
        
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
            self._add_pet_tree_item(pet_data) # This might duplicate if I don't clear or update current item
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

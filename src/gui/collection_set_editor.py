"""
Collection Set editor frame for editing game collection sets
"""

import re
from typing import Optional, List, Tuple
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QHeaderView,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from ..models.game_item import SaveData, PlayerInventoryItem, GameDatabase, ItemCategory
from ..services.save_service import SaveFileService
from ..services.dict_service import DictDataService
from ..services.augmentation_service import InventoryType
from ..services.image_service import ImageService
from .hover_preview import HoverPreviewBehavior

logger = logging.getLogger(__name__)


class CollectionSetEditorFrame(QWidget):
    """Frame for editing collection sets"""

    def __init__(
        self,
        parent,
        save_service: SaveFileService,
        dict_service: DictDataService,
        image_service: ImageService,
    ):
        super().__init__(parent)

        self.save_service = save_service
        self.dict_service = dict_service
        self.image_service = image_service
        self.game_database: Optional[GameDatabase] = None
        self.save_data: Optional[SaveData] = None
        self._is_handling_check_change = False

        self.setup_ui()
        self.hover_behavior = HoverPreviewBehavior(
            self.collection_set_tree, self.image_service, self._get_category_for_item
        )

    def _get_category_for_item(
        self, item_id: int, item: QTreeWidgetItem
    ) -> Optional[ItemCategory]:
        """Find the category for a given item ID."""
        if not self.game_database:
            return None
        for category in self.game_database.collections.values():
            if category.get_item(item_id):
                return category.category
        return None

    def _format_collection_name(self, raw_name: str) -> str:
        """Formats the raw collection name to be more user-friendly."""
        if not raw_name or raw_name == "Unknown Group":
            return "Unknown Collection"

        name = raw_name.replace("CollectionSet.", "")
        name = re.sub(r"_CollectionName.*", "", name)
        name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        name = name.replace("_", " ")

        return name.strip().title()

    def setup_ui(self):
        """Setup the UI for the collection set editor"""
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Collection Sets</b>"))
        layout.addLayout(header_layout)

        self.collection_set_tree = QTreeWidget()
        self.collection_set_tree.setHeaderLabels(
            ["Collection / Item", "Item ID", "Collected"]
        )
        self.collection_set_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.collection_set_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.collection_set_tree.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        layout.addWidget(self.collection_set_tree)

        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self.set_all_items_checked(True))
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self.set_all_items_checked(False))
        button_layout.addWidget(deselect_all_btn)

        unlock_all_btn = QPushButton("Unlock & Add All Items")
        unlock_all_btn.clicked.connect(self.unlock_and_add_all_items)
        button_layout.addWidget(unlock_all_btn)
        layout.addLayout(button_layout)

    def load_save_data(self, save_data: SaveData):
        """Load save data into the collection set editor"""
        self.save_data = save_data
        self.refresh_collection_set_tree()

    def refresh_collection_set_tree(self):
        """Refresh the collection set tree from save data"""
        self.collection_set_tree.clear()
        if not self.save_data or not self.save_data.collection_sets:
            return

        for collection_set in self.save_data.collection_sets:
            if "GroupData" not in collection_set:
                continue

            for group_data in collection_set.get("GroupData", []):
                raw_group_name = group_data.get("GroupName", "Unknown Group")
                display_name = self._format_collection_name(raw_group_name)

                group_item = QTreeWidgetItem(self.collection_set_tree)
                group_item.setText(
                    0,
                    f"{display_name} (ID: {collection_set.get('CollectionDefinitionID', 'N/A')})",
                )
                group_item.setData(0, Qt.ItemDataRole.UserRole, group_data)

                if "GroupsCollectionItems" in group_data:
                    items_to_sort: List[Tuple[str, str, bool]] = []
                    for item_id, is_collected in group_data[
                        "GroupsCollectionItems"
                    ].items():
                        item_name = self.dict_service.get_item_name(int(item_id))
                        items_to_sort.append((item_name, item_id, is_collected))

                    items_to_sort.sort(key=lambda x: x[0])

                    child_items = []
                    for item_name, item_id, is_collected in items_to_sort:
                        child_item = QTreeWidgetItem(group_item)
                        child_item.setText(0, item_name)
                        child_item.setText(1, item_id)

                        checkbox = QCheckBox()
                        checkbox.setChecked(is_collected)
                        checkbox.toggled.connect(
                            lambda checked, item_id=item_id, group_data=group_data: self._on_checkbox_toggled(
                                checked, item_id, group_data
                            )
                        )
                        self.collection_set_tree.setItemWidget(child_item, 2, checkbox)
                        child_items.append(child_item)

        for i in range(self.collection_set_tree.columnCount()):
            self.collection_set_tree.resizeColumnToContents(i)

    def _on_checkbox_toggled(self, is_checked: bool, item_id: str, group_data: dict):
        """Handle toggling of an item's collected status."""
        print(f"Checkbox for item {item_id} toggled to {is_checked}")
        logger.debug(f"Checkbox for item {item_id} toggled to {is_checked}")
        if (
            "GroupsCollectionItems" in group_data
            and item_id in group_data["GroupsCollectionItems"]
        ):
            group_data["GroupsCollectionItems"][item_id] = is_checked
            if is_checked:
                if self._add_item_to_inventory(int(item_id)):
                    QMessageBox.information(
                        self,
                        "Item Added",
                        f"Item {item_id} has been added to your inventory.",
                    )

    def _add_item_to_inventory(self, item_id: int) -> bool:
        """Adds a single item to the inventory if it doesn't already exist."""
        print(f"DEBUG: _add_item_to_inventory called for item {item_id}")
        print(f"DEBUG: self.save_data is {'present' if self.save_data else 'None'}")
        print(
            f"DEBUG: self.game_database is {'present' if self.game_database else 'None'}"
        )

        if not self.save_data or not self.game_database:
            print(
                f"DEBUG: Skipping adding item {item_id}: No save data or game database available."
            )
            logger.debug(
                f"Skipping adding item {item_id}: No save data or game database available."
            )
            return False

        existing_item_ids = {item.item_id for item in self.save_data.inventory_items}
        if item_id in existing_item_ids:
            print(
                f"DEBUG: Item {item_id} already exists in inventory. Skipping addition."
            )
            logger.info(
                f"Item {item_id} already exists in inventory. Skipping addition."
            )
            return False

        game_item = None
        for cat in self.game_database.collections.values():
            game_item = cat.get_item(item_id)
            if game_item:
                break

        if game_item:
            inventory_id = InventoryType.get_inventory_for_id(item_id) or "1"

            new_item = PlayerInventoryItem(
                item_id=item_id,
                amount=1,
                inventory_id=inventory_id,
                source_type="list",
                marker="ItemMarker_IsNew",
            )
            self.save_data.inventory_items.append(new_item)
            logger.info(
                f"Successfully added item {item_id} ({game_item.name}) to inventory {inventory_id}."
            )
            return True
        else:
            print(f"DEBUG: Could not find game item with ID {item_id} in the database.")
            logger.warning(
                f"Could not find game item with ID {item_id} in the database to add to inventory."
            )
            return False

    def set_all_items_checked(self, checked: bool):
        """Check or uncheck all items in the tree."""
        root = self.collection_set_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                child_item = group_item.child(j)
                checkbox = self.collection_set_tree.itemWidget(child_item, 2)
                if isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(checked)

    def unlock_and_add_all_items(self):
        """Mark all items in all collection sets as collected and add them to inventory if missing."""
        if (
            not self.save_data
            or not self.save_data.collection_sets
            or not self.game_database
        ):
            return

        items_added_count = 0
        for collection_set in self.save_data.collection_sets:
            if "GroupData" not in collection_set:
                continue

            for group_data in collection_set.get("GroupData", []):
                if "GroupsCollectionItems" not in group_data:
                    continue

                for item_id_str in group_data["GroupsCollectionItems"]:
                    group_data["GroupsCollectionItems"][item_id_str] = True
                    if self._add_item_to_inventory(int(item_id_str)):
                        items_added_count += 1

        self.refresh_collection_set_tree()
        QMessageBox.information(
            self,
            "Unlock All",
            f"All collection items unlocked. {items_added_count} new items added to your inventory.",
        )

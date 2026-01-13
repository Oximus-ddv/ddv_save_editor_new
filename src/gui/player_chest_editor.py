"""
Custom editor for Player Chests (ContainerInventories).
"""

from typing import List, Optional, Dict
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..models.game_item import (
    ItemCategory,
    ItemCollection,
    SaveData,
    PlayerInventoryItem,
)
from ..services.save_service import SaveFileService
from ..services.image_service import ImageService
from .hover_preview import HoverPreviewBehavior

logger = logging.getLogger(__name__)


class CustomQTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        try:
            return int(self.text(column)) < int(other.text(column))
        except ValueError:
            return self.text(column) < other.text(column)


class PlayerChestEditorFrame(QWidget):
    """
    A custom frame to display and edit items within player-owned chests,
    grouped by container.
    """

    data_changed = pyqtSignal()

    def __init__(
        self,
        parent,
        category: ItemCategory,
        collection: ItemCollection,
        image_service: ImageService,
        save_service: SaveFileService,
    ):
        super().__init__(parent)

        self.category = category
        self.collection = collection
        self.image_service = image_service
        self.save_service = save_service
        self.save_data: Optional[SaveData] = None

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Player Chests</b> (Owned Items)"))
        layout.addLayout(header)

        self.chest_tree = QTreeWidget()
        self.chest_tree.setHeaderLabels(["Container ID / Item Name", "Amount"])
        self.chest_tree.setSortingEnabled(True)
        self.chest_tree.header().setStretchLastSection(False)
        self.chest_tree.header().setSectionResizeMode(
            0, self.chest_tree.header().ResizeMode.Stretch
        )
        self.chest_tree.header().setSectionResizeMode(
            1, self.chest_tree.header().ResizeMode.Interactive
        )
        layout.addWidget(self.chest_tree)

        self.chest_tree.itemDoubleClicked.connect(self.edit_item_amount)

        actions_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit Amount")
        edit_btn.clicked.connect(self.edit_item_amount)
        actions_layout.addWidget(edit_btn)

        # We can add more actions like Add/Remove if needed later

        layout.addLayout(actions_layout)

        self.inv_hover = HoverPreviewBehavior(
            self.chest_tree, self.image_service, lambda id, item: self.category
        )

    def load_save_data(self, save_data: SaveData):
        self.save_data = save_data
        self.refresh_chest_tree()

    def refresh_chest_tree(self):
        self.chest_tree.clear()
        if not self.save_data:
            return

        # 1. Get all containers that belong to the player
        player_containers = {}

        # The raw save data is needed to find container properties
        raw_save = self.save_data.custom_data.get("original_save", {})
        container_inventories = raw_save.get("Player", {}).get(
            "ContainerInventories", []
        )

        for container in container_inventories:
            if container.get("BelongsToPlayer"):
                container_id = container.get("ID")
                if container_id:
                    player_containers[container_id] = {
                        "name": container.get("Name", f"Chest {container_id}"),
                        "items": [],
                    }

        # 2. Group items by their container ID
        for item in self.save_data.inventory_items:
            if item.inventory_id in player_containers:
                player_containers[item.inventory_id]["items"].append(item)

        # 3. Populate the tree
        for container_id, container_data in player_containers.items():
            container_name = container_data["name"]

            container_item = CustomQTreeWidgetItem(self.chest_tree)
            container_item.setText(0, f"{container_name} (ID: {container_id})")
            font = container_item.font(0)
            font.setBold(True)
            container_item.setFont(0, font)

            for inv_item in container_data["items"]:
                game_item = self.collection.get_item(inv_item.item_id)
                item_name = (
                    game_item.name
                    if game_item
                    else f"Unknown Item (ID: {inv_item.item_id})"
                )

                tree_item = CustomQTreeWidgetItem(container_item)
                tree_item.setText(0, item_name)
                tree_item.setText(1, str(inv_item.amount))

                # Store the PlayerInventoryItem for editing
                tree_item.setData(0, Qt.ItemDataRole.UserRole, inv_item)

        self.chest_tree.expandAll()

    def edit_item_amount(self):
        selected_items = self.chest_tree.selectedItems()
        if not selected_items:
            return

        editable_items = []
        for item in selected_items:
            # Only edit child items (actual items), not top-level containers
            if item.parent():
                inv_item = item.data(0, Qt.ItemDataRole.UserRole)
                if inv_item:
                    editable_items.append((item, inv_item))

        if not editable_items:
            return

        default_val = editable_items[0][1].amount
        prompt = (
            f"Enter amount for {len(editable_items)} items:"
            if len(editable_items) > 1
            else "Enter new amount:"
        )

        val, ok = QInputDialog.getInt(
            self, "Edit Amount", prompt, value=default_val, min=1, max=9999
        )

        if ok:
            for tree_item, inv_item in editable_items:
                inv_item.amount = val
                tree_item.setText(1, str(val))

            self.data_changed.emit()
            logger.info(f"Updated amount to {val} for {len(editable_items)} items.")

    def add_all_items(self):
        # This action might not be relevant for this view.
        pass

    def clear_all_items(self):
        # This action might not be relevant for this view.
        pass

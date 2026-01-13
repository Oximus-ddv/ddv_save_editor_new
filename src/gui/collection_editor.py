"""
Collection editor frame for editing game collections
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
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..models.game_item import SaveData, GameDatabase, GameItem
from ..services.save_service import SaveFileService


logger = logging.getLogger(__name__)


class CollectionEditorFrame(QWidget):
    """Frame for editing collections"""

    def __init__(
        self, parent, save_service: SaveFileService, game_database: GameDatabase
    ):
        super().__init__(parent)

        self.save_service = save_service
        self.game_database = game_database
        self.save_data: Optional[SaveData] = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI for the collection editor"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Collections</b>"))
        layout.addLayout(header_layout)

        # Tree widget for collections
        self.collection_tree = QTreeWidget()
        self.collection_tree.setHeaderLabels(
            ["Collection / Item", "Collected", "Locked"]
        )
        self.collection_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.collection_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.collection_tree.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        layout.addWidget(self.collection_tree)

        # Buttons
        button_layout = QHBoxLayout()
        complete_all_btn = QPushButton("Complete All Collections")
        complete_all_btn.clicked.connect(self.complete_all_collections)
        button_layout.addWidget(complete_all_btn)

        lock_all_btn = QPushButton("Lock All")
        lock_all_btn.clicked.connect(self.lock_all_collections)
        button_layout.addWidget(lock_all_btn)

        unlock_all_btn = QPushButton("Unlock All")
        unlock_all_btn.clicked.connect(self.unlock_all_collections)
        button_layout.addWidget(unlock_all_btn)

        layout.addLayout(button_layout)

    def load_save_data(self, save_data: SaveData):
        """Load save data into the collection editor"""
        self.save_data = save_data
        self.refresh_collection_tree()

    def refresh_collection_tree(self):
        """Refresh the collection tree from save data"""
        self.collection_tree.clear()
        if not self.save_data:
            return

        collection_sets = self.save_data.collection_sets
        if not collection_sets:
            return

        for set_data in collection_sets:
            set_name = set_data.get("Name", "Unknown Collection")
            if "Entries" not in set_data:
                continue

            set_item = QTreeWidgetItem(self.collection_tree)
            set_item.setText(0, set_name)

            for entry in set_data["Entries"]:
                item_id = entry.get("ItemId")
                if not item_id:
                    continue

                item = self.get_item_from_db(item_id)
                item_name = item.name if item else "Unknown Item"

                child_item = QTreeWidgetItem(set_item)
                child_item.setText(0, f"{item_name} ({item_id})")

                is_collected = "Yes" if entry.get("IsCollected", False) else "No"
                is_locked = "Yes" if entry.get("IsLocked", False) else "No"

                child_item.setText(1, is_collected)
                child_item.setText(2, is_locked)

                if entry.get("IsCollected", False):
                    child_item.setForeground(1, QColor("green"))
                else:
                    child_item.setForeground(1, QColor("red"))

                if entry.get("IsLocked", False):
                    child_item.setForeground(2, QColor("green"))
                else:
                    child_item.setForeground(2, QColor("red"))

        self.collection_tree.expandAll()

        for i in range(self.collection_tree.columnCount()):
            self.collection_tree.resizeColumnToContents(i)

    def get_item_from_db(self, item_id: int) -> Optional[GameItem]:
        for collection in self.game_database.collections.values():
            item = collection.get_item(item_id)
            if item:
                return item
        return None

    def complete_all_collections(self):
        """Mark all items in all collections as collected and add missing items"""
        if not self.save_data or not self.game_database:
            return

        all_item_ids = {
            item.id
            for col in self.game_database.collections.values()
            for item in col.items.values()
        }

        for set_data in self.save_data.collection_sets:
            if "Entries" in set_data:
                existing_item_ids = {entry["ItemId"] for entry in set_data["Entries"]}

                # Mark existing as collected
                for entry in set_data["Entries"]:
                    entry["IsCollected"] = True

                # Add missing items
                missing_item_ids = all_item_ids - existing_item_ids
                for item_id in missing_item_ids:
                    # We need to figure out which collection set this item belongs to.
                    # For now, we will add it to all of them, which is not correct.
                    # This needs to be improved.
                    set_data["Entries"].append(
                        {"ItemId": item_id, "IsCollected": True, "IsLocked": False}
                    )

        self.refresh_collection_tree()

    def lock_all_collections(self):
        """Lock all items in all collections"""
        if not self.save_data:
            return

        for set_data in self.save_data.collection_sets:
            if "Entries" in set_data:
                for entry in set_data["Entries"]:
                    entry["IsLocked"] = True

        self.refresh_collection_tree()

    def unlock_all_collections(self):
        """Unlock all items in all collections"""
        if not self.save_data:
            return

        for set_data in self.save_data.collection_sets:
            if "Entries" in set_data:
                for entry in set_data["Entries"]:
                    entry["IsLocked"] = False

        self.refresh_collection_tree()

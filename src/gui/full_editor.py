"""
Full JSON editor window for DDV Save Editor with key-value-description format
"""

import json
import logging
from typing import Optional, Dict, Any, Callable

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QMessageBox,
    QDialogButtonBox,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor

from ..services.dict_service import DictDataService

logger = logging.getLogger(__name__)


class FullEditorWindow(QDialog):
    """Window for viewing and editing the full save file in key-value-description format"""

    def __init__(self, parent, dict_service: DictDataService):
        super().__init__(parent)
        self.setWindowTitle("Full Editor")
        self.resize(1000, 600)

        self.dict_service = dict_service

        # Make window modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Create toolbar
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        # Search
        toolbar.addWidget(QLabel("Find:"))
        self.search_edit = QLineEdit()
        self.search_edit.setMinimumWidth(300)
        toolbar.addWidget(self.search_edit)

        # Add search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)
        toolbar.addWidget(self.search_button)

        # Add stretch to push everything to the left
        toolbar.addStretch()

        # Bind Enter key to search
        self.search_edit.returnPressed.connect(self._on_search)

        # Create tree view
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])

        # Set column widths
        self.tree.setColumnWidth(0, 600)  # Key column
        self.tree.setColumnWidth(1, 300)  # Value column

        layout.addWidget(self.tree)

        # Store all items in memory for faster searching
        self.all_items = []
        self.filtered_items = []

        # Double-click to edit
        self.tree.itemDoubleClicked.connect(self._on_double_click)

        # Store callback
        self.on_modified_callback: Optional[Callable] = None

        # Dictionary to store the full paths of items
        self.item_paths = {}

    def load_json(self, data: Dict[str, Any]):
        """Load JSON data into the tree"""
        # Clear existing data
        self.all_items.clear()
        self.filtered_items.clear()
        self.item_paths.clear()
        self.tree.clear()

        # Show loading cursor
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        QTimer.singleShot(0, lambda: self._load_json_data(data))

    def _load_json_data(self, data: Dict[str, Any]):
        """Load JSON data in a separate function to avoid blocking the UI"""
        try:
            # Load game database once
            game_db = self.dict_service.load_game_database()

            # Flatten the JSON structure first
            flat_data = {}
            self._flatten_json(data, "", flat_data)

            # Pre-process all items
            for key, value in flat_data.items():
                self.all_items.append((key, str(value)))

            # Sort items for consistent display
            self.all_items.sort(key=lambda x: x[0])  # Sort by key
            self.filtered_items = self.all_items.copy()

            # Add items in batches
            self._display_items()

        finally:
            self.unsetCursor()

    def _flatten_json(self, data: Any, prefix: str, result: Dict[str, Any]) -> None:
        """Convert nested JSON structure to flat key-value pairs"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._flatten_json(value, new_key, result)
                else:
                    result[new_key] = value
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_key = f"{prefix}[{i}]"
                if isinstance(value, (dict, list)):
                    self._flatten_json(value, new_key, result)
                else:
                    result[new_key] = value
        else:
            result[prefix] = data

    def _get_description(self, path: str) -> str:
        """Get description for a path"""
        # Try to get item name from dictionary service
        if path.endswith("ItemID"):
            try:
                item = self.tree.currentItem()
                if item:
                    item_id = int(item.text(1))  # Value is in column 1
                    item = self.dict_service.get_item_by_id(item_id)
                    if item:
                        return item.name
            except:
                pass
        return ""

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click to edit value"""
        if column != 1:  # Only allow editing values
            return

        path = self.item_paths.get(id(item))
        if not path:
            return

        # Create edit dialog
        dialog = EditValueDialog(self, path, item.text(1))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the tree
            item.setText(1, str(dialog.result))

            # Update description if it's an item ID
            if path.endswith("ItemID"):
                try:
                    item_id = int(dialog.result)
                    game_item = self.dict_service.get_item_by_id(item_id)
                    if game_item:
                        item.setToolTip(1, game_item.name)
                except:
                    pass

            # Notify that data was modified
            if self.on_modified_callback:
                self.on_modified_callback()

    def _display_items(self):
        """Display the current filtered items in the tree"""
        # Clear existing items
        self.tree.clear()

        # Add items in batches
        batch_size = 1000
        for i in range(0, len(self.filtered_items), batch_size):
            batch = self.filtered_items[i : i + batch_size]
            for key, value in batch:
                item = QTreeWidgetItem([key, value])
                self.tree.addTopLevelItem(item)
                self.item_paths[id(item)] = key  # Store key for editing

            # Process events periodically
            if i % (batch_size * 5) == 0:
                QTimer.singleShot(0, lambda: None)

    def _on_search(self):
        """Handle search button click or Enter key"""
        search_text = self.search_edit.text().lower()

        # Disable search controls during search
        self.search_button.setEnabled(False)
        self.search_edit.setEnabled(False)
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))

        try:
            if not search_text:
                # If search is empty, show all items
                self.filtered_items = self.all_items.copy()
            else:
                # Filter items
                self.filtered_items = [
                    item
                    for item in self.all_items
                    if search_text in item[0].lower()  # key
                    or search_text in item[1].lower()  # value
                ]

            # Display filtered items
            self._display_items()

            # Select and scroll to first match if any
            if self.filtered_items:
                first_item = self.tree.topLevelItem(0)
                if first_item:
                    self.tree.setCurrentItem(first_item)
                    self.tree.scrollToItem(first_item)

        finally:
            # Re-enable search controls
            self.search_button.setEnabled(True)
            self.search_edit.setEnabled(True)
            self.unsetCursor()
            self.search_edit.setFocus()

    def get_json_data(self) -> Dict[str, Any]:
        """Convert the current tree view back to a JSON object"""
        result = {}

        def process_path(path: str, value: str) -> None:
            """Process a path and set the value in the result dictionary"""
            parts = path.split(".")
            current = result

            for i, part in enumerate(parts[:-1]):
                # Handle array indices
                if "[" in part:
                    name = part[: part.index("[")]
                    index = int(part[part.index("[") + 1 : part.index("]")])

                    if name not in current:
                        current[name] = []
                    while len(current[name]) <= index:
                        current[name].append({})
                    current = current[name][index]
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            # Handle the final part
            last_part = parts[-1]
            if "[" in last_part:
                name = last_part[: last_part.index("[")]
                index = int(last_part[last_part.index("[") + 1 : last_part.index("]")])

                if name not in current:
                    current[name] = []
                while len(current[name]) <= index:
                    current[name].append(None)
                current[name][index] = self._convert_value(value)
            else:
                current[last_part] = self._convert_value(value)

        # Process all visible items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            path = self.item_paths[id(item)]
            value = item.text(1)
            process_path(path, value)

        return result

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Try to convert to number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Check for boolean
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # Check for null
        if value.lower() == "null":
            return None

        # Default to string
        return value


class EditValueDialog(QDialog):
    """Dialog for editing values"""

    def __init__(self, parent, path: str, current_value: str):
        super().__init__(parent)
        self.setWindowTitle("Edit Value")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.result = None

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Show path
        layout.addWidget(QLabel(f"Path: {path}"))

        # Value entry
        layout.addWidget(QLabel("Value:"))
        self.entry = QLineEdit()
        self.entry.setText(current_value)
        self.entry.selectAll()
        layout.addWidget(self.entry)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Center dialog
        self.setGeometry(
            parent.x() + parent.width() // 3,
            parent.y() + parent.height() // 3,
            300,
            150,
        )

    def _on_ok(self):
        """Save the edited value"""
        self.result = self.entry.text()
        self.accept()

"""
JSON Viewer and Editor window for DDV Save Editor
"""
import json
import logging
from typing import Optional, Dict, Any, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QFrame,
    QMessageBox, QDialogButtonBox, QWidget, QSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from ..services.augmentation_service import add_item_to_save

logger = logging.getLogger(__name__)


class JsonTreeWidget(QTreeWidget):
    """Custom tree widget for JSON data"""
    
    jsonModified = pyqtSignal()  # Signal emitted when JSON is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure columns
        self.setColumnCount(3)
        self.setHeaderLabels(["Key", "Value", "Type"])
        
        # Set column resizing
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Key
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Value
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Type
        
        # Double-click to edit
        self.itemDoubleClicked.connect(self._on_double_click)
    
    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click to edit value"""
        if column != 1:  # Only allow editing values
            return
        
        # Get current values
        key = item.text(0)
        value = item.text(1)
        type_name = item.text(2)
        
        # Don't edit if it's a container (dict/list)
        if type_name in ("dict", "list"):
            return
        
        # Create edit dialog
        dialog = EditValueDialog(self, key, value, type_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the tree
            item.setText(1, str(dialog.result))
            # Notify that JSON was modified
            self.jsonModified.emit()


class AddItemDialog(QDialog):
    """Dialog for adding items to the inventory"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Item")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.result = None
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Item ID entry
        layout.addWidget(QLabel("Item ID:"))
        self.id_spinbox = QSpinBox()
        self.id_spinbox.setRange(1, 999999999)
        layout.addWidget(self.id_spinbox)
        
        # Amount entry
        layout.addWidget(QLabel("Amount:"))
        self.amount_spinbox = QSpinBox()
        self.amount_spinbox.setRange(1, 999999999)
        self.amount_spinbox.setValue(1)
        layout.addWidget(self.amount_spinbox)
        
        # Inventory ID entry
        layout.addWidget(QLabel("Inventory ID (optional):"))
        self.inventory_edit = QLineEdit()
        layout.addWidget(self.inventory_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Center dialog
        self.setGeometry(
            parent.x() + parent.width()//3,
            parent.y() + parent.height()//3,
            300,
            200
        )
    
    def _on_ok(self):
        """Validate and save the new item"""
        try:
            # Get values
            item_id = self.id_spinbox.value()
            amount = self.amount_spinbox.value()
            inventory_id = self.inventory_edit.text().strip()
            
            self.result = {
                'item_id': item_id,
                'amount': amount,
                'inventory_id': inventory_id if inventory_id else None
            }
            
            self.accept()
            
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Invalid Input",
                str(e)
            )


class EditValueDialog(QDialog):
    """Dialog for editing JSON values"""
    
    def __init__(self, parent, key: str, value: str, type_name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Edit {key}")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.result = None
        self.type_name = type_name
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Value entry
        layout.addWidget(QLabel(f"Enter new value ({type_name}):"))
        self.entry = QLineEdit()
        self.entry.setText(value)
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
            parent.x() + parent.width()//3,
            parent.y() + parent.height()//3,
            300,
            150
        )
    
    def _on_ok(self):
        """Validate and save the new value"""
        try:
            value = self.entry.text()
            
            # Convert value based on type
            if self.type_name == "number":
                if "." in value:
                    self.result = float(value)
                else:
                    self.result = int(value)
            elif self.type_name == "boolean":
                self.result = value.lower() == "true"
            elif self.type_name == "null":
                self.result = None
            else:
                self.result = value
            
            self.accept()
            
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Invalid Value",
                f"Could not convert value to {self.type_name}: {str(e)}"
            )


class JsonViewerWindow(QDialog):
    """Window for viewing and editing JSON data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Viewer")
        self.resize(800, 600)
        
        # Make window modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create toolbar
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        
        # Add Item button
        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self._add_item_dialog)
        toolbar.addWidget(add_btn)
        
        # Search
        toolbar.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_edit)
        
        # Expand/Collapse buttons
        expand_btn = QPushButton("Expand All")
        expand_btn.clicked.connect(self._expand_all)
        toolbar.addWidget(expand_btn)
        
        collapse_btn = QPushButton("Collapse All")
        collapse_btn.clicked.connect(self._collapse_all)
        toolbar.addWidget(collapse_btn)
        
        # Create tree widget
        self.tree = JsonTreeWidget()
        layout.addWidget(self.tree)
        
        # Connect signals
        self.tree.jsonModified.connect(self._on_json_modified)
        
        # Store callback
        self.on_modified_callback: Optional[Callable] = None
    
    def load_json(self, data: Dict[str, Any]):
        """Load JSON data into the tree"""
        # Clear existing items
        self.tree.clear()
        
        # Add root item
        root = QTreeWidgetItem(["root", "", "dict"])
        self.tree.addTopLevelItem(root)
        
        # Recursively add items
        self._add_json_items(root, data)
        
        # Expand root
        root.setExpanded(True)
    
    def _add_json_items(self, parent: QTreeWidgetItem, data: Any):
        """Recursively add JSON items to the tree"""
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem([str(key), "", self._get_type_name(value)])
                parent.addChild(item)
                if isinstance(value, (dict, list)):
                    self._add_json_items(item, value)
                else:
                    item.setText(1, str(value))
        
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QTreeWidgetItem([str(i), "", self._get_type_name(value)])
                parent.addChild(item)
                if isinstance(value, (dict, list)):
                    self._add_json_items(item, value)
                else:
                    item.setText(1, str(value))
    
    def _get_type_name(self, value: Any) -> str:
        """Get type name for a value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, list):
            return "list"
        elif value is None:
            return "null"
        else:
            return type(value).__name__
    
    def _on_search(self, text: str):
        """Handle search text changes"""
        search_text = text.lower()
        
        def process_item(item: QTreeWidgetItem) -> bool:
            # Check current item
            item_matches = any(
                search_text in item.text(col).lower()
                for col in range(item.columnCount())
            )
            
            # Check children
            child_matches = False
            for i in range(item.childCount()):
                if process_item(item.child(i)):
                    child_matches = True
            
            # Show/hide based on matches
            item.setHidden(not (item_matches or child_matches))
            
            return item_matches or child_matches
        
        # Process all top-level items
        for i in range(self.tree.topLevelItemCount()):
            process_item(self.tree.topLevelItem(i))
    
    def _expand_all(self):
        """Expand all items"""
        self.tree.expandAll()
    
    def _collapse_all(self):
        """Collapse all items"""
        self.tree.collapseAll()
    
    def _on_json_modified(self):
        """Handle JSON modifications"""
        if self.on_modified_callback:
            self.on_modified_callback()
    
    def _add_item_dialog(self):
        """Show dialog to add an item"""
        dialog = AddItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Get the current save data as a dictionary
                save_dict = self.get_json_data()
                if not save_dict:
                    QMessageBox.critical(self, "Error", "Could not get current save data")
                    return
                
                # Add the item using the augmentation service
                success = add_item_to_save(
                    save_dict,
                    item_id=dialog.result['item_id'],
                    amount=dialog.result['amount'],
                    inventory_id=dialog.result['inventory_id']
                )
                
                if success:
                    # Update the tree view with the new save data
                    self.load_json(save_dict)
                    
                    # Show success message
                    inventory_id = dialog.result['inventory_id'] or 'default'
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Added item {dialog.result['item_id']} with amount {dialog.result['amount']} to inventory {inventory_id}"
                    )
                else:
                    QMessageBox.critical(self, "Error", "Failed to add item to save data")
                    
            except Exception as e:
                logger.error(f"Error adding item: {e}")
                QMessageBox.critical(self, "Error", f"Failed to add item: {str(e)}")
    
    def get_json_data(self) -> Dict[str, Any]:
        """Convert the current tree view back to a JSON object"""
        def process_item(item: QTreeWidgetItem) -> Any:
            type_name = item.text(2)  # Type is in column 2
            
            if type_name in ("dict", "list"):
                children = [item.child(i) for i in range(item.childCount())]
                if type_name == "dict":
                    return {
                        child.text(0): process_item(child)
                        for child in children
                    }
                else:  # list
                    return [process_item(child) for child in children]
            else:
                # Convert value based on type
                value = item.text(1)  # Value is in column 1
                if type_name == "number":
                    return float(value) if "." in value else int(value)
                elif type_name == "boolean":
                    return value.lower() == "true"
                elif type_name == "null":
                    return None
                else:
                    return value
        
        # Start with root's children (skip root itself)
        root = self.tree.topLevelItem(0)
        return process_item(root)
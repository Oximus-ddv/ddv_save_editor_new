"""
JSON Viewer and Editor window for DDV Save Editor
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
    QSpinBox,
    QHeaderView,
    QStackedWidget,
    QApplication,
    QGraphicsOpacityEffect,
    QStackedLayout,
    QSizePolicy,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
    QElapsedTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import QPixmap, QColor

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Key
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Value
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Type

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

    def _on_ok(self):
        """Validate and save the new item"""
        try:
            # Get values
            item_id = self.id_spinbox.value()
            amount = self.amount_spinbox.value()
            inventory_id = self.inventory_edit.text().strip()

            self.result = {
                "item_id": item_id,
                "amount": amount,
                "inventory_id": inventory_id if inventory_id else None,
            }

            self.accept()

        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", str(e))


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
                f"Could not convert value to {self.type_name}: {str(e)}",
            )


class JsonViewerWindow(QDialog):
    """Window for viewing and editing JSON data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Viewer")

        # Make window modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.loading_timer = QElapsedTimer()
        self.tree_generator = None

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

        # Create stacked widget for loading screen and tree view
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # --- Create loading widget ---
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(
            self.loading_widget
        )  # Use QVBoxLayout directly on loading_widget

        # Set background image via stylesheet
        pixmap_path = "images/json_loading.png"
        self.loading_widget.setStyleSheet(
            f"""
            QWidget#loading_widget {{
                background-image: url({pixmap_path});
                background-repeat: no-repeat;
                background-position: center;
                background-size: cover; /* Scale to cover the entire widget */
            }}
        """
        )
        self.loading_widget.setObjectName(
            "loading_widget"
        )  # Set object name for stylesheet targeting

        loading_layout.addStretch()
        self.loading_status_label = QLabel("Initializing...")
        self.loading_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_status_label.setStyleSheet(
            "font-size: 16pt; color: white; background-color: rgba(0,0,0,150); padding: 10px; border-radius: 5px;"
        )
        loading_layout.addWidget(self.loading_status_label)
        loading_layout.addStretch()

        self.stacked_widget.addWidget(self.loading_widget)

        # Animation for the status label
        self.opacity_effect = QGraphicsOpacityEffect(self.loading_status_label)
        self.loading_status_label.setGraphicsEffect(self.opacity_effect)
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.3)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setLoopCount(-1)
        self.animation.setDirection(QPropertyAnimation.Direction.Forward)

        # --- Create tree widget ---
        self.tree = JsonTreeWidget()
        self.stacked_widget.addWidget(self.tree)

        # Connect signals
        self.tree.jsonModified.connect(self._on_json_modified)

        # Store callback
        self.on_modified_callback: Optional[Callable] = None

    def load_json(self, data: Dict[str, Any]):
        """Starts the non-blocking process of loading JSON data into the tree."""
        self.loading_status_label.setText("Preparing to load JSON data...")
        self.stacked_widget.setCurrentWidget(self.loading_widget)
        self.animation.start()
        self.loading_timer.start()

        # Use a timer to allow the loading screen to show before starting the population
        QTimer.singleShot(100, lambda: self._start_population(data))

    def _start_population(self, data: Dict[str, Any]):
        """Sets up the generator and starts the chunked processing."""
        self.loading_status_label.setText("Building tree view...")
        self.tree.clear()

        root_item = QTreeWidgetItem(["root", "", "dict"])
        self.tree.addTopLevelItem(root_item)

        self.tree_generator = self._add_json_items_iterative(root_item, data)
        self._process_next_chunk()

    def _process_next_chunk(self):
        """Processes one chunk of the JSON tree generator."""
        try:
            # Process a chunk of items until the generator yields
            next(self.tree_generator)
            # Schedule the next chunk, allowing the event loop to run
            QTimer.singleShot(0, self._process_next_chunk)
        except StopIteration:
            # Finished
            self._finish_population()

    def _finish_population(self):
        """Finalizes the UI after the tree is populated."""
        self.tree.topLevelItem(0).setExpanded(True)
        for i in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(i)
        elapsed_time = self.loading_timer.elapsed()
        logger.info(f"JSON tree populated in {elapsed_time} ms.")
        self.animation.stop()
        self.stacked_widget.setCurrentWidget(self.tree)

    def _add_json_items_iterative(self, root_item, data):
        """Iteratively and non-blockingly populates the tree using a generator."""
        color_map = {
            "string": QColor("#a3e9a4"),
            "number": QColor("#569cd6"),
            "boolean": QColor("#ce9178"),
            "null": QColor("#c586c0"),
        }
        stack = [(root_item, data)]
        nodes_processed = 0

        while stack:
            parent_item, current_data = stack.pop()

            items_to_add = []
            if isinstance(current_data, dict):
                items_to_add = reversed(list(current_data.items()))
            elif isinstance(current_data, list):
                items_to_add = reversed(list(enumerate(current_data)))

            for key, value in items_to_add:
                type_name = self._get_type_name(value)
                item = QTreeWidgetItem([str(key), "", type_name])

                if type_name in color_map:
                    item.setForeground(1, color_map[type_name])
                    item.setForeground(2, color_map[type_name])

                parent_item.addChild(item)

                if isinstance(value, (dict, list)):
                    stack.append((item, value))
                else:
                    item.setText(1, str(value))

                nodes_processed += 1
                if nodes_processed % 200 == 0:  # Yield every 200 nodes
                    yield

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
            item_matches = any(
                search_text in item.text(col).lower()
                for col in range(item.columnCount())
            )
            child_matches = False
            for i in range(item.childCount()):
                if process_item(item.child(i)):
                    child_matches = True

            item.setHidden(not (item_matches or child_matches))
            return item_matches or child_matches

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
                save_dict = self.get_json_data()
                if not save_dict:
                    QMessageBox.critical(
                        self, "Error", "Could not get current save data"
                    )
                    return

                success = add_item_to_save(
                    save_dict,
                    item_id=dialog.result["item_id"],
                    amount=dialog.result["amount"],
                    inventory_id=dialog.result["inventory_id"],
                )

                if success:
                    self.load_json(save_dict)
                    inventory_id = dialog.result["inventory_id"] or "default"
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Added item {dialog.result['item_id']} with amount {dialog.result['amount']} to inventory {inventory_id}",
                    )
                else:
                    QMessageBox.critical(
                        self, "Error", "Failed to add item to save data"
                    )

            except Exception as e:
                logger.error(f"Error adding item: {e}")
                QMessageBox.critical(self, "Error", f"Failed to add item: {str(e)}")

    def get_json_data(self) -> Dict[str, Any]:
        """Convert the current tree view back to a JSON object"""

        def process_item(item: QTreeWidgetItem) -> Any:
            type_name = item.text(2)
            if type_name in ("dict", "list"):
                children = [item.child(i) for i in range(item.childCount())]
                if type_name == "dict":
                    return {child.text(0): process_item(child) for child in children}
                else:
                    return [process_item(child) for child in children]
            else:
                value = item.text(1)
                if type_name == "number":
                    return float(value) if "." in value else int(value)
                elif type_name == "boolean":
                    return value.lower() == "true"
                elif type_name == "null":
                    return None
                else:
                    return value

        root = self.tree.topLevelItem(0)
        return process_item(root)

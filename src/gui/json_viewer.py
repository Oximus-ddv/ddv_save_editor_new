"""
JSON Viewer and Editor window for DDV Save Editor (PyQt6)
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton, QHBoxLayout, QDialogButtonBox, QHeaderView

class JsonViewer(QDialog):
    """Window for viewing and editing JSON data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("JSON Viewer")
        self.setMinimumSize(800, 600)

        self.layout = QVBoxLayout(self)
        
        self.setup_toolbar()
        self.setup_treeview()
        self.setup_buttons()

    def setup_toolbar(self):
        toolbar_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search...")
        self.expand_button = QPushButton("Expand All")
        self.collapse_button = QPushButton("Collapse All")

        toolbar_layout.addWidget(self.search_edit)
        toolbar_layout.addWidget(self.expand_button)
        toolbar_layout.addWidget(self.collapse_button)

        self.layout.addLayout(toolbar_layout)

    def setup_treeview(self):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.tree)

    def setup_buttons(self):
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

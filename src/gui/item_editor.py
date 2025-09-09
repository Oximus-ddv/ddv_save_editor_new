"""
Item editor frame for editing game items (PyQt6)
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton, QGroupBox, QSplitter, QLabel, QMenu, QInputDialog, QMessageBox, QTreeWidgetItemIterator
from PyQt6.QtCore import Qt
from ..models.game_item import GameDatabase, SaveData, ItemCategory, PlayerInventoryItem
from ..services.save_service import SaveFileService

class ItemEditor(QWidget):
    """Frame for editing items of a specific category"""
    
    def __init__(self, category: ItemCategory, game_database: GameDatabase, save_service: SaveFileService, parent=None):
        super().__init__(parent)
        self.category = category
        self.game_database = game_database
        self.save_service = save_service
        
        self.setup_ui()
        self.populate_available_items()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QHBoxLayout(self)
        splitter = QSplitter()

        # Left side - Available items
        available_items_widget = self.setup_available_items_panel()
        splitter.addWidget(available_items_widget)

        # Right side - Items in save
        save_items_widget = self.setup_save_items_panel()
        splitter.addWidget(save_items_widget)

        main_layout.addWidget(splitter)

    def setup_available_items_panel(self):
        """Setup the available items panel"""
        container = QGroupBox("Available Items")
        layout = QVBoxLayout()

        self.available_search_edit = QLineEdit()
        self.available_search_edit.setPlaceholderText("Search...")
        self.available_search_edit.textChanged.connect(self.filter_available_items)
        layout.addWidget(self.available_search_edit)

        self.available_list = QListWidget()
        self.available_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.available_list.customContextMenuRequested.connect(self.show_available_context_menu)
        layout.addWidget(self.available_list)

        add_button = QPushButton("Add Selected")
        add_button.clicked.connect(self.add_selected_items)
        layout.addWidget(add_button)

        container.setLayout(layout)
        return container

    def setup_save_items_panel(self):
        """Setup the items in save panel"""
        container = QGroupBox("Items in Save")
        layout = QVBoxLayout()

        self.save_search_edit = QLineEdit()
        self.save_search_edit.setPlaceholderText("Search...")
        self.save_search_edit.textChanged.connect(self.filter_save_items)
        layout.addWidget(self.save_search_edit)

        self.save_tree = QTreeWidget()
        self.save_tree.setColumnCount(3)
        self.save_tree.setHeaderLabels(["ID", "Name", "Amount"])
        self.save_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.save_tree.customContextMenuRequested.connect(self.show_save_context_menu)
        layout.addWidget(self.save_tree)

        button_layout = QHBoxLayout()
        edit_button = QPushButton("Edit Amount")
        edit_button.clicked.connect(self.edit_item_amount)
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_items)
        clear_all_button = QPushButton("Clear All")
        clear_all_button.clicked.connect(self.clear_all_items)
        add_all_button = QPushButton("Add All")
        add_all_button.clicked.connect(self.add_all_items)

        button_layout.addWidget(edit_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(clear_all_button)
        button_layout.addStretch()
        button_layout.addWidget(add_all_button)
        layout.addLayout(button_layout)

        container.setLayout(layout)
        return container

    def populate_available_items(self):
        self.available_list.clear()
        collection = self.game_database.get_collection(self.category)
        for item in sorted(collection.items.values(), key=lambda x: x.name):
            self.available_list.addItem(f"{item.name} ({item.id})")

    def filter_available_items(self, text):
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def filter_save_items(self, text):
        iterator = QTreeWidgetItemIterator(self.save_tree)
        while iterator.value():
            item = iterator.value()
            item.setHidden(text.lower() not in item.text(1).lower())
            iterator += 1

    def show_available_context_menu(self, position):
        menu = QMenu()
        copy_id_action = menu.addAction("Copy ID")
        copy_name_action = menu.addAction("Copy Name")
        add_to_save_action = menu.addAction("Add to Save")
        action = menu.exec(self.available_list.mapToGlobal(position))
        if action == add_to_save_action:
            self.add_selected_items()

    def show_save_context_menu(self, position):
        menu = QMenu()
        copy_id_action = menu.addAction("Copy ID")
        copy_name_action = menu.addAction("Copy Name")
        edit_amount_action = menu.addAction("Edit Amount")
        remove_action = menu.addAction("Remove")
        action = menu.exec(self.save_tree.mapToGlobal(position))
        if action == edit_amount_action:
            self.edit_item_amount()
        elif action == remove_action:
            self.remove_selected_items()

    def add_selected_items(self):
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            return

        save_data = self.save_service.current_save_data
        if not save_data:
            QMessageBox.warning(self, "No Save Data", "Please load a save file first.")
            return

        for list_item in selected_items:
            item_text = list_item.text()
            item_id = int(item_text.split('(')[-1].replace(')', ''))
            
            collection = self.game_database.get_collection(self.category)
            game_item = collection.get_item(item_id)

            if game_item:
                # Check if item already exists in save
                exists = False
                for inv_item in save_data.inventory_items:
                    if inv_item.item_id == game_item.id:
                        inv_item.amount += 1
                        exists = True
                        break
                
                if not exists:
                    new_item = PlayerInventoryItem(item_id=game_item.id, amount=1)
                    save_data.inventory_items.append(new_item)

        self.load_save_data(save_data, self.game_database)

    def add_all_items(self):
        reply = QMessageBox.question(self, 'Confirm', f"Add all available items to save?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            pass # Placeholder for add all items logic

    def remove_selected_items(self):
        pass # Placeholder

    def clear_all_items(self):
        reply = QMessageBox.question(self, 'Confirm', f"Remove all items from save?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            pass # Placeholder for clear all items logic

    def edit_item_amount(self):
        selected_items = self.save_tree.selectedItems()
        if not selected_items:
            return

        if len(selected_items) == 1:
            item = selected_items[0]
            item_name = item.text(1)
            current_amount = int(item.text(2))
            new_amount, ok = QInputDialog.getInt(self, "Edit Amount", f"Enter new amount for {item_name}:", current_amount, 0, 999999)
            if ok:
                item.setText(2, str(new_amount))
        else:
            new_amount, ok = QInputDialog.getInt(self, "Edit Amount", f"Enter new amount for {len(selected_items)} selected items:", 1, 0, 999999)
            if ok:
                for item in selected_items:
                    item.setText(2, str(new_amount))

    def load_save_data(self, save_data: SaveData, game_database: GameDatabase):
        self.save_tree.clear()
        if not save_data:
            return
        
        collection = game_database.get_collection(self.category)

        for item in save_data.inventory_items:
            game_item = collection.get_item(item.item_id)
            if game_item:
                tree_item = QTreeWidgetItem([str(item.item_id), game_item.name, str(item.amount)])
                self.save_tree.addTopLevelItem(tree_item)

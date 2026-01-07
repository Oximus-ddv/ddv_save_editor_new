
"""
Pet editor frame for editing pet information (PyQt6)
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QLineEdit, QSpinBox, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from ..services.pet_service import get_level_for_xp, get_xp_for_level, get_friendship_level_for_xp, get_xp_for_friendship_level
from ..models.game_item import ItemCategory, PetData

class PetEditor(QWidget):
    """Frame for editing pet information"""
    
    def __init__(self, save_service, game_database, parent=None):
        super().__init__(parent)
        self.save_service = save_service
        self.game_database = game_database
        self.selected_pet = None
        
        self.on_pet_selected_initial_call = False # Flag to prevent initial call

        self.setup_ui()

    def on_pet_selected(self, index):
        """Handle pet selection change"""
        if not self.save_service.current_save_data or index < 0:
            return
            
        # Prevent initial call from load_save_data
        if not self.on_pet_selected_initial_call:
            self.on_pet_selected_initial_call = True
            return

        self.selected_pet = self.save_service.current_save_data.pets[index]
        self.update_pet_data()
        
    def on_level_changed(self, level):
        """Handle companion level change"""
        if self.selected_pet:
            xp = get_xp_for_level(level)
            self.selected_pet.xp = xp
            self.xp_label.setText(str(xp))

    def on_friendship_level_changed(self, level):
        """Handle friendship level change"""
        if self.selected_pet:
            xp = get_xp_for_friendship_level(level)
            self.selected_pet.friendship_level = level
            self.selected_pet.xp = xp
            self.friendship_xp_label.setText(str(xp))

    def on_name_changed(self, name):
        """Handle name change"""
        if self.selected_pet:
            self.selected_pet.custom_name = name
            self.pet_combo.setItemText(self.pet_combo.currentIndex(), name)

    def update_pet_data(self):
        """Update the UI with the selected pet's data"""
        if not self.selected_pet:
            return

        self.name_edit.setText(self.selected_pet.custom_name or self.selected_pet.name)
        
        # Companion Level and XP
        level = get_level_for_xp(self.selected_pet.xp or 0)
        self.level_spinbox.setValue(level)
        self.xp_label.setText(str(self.selected_pet.xp or 0))

        # Friendship Level and XP
        friendship_level = get_friendship_level_for_xp(self.selected_pet.friendship_level or 0)
        self.friendship_level_spinbox.setValue(friendship_level)
        self.friendship_xp_label.setText(str(get_xp_for_friendship_level(friendship_level)))

    def on_pets_table_selection_changed(self):
        selected_rows = self.pets_table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            self.pet_combo.setCurrentIndex(row)

    def on_add_pet_button_clicked(self):
        selected_pet_index = self.add_pet_combo.currentIndex()
        if selected_pet_index < 0:
            return

        selected_pet_id = self.add_pet_combo.currentData()
        pet_item = self.game_database.get_item(ItemCategory.PETS, selected_pet_id)

        if pet_item and self.save_service.current_save_data:
            new_pet = PetData(
                pet_item_id=pet_item.id,
                name=pet_item.name,
                custom_name=None, # User can set custom name later
                friendship_level=1, # Default to level 1
                xp=0, # Default XP
                is_following=False
            )
            self.save_service.current_save_data.pets.append(new_pet)
            self.load_save_data(self.save_service.current_save_data, self.game_database) # Refresh UI

    def load_save_data(self, save_data, game_database):
        """Load pet data from save file"""
        self.save_service.current_save_data = save_data
        self.game_database = game_database
        
        self.pet_combo.clear()
        self.pets_table.setRowCount(0) # Clear table
        self.add_pet_combo.clear()

        if not save_data or not hasattr(save_data, 'pets'):
            return
            
        for i, pet in enumerate(save_data.pets):
            pet_item = self.game_database.get_item(ItemCategory.PETS, pet.pet_item_id)
            pet_name = pet_item.name if pet_item else pet.name
            
            # Populate pet_combo
            self.pet_combo.addItem(pet.custom_name or pet_name)

            # Populate pets_table
            row_position = self.pets_table.rowCount()
            self.pets_table.insertRow(row_position)
            self.pets_table.setItem(row_position, 0, QTableWidgetItem(pet.custom_name or pet_name))
            self.pets_table.setItem(row_position, 1, QTableWidgetItem(str(pet.friendship_level or 0)))
            self.pets_table.setItem(row_position, 2, QTableWidgetItem(str(pet.xp or 0)))
        
        if save_data.pets:
            # Set the flag to prevent on_pet_selected from being called initially
            self.on_pet_selected_initial_call = False
            self.on_pet_selected(0)

        # Populate add_pet_combo with all available pets from the dictionary
        if self.game_database and ItemCategory.PETS in self.game_database.collections:
            for pet_id, pet_item in self.game_database.collections[ItemCategory.PETS].items.items():
                self.add_pet_combo.addItem(pet_item.name, pet_item.id)
            
    def get_edited_pets(self):
        """Return the edited pet data"""
        return self.save_service.current_save_data.pets

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QHBoxLayout(self) # Changed to QHBoxLayout
        
        # Left side: Pet selection and details
        left_layout = QVBoxLayout()

        # Pet selection
        pet_selection_group = QGroupBox("Select Pet")
        pet_selection_layout = QFormLayout()
        self.pet_combo = QComboBox()
        pet_selection_layout.addRow(QLabel("Pet:"), self.pet_combo)
        pet_selection_group.setLayout(pet_selection_layout)
        left_layout.addWidget(pet_selection_group)
        
        # Pet details
        pet_details_group = QGroupBox("Pet Details")
        pet_details_layout = QFormLayout()
        self.name_edit = QLineEdit()
        
        self.level_spinbox = QSpinBox()
        self.level_spinbox.setRange(1, 10)
        self.xp_label = QLabel()

        self.friendship_level_spinbox = QSpinBox()
        self.friendship_level_spinbox.setRange(1, 10)
        self.friendship_xp_label = QLabel()
        
        pet_details_layout.addRow(QLabel("Name:"), self.name_edit)
        pet_details_layout.addRow(QLabel("Level:"), self.level_spinbox)
        pet_details_layout.addRow(QLabel("XP:"), self.xp_label)
        pet_details_layout.addRow(QLabel("Friendship Level:"), self.friendship_level_spinbox)
        pet_details_layout.addRow(QLabel("Friendship XP:"), self.friendship_xp_label)
        
        pet_details_group.setLayout(pet_details_layout)
        left_layout.addWidget(pet_details_group)
        
        left_layout.addStretch(1)
        main_layout.addLayout(left_layout)

        # Right side: List of all pets and Add New Pet section
        right_layout = QVBoxLayout()

        # All Pets in Save
        all_pets_group = QGroupBox("All Pets in Save")
        all_pets_layout = QVBoxLayout()
        self.pets_table = QTableWidget()
        self.pets_table.setColumnCount(3)
        self.pets_table.setHorizontalHeaderLabels(["Name", "Friendship Level", "XP"])
        self.pets_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pets_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pets_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pets_table.itemSelectionChanged.connect(self.on_pets_table_selection_changed)
        all_pets_layout.addWidget(self.pets_table)
        all_pets_group.setLayout(all_pets_layout)
        right_layout.addWidget(all_pets_group)

        # Add New Pet
        add_pet_group = QGroupBox("Add New Pet")
        add_pet_layout = QFormLayout()
        self.add_pet_combo = QComboBox()
        self.add_pet_button = QPushButton("Add Pet to Save")
        self.add_pet_button.clicked.connect(self.on_add_pet_button_clicked)
        add_pet_layout.addRow(QLabel("Select Pet:"), self.add_pet_combo)
        add_pet_layout.addRow(self.add_pet_button)
        add_pet_group.setLayout(add_pet_layout)
        right_layout.addWidget(add_pet_group)

        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.pet_combo.currentIndexChanged.connect(self.on_pet_selected)
        self.level_spinbox.valueChanged.connect(self.on_level_changed)
        self.friendship_level_spinbox.valueChanged.connect(self.on_friendship_level_changed)
        self.name_edit.textChanged.connect(self.on_name_changed)

"""
Currency editor frame for editing game currencies (PyQt6)
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QPushButton, QGroupBox, QHBoxLayout

class CurrencyEditor(QWidget):
    """Frame for editing game currencies"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Player info section
        self.setup_player_info_section(main_layout)
        
        # Currencies section
        self.setup_currencies_section(main_layout)
        
        # Action buttons
        self.setup_action_buttons(main_layout)

    def setup_player_info_section(self, parent_layout):
        """Setup player information section"""
        player_group = QGroupBox("Player Information")
        layout = QFormLayout()
        
        self.player_name_edit = QLineEdit()
        self.player_level_spinbox = QSpinBox()
        self.player_level_spinbox.setRange(1, 999)
        
        layout.addRow("Player Name:", self.player_name_edit)
        layout.addRow("Level:", self.player_level_spinbox)
        
        player_group.setLayout(layout)
        parent_layout.addWidget(player_group)

    def setup_currencies_section(self, parent_layout):
        """Setup currencies section"""
        currency_group = QGroupBox("Currencies")
        layout = QFormLayout()

        self.star_coins_spinbox = QSpinBox()
        self.dreamlight_spinbox = QSpinBox()
        self.daisy_coins_spinbox = QSpinBox()
        self.mist_spinbox = QSpinBox()
        self.pixel_dust_spinbox = QSpinBox()

        for spinbox in [self.star_coins_spinbox, self.dreamlight_spinbox, self.daisy_coins_spinbox, self.mist_spinbox, self.pixel_dust_spinbox]:
            spinbox.setRange(0, 2147483647)

        layout.addRow("Star Coins:", self.star_coins_spinbox)
        layout.addRow("Dreamlight:", self.dreamlight_spinbox)
        layout.addRow("Daisy Coins:", self.daisy_coins_spinbox)
        layout.addRow("Mist:", self.mist_spinbox)
        layout.addRow("Pixel Dust:", self.pixel_dust_spinbox)

        currency_group.setLayout(layout)
        parent_layout.addWidget(currency_group)

    def setup_action_buttons(self, parent_layout):
        """Setup action buttons"""
        button_layout = QHBoxLayout()
        
        self.max_all_button = QPushButton("Max All Currencies")
        self.reset_all_button = QPushButton("Reset All Currencies")
        self.apply_button = QPushButton("Apply Changes")
        
        button_layout.addWidget(self.max_all_button)
        button_layout.addWidget(self.reset_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        
        parent_layout.addLayout(button_layout)

    def get_edited_data(self, save_data):
        """Collects edited data from the UI and updates the SaveData object."""
        save_data.player_name = self.player_name_edit.text()
        save_data.player_level = self.player_level_spinbox.value()
        save_data.star_coins = self.star_coins_spinbox.value()
        save_data.dreamlight = self.dreamlight_spinbox.value()
        save_data.daisy_coins = self.daisy_coins_spinbox.value()
        save_data.mist = self.mist_spinbox.value()
        save_data.pixel_dust = self.pixel_dust_spinbox.value()
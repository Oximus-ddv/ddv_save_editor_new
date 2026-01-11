"""
Currency editor frame for editing game currencies
"""
from typing import Optional
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QGroupBox, QGridLayout, QFrame,
    QMessageBox, QToolTip
)
from PyQt6.QtCore import Qt, QPoint

from ..models.game_item import SaveData
from ..services.save_service import SaveFileService


logger = logging.getLogger(__name__)


class CurrencyEditorFrame(QWidget):
    """Frame for editing game currencies"""
    
    def __init__(self, parent, save_service: SaveFileService, danger_zone_enabled: bool = False):
        super().__init__(parent)
        
        self.save_service = save_service
        self.save_data: Optional[SaveData] = None
        self._danger_zone_enabled = danger_zone_enabled
        
        # Currency variables
        self.star_coins_spinbox = QSpinBox()
        self.dreamlight_spinbox = QSpinBox()
        self.daisy_coins_spinbox = QSpinBox()
        self.mist_spinbox = QSpinBox()
        self.pixel_dust_spinbox = QSpinBox()
        self.story_book_magic_spinbox = QSpinBox()
        self.moonstones_spinbox = QSpinBox()
        
        # Player info variables
        self.player_name_edit = QLineEdit()
        self.player_level_spinbox = QSpinBox()

        # Widgets to hide in danger zone
        self.moonstone_widgets = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Player info section
        self.setup_player_info_section(main_layout)
        
        # Currencies section
        self.setup_currencies_section(main_layout)
        
        # Action buttons
        self.setup_action_buttons(main_layout)

        # Set initial visibility
        self.set_danger_zone_mode(self._danger_zone_enabled)
    
    def set_danger_zone_mode(self, enabled: bool):
        """Show or hide widgets based on danger zone mode."""
        self._danger_zone_enabled = enabled
        for widget in self.moonstone_widgets:
            widget.setVisible(enabled)

    def setup_player_info_section(self, parent_layout):
        """Setup player information section"""
        player_group = QGroupBox("Player Information")
        player_layout = QGridLayout(player_group)
        
        # Player name
        player_layout.addWidget(QLabel("Player Name:"), 0, 0)
        # self.player_name_edit.setMinimumWidth(200)
        player_layout.addWidget(self.player_name_edit, 0, 1)
        
        # Player level
        player_layout.addWidget(QLabel("Level:"), 1, 0)
        self.player_level_spinbox.setRange(1, 999)
        # self.player_level_spinbox.setMinimumWidth(100)
        player_layout.addWidget(self.player_level_spinbox, 1, 1)
        
        parent_layout.addWidget(player_group)
    
    def setup_currencies_section(self, parent_layout):
        """Setup currencies section"""
        currency_group = QGroupBox("Currencies")
        self.currency_layout = QGridLayout(currency_group)
        
        # Currency definitions
        currencies = [
            ("Star Coins:", self.star_coins_spinbox, "Main currency for purchases"),
            ("Dreamlight:", self.dreamlight_spinbox, "Used for unlocking areas and features"),
            ("Daisy Coins:", self.daisy_coins_spinbox, "Special event currency"),
            ("Mist:", self.mist_spinbox, "Mystical realm currency"),
            ("Pixel Dust:", self.pixel_dust_spinbox, "Digital realm currency"),
            ("StoryBook Magic:", self.story_book_magic_spinbox, "Currency for Storybook content"),
        ]

        moonstone_currency = ("Moonstones:", self.moonstones_spinbox, "Premium currency (WARNING: May not work)")
        
        # Create currency editors
        for i, (label_text, spinbox, tooltip) in enumerate(currencies):
            # Label
            label = QLabel(label_text)
            label.setToolTip(tooltip)
            self.currency_layout.addWidget(label, i, 0)
            
            # SpinBox
            spinbox.setRange(0, 2147483647)
            # spinbox.setMinimumWidth(150)
            self.currency_layout.addWidget(spinbox, i, 1)
            
            # Max button
            max_btn = QPushButton("Max")
            # max_btn.setMaximumWidth(60)
            max_btn.clicked.connect(lambda checked, sb=spinbox: self.set_max_currency(sb))
            self.currency_layout.addWidget(max_btn, i, 2)
            
            # Reset button
            reset_btn = QPushButton("Reset")
            # reset_btn.setMaximumWidth(60)
            reset_btn.clicked.connect(lambda checked, sb=spinbox: sb.setValue(0))
            self.currency_layout.addWidget(reset_btn, i, 3)

        # Create Moonstone editor separately to manage visibility
        i = len(currencies)
        label = QLabel(moonstone_currency[0])
        label.setToolTip(moonstone_currency[2])
        self.currency_layout.addWidget(label, i, 0)
        self.moonstone_widgets.append(label)

        spinbox = moonstone_currency[1]
        spinbox.setRange(0, 2147483647)
        # spinbox.setMinimumWidth(150)
        self.currency_layout.addWidget(spinbox, i, 1)
        self.moonstone_widgets.append(spinbox)

        max_btn = QPushButton("Max")
        # max_btn.setMaximumWidth(60)
        max_btn.clicked.connect(lambda checked, sb=spinbox: self.set_max_currency(sb))
        self.currency_layout.addWidget(max_btn, i, 2)
        self.moonstone_widgets.append(max_btn)

        reset_btn = QPushButton("Reset")
        # reset_btn.setMaximumWidth(60)
        reset_btn.clicked.connect(lambda checked, sb=spinbox: sb.setValue(0))
        self.currency_layout.addWidget(reset_btn, i, 3)
        self.moonstone_widgets.append(reset_btn)
        
        parent_layout.addWidget(currency_group)
    
    def setup_action_buttons(self, parent_layout):
        """Setup action buttons"""
        button_layout = QHBoxLayout()
        
        max_all_btn = QPushButton("Max All Currencies")
        max_all_btn.clicked.connect(self.max_all_currencies)
        button_layout.addWidget(max_all_btn)
        
        reset_all_btn = QPushButton("Reset All Currencies")
        reset_all_btn.clicked.connect(self.reset_all_currencies)
        button_layout.addWidget(reset_all_btn)
        
        button_layout.addStretch()
        
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(self.apply_changes)
        button_layout.addWidget(apply_btn)
        
        parent_layout.addLayout(button_layout)
    
    def set_max_currency(self, spinbox: QSpinBox):
        """Set a currency to maximum value"""
        spinbox.setValue(2147483647)  # Max 32-bit signed integer
    
    def max_all_currencies(self):
        """Set all currencies to maximum"""
        max_value = 2147483647
        self.star_coins_spinbox.setValue(max_value)
        self.dreamlight_spinbox.setValue(max_value)
        self.daisy_coins_spinbox.setValue(max_value)
        self.mist_spinbox.setValue(max_value)
        self.pixel_dust_spinbox.setValue(max_value)
        self.story_book_magic_spinbox.setValue(max_value)
        self.moonstones_spinbox.setValue(max_value)
    
    def reset_all_currencies(self):
        """Reset all currencies to zero"""
        self.star_coins_spinbox.setValue(0)
        self.dreamlight_spinbox.setValue(0)
        self.daisy_coins_spinbox.setValue(0)
        self.mist_spinbox.setValue(0)
        self.pixel_dust_spinbox.setValue(0)
        self.story_book_magic_spinbox.setValue(0)
        self.moonstones_spinbox.setValue(0)
    
    def apply_changes(self):
        """Apply changes to save data"""
        if self.save_data:
            self.update_save_data()
            QMessageBox.information(self, "Success", "Currency changes applied!")
    
    def load_save_data(self, save_data: SaveData):
        """Load save data into the editor"""
        self.save_data = save_data
        
        # Load player info
        self.player_name_edit.setText(save_data.player_name)
        self.player_level_spinbox.setValue(save_data.player_level)
        
        # Load currencies
        self.star_coins_spinbox.setValue(save_data.star_coins)
        self.dreamlight_spinbox.setValue(save_data.dreamlight)
        self.daisy_coins_spinbox.setValue(save_data.daisy_coins)
        self.mist_spinbox.setValue(save_data.mist)
        self.pixel_dust_spinbox.setValue(save_data.pixel_dust)
        self.story_book_magic_spinbox.setValue(save_data.story_book_magic)
        self.moonstones_spinbox.setValue(save_data.moonstones)
    
    def update_save_data(self):
        """Update save data with current values"""
        if not self.save_data:
            return
        
        # Update player info
        self.save_data.player_name = self.player_name_edit.text()
        self.save_data.player_level = max(1, self.player_level_spinbox.value())
        
        # Update currencies
        self.save_data.star_coins = max(0, self.star_coins_spinbox.value())
        self.save_data.dreamlight = max(0, self.dreamlight_spinbox.value())
        self.save_data.daisy_coins = max(0, self.daisy_coins_spinbox.value())
        self.save_data.mist = max(0, self.mist_spinbox.value())
        self.save_data.pixel_dust = max(0, self.pixel_dust_spinbox.value())
        self.save_data.story_book_magic = max(0, self.story_book_magic_spinbox.value())
        self.save_data.moonstones = max(0, self.moonstones_spinbox.value())

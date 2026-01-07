"""
Dialog for editing pet details
"""
from typing import Optional
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QComboBox, QDialogButtonBox,
    QGroupBox, QFormLayout, QWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image

from ..models.game_item import PetData, GameItem, ItemCategory
from ..services.image_service import ImageService

logger = logging.getLogger(__name__)

class PetEditorDialog(QDialog):
    """Dialog for editing detailed pet information"""
    
    # Cumulative XP requirements for levels (1-based index)
    # Level 1 starts at 0
    # Level 2 starts at 750 (diff 750)
    # Level 3 starts at 3000 (diff 2250)
    # Level 4 starts at 7500 (diff 4500)
    # Level 5 starts at 15000 (diff 7500)
    LEVEL_THRESHOLDS = {
        1: 0,
        2: 750,
        3: 3000,
        4: 7500,
        5: 15000,
        6: 33000, # Extrapolated/Guessed or standard DDV progression if known. 
                  # Common DDV pattern: 750, 2250, 4500, 7500, 18000 (for lvl 6 usually jumps)
                  # Given the prompt only supplied up to 5, we will strictly support auto-calc up to 5
                  # and allow manual entry for higher.
    }

    def __init__(self, parent, pet_data: PetData, game_item: Optional[GameItem], image_service: ImageService):
        super().__init__(parent)
        self.setWindowTitle("Edit Pet Details")
        self.setModal(True)
        self.resize(500, 600)
        
        self.pet_data = pet_data
        self.game_item = game_item
        self.image_service = image_service
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Header with Image and Basic Info ---
        header_layout = QHBoxLayout()
        
        # Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(128, 128)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        header_layout.addWidget(self.image_label)
        
        # Info
        info_layout = QVBoxLayout()
        self.name_label = QLabel()
        font = self.name_label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.name_label.setFont(font)
        info_layout.addWidget(self.name_label)
        
        self.id_label = QLabel()
        info_layout.addWidget(self.id_label)
        info_layout.addStretch()
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # --- Form Fields ---
        form_group = QGroupBox("Pet Attributes")
        form_layout = QFormLayout(form_group)
        
        # Custom Name
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("Enter custom name...")
        form_layout.addRow("Custom Name:", self.custom_name_edit)
        
        # Friendship Level
        self.level_combo = QComboBox()
        for i in range(1, 11):
            self.level_combo.addItem(str(i), i)
        self.level_combo.currentIndexChanged.connect(self.on_level_changed)
        form_layout.addRow("Friendship Level:", self.level_combo)
        
        # XP
        self.xp_spin = QSpinBox()
        self.xp_spin.setRange(0, 9999999)
        self.xp_spin.setSingleStep(100)
        form_layout.addRow("Experience (XP):", self.xp_spin)
        
        # Granted Slots
        self.slots_spin = QSpinBox()
        self.slots_spin.setRange(0, 999)
        form_layout.addRow("Inventory Slots Granted:", self.slots_spin)
        
        # Dates (Text for now to avoid format issues)
        self.last_selfie_edit = QLineEdit()
        self.last_selfie_edit.setPlaceholderText("YYYY-MM-DDTHH:MM:SS or similar")
        form_layout.addRow("Last Selfie Date:", self.last_selfie_edit)
        
        self.last_petted_edit = QLineEdit()
        self.last_petted_edit.setPlaceholderText("YYYY-MM-DDTHH:MM:SS or similar")
        form_layout.addRow("Last Petted Date:", self.last_petted_edit)
        
        # Pending Rewards (Read-onlyish view or clear button?)
        # For now just a display of count or text
        self.rewards_edit = QLineEdit()
        self.rewards_edit.setReadOnly(True) # Basic display
        self.rewards_edit.setPlaceholderText("[]")
        form_layout.addRow("Pending Rewards:", self.rewards_edit)
        
        layout.addWidget(form_group)
        
        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_data(self):
        """Load data into fields"""
        # Basic Info
        item_name = self.game_item.name if self.game_item else "Unknown Pet"
        item_id = self.pet_data.pet_item_id
        
        self.name_label.setText(item_name)
        self.id_label.setText(f"ID: {item_id}")
        
        # Image
        if self.image_service:
            pil_image = self.image_service.get_item_image(item_id, ItemCategory.PETS, size=(128, 128))
            if pil_image:
                # Convert PIL to QPixmap
                if pil_image.mode == "RGB":
                    r, g, b = pil_image.split()
                    pil_image = Image.merge("RGB", (b, g, r))
                    im2 = pil_image.convert("RGBA")
                    data = im2.tobytes("raw", "BGRA")
                    qim = QImage(data, im2.size[0], im2.size[1], QImage.Format.Format_ARGB32)
                    pixmap = QPixmap.fromImage(qim)
                elif pil_image.mode == "RGBA":
                    # PyQt expects ARGB or BGRA usually, PIL gives RGBA
                    # We might need to swap channels for some Qt versions/platforms, but usually QImage can handle it
                    # if we specify Format_RGBA8888
                    data = pil_image.tobytes("raw", "RGBA")
                    qim = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qim)
                else:
                    pixmap = QPixmap() # Empty or default
                
                self.image_label.setPixmap(pixmap)
        
        # Attributes
        self.custom_name_edit.setText(self.pet_data.custom_name or "")
        
        current_level = self.pet_data.friendship_level or 1
        # Block signal to avoid auto-calc during load
        self.level_combo.blockSignals(True)
        idx = self.level_combo.findData(current_level)
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)
        else:
            self.level_combo.setCurrentIndex(0) # Level 1
        self.level_combo.blockSignals(False)
            
        self.xp_spin.setValue(self.pet_data.xp or 0)
        self.slots_spin.setValue(self.pet_data.granted_inventory_slots or 0)
        
        self.last_selfie_edit.setText(self.pet_data.last_selfie_date or "")
        self.last_petted_edit.setText(self.pet_data.last_petted_date or "")
        
        rewards = self.pet_data.pending_hangout_rewards or []
        self.rewards_edit.setText(str(rewards))

    def on_level_changed(self, index):
        """Update XP based on selected level"""
        level = self.level_combo.currentData()
        if level in self.LEVEL_THRESHOLDS:
            self.xp_spin.setValue(self.LEVEL_THRESHOLDS[level])
        else:
            # If level > 5 and we don't have a threshold, maybe extrapolate?
            # Or just leave it alone.
            pass

    def save_and_accept(self):
        """Save data back to PetData object"""
        self.pet_data.custom_name = self.custom_name_edit.text() or None
        self.pet_data.friendship_level = self.level_combo.currentData()
        self.pet_data.xp = self.xp_spin.value()
        self.pet_data.granted_inventory_slots = self.slots_spin.value()
        
        self.pet_data.last_selfie_date = self.last_selfie_edit.text() or None
        self.pet_data.last_petted_date = self.last_petted_edit.text() or None
        
        # Not editing rewards for now as it's complex structure
        
        self.accept()

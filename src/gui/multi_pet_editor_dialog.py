"""
Dialog for editing multiple pets at once
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QLabel,
)


class MultiPetEditorDialog(QDialog):
    """Dialog for bulk editing pet attributes."""

    def __init__(self, parent, num_pets: int):
        super().__init__(parent)
        self.setWindowTitle(f"Edit {num_pets} Pets")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        info_label = QLabel(
            "Set new values for the selected pets. Use 'Don't change' or -1 to keep existing values."
        )
        layout.addWidget(info_label)

        self.level_combo = QComboBox()
        self.level_combo.addItem("Don't change", -1)
        for i in range(1, 6):
            self.level_combo.addItem(str(i), i)
        form_layout.addRow("Friendship Level:", self.level_combo)

        self.xp_spin = QSpinBox()
        self.xp_spin.setRange(-1, 9999999)
        self.xp_spin.setSpecialValueText("Don't change")
        self.xp_spin.setValue(-1)
        form_layout.addRow("Experience (XP):", self.xp_spin)

        self.slots_spin = QSpinBox()
        self.slots_spin.setRange(-1, 999)
        self.slots_spin.setSpecialValueText("Don't change")
        self.slots_spin.setValue(-1)
        form_layout.addRow("Inventory Slots Granted:", self.slots_spin)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        """Returns a dict of values to be changed."""
        return {
            "level": self.level_combo.currentData(),
            "xp": self.xp_spin.value(),
            "slots": self.slots_spin.value(),
        }

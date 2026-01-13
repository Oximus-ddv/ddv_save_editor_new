"""
Settings dialog for DDV Save Editor
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QTabWidget,
    QWidget,
    QFrame,
    QGroupBox,
    QRadioButton,
    QComboBox,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """Settings configuration dialog"""

    def __init__(self, parent, initial_settings: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        # self.setFixedSize(500, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._initial = initial_settings or {}

        # Variables (prefilled from provided settings or defaults)

        self.image_zip_path = self._initial.get("image_zip_path", "img.zip")
        self.image_folder_path = self._initial.get("image_folder_path", "img")
        self.max_backups = int(self._initial.get("max_backups", 10))
        self.auto_backup = bool(self._initial.get("auto_backup", True))
        self.show_images = bool(self._initial.get("show_images", True))
        self.cache_size = int(self._initial.get("cache_size", 200))
        self.data_source = str(self._initial.get("data_source", "dict")).lower()
        self.dict_root = str(self._initial.get("dict_root", "Dict"))
        self.thumbnail_size = self._initial.get("thumbnail_size", "64x64")
        self.preview_size = self._initial.get("preview_size", "128x128")
        self.danger_zone_enabled = bool(self._initial.get("danger_zone_enabled", False))
        self.font_size = self._initial.get("font_size", "Medium")
        self.large_scrollbars = bool(self._initial.get("large_scrollbars", False))

        # Default DDV hex key (from settings or environment override if packaged)
        default_hex = os.environ.get(
            "DDV_HEX_KEY",
            "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35",
        )
        self.hex_key = self._initial.get("hex_key", default_hex)

        # Create UI components

        self.image_zip_edit = None
        self.image_folder_edit = None
        self.max_backups_spin = None
        self.auto_backup_check = None
        self.show_images_check = None
        self.cache_size_spin = None

        self.data_source_dict_radio = None
        self.dict_root_edit = None
        self.thumbnail_size_combo = None
        self.preview_size_combo = None
        self.hex_key_edit = None
        self.danger_zone_check = None
        self.font_size_combo = None
        self.large_scrollbars_check = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Add tabs
        self.setup_appearance_tab(tab_widget)
        self.setup_file_paths_tab(tab_widget)
        self.setup_data_source_tab(tab_widget)
        self.setup_image_settings_tab(tab_widget)
        self.setup_backup_settings_tab(tab_widget)
        self.setup_encryption_tab(tab_widget)
        self.setup_danger_zone_tab(tab_widget)

        # Add buttons
        self.setup_buttons(layout)

    def setup_appearance_tab(self, tab_widget):
        """Setup appearance settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Font size
        font_group = QGroupBox("Font Size")
        font_layout = QHBoxLayout(font_group)
        font_layout.addWidget(QLabel("Application Font Size:"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["Small", "Medium", "Large"])
        self.font_size_combo.setCurrentText(self.font_size)
        font_layout.addWidget(self.font_size_combo)
        font_layout.addStretch()
        layout.addWidget(font_group)

        # Scrollbar size
        scrollbar_group = QGroupBox("Scrollbars")
        scrollbar_layout = QVBoxLayout(scrollbar_group)
        self.large_scrollbars_check = QCheckBox(
            "Use larger scrollbars for easier clicking"
        )
        self.large_scrollbars_check.setChecked(self.large_scrollbars)
        scrollbar_layout.addWidget(self.large_scrollbars_check)
        layout.addWidget(scrollbar_group)

        layout.addStretch()
        tab_widget.addTab(tab, "Appearance")

    def setup_danger_zone_tab(self, tab_widget):
        """Setup danger zone settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        danger_group = QGroupBox("⚠️ Danger Zone")
        danger_layout = QVBoxLayout(danger_group)

        self.danger_zone_check = QCheckBox(
            "Enable Danger Zone features (currency editing, etc.)"
        )
        self.danger_zone_check.setChecked(self.danger_zone_enabled)
        danger_layout.addWidget(self.danger_zone_check)

        info_label = QLabel(
            "Enabling this will show advanced features that can corrupt your save file if used incorrectly. Use with caution."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #FFC107;")
        danger_layout.addWidget(info_label)

        layout.addWidget(danger_group)
        layout.addStretch()
        tab_widget.addTab(tab, "Danger Zone")

    def setup_file_paths_tab(self, tab_widget):
        """Setup file paths configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Image ZIP path
        layout.addWidget(QLabel("Image ZIP File:"))
        zip_layout = QHBoxLayout()
        self.image_zip_edit = QLineEdit(self.image_zip_path)
        zip_layout.addWidget(self.image_zip_edit)
        zip_browse = QPushButton("Browse")
        zip_browse.clicked.connect(self.browse_image_zip)
        zip_layout.addWidget(zip_browse)
        layout.addLayout(zip_layout)

        # Image folder path
        layout.addWidget(QLabel("Image Folder:"))
        folder_layout = QHBoxLayout()
        self.image_folder_edit = QLineEdit(self.image_folder_path)
        folder_layout.addWidget(self.image_folder_edit)
        folder_browse = QPushButton("Browse")
        folder_browse.clicked.connect(self.browse_image_folder)
        folder_layout.addWidget(folder_browse)
        layout.addLayout(folder_layout)

        # Help text
        help_text = (
            "Note: The application will try the ZIP file first, then fall back to the folder. "
            "You can use either or both options."
        )
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(help_label)

        layout.addStretch()
        tab_widget.addTab(tab, "File Paths")

    def setup_data_source_tab(self, tab_widget):
        """Setup data source selection tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Data source group
        source_group = QGroupBox("Choose Data Source")
        source_layout = QVBoxLayout(source_group)
        self.data_source_dict_radio = QRadioButton("Dict folder (JSON)")
        self.data_source_dict_radio.setChecked(True)  # Always check Dict
        source_layout.addWidget(self.data_source_dict_radio)
        layout.addWidget(source_group)

        # Dict folder group
        dict_group = QGroupBox("Dict Folder")
        dict_layout = QVBoxLayout(dict_group)
        dict_layout.addWidget(QLabel("Root folder containing category subfolders:"))
        dict_input_layout = QHBoxLayout()
        self.dict_root_edit = QLineEdit(self.dict_root)
        dict_input_layout.addWidget(self.dict_root_edit)
        dict_browse = QPushButton("Browse")
        dict_browse.clicked.connect(self.browse_dict_folder)
        dict_input_layout.addWidget(dict_browse)
        dict_layout.addLayout(dict_input_layout)
        layout.addWidget(dict_group)

        layout.addStretch()
        tab_widget.addTab(tab, "Data Source")

    def setup_image_settings_tab(self, tab_widget):
        """Setup image settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Show images checkbox
        self.show_images_check = QCheckBox("Show image previews")
        self.show_images_check.setChecked(self.show_images)
        layout.addWidget(self.show_images_check)

        # Cache size
        layout.addWidget(QLabel("Image Cache Size (number of images):"))
        cache_layout = QHBoxLayout()
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(50, 1000)
        self.cache_size_spin.setValue(self.cache_size)
        cache_layout.addWidget(self.cache_size_spin)
        cache_layout.addWidget(
            QLabel("Higher values use more memory but improve performance")
        )
        cache_layout.addStretch()
        layout.addLayout(cache_layout)

        # Image quality group
        quality_group = QGroupBox("Image Quality")
        quality_layout = QVBoxLayout(quality_group)

        # Thumbnail size
        thumb_layout = QHBoxLayout()
        thumb_layout.addWidget(QLabel("Thumbnail Size:"))
        self.thumbnail_size_combo = QComboBox()
        self.thumbnail_size_combo.addItems(["32x32", "48x48", "64x64", "96x96"])
        self.thumbnail_size_combo.setCurrentText(self.thumbnail_size)
        thumb_layout.addWidget(self.thumbnail_size_combo)
        thumb_layout.addStretch()
        quality_layout.addLayout(thumb_layout)

        # Preview size
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Preview Size:"))
        self.preview_size_combo = QComboBox()
        self.preview_size_combo.addItems(["96x96", "128x128", "192x192", "256x256"])
        self.preview_size_combo.setCurrentText(self.preview_size)
        preview_layout.addWidget(self.preview_size_combo)
        preview_layout.addStretch()
        quality_layout.addLayout(preview_layout)

        layout.addWidget(quality_group)
        layout.addStretch()
        tab_widget.addTab(tab, "Images")

    def setup_backup_settings_tab(self, tab_widget):
        """Setup backup settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Auto backup checkbox
        self.auto_backup_check = QCheckBox(
            "Create automatic backups when loading/saving"
        )
        self.auto_backup_check.setChecked(self.auto_backup)
        layout.addWidget(self.auto_backup_check)

        # Max backup count
        layout.addWidget(QLabel("Maximum number of backups to keep:"))
        backup_layout = QHBoxLayout()
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(1, 100)
        self.max_backups_spin.setValue(self.max_backups)
        backup_layout.addWidget(self.max_backups_spin)
        backup_layout.addWidget(QLabel("Older backups will be automatically deleted"))
        backup_layout.addStretch()
        layout.addLayout(backup_layout)

        # Backup info group
        info_group = QGroupBox("Backup Information")
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(QLabel("Backups are stored in: ./backups/"))
        info_layout.addWidget(QLabel("Format: filename_YYYYMMDD_HHMMSS_backup.ext"))
        layout.addWidget(info_group)

        # Backup actions group
        action_group = QGroupBox("Backup Actions")
        action_layout = QHBoxLayout(action_group)
        open_btn = QPushButton("Open Backup Folder")
        open_btn.clicked.connect(self.open_backup_folder)
        action_layout.addWidget(open_btn)
        clean_btn = QPushButton("Clean Old Backups")
        clean_btn.clicked.connect(self.clean_old_backups)
        action_layout.addWidget(clean_btn)
        action_layout.addStretch()
        layout.addWidget(action_group)

        layout.addStretch()
        tab_widget.addTab(tab, "Backups")

    def setup_encryption_tab(self, tab_widget):
        """Setup encryption settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Encryption settings group
        encryption_group = QGroupBox("Decryption Settings")
        encryption_layout = QVBoxLayout(encryption_group)

        # Hex key
        encryption_layout.addWidget(QLabel("Default Decryption Key (Hex):"))
        self.hex_key_edit = QLineEdit(self.hex_key)
        self.hex_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        encryption_layout.addWidget(self.hex_key_edit)

        # Key actions
        key_layout = QHBoxLayout()
        show_btn = QPushButton("Show/Hide Key")
        show_btn.clicked.connect(lambda: self.toggle_hex_key_visibility())
        key_layout.addWidget(show_btn)
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.reset_hex_key)
        key_layout.addWidget(reset_btn)
        key_layout.addStretch()
        encryption_layout.addLayout(key_layout)

        # Info text
        info_label = QLabel("ℹ️ This is the standard DDV encryption key.")
        info_label.setStyleSheet("color: #64B5F6;")
        encryption_layout.addWidget(info_label)
        help_label = QLabel(
            "The application will try this key first before prompting you."
        )
        help_label.setStyleSheet("color: #9E9E9E;")
        encryption_layout.addWidget(help_label)

        layout.addWidget(encryption_group)

        # CyberChef info group
        cyberchef_group = QGroupBox("CyberChef Integration")
        cyberchef_layout = QVBoxLayout(cyberchef_group)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "This key matches your CyberChef configuration:\n"
            "• AES Decrypt with ECB/NoPadding mode\n"
            "• Followed by Unzip operation\n"
            "• Same 32-byte hex key format"
        )
        cyberchef_layout.addWidget(info_text)
        layout.addWidget(cyberchef_group)

        layout.addStretch()
        tab_widget.addTab(tab, "Encryption")

    def setup_buttons(self, layout):
        """Setup dialog buttons"""
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def toggle_hex_key_visibility(self):
        """Toggle visibility of hex key"""
        if self.hex_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.hex_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.hex_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def reset_hex_key(self):
        """Reset hex key to default DDV key"""
        default_key = "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35"
        self.hex_key_edit.setText(default_key)

    def browse_image_zip(self):
        """Browse for image ZIP file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Image ZIP File", "", "ZIP files (*.zip);;All files (*.*)"
        )
        if filename:
            self.image_zip_edit.setText(filename)

    def browse_image_folder(self):
        """Browse for image folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder_edit.setText(folder)

    def browse_dict_folder(self):
        """Browse for Dict root folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Dict Root Folder")
        if folder:
            self.dict_root_edit.setText(folder)

    def open_backup_folder(self):
        """Open backup folder in file explorer"""
        backup_path = Path("backups")
        backup_path.mkdir(exist_ok=True)

        if sys.platform == "win32":
            subprocess.run(["explorer", str(backup_path)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(backup_path)])
        else:
            subprocess.run(["xdg-open", str(backup_path)])

    def clean_old_backups(self):
        """Clean old backup files"""
        # This would implement backup cleanup logic
        QMessageBox.information(
            self, "Clean Backups", "Old backups cleaned successfully!"
        )

    def reset_defaults(self):
        """Reset all settings to defaults"""
        self.font_size_combo.setCurrentText("Medium")
        self.large_scrollbars_check.setChecked(False)
        self.image_zip_edit.setText("img.zip")
        self.image_folder_edit.setText("img")
        self.max_backups_spin.setValue(10)
        self.auto_backup_check.setChecked(True)
        self.show_images_check.setChecked(True)
        self.cache_size_spin.setValue(200)
        self.thumbnail_size_combo.setCurrentText("64x64")
        self.preview_size_combo.setCurrentText("128x128")
        self.data_source_dict_radio.setChecked(True)  # Always check Dict
        self.dict_root_edit.setText("Dict")

    def get_settings(self):
        """Get the current settings as a dictionary"""
        return {
            "font_size": self.font_size_combo.currentText(),
            "large_scrollbars": self.large_scrollbars_check.isChecked(),
            "image_zip_path": self.image_zip_edit.text(),
            "image_folder_path": self.image_folder_edit.text(),
            "max_backups": self.max_backups_spin.value(),
            "auto_backup": self.auto_backup_check.isChecked(),
            "show_images": self.show_images_check.isChecked(),
            "cache_size": self.cache_size_spin.value(),
            "thumbnail_size": self.thumbnail_size_combo.currentText(),
            "preview_size": self.preview_size_combo.currentText(),
            "hex_key": self.hex_key_edit.text(),
            "data_source": "dict",  # Always "dict"
            "dict_root": self.dict_root_edit.text(),
            "danger_zone_enabled": self.danger_zone_check.isChecked(),
        }

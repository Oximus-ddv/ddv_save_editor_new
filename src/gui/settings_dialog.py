"""
Settings dialog for DDV Save Editor (PyQt6)
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QComboBox, QPushButton, QHBoxLayout, QDialogButtonBox
from ..services.settings_service import SettingsService

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings_service
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.setup_tabs()
        self.setup_buttons()
        self.load_settings()

    def setup_tabs(self):
        self.tabs.addTab(self.create_file_paths_tab(), "File Paths")
        self.tabs.addTab(self.create_data_source_tab(), "Data Source")
        self.tabs.addTab(self.create_image_settings_tab(), "Images")
        self.tabs.addTab(self.create_backup_settings_tab(), "Backups")
        self.tabs.addTab(self.create_encryption_tab(), "Encryption")

    def create_file_paths_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.excel_path_edit = QLineEdit()
        self.image_zip_edit = QLineEdit()
        self.image_folder_edit = QLineEdit()

        layout.addRow("Excel Data File:", self.excel_path_edit)
        layout.addRow("Image ZIP File:", self.image_zip_edit)
        layout.addRow("Image Folder:", self.image_folder_edit)

        return widget

    def create_data_source_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["Excel", "Dict"])
        self.dict_root_edit = QLineEdit()

        layout.addRow("Data Source:", self.data_source_combo)
        layout.addRow("Dict Root Folder:", self.dict_root_edit)

        return widget

    def create_image_settings_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.show_images_checkbox = QCheckBox("Show image previews")
        self.cache_size_spinbox = QSpinBox()
        self.cache_size_spinbox.setRange(50, 1000)
        self.thumbnail_size_combo = QComboBox()
        self.thumbnail_size_combo.addItems(["32x32", "48x48", "64x64", "96x96"])
        self.preview_size_combo = QComboBox()
        self.preview_size_combo.addItems(["96x96", "128x128", "192x192", "256x256"])

        layout.addRow(self.show_images_checkbox)
        layout.addRow("Image Cache Size:", self.cache_size_spinbox)
        layout.addRow("Thumbnail Size:", self.thumbnail_size_combo)
        layout.addRow("Preview Size:", self.preview_size_combo)

        return widget

    def create_backup_settings_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.auto_backup_checkbox = QCheckBox("Create automatic backups")
        self.backup_count_spinbox = QSpinBox()
        self.backup_count_spinbox.setRange(1, 100)

        layout.addRow(self.auto_backup_checkbox)
        layout.addRow("Maximum Backups:", self.backup_count_spinbox)

        return widget

    def create_encryption_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.hex_key_edit = QLineEdit()
        self.hex_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Default Decryption Key (Hex):", self.hex_key_edit)

        return widget

    def setup_buttons(self):
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Reset)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_defaults)

        self.layout.addWidget(button_box)

    def load_settings(self):
        settings = self.settings_service.load()
        self.excel_path_edit.setText(settings.get("excel_path", ""))
        self.image_zip_edit.setText(settings.get("image_zip_path", ""))
        self.image_folder_edit.setText(settings.get("image_folder_path", ""))
        self.data_source_combo.setCurrentText(settings.get("data_source", "Dict"))
        self.dict_root_edit.setText(settings.get("dict_root", "Dict"))
        self.show_images_checkbox.setChecked(settings.get("show_images", True))
        self.cache_size_spinbox.setValue(settings.get("cache_size", 200))
        self.thumbnail_size_combo.setCurrentText(settings.get("thumbnail_size", "64x64"))
        self.preview_size_combo.setCurrentText(settings.get("preview_size", "128x128"))
        self.auto_backup_checkbox.setChecked(settings.get("auto_backup", True))
        self.backup_count_spinbox.setValue(settings.get("max_backups", 10))
        self.hex_key_edit.setText(settings.get("hex_key", ""))

    def save_settings(self):
        settings = {
            "excel_path": self.excel_path_edit.text(),
            "image_zip_path": self.image_zip_edit.text(),
            "image_folder_path": self.image_folder_edit.text(),
            "data_source": self.data_source_combo.currentText(),
            "dict_root": self.dict_root_edit.text(),
            "show_images": self.show_images_checkbox.isChecked(),
            "cache_size": self.cache_size_spinbox.value(),
            "thumbnail_size": self.thumbnail_size_combo.currentText(),
            "preview_size": self.preview_size_combo.currentText(),
            "auto_backup": self.auto_backup_checkbox.isChecked(),
            "max_backups": self.backup_count_spinbox.value(),
            "hex_key": self.hex_key_edit.text(),
        }
        self.settings_service.save(settings)

    def accept(self):
        self.save_settings()
        super().accept()

    def reset_defaults(self):
        defaults = self.settings_service.default_settings()
        self.excel_path_edit.setText(defaults.get("excel_path", ""))
        self.image_zip_edit.setText(defaults.get("image_zip_path", ""))
        self.image_folder_edit.setText(defaults.get("image_folder_path", ""))
        self.data_source_combo.setCurrentText(defaults.get("data_source", "Dict"))
        self.dict_root_edit.setText(defaults.get("dict_root", "Dict"))
        self.show_images_checkbox.setChecked(defaults.get("show_images", True))
        self.cache_size_spinbox.setValue(defaults.get("cache_size", 200))
        self.thumbnail_size_combo.setCurrentText(defaults.get("thumbnail_size", "64x64"))
        self.preview_size_combo.setCurrentText(defaults.get("preview_size", "128x128"))
        self.auto_backup_checkbox.setChecked(defaults.get("auto_backup", True))
        self.backup_count_spinbox.setValue(defaults.get("max_backups", 10))
        self.hex_key_edit.setText(defaults.get("hex_key", ""))

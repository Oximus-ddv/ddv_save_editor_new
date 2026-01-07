"""
Main GUI window for DDV Save Editor (PyQt6)
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QMenu, QToolBar, QStatusBar, QTabWidget, QWidget, QVBoxLayout, QFileDialog, QLabel, QComboBox
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtCore import Qt
from ..services.save_service import SaveFileService
from ..services.dict_service import DictDataService
from ..services.settings_service import SettingsService
from ..models.game_item import ItemCategory

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DDV Save Editor - Python (PyQt6)")
        self.setGeometry(100, 100, 1200, 800)

        self.settings_service = SettingsService()
        self.save_service = SaveFileService()
        self.dict_service = DictDataService()
        self.game_database = None

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bars()
        self._create_status_bar()

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Add currency editor tab
        from .currency_editor import CurrencyEditor
        self.currency_editor = CurrencyEditor()
        self.tab_widget.addTab(self.currency_editor, "Currencies")

        # Add pet editor tab
        from .pet_editor import PetEditor
        self.pet_editor = PetEditor(self.save_service, self.game_database)
        self.tab_widget.addTab(self.pet_editor, "Pets")
        self.tab_widget.setTabEnabled(1, False)  # Disable pets tab initially

        self.load_initial_data()

    def _create_category_tabs(self):
        # Clear existing tabs except for Currencies and Pets
        while self.tab_widget.count() > 2:
            self.tab_widget.removeTab(2)

        from .item_editor import ItemEditor
        self.item_editors = {}
        if self.game_database:
            categories = [cat for cat in ItemCategory if cat != ItemCategory.PETS]
            for category in categories:
                item_editor = ItemEditor(category, self.game_database, self.save_service)
                self.item_editors[category] = item_editor
                self.tab_widget.addTab(item_editor, category.value.replace("_", " ").title())

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.auto_load_action)
        file_menu.addAction(self.manual_load_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_excel_action)
        file_menu.addAction(self.refresh_excel_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.add_all_items_action)
        edit_menu.addAction(self.clear_all_items_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.settings_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction(self.backup_manager_action)
        tools_menu.addAction(self.validate_save_action)
        tools_menu.addAction(self.clear_image_cache_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.add_basic_tools_action)
        tools_menu.addAction(self.add_monster_pickaxe_action)
        tools_menu.addAction(self.add_main_pickaxe_action)
        tools_menu.addAction(self.augment_save_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.cache_images_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _create_tool_bars(self):
        # File toolbar
        file_tool_bar = self.addToolBar("File")
        file_tool_bar.addAction(self.auto_load_action)
        file_tool_bar.addAction(self.manual_load_action)
        file_tool_bar.addAction(self.save_action)
        file_tool_bar.addAction(self.json_viewer_action)
        file_tool_bar.addAction(self.full_editor_action)

        data_source_label = QLabel("Data Source:")
        file_tool_bar.addWidget(data_source_label)

        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["Dict", "Excel"])
        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        file_tool_bar.addWidget(self.data_source_combo)

        theme_label = QLabel("Theme:")
        file_tool_bar.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        file_tool_bar.addWidget(self.theme_combo)

    def _create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready", 3000)

    def _create_actions(self):
        # File actions
        self.auto_load_action = QAction("&Auto-Load Latest Save", self)
        self.auto_load_action.triggered.connect(self.auto_load)
        self.manual_load_action = QAction("&Load Save File Manually...", self)
        self.manual_load_action.triggered.connect(self.load_save_file_manual)
        self.save_action = QAction("&Save", self)
        self.save_action.triggered.connect(self.save_current_file)
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.triggered.connect(self.save_file_as)
        self.load_excel_action = QAction("Load &Excel Data...", self)
        self.load_excel_action.triggered.connect(self.load_excel_data)
        self.refresh_excel_action = QAction("&Refresh Excel Data", self)
        self.exit_action = QAction("E&xit", self)
        self.exit_action.triggered.connect(self.close)

        # Edit actions
        self.add_all_items_action = QAction("&Add All Items", self)
        self.clear_all_items_action = QAction("&Clear All Items", self)
        self.settings_action = QAction("&Settings...", self)
        self.settings_action.triggered.connect(self.open_settings_dialog)

        # Tools actions
        self.backup_manager_action = QAction("&Backup Manager...", self)
        self.validate_save_action = QAction("&Validate Save File", self)
        self.clear_image_cache_action = QAction("Clear &Image Cache", self)
        self.add_basic_tools_action = QAction("Add &Basic Tools", self)
        self.add_monster_pickaxe_action = QAction("Add &Monster Pickaxe", self)
        self.add_main_pickaxe_action = QAction("Add M&ain Pickaxe", self)
        self.augment_save_action = QAction("&Augment Save (legacy dicts)", self)
        self.cache_images_action = QAction("&Cache Online Images (Current Category)", self)

        # Help actions
        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self.about)

        # Toolbar actions
        self.json_viewer_action = QAction("JSON Viewer", self)
        self.json_viewer_action.triggered.connect(self.open_json_viewer)
        self.full_editor_action = QAction("Full Editor", self)
        self.full_editor_action.triggered.connect(self.open_full_editor)

    def load_initial_data(self):
        settings = self.settings_service.load()
        data_source = settings.get("data_source", "Dict")
        self.data_source_combo.setCurrentText(data_source)
        self.on_data_source_changed(data_source)

    def on_data_source_changed(self, source):
        settings = self.settings_service.load()
        if source == "Dict":
            dict_root = settings.get("dict_root", "Dict")
            self.game_database = self.dict_service.load_game_database(force_reload=True)
        else:
            # excel_path = settings.get("excel_path", "Disney Dream Light ID List - Mainted by Rubyelf.xlsx")
            # self.game_database = self.excel_service.load_game_database(excel_path, force_reload=True)
            self.game_database = None # Placeholder for excel service
        self._create_category_tabs()
        self.update_ui_with_loaded_data()

    def auto_load(self):
        self.statusBar.showMessage("Auto-loading latest save...", 3000)
        latest_save_path = self.save_service.find_latest_save_file()
        if latest_save_path:
            self._load_specific_file(latest_save_path)
        else:
            QMessageBox.warning(self, "Auto-Load", "Could not find any save files.")

    def load_save_file_manual(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select DDV Save File", "", "JSON files (*.json);;All files (*.*)")
        if file_name:
            self._load_specific_file(file_name)

    def _load_specific_file(self, file_path):
        settings = self.settings_service.load()
        hex_key = settings.get('hex_key')
        success, message = self.save_service.load_save_file(file_path, hex_key)
        if success:
            self.statusBar.showMessage("Save file loaded successfully", 3000)
            self.on_data_source_changed(self.data_source_combo.currentText())
            self.update_ui_with_loaded_data()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load save file: {message}")

    def update_ui_with_loaded_data(self):
        save_data = self.save_service.current_save_data
        if not save_data:
            return

        # Update currency editor
        self.currency_editor.player_name_edit.setText(save_data.player_name)
        self.currency_editor.player_level_spinbox.setValue(save_data.player_level)
        self.currency_editor.star_coins_spinbox.setValue(save_data.star_coins)
        self.currency_editor.dreamlight_spinbox.setValue(save_data.dreamlight)
        self.currency_editor.daisy_coins_spinbox.setValue(save_data.daisy_coins)
        self.currency_editor.mist_spinbox.setValue(save_data.mist)
        self.currency_editor.pixel_dust_spinbox.setValue(save_data.pixel_dust)

        # Update item editors
        if self.game_database:
            for category, editor in self.item_editors.items():
                editor.load_save_data(save_data, self.game_database)

        # Update pet editor
        self.pet_editor.load_save_data(save_data, self.game_database)
        self.tab_widget.setTabEnabled(1, True) # Enable pets tab

    def save_file_as(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save DDV Save File As", "", "JSON files (*.json);;All files (*.*)")
        if file_name:
            save_data = self.save_service.current_save_data
            if not save_data:
                QMessageBox.warning(self, "No Save Data", "Please load a save file first.")
                return

            # Update pets data
            edited_pets = self.pet_editor.get_edited_pets()
            save_data.pets = edited_pets

            # Collect data from all editors
            self.collect_data_from_editors()

            # Save the file
            success, message = self.save_service.save_file(file_name)
            if success:
                self.statusBar.showMessage("File saved successfully", 3000)
            else:
                QMessageBox.critical(self, "Error", f"Failed to save file: {message}")

    def save_current_file(self):
        """Saves the current save data to the loaded file path."""
        save_data = self.save_service.current_save_data
        if not save_data:
            QMessageBox.warning(self, "No Save Data", "Please load a save file first.")
            return

        self.collect_data_from_editors()

        success, message = self.save_service.save_file()
        if success:
            self.statusBar.showMessage("File saved successfully", 3000)
        else:
            QMessageBox.critical(self, "Error", f"Failed to save file: {message}")

    def collect_data_from_editors(self):
        """Collects edited data from all active editors and updates the save_service.current_save_data."""
        save_data = self.save_service.current_save_data
        if not save_data:
            return

        # Collect data from Currency Editor
        self.currency_editor.get_edited_data(save_data)

        # Collect data from Pet Editor
        # The pet editor directly modifies save_data.pets, so we just need to ensure it's up-to-date
        # (which it should be via its internal signal connections)
        # However, we can explicitly get the edited pets if needed, though it's redundant here
        save_data.pets = self.pet_editor.get_edited_pets()

        # Collect data from Item Editors (if they exist)
        if self.game_database:
            for category, editor in self.item_editors.items():
                # Assuming item editors also have a method to update save_data
                # editor.get_edited_data(save_data) # This method would need to be implemented
                pass # Placeholder for now

    def load_excel_data(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Excel Data File", "", "Excel files (*.xlsx);;All files (*.*)")
        if file_name:
            # self.excel_service.excel_path = Path(file_name)
            # self.refresh_excel_data()
            pass

    def open_settings_dialog(self):
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.settings_service, self)
        if dialog.exec():
            self.load_initial_data() # Reload data if settings changed

    def open_json_viewer(self):
        from .json_viewer import JsonViewer
        dialog = JsonViewer(self)
        dialog.exec()

    def open_full_editor(self):
        from .full_editor import FullEditor
        dialog = FullEditor(self)
        dialog.exec()

    def about(self):
        QMessageBox.about(self, "About DDV Save Editor",
                          "DDV Save Editor - Python Version\n\n"
                          "A tool for editing Disney Dreamlight Valley save files\n\n"
                          "Features:\n"
                          "• Load and save encrypted save files\n"
                          "• Dynamic Excel data loading\n"
                          "• Image previews for items\n"
                          "• Automatic backups\n"
                          "• Modern Python GUI")

    def on_theme_changed(self, theme):
        if theme == "Dark":
            set_dark_mode(QApplication.instance())
        else:
            set_light_mode(QApplication.instance())

def set_light_mode(app):
    """Sets a light theme for the application."""
    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(light_palette)

def set_dark_mode(app):
    """Sets a dark theme for the application."""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark_palette)

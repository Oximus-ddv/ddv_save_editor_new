"""
Main GUI window for DDV Save Editor - PyQt6 Version
"""

import sys
import json
import re
import os
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import threading

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTabWidget,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QStatusBar,
    QMenuBar,
    QMenu,
    QStyle,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QInputDialog,
    QHeaderView,
    QStackedWidget,
    QGridLayout,
    QToolButton,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt,
    QSize,
    QEvent,
    pyqtSignal,
    pyqtSlot,
    QTimer,
    QPropertyAnimation,
    QParallelAnimationGroup,
)
from PyQt6.QtGui import QAction, QPalette, QResizeEvent, QPixmap, QScreen, QIcon
import qdarktheme


from .toast_notification import ToastNotification
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.settings_service import SettingsService
from ..services.dict_service import DictDataService
from ..services.augmentation_service import (
    augment_save_dict,
    add_basic_tools,
    add_specific_tool,
)
from ..models.game_item import GameDatabase, ItemCategory, PlayerInventoryItem
from .item_editor import ItemEditorFrame
from .currency_editor import CurrencyEditorFrame
from .collection_editor import CollectionEditorFrame
from .collection_set_editor import CollectionSetEditorFrame
from .settings_dialog import SettingsDialog
from .search_results import SearchResultsFrame
from .json_viewer import JsonViewerWindow
from .battle_pass_editor import BattlePassEditor
from .hover_preview import HoverPreviewBehavior
from .draggable_button import DraggableButton


logger = logging.getLogger(__name__)


THEMES = {
    "Dark": {"qdarktheme_id": "dark", "qss_file": "src/gui/themes/dark.qss"},
    "Light": {"qdarktheme_id": "light", "qss_file": "src/gui/themes/light.qss"},
}


class MainWindow(QMainWindow):
    """Main application window"""

    # Define signals for thread-safe GUI updates
    save_loaded_signal = pyqtSignal(bool, str)
    save_completed_signal = pyqtSignal(bool, str)
    data_refreshed_signal = pyqtSignal()
    status_signal = pyqtSignal(str)

    def __init__(self, splash=None, splash_handler=None):
        super().__init__()
        self.splash = splash
        self.splash_handler = splash_handler
        self.modify_mode = False
        self.settings_service = SettingsService()
        self.settings: Dict[str, Any] = self.settings_service.load()

        # Setup window
        self.setWindowTitle("DDV Save Editor")

        # Setup dark theme now that settings are available
        self.setup_theme()

        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Set a reasonable default size and center the window
        screen = QApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            self.resize(
                int(available_geometry.width() * 0.8),
                int(available_geometry.height() * 0.8),
            )
            self.move(available_geometry.center() - self.rect().center())

        # Services configured from settings
        self._initialize_dict_service()
        self.image_service = ImageService(
            zip_path=self.settings.get("image_zip_path", "img.zip"),
            folder_path=self.settings.get("image_folder_path", "img"),
            cache_size_limit=int(self.settings.get("cache_size", 200) or 200),
        )
        # Apply image sizes from settings
        from ..services.settings_service import SettingsService as _SS

        self.image_service.thumbnail_size = _SS.parse_size(
            self.settings.get("thumbnail_size", "64x64"), (64, 64)
        )
        self.image_service.preview_size = _SS.parse_size(
            self.settings.get("preview_size", "128x128"), (128, 128)
        )

        self.save_service = SaveFileService(
            max_backups=int(self.settings.get("max_backups", 10) or 10)
        )

        # Default hex key for decryption
        self.default_hex_key = str(
            self.settings.get("hex_key")
            or "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35"
        )

        # Data
        self.game_database: Optional[GameDatabase] = None
        self.current_category = ItemCategory.PETS

        # UI Components
        self.setup_menu()
        self.setup_main_layout()
        self.setup_status_bar()

        # Item editor frames (will be created dynamically)
        self.item_editor_frames: Dict[ItemCategory, ItemEditorFrame] = {}

        # Connect signals
        self.save_loaded_signal.connect(self.handle_save_loaded)
        self.save_completed_signal.connect(self.handle_save_completed)
        self.data_refreshed_signal.connect(self.handle_data_refreshed)
        self.status_signal.connect(self.handle_status_update)

        # Initialize
        self.load_initial_data()

        # Handle window closing
        self.closeEvent = self.on_closing

    def setup_menu(self):
        """Setup main menu bar"""
        # Create menu bar
        self.menubar = self.menuBar()

        # File menu
        file_menu = self.menubar.addMenu("&File")

        auto_load_action = QAction("Auto-Load Latest Save", self)
        auto_load_action.setToolTip(
            "Automatically finds and loads the latest save file from the default location."
        )
        auto_load_action.triggered.connect(self.load_save_file)
        file_menu.addAction(auto_load_action)

        manual_load_action = QAction("Load Save File Manually...", self)
        manual_load_action.setToolTip(
            "Opens a file dialog to manually select a save file to load."
        )
        manual_load_action.triggered.connect(self.load_save_file_manual)
        file_menu.addAction(manual_load_action)

        file_menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.setToolTip("Saves the current changes to the loaded save file.")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setToolTip("Saves the current changes to a new save file.")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        exit_action = QAction("Exit", self)
        exit_action.setToolTip("Exits the application.")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = self.menubar.addMenu("&Settings")
        settings_action = QAction("Settings...", self)
        settings_action.setToolTip("Opens the application settings dialog.")
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        # Appearance menu
        appearance_menu = self.menubar.addMenu("&Appearance")

        appearance_menu.addSeparator()

        from PyQt6.QtGui import QActionGroup

        self.theme_menu = QMenu("Theme", self)
        appearance_menu.addMenu(self.theme_menu)
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        current_theme = self.settings.get("theme", "Dark")
        for theme_name in THEMES:
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked, name=theme_name: self.on_theme_changed(name)
            )
            self.theme_menu.addAction(action)
            self.theme_action_group.addAction(action)

            if theme_name == current_theme:
                action.setChecked(True)

        # Help menu
        help_menu = self.menubar.addMenu("&Help")

        about_action = QAction("About", self)
        about_action.setToolTip("Shows information about the application.")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _initialize_dict_service(self):
        """
        Initializes the DictDataService, prompting the user for a valid dict_root
        if the current setting is empty or points to a non-existent path.
        """
        dict_root_path = self.settings.get("dict_root", "")
        dict_valid = False

        while not dict_valid:
            logger.info(f"Checking dict_root: '{dict_root_path}'")
            if dict_root_path:
                current_path = Path(dict_root_path)
                if (current_path.is_dir() and current_path.name == "Dict") or (
                    current_path.is_file() and current_path.name == "Dict.zip"
                ):
                    logger.info(f"Configured dict_root '{dict_root_path}' is valid.")
                    dict_valid = True
                else:
                    logger.warning(f"Configured dict_root '{dict_root_path}' is invalid or missing.")
                    QMessageBox.warning(
                        self,
                        "Dict Data Missing",
                        f"The configured Dict path '{dict_root_path}' does not exist or is invalid.\n"
                        "Please select the 'Dict.zip' file.",
                    )
            else:
                logger.info("dict_root setting is empty. Prompting user for selection.")
                QMessageBox.information(
                    self,
                    "Dict Data Required",
                    "The 'dict_root' setting is empty. Please select the 'Dict.zip' file.",
                )

            if not dict_valid:
                # Unified dialog for selecting either Dict.zip or a file within the Dict folder
                start_path = os.getcwd()  # Default to current working directory
                if getattr(sys, "frozen", False):
                    start_path = Path(sys.executable).parent
                else:
                    # Running from source, __file__ is in src/gui
                    start_path = Path(__file__).resolve().parent.parent.parent

                logger.info("Opening file dialog to select Dict data source.")
                selected_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select 'Dict.zip' or a file inside 'Dict' folder",
                    str(start_path),
                    "Dict.zip (Dict.zip);;All files (*.*)",
                )

                if selected_path:
                    logger.info(f"User selected: '{selected_path}'")
                    selected_path_obj = Path(selected_path)

                    # Case 1: User selected Dict.zip
                    if (
                        selected_path_obj.is_file()
                        and selected_path_obj.name == "Dict.zip"
                    ):
                        dict_root_path = str(selected_path_obj)
                        self.settings["dict_root"] = dict_root_path
                        self.settings_service.save(self.settings)
                        dict_valid = True
                        logger.info(f"Selected '{selected_path}' (Dict.zip) is valid.")
                    # Case 2: User selected a file inside a 'Dict' directory
                    elif (
                        selected_path_obj.is_file()
                        and selected_path_obj.parent.name == "Dict"
                    ):
                        dict_root_path = str(selected_path_obj.parent)
                        self.settings["dict_root"] = dict_root_path
                        self.settings_service.save(self.settings)
                        dict_valid = True
                        logger.info(f"Selected file in '{selected_path_obj.parent}' (Dict folder) is valid.")
                    else:
                        logger.warning(f"Invalid selection: '{selected_path}'. Must be Dict.zip or a file in a Dict folder.")
                        QMessageBox.warning(
                            self,
                            "Invalid Selection",
                            "You must select either the 'Dict.zip' file or a file inside the folder named 'Dict'.",
                        )
                else:  # User cancelled
                    logger.warning("User cancelled Dict data source selection.")
                    QMessageBox.critical(
                        self,
                        "Dict Data Error",
                        "No valid Dict data source selected. The application will not function correctly without it.",
                    )
                    # Fallback to default and exit loop
                    dict_root_path = "Dict"
                    dict_valid = True

        self.dict_service = DictDataService(dict_root_path)

    def setup_theme(self):
        """Setup the application theme using qdarktheme."""
        try:
            theme_choice = self.settings.get("theme", "Dark")
            self._apply_stylesheet(theme_choice)

        except Exception as e:
            logger.error(f"Error setting up theme: {e}")
            pass

    def _apply_stylesheet(self, theme_name: str):
        """Generates and applies the application stylesheet."""
        theme_info = THEMES.get(theme_name)
        if not theme_info:
            logger.warning(
                f"Theme '{theme_name}' not found. Falling back to Dark theme."
            )
            theme_name = "Dark"
            theme_info = THEMES[theme_name]

        base_stylesheet = qdarktheme.load_stylesheet(theme_info["qdarktheme_id"])

        # Load static stylesheet from file
        try:
            with open(theme_info["qss_file"], "r") as f:
                static_stylesheet = f.read()
        except FileNotFoundError:
            logger.error(f"Stylesheet file not found: {theme_info['qss_file']}")
            static_stylesheet = ""

        # --- Dynamic styles based on settings ---
        font_size_str = self.settings.get("font_size", "Medium")
        size_map = {"Small": 10, "Medium": 12, "Large": 14}
        font_size = size_map.get(font_size_str, 12)

        large_scrollbars = self.settings.get("large_scrollbars", False)
        scrollbar_width = 30 if large_scrollbars else 15

        dynamic_stylesheet = f"""
        * {{
            font-size: {font_size}pt;
        }}
        QScrollBar:vertical {{
            width: {scrollbar_width}px;
        }}
        QScrollBar:horizontal {{
            height: {scrollbar_width}px;
        }}
        """

        # Combine and apply
        full_stylesheet = base_stylesheet + static_stylesheet + dynamic_stylesheet
        QApplication.instance().setStyleSheet(full_stylesheet)

    def on_theme_changed(self, theme_name: str):
        """Handle theme change from the menu, saves setting."""
        self.settings["theme"] = theme_name
        self.settings_service.save(self.settings)
        self._apply_stylesheet(theme_name)

        # The action group handles the check state automatically.
        # This is just to be safe if called from elsewhere.
        for action in self.theme_action_group.actions():
            if action.text() == theme_name:
                action.setChecked(True)
                break

    def setup_main_layout(self):
        """Setup main window layout"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        # Top toolbar
        self.setup_toolbar()

        # Central stacked widget for switching between category grid and item editors
        self.central_stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.central_stacked_widget)

        # These frames are always present
        danger_zone_enabled = self.settings.get("danger_zone_enabled", False)
        self.currency_frame = CurrencyEditorFrame(
            self.central_stacked_widget, self.save_service, danger_zone_enabled
        )
        self.central_stacked_widget.addWidget(self.currency_frame)

        self.collection_set_frame = CollectionSetEditorFrame(
            self.central_stacked_widget,
            self.save_service,
            self.dict_service,
            self.image_service,
        )
        self.central_stacked_widget.addWidget(self.collection_set_frame)

        # Conditionally add other danger zone tabs
        self._update_danger_zone_tabs()

        # Item editor frames (will be created dynamically)
        self.item_editor_frames: Dict[ItemCategory, ItemEditorFrame] = {}

    def setup_toolbar(self):
        """Setup toolbar with common actions"""
        # Create toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        toolbar_layout.setSpacing(5)

        # Add logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("images/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            toolbar_layout.addWidget(logo_label)

        # Load/Save buttons
        load_btn = QPushButton("Auto-Load")
        load_btn.setToolTip("Automatically finds and loads the latest save file.")
        load_btn.clicked.connect(self.load_save_file)
        toolbar_layout.addWidget(load_btn)

        manual_load_btn = QPushButton("Manual Load")
        manual_load_btn.setToolTip(
            "Opens a file dialog to manually select a save file."
        )
        manual_load_btn.clicked.connect(self.load_save_file_manual)
        toolbar_layout.addWidget(manual_load_btn)

        save_btn = QPushButton("Save")
        save_btn.setToolTip("Saves the current changes to the loaded save file.")
        save_btn.clicked.connect(self.save_file)
        toolbar_layout.addWidget(save_btn)

        json_viewer_btn = QPushButton("JSON Viewer")
        json_viewer_btn.setToolTip(
            "Opens a read-write JSON viewer for the raw save data."
        )
        json_viewer_btn.clicked.connect(self.show_json_viewer)
        toolbar_layout.addWidget(json_viewer_btn)

        full_editor_btn = QPushButton("Full Editor")
        full_editor_btn.setToolTip(
            "Opens a full editor for the raw save data (Advanced users only)."
        )
        full_editor_btn.clicked.connect(self.show_full_editor)
        toolbar_layout.addWidget(full_editor_btn)

        # self.modify_btn = QPushButton("Modify Order")
        # self.modify_btn.setCheckable(True)
        # self.modify_btn.toggled.connect(self.toggle_modify_mode)
        # toolbar_layout.addWidget(self.modify_btn)

        # Add vertical separator
        from PyQt6.QtWidgets import QFrame

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        toolbar_layout.addWidget(separator)

        # Data source quick switch
        toolbar_layout.addWidget(QLabel("Data Source:"))
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["Dict"])
        self.data_source_combo.setCurrentText(
            str(self.settings.get("data_source", "dict")).title()
        )
        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        toolbar_layout.addWidget(self.data_source_combo)

        dict_folder_btn = QPushButton("Choose Dict Folder")
        dict_folder_btn.setToolTip("Choose the folder containing the 'Dict' data.")
        dict_folder_btn.clicked.connect(self.choose_dict_folder)
        toolbar_layout.addWidget(dict_folder_btn)

        # Add vertical separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        toolbar_layout.addWidget(separator2)

        # Search
        toolbar_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.returnPressed.connect(self.on_search)
        toolbar_layout.addWidget(self.search_entry)

        search_btn = QPushButton("Search")
        search_btn.setToolTip("Searches for items in the game database.")
        search_btn.clicked.connect(self.on_search)
        toolbar_layout.addWidget(search_btn)

        # Add stretch to push status to right
        toolbar_layout.addStretch()

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #d14;")
        toolbar_layout.addWidget(self.status_indicator)

        self.status_label = QLabel("No save loaded")
        toolbar_layout.addWidget(self.status_label)

        # Add toolbar to main layout
        self.main_layout.addWidget(toolbar)

    def toggle_modify_mode(self, checked):
        # This function is now effectively disabled since the button is commented out.
        # Keeping it as a placeholder if needed later.
        self.modify_mode = checked

    def save_category_order(self):
        """Saves the current order of the categories in the grid."""
        order = []
        layout = self.category_grid_widget.layout()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, DraggableButton):
                order.append(widget.objectName())

        self.settings["category_order"] = order
        self.settings_service.save(self.settings)
        logger.debug(f"Saving category order: {order}")

    def setup_status_bar(self):
        """Setup status bar at bottom"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status text
        self.status_text = QLabel("Ready")
        self.status_bar.addWidget(self.status_text)

        # Progress bar (hidden by default)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(100)
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.status_bar.addPermanentWidget(self.progress)

        # Database stats
        self.db_stats_label = QLabel("")
        self.status_bar.addPermanentWidget(self.db_stats_label)

    def load_initial_data(self):
        """Load initial data on startup"""
        source = str(self.settings.get("data_source", "dict")).lower()
        self.set_status(f"Loading Dict data...")

        def load_data():
            try:
                if source == "dict":
                    self.game_database = self.dict_service.load_game_database()
                else:
                    # Excel is no longer supported, fall back to Dict
                    self.game_database = self.dict_service.load_game_database()
                QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))
            except Exception as e:
                logger.error(f"Error loading initial data: {e}")
                QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))

        threading.Thread(target=load_data, daemon=True).start()

    def event(self, event: QEvent) -> bool:
        """Handle custom events"""
        if event.type() == QEvent.Type.User:
            self.on_data_loaded()
            return True
        return super().event(event)

    def eventFilter(self, obj, event):
        if obj == self.category_grid_widget and self.modify_mode:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True

            if event.type() == QEvent.Type.DragMove:
                target_widget = obj.childAt(event.position().toPoint())
                if (
                    self.last_highlighted_button
                    and self.last_highlighted_button != target_widget
                ):
                    self.last_highlighted_button.setStyleSheet(self.button_style)
                    self.last_highlighted_button = None

                if isinstance(target_widget, DraggableButton):
                    target_widget.setStyleSheet(
                        self.button_style + "border: 2px solid #00BFFF;"
                    )
                    self.last_highlighted_button = target_widget

                if event.mimeData().hasText():
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True

            if event.type() == QEvent.Type.Drop:
                if self.last_highlighted_button:
                    self.last_highlighted_button.setStyleSheet(self.button_style)
                    self.last_highlighted_button = None

                if event.mimeData().hasText():
                    widget_name = event.mimeData().text()
                    dragged_widget = self.findChild(DraggableButton, widget_name)

                    if dragged_widget:
                        target_widget = obj.childAt(event.position().toPoint())
                        if target_widget and isinstance(target_widget, DraggableButton):

                            layout = self.category_grid_widget.layout()

                            old_index = layout.indexOf(dragged_widget)
                            old_row, old_col, _, _ = layout.getItemPosition(old_index)

                            new_index = layout.indexOf(target_widget)
                            new_row, new_col, _, _ = layout.getItemPosition(new_index)

                            layout.removeWidget(dragged_widget)
                            layout.removeWidget(target_widget)

                            layout.addWidget(dragged_widget, new_row, new_col)
                            layout.addWidget(target_widget, old_row, old_col)

                            # Force repaint of the icons
                            dragged_widget.setIcon(dragged_widget.icon())
                            target_widget.setIcon(target_widget.icon())

                            event.acceptProposedAction()
                        else:
                            event.ignore()
                    else:
                        event.ignore()
                else:
                    event.ignore()
                return True

        return super().eventFilter(obj, event)

    def on_data_loaded(self):
        """Called when initial game data is loaded"""
        if self.game_database and len(self.game_database.get_all_categories()) > 0:
            # Update frames that depend on game_database
            # self.collection_frame.game_database = self.game_database
            if hasattr(self, "collection_set_frame"):
                self.collection_set_frame.game_database = self.game_database

            self.create_item_editors()
            self.create_category_grid()
            self.update_database_stats()
            self.set_status("Game data loaded successfully")

            # Auto-load save file
            self.load_save_file()
        else:
            source = str(self.settings.get("data_source", "dict")).lower()
            if source == "dict":
                msg = "No Dict data found. Please check the 'Dict' folder path in Settings."
                logger.error(msg)
                self.set_status(msg)
            else:
                msg = "No game data found. Categories will be unavailable."
                logger.error(msg)
                self.set_status(msg)
            QTimer.singleShot(5000, self._close_splash_and_show)

    def create_category_grid(self):
        """Creates the category selection grid."""
        self.category_grid_widget = QWidget()
        self.category_grid_widget.setAcceptDrops(True)
        self.category_grid_widget.installEventFilter(self)
        self.category_grid_widget.setStyleSheet("background-color: #2E2E2E;")
        layout = QGridLayout(self.category_grid_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        row, col = 0, 0

        # A map from our categories to the icon files
        icon_map = {
            ItemCategory.PETS: "pets.svg",
            ItemCategory.CLOTHES_OUTFITS: "clothing.svg",
            ItemCategory.CLOTHES_TOPS: "clothing.svg",
            ItemCategory.CLOTHES_BOTTOMS: "clothing.svg",
            ItemCategory.CLOTHES_HELMETS: "clothing.svg",
            ItemCategory.CLOTHES_SHOES: "clothing.svg",
            ItemCategory.CLOTHES_ACCESSORIES: "clothing.svg",
            ItemCategory.CLOTHES_OTHER: "clothing.svg",
            ItemCategory.HOUSE_SKINS: "house.svg",
            ItemCategory.HOUSE_WALLPAPER: "house.svg",
            ItemCategory.HOUSE_FLOORS: "house.svg",
            ItemCategory.NPC_HOUSES: "house.svg",
            ItemCategory.NPC_SKINS: "npc_skins.svg",
            ItemCategory.FURNITURE: "furniture.svg",
            ItemCategory.TOOLS: "tools.svg",
            ItemCategory.FOOD: "food.svg",
            ItemCategory.MATERIALS: "materials.svg",
            ItemCategory.MOTIFS: "motifs.svg",
            ItemCategory.GLIDERS: "gliders.svg",
            ItemCategory.MAKEUP: "makeup.svg",
            ItemCategory.TRIMMING: "trimming.svg",
            ItemCategory.ACTIVITY: "activity.svg",
            ItemCategory.SCRAMBLECOIN: "scramblecoin.svg",
            ItemCategory.AVATAR_FEATURES: "avatar_features.svg",
            ItemCategory.PHOTO_MODE: "photo_mode.svg",
            ItemCategory.MOUNT_GEAR: "mount_gear.svg",
        }

        self.button_style = """
            QToolButton {
                color: white;
                background-color: #3C3C3C;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                text-align: center;
            }
            QToolButton:hover {
                background-color: #4A4A4A;
            }
        """

        # Collect all possible draggable items with their default sorting
        all_draggable_items = []
        for category_enum in self.game_database.get_all_categories():
            # Exclude categories that might not have items
            if len(self.game_database.get_collection(category_enum)) > 0:
                all_draggable_items.append(self._humanize_category(category_enum))
        all_draggable_items.append("Player Inventory")  # Add special item

        # Apply saved order if available
        category_order_from_settings = self.settings.get("category_order", [])
        logger.debug(
            f"Loaded category order from settings: {category_order_from_settings}"
        )

        final_display_order = []
        seen_items = set()

        if category_order_from_settings:
            for item_name in category_order_from_settings:
                if item_name in all_draggable_items and item_name not in seen_items:
                    final_display_order.append(item_name)
                    seen_items.add(item_name)

        # Add any items not in the saved order (new categories or forgotten ones)
        for item_name in sorted(
            all_draggable_items, key=lambda x: x
        ):  # Sort new items alphabetically
            if item_name not in seen_items:
                final_display_order.append(item_name)

        logger.debug(f"Final display order for grid: {final_display_order}")

        for item_name in final_display_order:
            if item_name == "Player Inventory":
                inv_btn = DraggableButton()
                inv_btn.setObjectName("Player Inventory")
                inv_btn.setText("Player Inventory")
                inv_btn.setIcon(QIcon("images/icons/inventory.svg"))
                inv_btn.setIconSize(QSize(64, 64))
                inv_btn.setFixedSize(180, 150)
                inv_btn.setStyleSheet(self.button_style)
                inv_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                inv_btn.clicked.connect(self.show_inventory_editor)
                layout.addWidget(inv_btn, row, col)
            else:
                category = next(
                    cat
                    for cat in self.game_database.get_all_categories()
                    if self._humanize_category(cat) == item_name
                )
                collection = self.game_database.get_collection(category)
                if (
                    len(collection) == 0
                ):  # Should be caught by initial all_draggable_items filtering
                    continue

                btn = DraggableButton()
                btn.setObjectName(item_name)
                btn.setText(item_name)
                btn.setIcon(
                    QIcon(f"images/icons/{icon_map.get(category, 'unknown.svg')}")
                )
                btn.setIconSize(QSize(64, 64))
                btn.setFixedSize(180, 150)
                btn.setStyleSheet(self.button_style)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                btn.clicked.connect(
                    lambda checked, cat=category: self.show_item_editor(cat)
                )
                layout.addWidget(btn, row, col)

            col += 1
            if col > 4:
                col = 0
                row += 1

        self.central_stacked_widget.insertWidget(0, self.category_grid_widget)
        self.central_stacked_widget.setCurrentIndex(0)

    def show_item_editor(self, category: ItemCategory):
        """Shows the item editor for the given category."""
        if category in self.item_editor_frames:
            editor = self.item_editor_frames[category]
            self.central_stacked_widget.setCurrentWidget(editor)

    def show_category_grid(self):
        """Shows the category grid."""
        self.central_stacked_widget.setCurrentWidget(self.category_grid_widget)

    def show_inventory_editor(self):
        """Shows the player inventory editor."""
        for i in range(self.central_stacked_widget.count()):
            widget = self.central_stacked_widget.widget(i)
            if isinstance(widget, QWidget) and hasattr(widget, "tree"):
                self.central_stacked_widget.setCurrentWidget(widget)
                return

    def create_inventory_tab(self) -> QWidget:
        """Create the Inventory tab that shows player's inventory"""
        frame = QWidget()
        layout = QVBoxLayout(frame)

        # Add a back button
        back_btn = QPushButton("← Back to Categories")
        back_btn.clicked.connect(self.show_category_grid)
        layout.addWidget(back_btn)

        # Create a tree widget to display inventory items
        tree = QTreeWidget(frame)
        tree.setHeaderLabels(
            ["ID", "Name", "Amount", "Category", "Container", "Actions"]
        )
        tree.setAlternatingRowColors(True)
        tree.setUniformRowHeights(True)
        tree.setColumnCount(6)  # Updated from 5 to 6

        # Add tree widget to layout
        layout.addWidget(tree)

        # Configure column resizing
        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Amount
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Category
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Container
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Actions

        # Button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # Add refresh button
        refresh_btn = QPushButton("Refresh", frame)
        refresh_btn.clicked.connect(lambda: self.refresh_inventory_tab(frame))
        button_layout.addWidget(refresh_btn)

        # Add backpack size button
        size_btn = QPushButton("Set Backpack Size", frame)
        size_menu = QMenu(size_btn)
        size_btn.setMenu(size_menu)
        button_layout.addWidget(size_btn)

        # Add menu actions
        for size in [28, 35, 42]:
            action = QAction(f"Set to {size}", self)
            action.triggered.connect(
                lambda checked=False, s=size: self.set_backpack_size(s)
            )
            size_menu.addAction(action)

        size_menu.addSeparator()
        custom_action = QAction("Custom...", self)
        custom_action.triggered.connect(self.set_custom_backpack_size)
        size_menu.addAction(custom_action)

        # Add fix bag button
        fix_bag_btn = QPushButton("Fix Inventory Bag", frame)
        fix_bag_btn.clicked.connect(lambda: self._fix_main_inventory_bag(frame))
        button_layout.addWidget(fix_bag_btn)

        button_layout.addStretch()  # Push buttons to the left

        # Store tree reference
        frame.tree = tree

        # Connect double-click handler
        tree.itemDoubleClicked.connect(
            lambda item, col: self.edit_inventory_amount(frame)
        )

        # Store item data for saving
        frame.items = {}

        # Setup hover preview
        # Helper to resolve category from tree item text (col 3)
        def resolve_category(item_id, item: QTreeWidgetItem):
            cat_text = item.text(3)
            for category_enum in ItemCategory:
                if self._humanize_category(category_enum) == cat_text:
                    return category_enum
            logger.warning(f"Could not resolve ItemCategory for text: {cat_text}")
            return None  # Should ideally not happen if data is consistent

        frame.hover_behavior = HoverPreviewBehavior(
            tree, self.image_service, resolve_category
        )

        return frame

    def refresh_inventory_tab(self, frame: QWidget):
        """Refresh the inventory tab with current data"""
        if not self.save_service.current_save_data:
            return

        tree = frame.tree
        # Clear existing items
        tree.clear()

        # Use the parsed inventory items from save service, filtering for player backpack
        for item in self.save_service.current_save_data.inventory_items:
            # Only show items from player's main inventory (backpack, container id '0')
            if item.source_type == "container" and item.inventory_id == "0":
                item_id = str(item.item_id)
                if item_id and item_id != "0":  # Skip empty slots
                    name = self.get_item_name(int(item_id))
                    amount = item.amount
                    category = self.get_item_category(int(item_id))

                    # Create QTreeWidgetItem for the main item
                    tree_item = QTreeWidgetItem(tree)
                    tree_item.setText(0, item_id)
                    tree_item.setText(1, name)
                    tree_item.setText(2, str(amount))
                    tree_item.setText(3, category)

                    # Determine source inventory for display
                    inv_name = "Player Inventory"  # It's always player inventory here
                    tree_item.setText(4, inv_name)

                    # Store item object for saving/editing
                    tree_item.setData(0, Qt.ItemDataRole.UserRole, item)

                    # Add delete button to the "Actions" column
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    delete_btn = QPushButton("Delete")
                    delete_btn.setFixedSize(60, 20)  # Small fixed size for the button
                    # Use functools.partial to pass arguments to the slot
                    from functools import partial

                    delete_btn.clicked.connect(
                        partial(self._delete_inventory_item, item, frame)
                    )
                    actions_layout.addWidget(delete_btn)
                    actions_layout.addStretch()
                    tree.setItemWidget(tree_item, 5, actions_widget)

                    # If there's a state with ConsummableData, show that item's info too (read-only for now)
                    if isinstance(item.state, dict) and "ConsummableData" in item.state:
                        consumable = item.state["ConsummableData"]
                        cons_id = str(consumable.get("ItemID", ""))
                        if cons_id and cons_id != "0":
                            cons_name = self.get_item_name(int(cons_id))
                            cons_amount = consumable.get("Amount", 0)

                            # Create QTreeWidgetItem for the consumable
                            cons_item = QTreeWidgetItem(tree)
                            cons_item.setText(0, cons_id)
                            cons_item.setText(1, f"{cons_name} (in {name})")
                            cons_item.setText(2, str(cons_amount))
                            cons_item.setText(3, "Consumable")
                            cons_item.setText(4, inv_name)

                            # Add delete button for consumable as well
                            cons_item.setData(
                                0, Qt.ItemDataRole.UserRole, item
                            )  # Still delete the parent item
                            cons_actions_widget = QWidget()
                            cons_actions_layout = QHBoxLayout(cons_actions_widget)
                            cons_actions_layout.setContentsMargins(0, 0, 0, 0)
                            cons_delete_btn = QPushButton("Delete")
                            cons_delete_btn.setFixedSize(60, 20)
                            cons_delete_btn.clicked.connect(
                                partial(self._delete_inventory_item, item, frame)
                            )
                            cons_actions_layout.addWidget(cons_delete_btn)
                            cons_actions_layout.addStretch()
                            tree.setItemWidget(cons_item, 5, cons_actions_widget)

        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)

    def edit_inventory_amount(self, frame: QWidget):
        """Edit the amount of a selected item"""
        tree = frame.tree
        current_item = tree.currentItem()
        if not current_item:
            return

        # Get the PlayerInventoryItem object
        inventory_item = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not inventory_item:
            return

        name = current_item.text(1)
        current_amount = inventory_item.amount

        # Ask for new amount using QInputDialog
        from PyQt6.QtWidgets import QInputDialog

        new_amount, ok = QInputDialog.getInt(
            self,
            "Edit Amount",
            f"Enter new amount for {name}:",
            value=current_amount,
            min=0,
            max=99999,
        )

        if ok:
            # Update tree display
            current_item.setText(2, str(new_amount))
            # Update model
            inventory_item.amount = new_amount

    def set_backpack_size(self, size: int):
        """Set the player's backpack size."""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded.")
            return

        try:
            save_dict = self.save_service.current_save_data.custom_data.get(
                "original_save", {}
            )
            if "Player" in save_dict and "ContainerInventories" in save_dict["Player"]:
                if "0" in save_dict["Player"]["ContainerInventories"]:
                    save_dict["Player"]["ContainerInventories"]["0"]["Size"] = size
                    self.set_status(
                        f"Backpack size set to {size}. Save to apply changes."
                    )
                else:
                    QMessageBox.warning(
                        self, "Warning", "Player backpack inventory (ID 0) not found."
                    )
            else:
                QMessageBox.warning(
                    self, "Warning", "Could not find ContainerInventories in save data."
                )
        except Exception as e:
            logger.error(f"Error setting backpack size: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def set_custom_backpack_size(self):
        """Open a dialog to set a custom backpack size."""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded.")
            return

        current_size = 0
        try:
            save_dict = self.save_service.current_save_data.custom_data.get(
                "original_save", {}
            )
            current_size = save_dict["Player"]["ContainerInventories"]["0"]["Size"]
        except (KeyError, TypeError):
            pass

        new_size, ok = QInputDialog.getInt(
            self,
            "Set Custom Backpack Size",
            "Enter new backpack size:",
            value=current_size,
            min=1,
            max=200,  # A reasonable upper limit
        )

        if ok:
            if new_size > 42:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "The in-game maximum backpack size is 42. Setting a size greater than 42 may not be reflected in the game or may cause unexpected behavior.",
                )
            self.set_backpack_size(new_size)

    def _fix_main_inventory_bag(self, frame: QWidget):
        """Fixes the main inventory bag (ContainerInventories ID 0) by adjusting its size
        and removing excess non-quest items based on companion count."""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded.")
            return

        if not self.game_database:
            QMessageBox.warning(
                self,
                "Warning",
                "Game database not loaded. Cannot determine quest items.",
            )
            return

        save_data = self.save_service.current_save_data

        # 1. Determine companion count (only those following)
        assigned_pets = [p for p in save_data.pets if p.is_following]
        companion_count = len(assigned_pets)

        total_granted_slots = 0
        for pet in assigned_pets:
            total_granted_slots += pet.granted_inventory_slots

        # 2. Calculate expected bag size
        base_size = 42
        expected_size = base_size + total_granted_slots

        if companion_count == 0:
            bag_space_msg = "42 (0 companions)"
        elif companion_count == 1:
            bag_space_msg = "49 (1 companion)"
        else:  # 2 or more companions
            bag_space_msg = "56 (2+ companions)"

        logger.info(
            f"Fixing main inventory bag: {companion_count} companions -> expected size {expected_size}"
        )

        # 3. Identify Main Inventory Items and separate quest/non-quest
        all_player_inventory_items = save_data.inventory_items
        main_bag_items: List[PlayerInventoryItem] = []
        other_inventory_items: List[PlayerInventoryItem] = []

        for item in all_player_inventory_items:
            if item.source_type == "container" and item.inventory_id == "0":
                main_bag_items.append(item)
            else:
                other_inventory_items.append(item)

        # Filter out empty slots for actual item count
        actual_main_bag_items = [item for item in main_bag_items if item.item_id != 0]

        quest_items: List[PlayerInventoryItem] = []
        non_quest_items: List[PlayerInventoryItem] = []

        for player_item in actual_main_bag_items:
            game_item = self.game_database.get_item_by_id(player_item.item_id)
            if game_item and game_item.is_quest:
                quest_items.append(player_item)
            else:
                non_quest_items.append(player_item)

        current_physical_item_count = len(actual_main_bag_items)
        excess_items_count = current_physical_item_count - expected_size

        message = f"Current main inventory has {current_physical_item_count} items. Expected size: {expected_size}."
        if excess_items_count > 0:
            logger.info(
                f"Excess items found: {excess_items_count}. Attempting to remove non-quest items."
            )
            # Remove excess non-quest items
            items_removed = 0
            while items_removed < excess_items_count and non_quest_items:
                non_quest_items.pop()  # Remove from end
                items_removed += 1

            # Reconstruct the main bag items list with remaining non-quest items and all quest items
            items_to_keep = quest_items + non_quest_items

            # Warn if quest items prevent full truncation
            if len(items_to_keep) > expected_size:
                remaining_excess = len(items_to_keep) - expected_size
                QMessageBox.warning(
                    self,
                    "Inventory Fix Warning",
                    f"Warning: Your inventory still has {remaining_excess} too many items even after removing all non-quest items. "
                    "Quest items cannot be removed automatically. Please consider removing them manually if you wish to reach the exact target size.",
                )
                message += f"\nRemoved {items_removed} non-quest items. Still {remaining_excess} items over limit (quest items)."
                logger.warning(
                    f"Failed to fully truncate inventory due to {remaining_excess} quest items."
                )

            else:
                QMessageBox.information(
                    self,
                    "Inventory Fix",
                    f"Successfully resized your main inventory to {expected_size}. Removed {items_removed} excess non-quest items.",
                )
                message += f"\nRemoved {items_removed} excess non-quest items."
                logger.info(
                    f"Successfully truncated inventory. Final item count: {len(items_to_keep)}."
                )

            # Update save_data.inventory_items
            # Remove all original main_bag_items and add back the items_to_keep
            new_all_inventory_items = other_inventory_items + items_to_keep
            save_data.inventory_items = new_all_inventory_items

        else:
            message += "\nNo excess items found or items are below expected size. No items removed."
            QMessageBox.information(self, "Inventory Fix", message)
            logger.info("No excess items to remove from main inventory.")

        # 4. Update 'Size' in raw save data
        try:
            save_dict = save_data.custom_data.get("original_save", {})
            if "Player" in save_dict and "ContainerInventories" in save_dict["Player"]:
                if "0" in save_dict["Player"]["ContainerInventories"]:
                    save_dict["Player"]["ContainerInventories"]["0"][
                        "Size"
                    ] = expected_size
                    save_dict["Player"]["ContainerInventories"]["0"][
                        "ExtraBagSpace"
                    ] = total_granted_slots
                    logger.info(
                        f"Updated raw save data ContainerInventories ID 0 'Size' to {expected_size} and 'ExtraBagSpace' to {total_granted_slots}."
                    )
                    QMessageBox.information(
                        self,
                        "Inventory Fix",
                        f"Backpack size adjusted to {expected_size}. Remember to save the file to apply changes.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Player backpack inventory (ID 0) not found in raw save data.",
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Could not find ContainerInventories in raw save data.",
                )
        except Exception as e:
            logger.error(f"Error updating raw save data 'Size': {e}")
            QMessageBox.critical(
                self, "Error", f"Error updating raw save data 'Size': {e}"
            )

        # 5. Save the file and refresh UI
        self.set_status("Saving updated inventory...")

        def save_and_refresh():
            try:
                success, save_message = self.save_service.save_file()
                self.save_completed_signal.emit(success, save_message)
                if success:
                    # After saving, we need to re-parse the save_data to reflect the new size in the model
                    # This is important because save_file() rebuilds containerInventories, but not necessarily in-memory SaveData model
                    self.save_service.reparse_from_json(
                        self.save_service.current_save_data.custom_data.get(
                            "original_save", {}
                        )
                    )
                    self.data_refreshed_signal.emit()  # This will trigger refresh_inventory_tab
                else:
                    QMessageBox.critical(
                        self, "Save Error", f"Failed to save changes: {save_message}"
                    )
            except Exception as e:
                logger.error(f"Error during save and refresh: {e}")
                QMessageBox.critical(
                    self, "Error", f"An error occurred during save and refresh: {e}"
                )

                threading.Thread(target=save_and_refresh, daemon=True).start()

    def _delete_inventory_item(
        self, player_item_to_delete: PlayerInventoryItem, frame: QWidget
    ):
        """Deletes a specific PlayerInventoryItem from the current save data."""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded.")
            return

        item_name = self.get_item_name(player_item_to_delete.item_id)
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete '{item_name}' (ID: {player_item_to_delete.item_id}, Amount: {player_item_to_delete.amount}) from your inventory?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Create a new list excluding the item to delete
                new_inventory_items = [
                    item
                    for item in self.save_service.current_save_data.inventory_items
                    if not (
                        item == player_item_to_delete
                    )  # Pydantic model equality works for comparison
                ]
                self.save_service.current_save_data.inventory_items = (
                    new_inventory_items
                )

                # Save the file and refresh UI
                self.set_status(f"Deleting '{item_name}' and saving...")

                def save_and_refresh_after_delete():  # Renamed to avoid clash
                    try:
                        success, save_message = self.save_service.save_file()
                        self.save_completed_signal.emit(success, save_message)
                        if success:
                            # Re-parse to ensure UI reflects latest state, including potential re-sizing if relevant
                            self.save_service.reparse_from_json(
                                self.save_service.current_save_data.custom_data.get(
                                    "original_save", {}
                                )
                            )
                            self.data_refreshed_signal.emit()  # This will trigger refresh_inventory_tab
                            QMessageBox.information(
                                self,
                                "Deletion Successful",
                                f"'{item_name}' deleted and save updated.",
                            )
                        else:
                            QMessageBox.critical(
                                self,
                                "Save Error",
                                f"Failed to save changes after deletion: {save_message}",
                            )
                    except Exception as e:
                        logger.error(
                            f"Error during save and refresh after deletion: {e}"
                        )
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"An error occurred during save and refresh after deletion: {e}",
                        )

                threading.Thread(
                    target=save_and_refresh_after_delete, daemon=True
                ).start()

            except Exception as e:
                logger.error(f"Error deleting inventory item: {e}")
                QMessageBox.critical(
                    self, "Error", f"An error occurred while deleting the item: {e}"
                )
        else:
            logger.info("Item deletion cancelled by user.")

    def get_item_name(self, item_id: int) -> str:
        """Get the name of an item using the Dict service."""
        try:
            if hasattr(self, "dict_service"):
                return self.dict_service.get_item_name(item_id)
            return f"Item {item_id}"
        except Exception as e:
            logger.error(f"Error getting item name: {e}")
            return f"Item {item_id}"

    def get_inventory_category_name(self, inv_id: str) -> str:
        """Get category name for inventory ID"""
        categories = {
            "0": "Furniture",
            "1": "Clothes",
            "2": "Player Chest",
            "3": "Makeup",
            "4": "Trimming",
            "5": "Houses",
            "6": "Touch of Magic",
            "7": "NPC Skins",
            "8": "Board Games",
            "9": "Avatar Features",
            "10": "Photo Mode",
        }
        return categories.get(inv_id, "Unknown")

    def get_item_category(self, item_id: int) -> str:
        """Get the category of an item using the Dict service or prefix fallback."""
        try:
            if hasattr(self, "game_database") and self.game_database:
                for category in self.game_database.get_all_categories():
                    collection = self.game_database.get_collection(category)
                    if collection.get_item(item_id):
                        return category.value.replace("_", " ").title()

            # Fallback to ID-based categorization
            s = str(item_id)
            if s.startswith("10"):
                return "Motifs"
            if s.startswith("11"):
                return "Tools"
            if s.startswith("12"):
                return "Pets"
            if s.startswith("14"):
                return "Makeup"
            if s.startswith("16"):
                return "Trimming"
            if s.startswith("17"):
                return "NPC Skins"
            if s.startswith("18"):
                return "Board Games"
            if s.startswith("19"):
                return "Photo Mode"
            if s.startswith("20"):
                return "Houses"
            if s.startswith("21"):
                return "Tool Skins"
            if s.startswith("30"):
                return "Materials"
            if s.startswith("31"):
                return "Activity"
            if s.startswith("40"):
                return "Furniture"
            if s.startswith("50"):
                return "Clothing"
            if s.startswith("70"):
                return "Gliders"

            return "Unknown"
        except Exception as e:
            logger.error(f"Error getting item category: {e}")
            return "Unknown"

    def create_item_editors(self):
        """Create item editor frames and add them to the stacked widget."""
        if not self.game_database:
            return

        self.item_editor_frames.clear()

        for category in self.game_database.get_all_categories():
            collection = self.game_database.get_collection(category)
            if len(collection) == 0:
                continue

            frame = ItemEditorFrame(
                self,
                category,
                collection,
                self.image_service,
                self.save_service,
            )
            if self.save_service.current_save_data:
                frame.load_save_data(self.save_service.current_save_data)
            frame.back_button_clicked.connect(self.show_category_grid)
            self.item_editor_frames[category] = frame
            self.central_stacked_widget.addWidget(frame)

        # Add the Inventory tab at the end
        inventory_frame = self.create_inventory_tab()
        self.central_stacked_widget.addWidget(inventory_frame)

    def _update_danger_zone_tabs(self):
        """Add or remove danger zone tabs based on settings."""
        danger_zone_enabled = self.settings.get("danger_zone_enabled", False)
        logger.info(f"Updating danger zone tabs. Enabled: {danger_zone_enabled}")

        # Update the currency frame's internal state
        if hasattr(self, "currency_frame"):
            self.currency_frame.set_danger_zone_mode(danger_zone_enabled)

        # Conditionally add/remove the Battle Pass tab
        battle_pass_tab_exists = (
            hasattr(self, "battle_pass_frame")
            and self.central_stacked_widget.indexOf(self.battle_pass_frame) != -1
        )

        if danger_zone_enabled and not battle_pass_tab_exists:
            # Add the Battle Pass tab
            self.battle_pass_frame = BattlePassEditor(self.central_stacked_widget)
            # Insert it after the Currencies tab
            self.central_stacked_widget.insertWidget(1, self.battle_pass_frame)

            if self.save_service.current_save_data:
                self.battle_pass_frame.setData(
                    self.save_service.current_save_data.custom_data.get(
                        "original_save", {}
                    )
                )

        elif not danger_zone_enabled and battle_pass_tab_exists:
            # Remove the Battle Pass tab
            self.central_stacked_widget.removeWidget(self.battle_pass_frame)
            del self.battle_pass_frame

    def show_settings(self):
        """Show settings dialog"""
        logger.info("User opened the settings dialog.")
        # Preload dialog with current settings
        dialog = SettingsDialog(self, initial_settings=self.settings)
        if dialog.exec():
            logger.info("User saved new settings.")
            # Persist settings
            new_settings = dialog.get_settings()
            # Ensure hex_key is preserved if dialog returns it
            if "hex_key" not in new_settings and "hex_key" in self.settings:
                new_settings["hex_key"] = self.settings["hex_key"]
            self.settings = {**self.settings, **new_settings}
            self.settings_service.save(self.settings)

            # Apply settings live

            # Image paths and cache
            if self.settings.get("image_zip_path"):
                self.image_service.zip_path = Path(self.settings["image_zip_path"])
            if self.settings.get("image_folder_path"):
                self.image_service.folder_path = Path(
                    self.settings["image_folder_path"]
                )
            if "cache_size" in self.settings:
                try:
                    self.image_service.cache_size_limit = int(
                        self.settings["cache_size"]
                    )
                except Exception:
                    pass
            # Image sizes
            from ..services.settings_service import SettingsService as _SS2

            self.image_service.thumbnail_size = _SS2.parse_size(
                self.settings.get("thumbnail_size", "64x64"), (64, 64)
            )
            self.image_service.preview_size = _SS2.parse_size(
                self.settings.get("preview_size", "128x128"), (128, 128)
            )
            # Refresh image catalog
            self.image_service.refresh_available_images()

            # Backup retention
            if "max_backups" in self.settings:
                try:
                    self.save_service.max_backups = int(self.settings["max_backups"])
                except Exception:
                    pass

            # Decryption key
            if "hex_key" in self.settings:
                self.default_hex_key = str(self.settings["hex_key"])

            # Update UI based on new settings
            self._update_danger_zone_tabs()
            self._apply_stylesheet(self.settings.get("theme", "dark"))

    def show_backup_manager(self):
        """Show backup manager dialog"""
        logger.info("User opened the backup manager.")
        # This would be implemented as a separate dialog
        backups = self.save_service.get_backup_list()
        if not backups:
            QMessageBox.information(self, "Backup Manager", "No backups found")
            logger.info("No backups found.")
            return

        # For now, just show backup count
        QMessageBox.information(
            self, "Backup Manager", f"Found {len(backups)} backup files"
        )
        logger.info(f"Found {len(backups)} backup files.")

    def validate_save_file(self):
        """Validate the current save file"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            logger.warning("Validation requested but no save file loaded.")
            return

        logger.info("User requested to validate the current save file.")
        save_data = self.save_service.current_save_data
        issues = []

    def clear_image_cache(self):
        """Clear image cache"""
        logger.info("User requested to clear the image cache.")
        self.image_service.clear_cache()
        self.set_status("Image cache cleared")
        logger.info("Image cache cleared.")

    def show_full_editor(self):
        """Show full editor window"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            logger.warning("Full editor requested but no save file loaded.")
            return

        logger.info("User opened the full editor window.")
        # Get the raw save data
        save_dict = self.save_service.current_save_data.custom_data.get(
            "original_save", {}
        )

        # Create and show the full editor window
        from .full_editor import FullEditorWindow

        editor = FullEditorWindow(self, self.dict_service)
        editor.load_json(save_dict)

        # Set up callback for when data is modified
        def on_data_changed():
            try:
                # Update the save data when JSON is modified
                new_data = editor.get_json_data()
                self.save_service.current_save_data.custom_data["original_save"] = (
                    new_data
                )

                # Re-parse the save data to update the model (inventory, currencies, etc.)
                self.save_service.reparse_from_json(new_data)

                # Refresh all UI components
                self.on_save_loaded(True, "Refreshed from Full Editor")

            except Exception as e:
                logger.error(f"Error updating save data from Full Editor: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update save data: {e}")

        editor.on_modified_callback = on_data_changed
        editor.exec()

    def show_json_viewer(self):
        """Show JSON viewer window"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return

        logger.info("User opened the JSON viewer window.")
        # Get the raw save data
        save_dict = self.save_service.current_save_data.custom_data.get(
            "original_save", {}
        )

        # Create and show the JSON viewer window
        viewer = JsonViewerWindow(self)

        # Set size relative to main window
        main_size = self.size()
        viewer.resize(int(main_size.width() * 0.7), int(main_size.height() * 0.7))

        viewer.load_json(save_dict)

        # Set up callback for when JSON is modified
        def on_json_changed():
            try:
                # Update the save data when JSON is modified
                new_data = viewer.get_json_data()
                self.save_service.current_save_data.custom_data["original_save"] = (
                    new_data
                )
                self.set_status("Save data updated from JSON viewer")
            except Exception as e:
                logger.error(f"Error updating save data from JSON viewer: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update save data: {e}")

        viewer.on_modified_callback = on_json_changed
        viewer.exec()

    def show_about(self):
        """Show about dialog"""
        logger.info("User opened the about dialog.")
        QMessageBox.information(
            self,
            "About DDV Save Editor",
            "DDV Save Editor - Python Version\n"
            "A tool for editing Disney Dreamlight Valley save files\n\n"
            "Features:\n"
            "• Load and save encrypted save files\n"
            "• Image previews for items\n"
            "• Automatic backups\n"
            "• Modern Python GUI",
        )

    def add_specific_tool(self, tool_id: int, current_of_type: bool = False):
        """Add a specific tool to the player's inventory"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return False

        logger.info(f"User requested to add specific tool: {tool_id}")
        try:
            # Get the raw save data
            save_dict = self.save_service.current_save_data.custom_data.get(
                "original_save", {}
            )

            # Add tool
            success = add_specific_tool(save_dict, tool_id, current_of_type)

            # Update the save data
            self.save_service.current_save_data.custom_data["original_save"] = save_dict

            # Show results
            if success:
                QMessageBox.information(
                    self, "Tool Added", f"Successfully added tool {tool_id}"
                )
            else:
                QMessageBox.information(self, "Tool", f"Tool {tool_id} already exists")

            return success

        except Exception as e:
            logger.error(f"Error adding tool: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add tool: {e}")
            return False

    def add_basic_tools(self):
        """Add a basic set of tools to the player's inventory"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return

        logger.info("User requested to add basic tools.")
        try:
            # Get the raw save data
            save_dict = self.save_service.current_save_data.custom_data.get(
                "original_save", {}
            )

            # Add tools
            result = add_basic_tools(save_dict)

            # Update the save data
            self.save_service.current_save_data.custom_data["original_save"] = save_dict

            # Show results
            if result["tools_added"] > 0:
                added_tools = "\n".join(f"• {tool}" for tool in result["added_tools"])
                QMessageBox.information(
                    self,
                    "Tools Added",
                    f"Added {result['tools_added']} tools:\n\n{added_tools}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Tools",
                    "No new tools needed - all basic tools already present",
                )

        except Exception as e:
            logger.error(f"Error adding tools: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add tools: {e}")

    def augment_save_with_legacy_dicts(self):
        """Add missing clothes, houses, and NPC skins to the loaded save using legacy C# dicts.
        This mirrors the behavior in EditPets.cs but applies safely to the current Python model.
        """
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return

        logger.info("User requested to augment save with legacy dicts.")
        # Locate legacy C# dictionary files
        try:
            repo_root = Path(__file__).resolve().parents[2]
            dicts_dir = (
                repo_root / "Ddv-Save-Editor" / "fast edit ddv" / "Class" / "Dict"
            )
            clothes_cs = dicts_dir / "Clothes.cs"
            houses_cs = dicts_dir / "Houses.cs"
            skins_cs = dicts_dir / "SkinsNpc.cs"
        except Exception as e:
            logger.error(f"Failed to resolve legacy dict paths: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to resolve legacy dict paths: {e}"
            )
            return

        if not (clothes_cs.exists() and houses_cs.exists() and skins_cs.exists()):
            QMessageBox.critical(
                self,
                "Error",
                "Legacy C# dictionaries not found. Ensure 'Ddv-Save-Editor/fast edit ddv/Class/Dict/*.cs' exist.",
            )
            return

        self.set_status("Augmenting save with legacy dictionaries...")
        self.show_progress()

        def do_augment():
            try:
                # Work on a direct dict copy of the original save
                save_dict = self.save_service.current_save_data.custom_data.get(
                    "original_save"
                )
                if not isinstance(save_dict, dict):
                    raise RuntimeError("Original save dictionary is not available")

                # Snapshot of existing keys for the targeted inventories
                def inv_keys(d: Dict[str, Any], inv_id: str) -> set:
                    try:
                        return set(
                            (
                                d.get("Player", {})
                                .get("ListInventories", {})
                                .get(inv_id, {})
                                .get("Inventory", {})
                                or {}
                            ).keys()
                        )
                    except Exception:
                        return set()

                before_1 = inv_keys(save_dict, "1")
                before_5 = inv_keys(save_dict, "5")
                before_7 = inv_keys(save_dict, "7")

                summary = augment_save_dict(
                    save_dict,
                    add_clothes=True,
                    add_houses=True,
                    add_skins=True,
                    inventory_for_clothes="1",
                    inventory_for_houses="5",
                    inventory_for_skins="7",
                    amount=1,
                    mode="missing-only",
                    clothes_cs_path=clothes_cs,
                    houses_cs_path=houses_cs,
                    skins_cs_path=skins_cs,
                )

                after_1 = inv_keys(save_dict, "1")
                after_5 = inv_keys(save_dict, "5")
                after_7 = inv_keys(save_dict, "7")

                added_1 = after_1 - before_1
                added_5 = after_5 - before_5
                added_7 = after_7 - before_7

                # Reflect additions into the in-memory SaveData model so save() will persist them
                from ..models.game_item import PlayerInventoryItem

                def add_items_to_model(inv_id: str, keys: set):
                    for k in keys:
                        try:
                            item_id = int(k)
                        except ValueError:
                            continue
                        # Avoid duplicates in model list
                        exists = any(
                            (
                                itm.item_id == item_id
                                and (itm.inventory_id or "1") == inv_id
                            )
                            for itm in self.save_service.current_save_data.inventory_items
                        )
                        if not exists:
                            self.save_service.current_save_data.inventory_items.append(
                                PlayerInventoryItem(
                                    item_id=item_id,
                                    amount=1,
                                    state=None,
                                    inventory_id=inv_id,
                                )
                            )

                add_items_to_model("1", added_1)
                add_items_to_model("5", added_5)
                add_items_to_model("7", added_7)

                # Update original save dict reference
                self.save_service.current_save_data.custom_data["original_save"] = (
                    save_dict
                )

                msg = (
                    f"Clothes added: {summary['clothes_added']}, Houses added: {summary['houses_added']}, "
                    f"NPC skins added: {summary['skins_added']}"
                )
                logger.info(f"Augmentation complete: {msg}")
                QTimer.singleShot(
                    0,
                    lambda: [
                        self.set_status("Augmentation complete"),
                        self.hide_progress(),
                        QMessageBox.information(self, "Augment Save", msg),
                    ],
                )
            except Exception as e:
                logger.error(f"Augmentation failed: {e}")
                QTimer.singleShot(
                    0,
                    lambda: [
                        self.set_status("Augmentation failed"),
                        self.hide_progress(),
                        QMessageBox.critical(
                            self, "Error", f"Augmentation failed: {e}"
                        ),
                    ],
                )

        threading.Thread(target=do_augment, daemon=True).start()

    def set_status(self, text: str):
        """Set status bar text"""
        self.status_text.setText(text)
        QApplication.processEvents()

    def show_progress(self):
        """Show progress bar"""
        self.progress.setRange(0, 0)  # Indeterminate mode
        self.progress.show()

    def hide_progress(self):
        """Hide progress bar"""
        self.progress.hide()
        self.progress.setRange(0, 100)  # Reset to determinate mode

    def update_database_stats(self):
        """Update database statistics display"""
        if self.game_database:
            stats = self.game_database.get_stats()
            source = str(self.settings.get("data_source", "excel")).title()
            text = f"Items: {stats['total_items']} | Categories: {stats['categories']} | Source: {source}"
            self.db_stats_label.setText(text)
        else:
            self.db_stats_label.setText("")

    def on_data_source_changed(self, source: str):
        """Handle change in data source (only Dict remains)"""
        source = source.lower()

        # Save setting
        self.settings["data_source"] = source
        self.settings_service.save(self.settings)
        logger.info(f"Data source changed to: {source}")

        self.refresh_game_data()

    def choose_dict_folder(self):
        """Prompt user to choose Dict root and persist it"""
        logger.info("User requested to choose a Dict folder/file.")

        current_dict_root = self.settings.get("dict_root", "")
        chosen_path = ""

        while not chosen_path:
            # Try to get a directory first
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select 'Dict' Folder",
                (
                    str(Path(current_dict_root).parent)
                    if current_dict_root
                    else os.getcwd()
                ),
            )

            if folder:
                folder_path_obj = Path(folder)
                if folder_path_obj.name == "Dict" and folder_path_obj.is_dir():
                    chosen_path = str(folder_path_obj)
                else:
                    QMessageBox.warning(
                        self,
                        "Invalid Selection",
                        "You must select the folder named 'Dict'.",
                    )

            if (
                not chosen_path
            ):  # If directory selection failed or was invalid, try for Dict.zip
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select 'Dict.zip' File",
                    (
                        str(Path(current_dict_root).parent)
                        if current_dict_root
                        else os.getcwd()
                    ),
                    "Dict Zip File (Dict.zip);;All Files (*.*)",
                )

                if file_path:
                    file_path_obj = Path(file_path)
                    if file_path_obj.name == "Dict.zip" and file_path_obj.is_file():
                        chosen_path = str(file_path_obj)
                    else:
                        QMessageBox.warning(
                            self,
                            "Invalid Selection",
                            "You must select the 'Dict.zip' file.",
                        )

            if not chosen_path:
                reply = QMessageBox.question(
                    self,
                    "Selection Cancelled",
                    "No valid Dict data source selected. Continue without Dict data? "
                    "Some features may not work correctly.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    break  # User explicitly chose to continue without selecting a valid path
                # Else, loop again to prompt for selection

        if chosen_path:
            logger.info(f"User selected Dict path: {chosen_path}")
            self.settings["dict_root"] = chosen_path
            self.settings_service.save(self.settings)

            # Update service and reload
            try:
                self.dict_service.dict_root = Path(chosen_path)
                # If Dict is selected, refresh now
                if str(self.settings.get("data_source", "excel")).lower() == "dict":
                    self.refresh_game_data()
            except Exception as e:
                logger.error(f"Error updating DictDataService with new path: {e}")
                QMessageBox.critical(
                    self, "Error", f"Failed to update Dict service: {e}"
                )
        else:
            logger.info(
                "User cancelled Dict folder/file selection or chose to proceed without valid data."
            )

    def _close_splash_and_show(self):
        """Finish the splash screen and show the main window."""
        if self.splash_handler:
            logging.getLogger().removeHandler(self.splash_handler)
            self.splash_handler = None
        if self.splash:
            self.splash.finish(self)
            self.splash = None  # Prevent multiple calls
        self.show()

    def on_closing(self, event):
        """Handle window closing"""
        logger.info("Application closing.")
        try:
            # Cleanup services
            self.image_service.close()
            event.accept()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            event.accept()

    def run(self):
        """Start the application."""
        # The window is now shown via _close_splash_and_show() after loading.
        pass

    def cache_current_category_images(self):
        """Download and cache online images for all items in the visible category."""
        try:
            frame = self._get_active_item_editor_frame()
            if frame is None:
                QMessageBox.information(
                    self, "Cache Images", "Open a category tab to cache its images."
                )
                return

            logger.info(
                f"User requested to cache images for category: {frame.category.name}"
            )
            collection = frame.collection
            ids_and_names = [(gi.id, gi.name) for gi in collection]
            total = len(ids_and_names)
            if total == 0:
                QMessageBox.information(
                    self, "Cache Images", "No items to cache in this category."
                )
                return
            self.set_status(f"Caching images for {total} items...")
            self.show_progress()

            def worker():
                done = 0
                for item_id, name in ids_and_names:
                    try:
                        self.image_service.cache_image_for_item(
                            item_id, name, frame.category
                        )
                    except Exception:
                        pass
                    done += 1
                QTimer.singleShot(
                    0,
                    lambda: [
                        self.hide_progress(),
                        self.set_status("Caching complete"),
                        QMessageBox.information(
                            self,
                            "Cache Images",
                            f"Cached images for {total} items (where available)",
                        ),
                    ],
                )

            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            logger.error(f"Error caching images: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _humanize_category(self, category: ItemCategory) -> str:
        """Make a user-friendly name from enum value (remove underscores, title case, fix abbreviations)."""
        name = category.value.replace("_", " ").title()
        # Fix common abbreviations
        name = name.replace("Npc", "NPC")
        return name

    def load_save_file(self):
        """Load a save file - first try auto-detection, then manual selection"""
        logger.info("Load save file requested")

        # First try auto-detection
        if self._try_auto_load():
            return

        # If auto-detection fails, show manual file dialog
        logger.info("Auto-detection failed, showing file dialog")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            caption="Select DDV Save File",
            filter="JSON files (*.json);;All files (*.*)",
            directory=str(Path.home() / "AppData" / "LocalLow"),
        )

        if not file_path:
            msg = "User cancelled save file selection. Application will start without a loaded save."
            logger.warning(msg) # Using warning level to make it visible
            self.set_status(msg) # Update status bar too
            QTimer.singleShot(5000, self._close_splash_and_show)
            return

        self._load_specific_file(file_path)

    def _try_auto_load(self) -> bool:
        """Try to automatically load the latest save file"""
        logger.info("Attempting automatic save file detection...")
        self.set_status("Auto-detecting latest save file...")

        def auto_load(latest_path: str):
            try:
                # Try with the known DDV key first using the already-detected path
                known_ddv_key = getattr(
                    self,
                    "default_hex_key",
                    "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35",
                )
                logger.info(f"Auto-loading: {latest_path}")
                success, message = self.save_service.load_save_file(
                    latest_path, known_ddv_key
                )
                self.save_loaded_signal.emit(success, message)
            except Exception as e:
                logger.error(f"Error in auto-load: {e}")
                self.save_loaded_signal.emit(False, str(e))

        # Check if auto-detection can find a save file
        latest_save_path = self.save_service.find_latest_save_file()
        if latest_save_path:
            logger.info(f"Auto-detected save file: {latest_save_path}")
            self.show_progress()
            threading.Thread(
                target=lambda: auto_load(latest_save_path), daemon=True
            ).start()
            return True
        else:
            logger.info("No save files found for auto-detection")
            self.set_status("No save files found - please select manually")
            return False

    def _load_specific_file(self, file_path: str):
        """Load a specific file (manual selection)"""
        logger.info(f"Loading manually selected file: {file_path}")

        # Check if file is encrypted
        if self.save_service.is_file_encrypted(Path(file_path)):
            # Try the known DDV key first (from settings or CyberChef configuration)
            known_ddv_key = getattr(
                self,
                "default_hex_key",
                "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35",
            )

            self.set_status("Trying known DDV decryption key...")
            logger.info("Attempting decryption with known DDV key...")

            # First try with known key
            success, message = self.save_service.load_save_file(
                file_path, known_ddv_key
            )

            if success:
                logger.info("Successfully decrypted with known DDV key!")
                self.on_save_loaded(success, message)
                return
            else:
                logger.info("Known DDV key failed, prompting user for key...")
                # If known key fails, ask user for decryption key
                key, ok = QInputDialog.getText(
                    self,
                    "Decryption Key Required",
                    "The standard DDV key didn't work.\nEnter the hexadecimal decryption key for this save file:",
                    QLineEdit.EchoMode.Password,
                )
                if not ok or not key:
                    logger.info("User cancelled decryption key entry.")
                    return
        else:
            key = None

        self.set_status("Loading save file...")
        self.show_progress()

        def load_save():
            try:
                success, message = self.save_service.load_save_file(file_path, key)
                self.save_loaded_signal.emit(success, message)
            except Exception as e:
                logger.error(f"Error loading save: {e}")
                self.save_loaded_signal.emit(False, str(e))

        threading.Thread(target=load_save, daemon=True).start()

    def load_save_file_manual(self):
        """Load a save file with manual file selection (no auto-detection)"""
        logger.info("Manual save file selection requested")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            caption="Select DDV Save File",
            filter="JSON files (*.json);;All files (*.*)",
            directory=str(Path.home() / "AppData" / "LocalLow"),
        )

        if not file_path:
            logger.info("User cancelled manual save file selection.")
            return

        self._load_specific_file(file_path)

    def on_save_loaded(self, success: bool, message: str):
        """Called when save file loading completes"""
        self.hide_progress()

        if success:
            logger.info(
                f"Save file loading completed. Success: {success}, Message: {message}"
            )
            self.set_status("Save file loaded successfully")
            self.status_indicator.setStyleSheet("color: green")
            self.status_label.setText("Save loaded")

            # Update danger zone frames only if they exist
            if hasattr(self, "currency_frame"):
                self.currency_frame.load_save_data(self.save_service.current_save_data)
            if hasattr(self, "battle_pass_frame"):
                self.battle_pass_frame.setData(
                    self.save_service.current_save_data.custom_data.get(
                        "original_save", {}
                    )
                )

            # Update collection editor
            # self.collection_frame.load_save_data(self.save_service.current_save_data)

            # Update collection set editor
            self.collection_set_frame.load_save_data(
                self.save_service.current_save_data
            )

            # Update item editors
            for frame in self.item_editor_frames.values():
                frame.load_save_data(self.save_service.current_save_data)

            # Update inventory tab
            for i in range(self.central_stacked_widget.count()):
                widget = self.central_stacked_widget.widget(i)
                if isinstance(widget, QWidget) and hasattr(widget, "tree"):
                    self.refresh_inventory_tab(widget)
                    break
            self._close_splash_and_show()
            # ToastNotification(self.root, f"Save loaded: {message}")
        else:
            logger.error(f"Failed to load save: {message}")
            self.set_status(f"Failed to load save: {message}")
            QTimer.singleShot(5000, self._close_splash_and_show)

    def save_file(self):
        """Save the current save file"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return

        logger.info("User requested to save the current file.")
        self.set_status("Saving file...")

        def save_data():
            try:
                # Update save data from editors, only if they exist
                if hasattr(self, "currency_frame"):
                    self.currency_frame.update_save_data()

                if hasattr(self, "battle_pass_frame"):
                    battle_pass_data = self.battle_pass_frame.getData()
                    if battle_pass_data:
                        save_dict = self.save_service.current_save_data.custom_data.get(
                            "original_save", {}
                        )
                        player_data = save_dict.setdefault("Player", {})
                        bp_states = player_data.setdefault("BattlePassStates", {})
                        bp_progress = bp_states.setdefault("Progress", {})

                        new_progress = (
                            battle_pass_data.get("Player", {})
                            .get("BattlePassStates", {})
                            .get("Progress", {})
                        )
                        if new_progress:
                            bp_progress.update(new_progress)

                        self.save_service.current_save_data.custom_data[
                            "original_save"
                        ] = save_dict

                # Merge updates from either category tabs or Search tab per category
                frames_by_category = dict(self.item_editor_frames)
                # Check for an existing Search tab
                try:
                    for i in range(self.central_stacked_widget.count()):
                        widget = self.central_stacked_widget.widget(i)
                        from .search_results import SearchResultsFrame as _SRF

                        if isinstance(widget, _SRF):
                            # Override categories with search subframes
                            for cat, sub in widget.category_frames.items():
                                frames_by_category[cat] = sub
                            break
                except Exception:
                    pass
                # Apply updates per category
                for frame in frames_by_category.values():
                    frame.update_save_data()

                success, message = self.save_service.save_file()
                self.save_completed_signal.emit(success, message)
            except Exception as e:
                logger.error(f"Error saving: {e}")
                self.save_completed_signal.emit(False, str(e))

        threading.Thread(target=save_data, daemon=True).start()

    def save_file_as(self):
        """Save the current save file to a new location"""
        if not self.save_service.current_save_data:
            QMessageBox.warning(self, "Warning", "No save file loaded")
            return

        logger.info("User requested to save the current file to a new location.")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save DDV Save File As",
            filter="JSON files (*.json);;All files (*.*)",
            directory=str(Path.home() / "AppData" / "LocalLow"),
        )

        if not file_path:
            logger.info("User cancelled 'Save As' operation.")
            return

        logger.info(f"User selected new save file location: {file_path}")
        self.set_status("Saving file...")

        def save_data():
            try:
                # Update save data from editors, only if they exist
                if hasattr(self, "currency_frame"):
                    self.currency_frame.update_save_data()

                frames_by_category = dict(self.item_editor_frames)
                try:
                    for i in range(self.central_stacked_widget.count()):
                        widget = self.central_stacked_widget.widget(i)
                        from .search_results import SearchResultsFrame as _SRF

                        if isinstance(widget, _SRF):
                            for cat, sub in widget.category_frames.items():
                                frames_by_category[cat] = sub
                            break
                except Exception:
                    pass
                for frame in frames_by_category.values():
                    frame.update_save_data()

                success, message = self.save_service.save_file(file_path)
                self.save_completed_signal.emit(success, message)
            except Exception as e:
                logger.error(f"Error saving: {e}")
                self.save_completed_signal.emit(False, str(e))

        threading.Thread(target=save_data, daemon=True).start()

    def on_save_completed(self, success: bool, message: str):
        """Called when save operation completes"""
        logger.info(f"Save completed. Success: {success}, Message: {message}")
        if success:
            self.set_status("Save completed successfully")
            # ToastNotification(self.root, f"Save successful: {message}")
            # Reload editors from model so every tab reflects the saved state
            try:
                if self.save_service.current_save_data:
                    self.currency_frame.load_save_data(
                        self.save_service.current_save_data
                    )
                    for frame in self.item_editor_frames.values():
                        frame.load_save_data(self.save_service.current_save_data)
                    # Refresh Search tab subframes if present
                    for i in range(self.central_stacked_widget.count()):
                        widget = self.central_stacked_widget.widget(i)
                        from .search_results import SearchResultsFrame as _SRF

                        if isinstance(widget, _SRF):
                            for sub in widget.category_frames.values():
                                sub.load_save_data(self.save_service.current_save_data)
                            break
            except Exception:
                pass
        else:
            self.set_status(f"Save failed: {message}")
            QMessageBox.critical(self, "Error", f"Error saving: {message}")

    def refresh_game_data(self):
        """Refresh game data from the selected source (now only Dict)"""
        # Since Excel data loading is removed, we only refresh from Dict.
        source = str(
            self.settings.get("data_source", "dict")
        ).lower()  # Ensure default is dict
        logger.info(f"Refreshing data from source: {source}")
        self.set_status(f"Refreshing Dict data...")
        self.show_progress()

        def refresh_data_thread():  # Renamed inner function to avoid confusion
            try:
                self.game_database = self.dict_service.load_game_database(
                    force_reload=True
                )
                self.data_refreshed_signal.emit()
            except Exception as e:
                logger.error(f"Error refreshing data: {e}")
                self.status_signal.emit(f"Error refreshing data: {e}")

        threading.Thread(target=refresh_data_thread, daemon=True).start()

    def on_data_refreshed(self):
        """Called when game data refresh completes"""
        logger.info("Data refresh completed.")
        self.hide_progress()
        if self.game_database:
            # self.collection_frame.game_database = self.game_database
            if hasattr(self, "collection_set_frame"):
                self.collection_set_frame.game_database = self.game_database
        self.create_item_editors()
        self.create_category_grid()
        self.update_database_stats()
        self.set_status("Data loaded successfully")

        # Auto-load save file if not already loaded
        if not self.save_service.current_save_data:
            self.load_save_file()

    def on_search(self, event=None):
        """Handle search"""
        query = self.search_entry.text().strip()
        if not query or not self.game_database:
            return

        results = self.game_database.search_all_items(query)
        # If empty, inform and bail
        total = sum(len(v) for v in results.values()) if results else 0
        if total == 0:
            QMessageBox.information(self, "Search", f"No items found for '{query}'")
            return

        # Either create or update a dedicated Search tab
        self._open_search_tab(results)

    def _open_search_tab(self, results: Dict[ItemCategory, list]):
        # If a Search tab exists, refresh it; else create one
        existing_index = None
        for i in range(self.central_stacked_widget.count()):
            widget = self.central_stacked_widget.widget(i)
            if isinstance(widget, SearchResultsFrame):
                existing_index = i
                break
        if existing_index is not None:
            # Tab already exists; refresh its content
            widget = self.central_stacked_widget.widget(existing_index)
            if isinstance(widget, SearchResultsFrame):
                widget.refresh_with(results)
            self.central_stacked_widget.setCurrentIndex(existing_index)
            return
        # Create a new tab
        search_frame = SearchResultsFrame(
            self, results, self.image_service, self.save_service
        )
        total = sum(len(v) for v in results.values())
        self.central_stacked_widget.addWidget(search_frame)
        self.central_stacked_widget.setCurrentWidget(search_frame)

    def add_all_items(self):
        """Add all items from current category to save"""
        logger.info("User requested to add all items from the current category.")
        frame = self._get_active_item_editor_frame()
        if frame:
            frame.add_all_items()

    def clear_all_items(self):
        """Clear all items from current category"""
        logger.info("User requested to clear all items from the current category.")
        if (
            QMessageBox.question(
                self, "Confirm", "Clear all items from current category?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            logger.info("User confirmed clearing all items.")
            frame = self._get_active_item_editor_frame()
            if frame:
                frame.clear_all_items()
        else:
            logger.info("User cancelled clearing all items.")

    def _get_active_item_editor_frame(self) -> ItemEditorFrame | None:
        """Resolve the currently visible ItemEditorFrame, accounting for the stacked widget."""
        current_widget = self.central_stacked_widget.currentWidget()
        if isinstance(current_widget, ItemEditorFrame):
            return current_widget
        return None

    @pyqtSlot(bool, str)
    def handle_save_loaded(self, success: bool, message: str):
        """Slot to handle save loaded (thread-safe)"""
        self.on_save_loaded(success, message)

    @pyqtSlot(bool, str)
    def handle_save_completed(self, success: bool, message: str):
        """Slot to handle save completed (thread-safe)"""
        self.on_save_completed(success, message)

    @pyqtSlot()
    def handle_data_refreshed(self):
        """Slot to handle data refreshed (thread-safe)"""
        self.on_data_refreshed()

    @pyqtSlot(str)
    def handle_status_update(self, message: str):
        """Slot to handle status updates (thread-safe)"""
        self.set_status(message)

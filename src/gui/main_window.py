"""
Main GUI window for DDV Save Editor
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import font as tkfont
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import threading

from ..services.excel_service import ExcelDataService
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.augmentation_service import augment_save_dict
from ..models.game_item import GameDatabase, ItemCategory
from .item_editor import ItemEditorFrame
from .currency_editor import CurrencyEditorFrame
from .settings_dialog import SettingsDialog


logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DDV Save Editor - Python")
        self.root.geometry("1200x800")
        
        # Visual theme and scaling first
        self.setup_theme()

        # Services
        self.excel_service = ExcelDataService()
        self.image_service = ImageService()
        self.save_service = SaveFileService()
        
        # Data
        self.game_database: Optional[GameDatabase] = None
        self.current_category = ItemCategory.PETS
        
        # UI Components
        self.setup_menu()
        self.setup_main_layout()
        self.setup_status_bar()
        
        # Initialize
        self.load_initial_data()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_menu(self):
        """Setup main menu bar"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Auto-Load Latest Save", command=self.load_save_file)
        file_menu.add_command(label="Load Save File Manually...", command=self.load_save_file_manual)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Load Excel Data...", command=self.load_excel_data)
        file_menu.add_command(label="Refresh Excel Data", command=self.refresh_excel_data, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add All Items", command=self.add_all_items)
        edit_menu.add_command(label="Clear All Items", command=self.clear_all_items)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings...", command=self.show_settings)
        
        # Tools menu
        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Backup Manager...", command=self.show_backup_manager)
        tools_menu.add_command(label="Validate Save File", command=self.validate_save_file)
        tools_menu.add_command(label="Clear Image Cache", command=self.clear_image_cache)
        tools_menu.add_separator()
        tools_menu.add_command(label="Augment Save (legacy dicts)", command=self.augment_save_with_legacy_dicts)
        
        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.refresh_excel_data())

    def setup_theme(self):
        """Set a modern ttk theme, fonts, and scaling for a cleaner look"""
        try:
            # High-DPI friendly scaling
            try:
                # Lightly upscale for readability on modern displays
                current = float(self.root.tk.call('tk', 'scaling'))
                if current < 1.25:
                    self.root.tk.call('tk', 'scaling', 1.25)
            except Exception:
                pass

            style = ttk.Style(self.root)
            # Prefer native Windows theme if available, fallback to 'clam'
            preferred = 'vista' if 'vista' in style.theme_names() else 'clam'
            style.theme_use(preferred)

            # Set application fonts to Segoe UI (Windows) or default
            try:
                default_font = tkfont.nametofont('TkDefaultFont')
                text_font = tkfont.nametofont('TkTextFont')
                fixed_font = tkfont.nametofont('TkFixedFont')
                menu_font = tkfont.nametofont('TkMenuFont')
                heading_font = tkfont.nametofont('TkHeadingFont')

                default_font.configure(family='Segoe UI', size=10)
                text_font.configure(family='Segoe UI', size=10)
                fixed_font.configure(family='Consolas', size=10)
                menu_font.configure(family='Segoe UI', size=10)
                heading_font.configure(family='Segoe UI Semibold', size=10)
            except Exception:
                pass

            # Global ttk style tweaks
            style.configure('TButton', padding=(10, 6))
            style.configure('TLabel', padding=(2, 2))
            style.configure('TEntry', padding=(4, 4))
            style.configure('TCombobox', padding=(4, 4))
            style.configure('TNotebook.Tab', padding=(14, 8))

            # Treeview aesthetics
            style.configure('Treeview', rowheight=26)
            style.configure('Treeview.Heading', font=('Segoe UI Semibold', 10))

            # Subtle hover/active states if supported
            try:
                style.map('TButton',
                          relief=[('pressed', 'sunken'), ('!pressed', 'raised')],
                          background=[('active', '#e7e7ef')])
            except Exception:
                pass

        except Exception:
            # If anything goes wrong, silently keep defaults
            pass
    
    def setup_main_layout(self):
        """Setup main window layout"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top toolbar
        self.setup_toolbar()
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Currency editor tab
        self.currency_frame = CurrencyEditorFrame(self.notebook, self.save_service)
        self.notebook.add(self.currency_frame, text="Currencies")
        
        # Item editor tabs (will be created dynamically)
        self.item_editor_frames: Dict[ItemCategory, ItemEditorFrame] = {}
        # Map top-level group container widgets to their nested notebooks
        self._group_container_to_notebook: Dict[tk.Widget, ttk.Notebook] = {}
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def setup_toolbar(self):
        """Setup toolbar with common actions"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Load/Save buttons
        ttk.Button(toolbar, text="Auto-Load", command=self.load_save_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Manual Load", command=self.load_save_file_manual).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Excel data buttons
        ttk.Button(toolbar, text="Load Excel", command=self.load_excel_data).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Refresh", command=self.refresh_excel_data).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Search
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=36)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', self.on_search)
        ttk.Button(toolbar, text="Search", command=self.on_search).pack(side=tk.LEFT)
        
        # Status indicator
        self.status_indicator = ttk.Label(toolbar, text="●", foreground="#d14")
        self.status_indicator.pack(side=tk.RIGHT, padx=5)
        self.status_label = ttk.Label(toolbar, text="No save loaded")
        self.status_label.pack(side=tk.RIGHT)
    
    def setup_status_bar(self):
        """Setup status bar at bottom"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_text = ttk.Label(self.status_bar, text="Ready")
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        # Progress bar (hidden by default)
        self.progress = ttk.Progressbar(self.status_bar, mode='indeterminate')
        
        self.db_stats_label = ttk.Label(self.status_bar, text="")
        self.db_stats_label.pack(side=tk.RIGHT, padx=5)
    
    def load_initial_data(self):
        """Load initial data on startup"""
        self.set_status("Loading Excel data...")
        
        def load_data():
            try:
                self.game_database = self.excel_service.load_game_database()
                self.root.after(0, self.on_data_loaded)
            except Exception as e:
                logger.error(f"Error loading initial data: {e}")
                self.root.after(0, lambda: self.set_status(f"Error loading data: {e}"))
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def on_data_loaded(self):
        """Called when Excel data is loaded"""
        if self.game_database and len(self.game_database.get_all_categories()) > 0:
            self.create_category_tabs()
            self.update_database_stats()
            self.set_status("Excel data loaded successfully")
        else:
            # Prompt user to locate the Excel data file when running from a packaged .exe
            self.set_status("No Excel data found. Please select the Excel file.")
            file_path = filedialog.askopenfilename(
                title="Select Excel Data File",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            if file_path:
                from pathlib import Path as _Path
                self.excel_service.excel_path = _Path(file_path)
                self.refresh_excel_data()
            else:
                self.set_status("Excel data not selected. Categories will be unavailable.")
    
    def create_category_tabs(self):
        """Create tabs for each item category"""
        if not self.game_database:
            return
        
        # Remove existing item editor tabs
        for frame in self.item_editor_frames.values():
            try:
                self.notebook.forget(frame)
            except:
                pass
        
        self.item_editor_frames.clear()
        
        # Create tabs grouped by main categories (e.g., Clothes, Houses)
        group_to_container: Dict[str, ttk.Frame] = {}
        group_to_notebook: Dict[str, ttk.Notebook] = {}

        for category in self.game_database.get_all_categories():
            collection = self.game_database.get_collection(category)
            if len(collection) == 0:
                continue

            group_name = self._group_for_category(category)
            if group_name is None:
                # Standalone tab
                frame = ItemEditorFrame(
                    self.notebook,
                    category,
                    collection,
                    self.image_service,
                    self.save_service,
                )
                if self.save_service.current_save_data:
                    frame.load_save_data(self.save_service.current_save_data)
                self.item_editor_frames[category] = frame
                friendly = self._humanize_category(category)
                self.notebook.add(frame, text=f"{friendly} ({len(collection)})")
            else:
                # Ensure group container and nested notebook exist
                if group_name not in group_to_container:
                    container = ttk.Frame(self.notebook)
                    nested = ttk.Notebook(container)
                    nested.pack(fill=tk.BOTH, expand=True)
                    group_to_container[group_name] = container
                    group_to_notebook[group_name] = nested
                    self._group_container_to_notebook[container] = nested

                    # Compute group count lazily as we add subcategories
                    self.notebook.add(container, text=group_name)

                nested = group_to_notebook[group_name]

                sub_frame = ItemEditorFrame(
                    nested,
                    category,
                    collection,
                    self.image_service,
                    self.save_service,
                )
                if self.save_service.current_save_data:
                    sub_frame.load_save_data(self.save_service.current_save_data)
                self.item_editor_frames[category] = sub_frame
                sub_label = self._humanize_category(category)
                nested.add(sub_frame, text=f"{sub_label} ({len(collection)})")

        # Update group tab labels with aggregate counts
        for group_name, container in group_to_container.items():
            total = 0
            nested = group_to_notebook[group_name]
            for i in range(len(nested.tabs())):
                text = nested.tab(i, 'text')
                # Extract count inside parentheses if present
                try:
                    count = int(text.split('(')[-1].split(')')[0])
                except Exception:
                    count = 0
                total += count
            # Update the top-level tab text with total count
            self.notebook.tab(container, text=f"{group_name} ({total})")

    def _humanize_category(self, category: ItemCategory) -> str:
        """Make a user-friendly name from enum value (remove underscores, title case, fix abbreviations)."""
        name = category.value.replace('_', ' ').title()
        # Fix common abbreviations
        name = name.replace('Npc', 'NPC')
        return name

    def _group_for_category(self, category: ItemCategory) -> str | None:
        """Return a main group name for a category, or None if standalone."""
        if category.name.startswith('CLOTHES_'):
            return 'Clothes'
        if category.name.startswith('HOUSE_') or category == ItemCategory.NPC_HOUSES:
            return 'Houses'
        return None
    
    def load_save_file(self):
        """Load a save file - first try auto-detection, then manual selection"""
        logger.info("Load save file requested")
        
        # First try auto-detection
        if self._try_auto_load():
            return
        
        # If auto-detection fails, show manual file dialog
        logger.info("Auto-detection failed, showing file dialog")
        file_path = filedialog.askopenfilename(
            title="Select DDV Save File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=Path.home() / "AppData" / "LocalLow"
        )
        
        if not file_path:
            return
        
        self._load_specific_file(file_path)
    
    def _try_auto_load(self) -> bool:
        """Try to automatically load the latest save file"""
        logger.info("Attempting automatic save file detection...")
        self.set_status("Auto-detecting latest save file...")
        
        def auto_load():
            try:
                # Try with the known DDV key first
                known_ddv_key = getattr(self, 'default_hex_key', "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35")
                success, message = self.save_service.auto_load_latest_save(known_ddv_key)
                self.root.after(0, lambda: self.on_save_loaded(success, message))
            except Exception as e:
                logger.error(f"Error in auto-load: {e}")
                self.root.after(0, lambda: self.on_save_loaded(False, str(e)))
        
        # Check if auto-detection can find a save file
        latest_save_path = self.save_service.find_latest_save_file()
        if latest_save_path:
            logger.info(f"Auto-detected save file: {latest_save_path}")
            self.show_progress()
            threading.Thread(target=auto_load, daemon=True).start()
            return True
        else:
            logger.info("No save files found for auto-detection")
            self.set_status("No save files found - please select manually")
            # If categories are not loaded yet, prompt for Excel file to ensure UI has data
            if not self.game_database or len(self.game_database.get_all_categories()) == 0:
                file_path = filedialog.askopenfilename(
                    title="Select Excel Data File",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
                )
                if file_path:
                    from pathlib import Path as _Path
                    self.excel_service.excel_path = _Path(file_path)
                    self.refresh_excel_data()
            return False
    
    def _load_specific_file(self, file_path: str):
        """Load a specific file (manual selection)"""
        logger.info(f"Loading manually selected file: {file_path}")
        
        # Check if file is encrypted
        if self.save_service.is_file_encrypted(Path(file_path)):
            # Try the known DDV key first (from settings or CyberChef configuration)
            known_ddv_key = getattr(self, 'default_hex_key', "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35")
            
            self.set_status("Trying known DDV decryption key...")
            logger.info("Attempting decryption with known DDV key...")
            
            # First try with known key
            success, message = self.save_service.load_save_file(file_path, known_ddv_key)
            
            if success:
                logger.info("Successfully decrypted with known DDV key!")
                self.on_save_loaded(success, message)
                return
            else:
                logger.info("Known DDV key failed, prompting user for key...")
                # If known key fails, ask user for decryption key
                key = simpledialog.askstring(
                    "Decryption Key Required",
                    "The standard DDV key didn't work.\nEnter the hexadecimal decryption key for this save file:",
                    show='*'
                )
                if not key:
                    return
        else:
            key = None
        
        self.set_status("Loading save file...")
        self.show_progress()
        
        def load_save():
            try:
                success, message = self.save_service.load_save_file(file_path, key)
                self.root.after(0, lambda: self.on_save_loaded(success, message))
            except Exception as e:
                logger.error(f"Error loading save: {e}")
                self.root.after(0, lambda: self.on_save_loaded(False, str(e)))
        
        threading.Thread(target=load_save, daemon=True).start()
    
    def load_save_file_manual(self):
        """Load a save file with manual file selection (no auto-detection)"""
        logger.info("Manual save file selection requested")
        
        file_path = filedialog.askopenfilename(
            title="Select DDV Save File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=Path.home() / "AppData" / "LocalLow"
        )
        
        if not file_path:
            return
        
        self._load_specific_file(file_path)
    
    def on_save_loaded(self, success: bool, message: str):
        """Called when save file loading completes"""
        self.hide_progress()
        
        if success:
            self.set_status("Save file loaded successfully")
            self.status_indicator.config(foreground="green")
            self.status_label.config(text="Save loaded")
            
            # Update currency editor
            self.currency_frame.load_save_data(self.save_service.current_save_data)
            
            # Update item editors
            for frame in self.item_editor_frames.values():
                frame.load_save_data(self.save_service.current_save_data)
                
            messagebox.showinfo("Success", message)
        else:
            self.set_status(f"Failed to load save: {message}")
            messagebox.showerror("Error", message)
    
    def save_file(self):
        """Save the current save file"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
        
        self.set_status("Saving file...")
        
        def save_data():
            try:
                # Update save data from editors
                self.currency_frame.update_save_data()
                for frame in self.item_editor_frames.values():
                    frame.update_save_data()
                
                success, message = self.save_service.save_file()
                self.root.after(0, lambda: self.on_save_completed(success, message))
            except Exception as e:
                logger.error(f"Error saving: {e}")
                self.root.after(0, lambda: self.on_save_completed(False, str(e)))
        
        threading.Thread(target=save_data, daemon=True).start()
    
    def save_file_as(self):
        """Save the current save file to a new location"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save DDV Save File As",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".json"
        )
        
        if not file_path:
            return
        
        self.set_status("Saving file...")
        
        def save_data():
            try:
                # Update save data from editors
                self.currency_frame.update_save_data()
                for frame in self.item_editor_frames.values():
                    frame.update_save_data()
                
                success, message = self.save_service.save_file(file_path)
                self.root.after(0, lambda: self.on_save_completed(success, message))
            except Exception as e:
                logger.error(f"Error saving: {e}")
                self.root.after(0, lambda: self.on_save_completed(False, str(e)))
        
        threading.Thread(target=save_data, daemon=True).start()
    
    def on_save_completed(self, success: bool, message: str):
        """Called when save operation completes"""
        if success:
            self.set_status("Save completed successfully")
            messagebox.showinfo("Success", message)
        else:
            self.set_status(f"Save failed: {message}")
            messagebox.showerror("Error", message)
    
    def load_excel_data(self):
        """Load Excel data from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Excel Data File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self.excel_service.excel_path = Path(file_path)
        self.refresh_excel_data()
    
    def refresh_excel_data(self):
        """Refresh Excel data"""
        self.set_status("Refreshing Excel data...")
        self.show_progress()
        
        def refresh_data():
            try:
                self.game_database = self.excel_service.load_game_database(force_reload=True)
                self.root.after(0, self.on_data_refreshed)
            except Exception as e:
                logger.error(f"Error refreshing data: {e}")
                self.root.after(0, lambda: self.set_status(f"Error refreshing data: {e}"))
        
        threading.Thread(target=refresh_data, daemon=True).start()
    
    def on_data_refreshed(self):
        """Called when Excel data refresh completes"""
        self.hide_progress()
        self.create_category_tabs()
        self.update_database_stats()
        self.set_status("Excel data refreshed successfully")
    
    def on_search(self, event=None):
        """Handle search"""
        query = self.search_var.get().strip()
        if not query or not self.game_database:
            return
        
        # Search across all categories
        results = self.game_database.search_all_items(query)
        
        if not results:
            messagebox.showinfo("Search Results", f"No items found for '{query}'")
            return
        
        # Show results in a new window
        self.show_search_results(query, results)
    
    def show_search_results(self, query: str, results: Dict):
        """Show search results in a new window"""
        # This would be implemented as a separate dialog
        # For now, just show a simple message
        total_results = sum(len(items) for items in results.values())
        message = f"Found {total_results} items for '{query}':\n\n"
        
        for category, items in results.items():
            message += f"{category.value.title()}: {len(items)} items\n"
        
        messagebox.showinfo("Search Results", message)
    
    def add_all_items(self):
        """Add all items from current category to save"""
        frame = self._get_active_item_editor_frame()
        if frame:
            frame.add_all_items()
    
    def clear_all_items(self):
        """Clear all items from current category"""
        if messagebox.askyesno("Confirm", "Clear all items from current category?"):
            frame = self._get_active_item_editor_frame()
            if frame:
                frame.clear_all_items()

    def _get_active_item_editor_frame(self) -> ItemEditorFrame | None:
        """Resolve the currently visible ItemEditorFrame, accounting for grouped tabs."""
        try:
            # If on the first tab (Currencies), return None
            if self.notebook.index(self.notebook.select()) == 0:
                return None

            current_widget = self.notebook.nametowidget(self.notebook.select())
            if isinstance(current_widget, ItemEditorFrame):
                return current_widget

            # If this is a container for a grouped tab, fetch its nested notebook
            nested = self._group_container_to_notebook.get(current_widget)
            if nested is not None:
                sub_widget = nested.nametowidget(nested.select())
                if isinstance(sub_widget, ItemEditorFrame):
                    return sub_widget
            return None
        except Exception:
            return None
    
    def on_tab_changed(self, event):
        """Handle tab change"""
        pass  # Could be used for lazy loading or other optimizations
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.root)
        if dialog.result:
            # Settings changed, might need to reload services
            pass
    
    def show_backup_manager(self):
        """Show backup manager dialog"""
        # This would be implemented as a separate dialog
        backups = self.save_service.get_backup_list()
        if not backups:
            messagebox.showinfo("Backup Manager", "No backups found")
            return
        
        # For now, just show backup count
        messagebox.showinfo("Backup Manager", f"Found {len(backups)} backup files")
    
    def validate_save_file(self):
        """Validate the current save file"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
        
        # Basic validation
        save_data = self.save_service.current_save_data
        issues = []
        
        if not save_data.player_name:
            issues.append("Player name is empty")
        
        if save_data.player_level < 1:
            issues.append("Invalid player level")
        
        # Check for duplicate pets
        pet_ids = [pet.pet_item_id for pet in save_data.pets]
        if len(pet_ids) != len(set(pet_ids)):
            issues.append("Duplicate pets found")
        
        if issues:
            messagebox.showwarning("Validation Issues", "\n".join(issues))
        else:
            messagebox.showinfo("Validation", "Save file appears to be valid")
    
    def clear_image_cache(self):
        """Clear image cache"""
        self.image_service.clear_cache()
        self.set_status("Image cache cleared")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About DDV Save Editor",
            "DDV Save Editor - Python Version\n"
            "A tool for editing Disney Dreamlight Valley save files\n\n"
            "Features:\n"
            "• Load and save encrypted save files\n"
            "• Dynamic Excel data loading\n"
            "• Image previews for items\n"
            "• Automatic backups\n"
            "• Modern Python GUI"
        )

    def augment_save_with_legacy_dicts(self):
        """Add missing clothes, houses, and NPC skins to the loaded save using legacy C# dicts.
        This mirrors the behavior in EditPets.cs but applies safely to the current Python model.
        """
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return

        # Locate legacy C# dictionary files
        try:
            repo_root = Path(__file__).resolve().parents[2]
            dicts_dir = repo_root / "Ddv-Save-Editor" / "fast edit ddv" / "Class" / "Dict"
            clothes_cs = dicts_dir / "Clothes.cs"
            houses_cs = dicts_dir / "Houses.cs"
            skins_cs = dicts_dir / "SkinsNpc.cs"
        except Exception as e:
            logger.error(f"Failed to resolve legacy dict paths: {e}")
            messagebox.showerror("Error", f"Failed to resolve legacy dict paths: {e}")
            return

        if not (clothes_cs.exists() and houses_cs.exists() and skins_cs.exists()):
            messagebox.showerror(
                "Error",
                "Legacy C# dictionaries not found. Ensure 'Ddv-Save-Editor/fast edit ddv/Class/Dict/*.cs' exist."
            )
            return

        self.set_status("Augmenting save with legacy dictionaries...")
        self.show_progress()

        def do_augment():
            try:
                # Work on a direct dict copy of the original save
                save_dict = self.save_service.current_save_data.custom_data.get('original_save')
                if not isinstance(save_dict, dict):
                    raise RuntimeError("Original save dictionary is not available")

                # Snapshot of existing keys for the targeted inventories
                def inv_keys(d: Dict[str, Any], inv_id: str) -> set:
                    try:
                        return set((d.get('Player', {})
                                      .get('ListInventories', {})
                                      .get(inv_id, {})
                                      .get('Inventory', {}) or {}).keys())
                    except Exception:
                        return set()

                before_1 = inv_keys(save_dict, '1')
                before_5 = inv_keys(save_dict, '5')
                before_7 = inv_keys(save_dict, '7')

                summary = augment_save_dict(
                    save_dict,
                    add_clothes=True,
                    add_houses=True,
                    add_skins=True,
                    inventory_for_clothes='1',
                    inventory_for_houses='5',
                    inventory_for_skins='7',
                    amount=1,
                    mode='missing-only',
                    clothes_cs_path=clothes_cs,
                    houses_cs_path=houses_cs,
                    skins_cs_path=skins_cs,
                )

                after_1 = inv_keys(save_dict, '1')
                after_5 = inv_keys(save_dict, '5')
                after_7 = inv_keys(save_dict, '7')

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
                            (itm.item_id == item_id and (itm.inventory_id or '1') == inv_id)
                            for itm in self.save_service.current_save_data.inventory_items
                        )
                        if not exists:
                            self.save_service.current_save_data.inventory_items.append(
                                PlayerInventoryItem(item_id=item_id, amount=1, state=None, inventory_id=inv_id)
                            )

                add_items_to_model('1', added_1)
                add_items_to_model('5', added_5)
                add_items_to_model('7', added_7)

                # Update original save dict reference
                self.save_service.current_save_data.custom_data['original_save'] = save_dict

                msg = (
                    f"Clothes added: {summary['clothes_added']}, Houses added: {summary['houses_added']}, "
                    f"NPC skins added: {summary['skins_added']}"
                )
                logger.info(f"Augmentation complete: {msg}")
                self.root.after(0, lambda: [
                    self.set_status("Augmentation complete"),
                    self.hide_progress(),
                    messagebox.showinfo("Augment Save", msg)
                ])
            except Exception as e:
                logger.error(f"Augmentation failed: {e}")
                self.root.after(0, lambda: [
                    self.set_status("Augmentation failed"),
                    self.hide_progress(),
                    messagebox.showerror("Error", f"Augmentation failed: {e}")
                ])

        threading.Thread(target=do_augment, daemon=True).start()
    
    def set_status(self, text: str):
        """Set status bar text"""
        self.status_text.config(text=text)
        self.root.update_idletasks()
    
    def show_progress(self):
        """Show progress bar"""
        self.progress.pack(side=tk.RIGHT, padx=5)
        self.progress.start()
    
    def hide_progress(self):
        """Hide progress bar"""
        self.progress.stop()
        self.progress.pack_forget()
    
    def update_database_stats(self):
        """Update database statistics display"""
        if self.game_database:
            stats = self.game_database.get_stats()
            text = f"Items: {stats['total_items']} | Categories: {stats['categories']}"
            self.db_stats_label.config(text=text)
        else:
            self.db_stats_label.config(text="")
    
    def on_closing(self):
        """Handle window closing"""
        try:
            # Cleanup services
            self.image_service.close()
            
            # Close window
            self.root.destroy()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

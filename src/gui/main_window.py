"""
Main GUI window for DDV Save Editor
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import threading

from ..services.excel_service import ExcelDataService
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
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
        
        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.refresh_excel_data())
    
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
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', self.on_search)
        ttk.Button(toolbar, text="Search", command=self.on_search).pack(side=tk.LEFT)
        
        # Status indicator
        self.status_indicator = ttk.Label(toolbar, text="●", foreground="red")
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
        if self.game_database:
            self.create_category_tabs()
            self.update_database_stats()
            self.set_status("Excel data loaded successfully")
        else:
            self.set_status("No Excel data found")
    
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
        
        # Create tabs for categories with items
        for category in self.game_database.get_all_categories():
            collection = self.game_database.get_collection(category)
            if len(collection) > 0:
                frame = ItemEditorFrame(
                    self.notebook, 
                    category, 
                    collection, 
                    self.image_service,
                    self.save_service
                )
                self.item_editor_frames[category] = frame
                self.notebook.add(frame, text=f"{category.value.title()} ({len(collection)})")
    
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
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Currency tab
            return
        
        # Get current item editor
        tab_text = self.notebook.tab(current_tab, 'text')
        category_name = tab_text.split(' ')[0].lower()
        
        for category, frame in self.item_editor_frames.items():
            if category.value == category_name:
                frame.add_all_items()
                break
    
    def clear_all_items(self):
        """Clear all items from current category"""
        if messagebox.askyesno("Confirm", "Clear all items from current category?"):
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 0:  # Currency tab
                return
            
            # Get current item editor
            tab_text = self.notebook.tab(current_tab, 'text')
            category_name = tab_text.split(' ')[0].lower()
            
            for category, frame in self.item_editor_frames.items():
                if category.value == category_name:
                    frame.clear_all_items()
                    break
    
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

"""
Main GUI window for DDV Save Editor
"""
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import font as tkfont
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import threading

from ..services.excel_service import ExcelDataService
from .toast_notification import ToastNotification
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.settings_service import SettingsService
from ..services.dict_service import DictDataService
from ..services.augmentation_service import augment_save_dict, add_basic_tools, add_specific_tool
from ..models.game_item import GameDatabase, ItemCategory
from .item_editor import ItemEditorFrame
from .currency_editor import CurrencyEditorFrame
from .settings_dialog import SettingsDialog
from .search_results import SearchResultsFrame
from .json_viewer import JsonViewerWindow


logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DDV Save Editor - Python")
        self.root.geometry("1200x800")
        # Maximize by default to ensure full visibility on all screen sizes
        try:
            self.root.state('zoomed')  # Windows
        except Exception:
            try:
                self.root.attributes('-zoomed', True)  # Some *nix
            except Exception:
                # Fallback: use full screen size minus small margins
                try:
                    w = self.root.winfo_screenwidth()
                    h = self.root.winfo_screenheight()
                    self.root.geometry(f"{max(800, w-40)}x{max(600, h-80)}+10+10")
                except Exception:
                    pass
        
        # Visual theme and scaling first
        self.setup_theme()

        # Settings
        self.settings_service = SettingsService()
        self.settings: Dict[str, Any] = self.settings_service.load()

        # Services configured from settings
        self.excel_service = ExcelDataService(self.settings.get('excel_path'))
        self.dict_service = DictDataService(self.settings.get('dict_root', 'Dict'))
        self.image_service = ImageService(
            zip_path=self.settings.get('image_zip_path', 'img.zip'),
            folder_path=self.settings.get('image_folder_path', 'img'),
            cache_size_limit=int(self.settings.get('cache_size', 200) or 200),
        )
        # Apply image sizes from settings
        from ..services.settings_service import SettingsService as _SS
        self.image_service.thumbnail_size = _SS.parse_size(self.settings.get('thumbnail_size', '64x64'), (64, 64))
        self.image_service.preview_size = _SS.parse_size(self.settings.get('preview_size', '128x128'), (128, 128))

        self.save_service = SaveFileService(
            max_backups=int(self.settings.get('max_backups', 10) or 10)
        )

        # Default hex key for decryption
        self.default_hex_key = str(self.settings.get('hex_key') or "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35")
        
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
        tools_menu.add_command(label="Add Basic Tools", command=self.add_basic_tools)
        tools_menu.add_command(label="Add Monster Pickaxe", command=lambda: self.add_specific_tool(110400004))
        tools_menu.add_command(label="Add Main Pickaxe", command=lambda: self.add_specific_tool(110400000))
        tools_menu.add_command(label="Augment Save (legacy dicts)", command=self.augment_save_with_legacy_dicts)
        tools_menu.add_separator()
        tools_menu.add_command(label="Cache Online Images (Current Category)", command=self.cache_current_category_images)
        
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

            # Global ttk style tweaks (support light/dark)
            theme_choice = str(getattr(self, 'settings', {}).get('theme', 'light')).lower()
            if theme_choice == 'dark':
                brand_bg = '#0f172a'      # slate-900
                brand_panel = '#111827'   # gray-900
                brand_text = '#e5e7eb'    # gray-200
                selected_tab_bg = '#1f2937'
                tree_bg = '#0b1220'
            else:
                brand_bg = '#f5f7fb'
                brand_panel = '#ffffff'
                brand_text = '#1f2937'
                selected_tab_bg = '#eef2ff'
                tree_bg = '#ffffff'

            style.configure('TFrame', background=brand_bg)
            style.configure('TLabelframe', background=brand_panel)
            style.configure('TLabelframe.Label', background=brand_panel, foreground=brand_text)
            style.configure('TLabel', background=brand_bg, foreground=brand_text, padding=(2,2))
            style.configure('TEntry', padding=(4,4))
            style.configure('TCombobox', padding=(4,4))
            style.configure('TNotebook', background=brand_bg)
            style.configure('TNotebook.Tab', padding=(14, 8))
            style.map('TNotebook.Tab', background=[('selected', selected_tab_bg)])
            style.configure('TButton', padding=(10,6))

            # Treeview aesthetics
            style.configure('Treeview', rowheight=26, fieldbackground=tree_bg, background=tree_bg)
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

    def on_theme_changed(self):
        choice = self.theme_var.get().strip().lower()
        self.settings['theme'] = choice
        self.settings_service.save(self.settings)
        self.setup_theme()
        try:
            self.root.update_idletasks()
        except Exception:
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
        ttk.Button(toolbar, text="JSON Viewer", command=self.show_json_viewer).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Full Editor", command=self.show_full_editor).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Data source quick switch
        ttk.Label(toolbar, text="Data Source:").pack(side=tk.LEFT, padx=(0, 5))
        self.data_source_var = tk.StringVar(value=str(self.settings.get('data_source', 'excel')).title())
        self.data_source_combo = ttk.Combobox(
            toolbar,
            textvariable=self.data_source_var,
            values=["Excel", "Dict"],
            state="readonly",
            width=8,
        )
        self.data_source_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.data_source_combo.bind('<<ComboboxSelected>>', lambda e: self.on_data_source_changed())
        ttk.Button(toolbar, text="Choose Dict Folder", command=self.choose_dict_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Reload Data", command=self.refresh_excel_data).pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Theme switcher
        ttk.Label(toolbar, text="Theme:").pack(side=tk.LEFT, padx=(8, 4))
        self.theme_var = tk.StringVar(value=str(self.settings.get('theme', 'light')).title())
        self.theme_combo = ttk.Combobox(toolbar, textvariable=self.theme_var, values=["Light", "Dark"], state="readonly", width=7)
        self.theme_combo.pack(side=tk.LEFT)
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.on_theme_changed())

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
        source = str(self.settings.get('data_source', 'excel')).lower()
        self.set_status(f"Loading {('Dict' if source=='dict' else 'Excel')} data...")
        
        def load_data():
            try:
                if source == 'dict':
                    self.game_database = self.dict_service.load_game_database()
                else:
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
            source = str(self.settings.get('data_source', 'excel')).lower()
            if source == 'dict':
                self.set_status("No Dict data found. Please check the 'Dict' folder path in Settings.")
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
    
    def create_inventory_tab(self) -> ttk.Frame:
        """Create the orange Inventory tab that shows player's inventory"""
        frame = ttk.Frame(self.notebook)
        
        # Configure orange style for the tab
        style = ttk.Style()
        style.map('TNotebook.Tab',
            background=[('selected', '#FFA500')])
        
        # Create a treeview to display inventory items
        tree = ttk.Treeview(frame, columns=('ID', 'Name', 'Amount', 'Category', 'Container'), show='headings')

        # Initialise default_order (will be set properly when data is loaded)
        tree.default_order = {}
        
        # Set up column headings with sorting
        tree.heading('ID', text='ID', command=lambda e=None: self.treeview_sort_column_inventory(tree, 'ID', False, False))
        tree.heading('Name', text='Name', command=lambda e=None: self.treeview_sort_column_inventory(tree, 'Name', False, False))
        tree.heading('Amount', text='Amount', command=lambda e=None: self.treeview_sort_column_inventory(tree, 'Amount', False, False))
        tree.heading('Category', text='Category', command=lambda e=None: self.treeview_sort_column_inventory(tree, 'Category', False, False))
        tree.heading('Container', text='Container', command=lambda e=None: self.treeview_sort_column_inventory(tree, 'Container', False, False))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Store tree reference
        frame.tree = tree
        
        # Create button frame
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, sticky='w', padx=5, pady=5)

        # Add refresh button
        refresh_btn = ttk.Button(button_frame, text="Refresh", command=lambda: self.refresh_inventory_tab(frame))
        refresh_btn.grid(row=0, column=0, padx=(0, 5))

        # Add edit amount button
        edit_amount_btn = ttk.Button(button_frame, text="Edit Amount", command=lambda: self.edit_inventory_amount(frame))
        edit_amount_btn.grid(row=0, column=1)
        
        # Bind double-click action to items only, no column headers
        tree.bind('<Double-Button-1>', lambda e: self.edit_inventory_amount(frame) if tree.identify_region(e.x, e.y) == "cell" else None)
        # Store item data for saving
        frame.items = {}
        
        return frame

    def on_tree_double_click(self, event):
        """Handles double-click event for inventory tree: triggers edit_inventory_amount() only when clicking on cells"""
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.edit_inventory_amount()

    def treeview_sort_column_inventory(self, tv, col, reverse, return_to_default=False):
        """Handles cyclical column sorting for inventory tree: default → ascending → descending → default"""
        
        if return_to_default:
            # Restore original order using saved default_order
            if hasattr(tv, 'default_order') and col in tv.default_order:
                for index, item in enumerate(tv.default_order[col]):
                    try:
                        tv.move(item, '', index)
                    except tk.TclError:
                        # Skip items that no longer exist after refresh
                        continue
            next_reverse, next_return_to_default, indicator = False, False, ""
        else:
            # Get column data for sorting
            items = [(tv.set(item, col), item) for item in tv.get_children('')]
            
            # Sort numerically if all values are numbers, otherwise alphabetically
            if all(str(item[0]).replace('.', '', 1).isdigit() for item in items if item[0] is not None and str(item[0]).strip()):
                items.sort(key=lambda t: float(t[0]) if t[0] is not None and str(t[0]).strip() else 0, reverse=reverse)
            else:
                items.sort(key=lambda t: str(t[0]).lower() if t[0] is not None else '', reverse=reverse)
            
            # Apply sorted order to treeview
            for index, (value, item) in enumerate(items):
                tv.move(item, '', index)
            
            # Set next sort state and arrow direction
            next_reverse, next_return_to_default, indicator = (False, True, " ▼") if reverse else (True, False, " ▲")
        
        # Remove sort arrows from all headers
        for column in tv["columns"]:
            heading_text = tv.heading(column)["text"]
            if any(marker in heading_text for marker in [" ▲", " ▼"]):
                tv.heading(column, text=heading_text[:-2])
        
        # Add sort arrow to current column and set next click action
        current_text = tv.heading(col)["text"].replace(" ▲", "").replace(" ▼", "")
        tv.heading(
            col,
            text=current_text + indicator,
            command=lambda e=None, column=col, rev=next_reverse, ret_def=next_return_to_default:
                    self.treeview_sort_column_inventory(tv, column, rev, ret_def)
        )

    def refresh_inventory_tab(self, frame: ttk.Frame):
        """Refresh the inventory tab with current data"""
        if not self.save_service.current_save_data:
            return
            
        tree = frame.tree
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
            
        save_data = self.save_service.current_save_data
        original_save = save_data.custom_data.get('original_save', {})
        player_data = original_save.get('Player', {})
        
        # Process only ContainerInventories.0
        container_inventories = player_data.get('ContainerInventories', {})
        container_0 = container_inventories.get('0', {})
        inventory = container_0.get('Inventory', [])
        
        if isinstance(inventory, list):
            for item in inventory:
                item_id = str(item.get('ItemID', ''))
                if item_id and item_id != '0':  # Skip empty slots
                    name = self.get_item_name(item_id)
                    amount = item.get('Amount', 0)
                    category = self.get_item_category(item_id)
                    state = item.get('State')
                    # If there's a state with ConsummableData, show that item's info too
                    if isinstance(state, dict) and 'ConsummableData' in state:
                        consumable = state['ConsummableData']
                        cons_id = str(consumable.get('ItemID', ''))
                        if cons_id and cons_id != '0':
                            cons_name = self.get_item_name(cons_id)
                            cons_amount = consumable.get('Amount', 0)
                            tree.insert('', 'end', values=(cons_id, f"{cons_name} (in {name})", cons_amount, "Consumable", "Player Inventory"))
                    tree.insert('', 'end', values=(item_id, name, amount, category, "Player Inventory"))
                    # Store item data for saving
                    frame.items[item_id] = {'amount': amount, 'state': item.get('State')}

        # Reset default_order to the current loaded order
        tree.default_order = {c: list(tree.get_children('')) for c in tree["columns"]}
        
        # Reset all column headers to remove any sort indicators
        for col in tree["columns"]:
            heading_text = tree.heading(col)["text"]
            clean_text = heading_text.replace(" ▲", "").replace(" ▼", "")
            tree.heading(col, text=clean_text, 
                        command=lambda e=None, c=col: self.treeview_sort_column_inventory(tree, c, False, False))
                        
    def edit_inventory_amount(self, frame: ttk.Frame):
        """Edit the amount of selected item(s)"""
        tree = frame.tree
        selection = tree.selection()
        if not selection:
            return
        
        if len(selection) == 1:
            # If single item selected - show item name and keep current amount
            item = tree.item(selection[0])
            item_id = item['values'][0]
            current_amount = item['values'][2]
            
            new_amount = simpledialog.askinteger(
                "Edit Amount",
                f"Enter new amount for {item['values'][1]}:",
                initialvalue=current_amount,
                minvalue=0,
                maxvalue=99999
            )
        else:
            # If multiple items selected - show selected count
            item_text = "items"
            new_amount = simpledialog.askinteger(
                "Edit Amount",
                f"Enter new amount for {len(selection)} selected {item_text}:",
                minvalue=0,
                maxvalue=99999
            )
        
        if new_amount is not None:
            # Update all selected items
            for selected_item in selection:
                item = tree.item(selected_item)
                item_id = item['values'][0]
                
                # Update tree display
                tree.set(selected_item, 'Amount', new_amount)
                
                # Update stored data
                if item_id in frame.items:
                    frame.items[item_id]['amount'] = new_amount
                
                # Update save data
                if self.save_service.current_save_data:
                    save_dict = self.save_service.current_save_data.custom_data.get('original_save', {})
                    player_data = save_dict.get('Player', {})
                    container_inventories = player_data.get('ContainerInventories', {})
                    container_0 = container_inventories.get('0', {})
                    inventory = container_0.get('Inventory', [])
                    
                    # Find and update the item
                    for inventory_item in inventory:
                        if str(inventory_item.get('ItemID', '')) == str(item_id):
                            inventory_item['Amount'] = new_amount
                            break
            
            # Update the save data once after all items are processed
            if self.save_service.current_save_data:
                self.save_service.current_save_data.custom_data['original_save'] = save_dict
                
    def get_item_name(self, item_id: str) -> str:
        """Get item name from database"""
        try:
            # First try the game database
            if self.game_database:
                for category in self.game_database.get_all_categories():
                    collection = self.game_database.get_collection(category)
                    for item in collection:
                        if str(item.id) == str(item_id):
                            return item.name
            
            # If not found, try loading from allknowids.json
            try:
                with open('Dict/allknowids.json', 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove comments and fix common JSON issues
                    lines = []
                    for line in content.split('\n'):
                        # Skip comment lines
                        if line.strip().startswith('//'):
                            continue
                        # Remove inline comments
                        if '//' in line:
                            line = line.split('//', 1)[0]
                        # Fix trailing commas
                        if line.strip().endswith(',}') or line.strip().endswith(',]'):
                            line = line.replace(',}', '}').replace(',]', ']')
                        lines.append(line)
                    cleaned_content = '\n'.join(lines)
                    # Fix any remaining trailing commas
                    cleaned_content = re.sub(r',\s*([}\]])', r'\1', cleaned_content)
                    all_ids = json.loads(cleaned_content)
                    item_id_str = str(item_id)
                    if item_id_str in all_ids:
                        return all_ids[item_id_str]
            except Exception as e:
                logger.warning(f"Error loading from allknowids.json: {e}")
            
            # If still not found, try the dict service directly
            if hasattr(self, 'dict_service'):
                item_id_str = str(item_id)
                
                # Try to load from specific dictionary files based on ID pattern
                try:
                    if item_id_str.startswith('50'):  # Clothes
                        with open('Dict/Clothes/clotheslist.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                    elif item_id_str.startswith('40'):  # Furniture
                        with open('Dict/Furnitures/furnitures.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                    elif item_id_str.startswith('20'):  # Houses
                        with open('Dict/Houses/houses.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                    elif item_id_str.startswith('170'):  # NPC Skins
                        with open('Dict/NPC Skins/npcskins.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                    elif item_id_str.startswith('110'):  # Tools
                        with open('Dict/Tools/tools.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                    elif item_id_str.startswith('16'):  # Wallpapers/Floors
                        with open('Dict/WallpapersFloors/wallsfloors.json', 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            if item_id_str in items:
                                return items[item_id_str]
                except Exception as e:
                    logger.warning(f"Error loading item name from dictionary: {e}")
            
            return f"Item {item_id}"
        except Exception as e:
            logger.error(f"Error getting item name: {e}")
            return f"Item {item_id}"
        
    def get_inventory_category_name(self, inv_id: str) -> str:
        """Get category name for inventory ID"""
        categories = {
            "0": "Furniture",
            "1": "Clothes",
            "2": "Activity Items",
            "3": "Makeup",
            "4": "Trimming",
            "5": "Houses",
            "6": "Touch of Magic",
            "7": "NPC Skins",
            "8": "Board Games",
            "9": "Avatar Features",
            "10": "Photo Mode"
        }
        return categories.get(inv_id, "Unknown")
        
    def get_item_category(self, item_id: str) -> str:
        """Get category based on item ID pattern"""
        patterns = {
            "40": "Furniture",
            "50": "Clothes",
            "110": "Activity",
            "140": "Makeup",
            "16": "Trimming",
            "20": "Houses",
            "100": "Touch of Magic",
            "170": "NPC Skins",
            "180": "Board Games",
            "70": "Avatar Features",
            "190": "Photo Mode",
            "302": "Container Items",
            "303": "Container Items",
            "304": "Container Items",
            "308": "Container Items",
            "310": "Container Items",
            "312": "Special Items",
            "314": "Special Containers",
            "316": "Container Items",
            "317": "Container Items",
            "30": "Container Items"  # Fallback for other 30xxxx items
        }
        for prefix, category in patterns.items():
            if str(item_id).startswith(prefix):
                return category
        return "Unknown"
        
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
        # Remove existing grouped container tabs
        try:
            for container in list(self._group_container_to_notebook.keys()):
                try:
                    self.notebook.forget(container)
                except Exception:
                    pass
        except Exception:
            pass

        # Remove existing Player Inventory tab
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Player Inventory":
                self.notebook.forget(i)
                break

        self.item_editor_frames.clear()
        self._group_container_to_notebook.clear()
        
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
        
        # Add the Inventory tab at the end
        inventory_frame = self.create_inventory_tab()
        self.notebook.add(inventory_frame, text="Player Inventory")
        
        # Configure orange color for the Inventory tab
        style = ttk.Style()
        style.configure('Orange.TFrame', background='#FFA500')  # Orange background for frame
        style.map('TNotebook.Tab',
                 background=[('selected', '#FFA500')])  # Orange background for selected tab

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
        
        def auto_load(latest_path: str):
            try:
                # Try with the known DDV key first using the already-detected path
                known_ddv_key = getattr(self, 'default_hex_key', "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35")
                logger.info(f"Auto-loading: {latest_path}")
                success, message = self.save_service.load_save_file(latest_path, known_ddv_key)
                self.root.after(0, lambda: self.on_save_loaded(success, message))
            except Exception as e:
                logger.error(f"Error in auto-load: {e}")
                self.root.after(0, lambda: self.on_save_loaded(False, str(e)))
        
        # Check if auto-detection can find a save file
        latest_save_path = self.save_service.find_latest_save_file()
        if latest_save_path:
            logger.info(f"Auto-detected save file: {latest_save_path}")
            self.show_progress()
            threading.Thread(target=lambda: auto_load(latest_save_path), daemon=True).start()
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
            
            # Update inventory tab
            for tab_id in self.notebook.tabs():
                widget = self.notebook.nametowidget(tab_id)
                if isinstance(widget, ttk.Frame) and hasattr(widget, 'tree'):
                    self.refresh_inventory_tab(widget)
                    break
                
            ToastNotification(self.root, f"Save loaded: {message}")
        else:
            self.set_status(f"Failed to load save: {message}")
            ToastNotification(self.root, f"Error: {message}", duration=5.0)
    
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
                # Merge updates from either category tabs or Search tab per category
                frames_by_category = dict(self.item_editor_frames)
                # Check for an existing Search tab
                try:
                    for tab_id in self.notebook.tabs():
                        widget = self.notebook.nametowidget(tab_id)
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
                frames_by_category = dict(self.item_editor_frames)
                try:
                    for tab_id in self.notebook.tabs():
                        widget = self.notebook.nametowidget(tab_id)
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
                self.root.after(0, lambda: self.on_save_completed(success, message))
            except Exception as e:
                logger.error(f"Error saving: {e}")
                self.root.after(0, lambda: self.on_save_completed(False, str(e)))
        
        threading.Thread(target=save_data, daemon=True).start()
    
    def on_save_completed(self, success: bool, message: str):
        """Called when save operation completes"""
        if success:
            self.set_status("Save completed successfully")
            ToastNotification(self.root, f"Save successful: {message}")
            # Reload editors from model so every tab reflects the saved state
            try:
                if self.save_service.current_save_data:
                    self.currency_frame.load_save_data(self.save_service.current_save_data)
                    for frame in self.item_editor_frames.values():
                        frame.load_save_data(self.save_service.current_save_data)
                    # Refresh Search tab subframes if present
                    for tab_id in self.notebook.tabs():
                        widget = self.notebook.nametowidget(tab_id)
                        from .search_results import SearchResultsFrame as _SRF
                        if isinstance(widget, _SRF):
                            for sub in widget.category_frames.values():
                                sub.load_save_data(self.save_service.current_save_data)
                            break
            except Exception:
                pass
        else:
            self.set_status(f"Save failed: {message}")
            ToastNotification(self.root, f"Error saving: {message}", duration=5.0)
    
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
        """Refresh data from the selected source"""
        source = str(self.settings.get('data_source', 'excel')).lower()
        self.set_status(f"Refreshing {('Dict' if source=='dict' else 'Excel')} data...")
        self.show_progress()
        
        def refresh_data():
            try:
                if source == 'dict':
                    self.game_database = self.dict_service.load_game_database(force_reload=True)
                else:
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

        results = self.game_database.search_all_items(query)
        # If empty, inform and bail
        total = sum(len(v) for v in results.values()) if results else 0
        if total == 0:
            messagebox.showinfo("Search", f"No items found for '{query}'")
            return

        # Either create or update a dedicated Search tab
        self._open_search_tab(results)
    
    def _open_search_tab(self, results: Dict[ItemCategory, list]):
        # If a Search tab exists, refresh it; else create one
        existing_index = None
        for i, tab_id in enumerate(self.notebook.tabs()):
            text = self.notebook.tab(tab_id, 'text')
            if text.startswith('Search'):
                existing_index = i
                break
        if existing_index is not None:
            # Tab already exists; refresh its content
            widget = self.notebook.nametowidget(self.notebook.tabs()[existing_index])
            if isinstance(widget, SearchResultsFrame):
                widget.refresh_with(results)
            self.notebook.select(existing_index)
            return
        # Create a new tab
        search_frame = SearchResultsFrame(self.notebook, results, self.image_service, self.save_service)
        total = sum(len(v) for v in results.values())
        self.notebook.add(search_frame, text=f"Search ({total})")
        self.notebook.select(search_frame)
    
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
        # Preload dialog with current settings
        dialog = SettingsDialog(self.root, initial_settings=self.settings)
        if dialog.result:
            # Persist settings
            new_settings = dialog.get_settings()
            # Ensure hex_key is preserved if dialog returns it
            if 'hex_key' not in new_settings and 'hex_key' in self.settings:
                new_settings['hex_key'] = self.settings['hex_key']
            self.settings = {**self.settings, **new_settings}
            self.settings_service.save(self.settings)

            # Apply settings live
            # Excel path
            if self.settings.get('excel_path'):
                self.excel_service.excel_path = Path(self.settings['excel_path'])
            # Image paths and cache
            if self.settings.get('image_zip_path'):
                self.image_service.zip_path = Path(self.settings['image_zip_path'])
            if self.settings.get('image_folder_path'):
                self.image_service.folder_path = Path(self.settings['image_folder_path'])
            if 'cache_size' in self.settings:
                try:
                    self.image_service.cache_size_limit = int(self.settings['cache_size'])
                except Exception:
                    pass
            # Image sizes
            from ..services.settings_service import SettingsService as _SS2
            self.image_service.thumbnail_size = _SS2.parse_size(self.settings.get('thumbnail_size', '64x64'), (64, 64))
            self.image_service.preview_size = _SS2.parse_size(self.settings.get('preview_size', '128x128'), (128, 128))
            # Refresh image catalog
            self.image_service.refresh_available_images()

            # Backup retention
            if 'max_backups' in self.settings:
                try:
                    self.save_service.max_backups = int(self.settings['max_backups'])
                except Exception:
                    pass

            # Decryption key
            if 'hex_key' in self.settings:
                self.default_hex_key = str(self.settings['hex_key'])
    
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
    
    def show_full_editor(self):
        """Show full editor window"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
            
        # Get the raw save data
        save_dict = self.save_service.current_save_data.custom_data.get('original_save', {})
        
        # Create and show the full editor window
        from .full_editor import FullEditorWindow
        editor = FullEditorWindow(self.root, self.dict_service)
        editor.load_json(save_dict)
        
        # Set up callback for when data is modified
        def on_data_changed():
            try:
                # Update the save data when JSON is modified
                new_data = editor.get_json_data()
                self.save_service.current_save_data.custom_data['original_save'] = new_data
                self.set_status("Save data updated from Full Editor")
            except Exception as e:
                logger.error(f"Error updating save data from Full Editor: {e}")
                messagebox.showerror("Error", f"Failed to update save data: {e}")
        
        editor.on_modified_callback = on_data_changed

    def show_json_viewer(self):
        """Show JSON viewer window"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
            
        # Get the raw save data
        save_dict = self.save_service.current_save_data.custom_data.get('original_save', {})
        
        # Create and show the JSON viewer window
        viewer = JsonViewerWindow(self.root)
        viewer.load_json(save_dict)
        
        # Set up callback for when JSON is modified
        def on_json_changed():
            try:
                # Update the save data when JSON is modified
                new_data = viewer.get_json_data()
                self.save_service.current_save_data.custom_data['original_save'] = new_data
                self.set_status("Save data updated from JSON viewer")
            except Exception as e:
                logger.error(f"Error updating save data from JSON viewer: {e}")
                messagebox.showerror("Error", f"Failed to update save data: {e}")
        
        viewer.on_modified_callback = on_json_changed
        
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

    def add_specific_tool(self, tool_id: int, current_of_type: bool = False):
        """Add a specific tool to the player's inventory"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return False
            
        try:
            # Get the raw save data
            save_dict = self.save_service.current_save_data.custom_data.get('original_save', {})
            
            # Add tool
            success = add_specific_tool(save_dict, tool_id, current_of_type)
            
            # Update the save data
            self.save_service.current_save_data.custom_data['original_save'] = save_dict
            
            # Show results
            if success:
                messagebox.showinfo("Tool Added", f"Successfully added tool {tool_id}")
            else:
                messagebox.showinfo("Tool", f"Tool {tool_id} already exists")
            
            return success
                
        except Exception as e:
            logger.error(f"Error adding tool: {e}")
            messagebox.showerror("Error", f"Failed to add tool: {e}")
            return False

    def add_basic_tools(self):
        """Add a basic set of tools to the player's inventory"""
        if not self.save_service.current_save_data:
            messagebox.showwarning("Warning", "No save file loaded")
            return
            
        try:
            # Get the raw save data
            save_dict = self.save_service.current_save_data.custom_data.get('original_save', {})
            
            # Add tools
            result = add_basic_tools(save_dict)
            
            # Update the save data
            self.save_service.current_save_data.custom_data['original_save'] = save_dict
            
            # Show results
            if result['tools_added'] > 0:
                added_tools = "\n".join(f"• {tool}" for tool in result['added_tools'])
                messagebox.showinfo(
                    "Tools Added",
                    f"Added {result['tools_added']} tools:\n\n{added_tools}"
                )
            else:
                messagebox.showinfo("Tools", "No new tools needed - all basic tools already present")
                
        except Exception as e:
            logger.error(f"Error adding tools: {e}")
            messagebox.showerror("Error", f"Failed to add tools: {e}")
            
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
            source = str(self.settings.get('data_source', 'excel')).title()
            text = f"Items: {stats['total_items']} | Categories: {stats['categories']} | Source: {source}"
            self.db_stats_label.config(text=text)
        else:
            self.db_stats_label.config(text="")

    def on_data_source_changed(self):
        """Handle quick switch between Excel and Dict sources"""
        choice = self.data_source_var.get().strip().lower()
        if choice not in ('excel', 'dict'):
            return
        self.settings['data_source'] = choice
        # If switching to Dict without a valid folder, prompt
        if choice == 'dict':
            dict_path = Path(self.settings.get('dict_root', 'Dict'))
            if not dict_path.exists():
                self.choose_dict_folder()
        self.settings_service.save(self.settings)
        self.refresh_excel_data()

    def choose_dict_folder(self):
        """Prompt user to choose Dict root and persist it"""
        folder = filedialog.askdirectory(title="Select Dict Root Folder")
        if folder:
            self.settings['dict_root'] = folder
            # Update service and reload
            try:
                self.dict_service.dict_root = Path(folder)
            except Exception:
                pass
            self.settings_service.save(self.settings)
            # If Dict is selected, refresh now
            if str(self.settings.get('data_source', 'excel')).lower() == 'dict':
                self.refresh_excel_data()
    
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

    def cache_current_category_images(self):
        """Download and cache online images for all items in the visible category."""
        try:
            frame = self._get_active_item_editor_frame()
            if frame is None:
                messagebox.showinfo("Cache Images", "Open a category tab to cache its images.")
                return
            collection = frame.collection
            ids_and_names = [(gi.id, gi.name) for gi in collection]
            total = len(ids_and_names)
            if total == 0:
                messagebox.showinfo("Cache Images", "No items to cache in this category.")
                return
            self.set_status(f"Caching images for {total} items...")
            self.show_progress()
            def worker():
                done = 0
                for item_id, name in ids_and_names:
                    try:
                        self.image_service.cache_image_for_item(item_id, name, frame.category)
                    except Exception:
                        pass
                    done += 1
                self.root.after(0, lambda: [self.hide_progress(), self.set_status("Caching complete"), messagebox.showinfo("Cache Images", f"Cached images for {total} items (where available)")])
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            logger.error(f"Error caching images: {e}")
            messagebox.showerror("Error", str(e))

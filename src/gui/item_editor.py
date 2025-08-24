"""
Item editor frame for editing game items
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional
import logging

from ..models.game_item import ItemCategory, ItemCollection, GameItem, SaveData, PlayerInventoryItem, PetData
from .toast_notification import ToastNotification
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService
from ..services.augmentation_service import InventoryType, add_item_to_save

# Configure logging
logger = logging.getLogger(__name__)


class ItemEditorFrame(ttk.Frame):
    """Frame for editing items of a specific category"""
    
    def __init__(self, parent, category: ItemCategory, collection: ItemCollection, 
                 image_service: ImageService, save_service: SaveFileService):
        super().__init__(parent)
        
        self.category = category
        self.collection = collection
        self.image_service = image_service
        self.save_service = save_service
        
        # Find the root window for clipboard operations and toasts
        self.root = self.winfo_toplevel()
        
        # Current items in save file
        self.save_items: List[PlayerInventoryItem] = []
        
        self.setup_ui()
        self.load_available_items()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main paned window
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Available items
        self.setup_available_items_panel()
        
        # Right side - Items in save
        self.setup_save_items_panel()
    
    def setup_available_items_panel(self):
        """Setup the available items panel"""
        left_frame = ttk.LabelFrame(self.paned, text="Available Items", padding=10)
        self.paned.add(left_frame, weight=1)
        
        # Search frame
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.available_search_var = tk.StringVar()
        self.available_search_entry = ttk.Entry(search_frame, textvariable=self.available_search_var)
        self.available_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.available_search_entry.bind('<KeyRelease>', self.on_available_search)
        
        # Available items listbox with scrollbar
        listbox_frame = ttk.Frame(left_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        self.available_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, activestyle='dotbox')
        scrollbar1 = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.available_listbox.yview)
        self.available_listbox.config(yscrollcommand=scrollbar1.set)
        
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="Add Selected", command=self.add_selected_items).pack(side=tk.LEFT, padx=(0, 5))
        
        # Bind double-click to add item
        self.available_listbox.bind('<Double-Button-1>', lambda e: self.add_selected_items())
        
        # Right-click menu for copying
        self.available_context_menu = tk.Menu(self.available_listbox, tearoff=0)
        self.available_context_menu.add_command(label="Copy ID", command=self.copy_selected_id)
        self.available_context_menu.add_command(label="Copy Name", command=self.copy_selected_name)
        self.available_context_menu.add_separator()
        self.available_context_menu.add_command(label="Add to Save", command=self.add_selected_items)
        self.available_listbox.bind('<Button-3>', self.show_available_context_menu)
    
    def setup_save_items_panel(self):
        """Setup the items in save panel"""
        # Build right side. For PETS, show pet details on the right, side-by-side with inventory
        right_container = ttk.Frame(self.paned)
        self.paned.add(right_container, weight=1)
        
        if self.category == ItemCategory.PETS:
            split = ttk.PanedWindow(right_container, orient=tk.HORIZONTAL)
            split.pack(fill=tk.BOTH, expand=True)
            left_col = ttk.Frame(split)
            split.add(left_col, weight=3)
            pets_frame = ttk.LabelFrame(split, text="Pet Details", padding=10)
            split.add(pets_frame, weight=1)
        else:
            left_col = right_container
            pets_frame = None
        
        # Search frame
        search_frame = ttk.Frame(left_col)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.save_search_var = tk.StringVar()
        self.save_search_entry = ttk.Entry(search_frame, textvariable=self.save_search_var)
        self.save_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.save_search_entry.bind('<KeyRelease>', self.on_save_search)
        
        # Treeview for save items (with quantity)
        tree_frame = ttk.Frame(left_col)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Name', 'Amount')
        # Slightly smaller height so both panes fit
        self.save_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=13)
        
        self.save_tree.heading('ID', text='ID')
        self.save_tree.heading('Name', text='Name')
        self.save_tree.heading('Amount', text='Amount')
        
        self.save_tree.column('ID', width=100, anchor=tk.W)
        self.save_tree.column('Name', width=240, anchor=tk.W)
        self.save_tree.column('Amount', width=100, anchor=tk.CENTER)
        
        scrollbar2 = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.save_tree.yview)
        self.save_tree.config(yscrollcommand=scrollbar2.set)
        
        # Add zebra striping tags
        self.save_tree.tag_configure('oddrow', background='#fbfbfe')
        self.save_tree.tag_configure('evenrow', background='#f2f2f7')

        self.save_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(left_col)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="Edit Amount", command=self.edit_item_amount).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected_items).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_items).pack(side=tk.LEFT)
        ttk.Label(button_frame, text="  ").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add All", command=self.add_all_items).pack(side=tk.LEFT)
        
        # Pets editor panel fields
        if pets_frame is not None:
            self.pet_name_var = tk.StringVar()
            self.pet_custom_name_var = tk.StringVar()
            self.pet_friendship_level_var = tk.IntVar(value=0)
            self.pet_xp_var = tk.IntVar(value=0)
            row = 0
            ttk.Label(pets_frame, text="Name (legacy):").grid(row=row, column=0, sticky=tk.W)
            ttk.Entry(pets_frame, textvariable=self.pet_name_var, width=22).grid(row=row, column=1, sticky=tk.W, padx=5)
            row += 1
            ttk.Label(pets_frame, text="Custom Name:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Entry(pets_frame, textvariable=self.pet_custom_name_var, width=22).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            ttk.Label(pets_frame, text="Friendship Level:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Spinbox(pets_frame, from_=0, to=50, textvariable=self.pet_friendship_level_var, width=6).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            ttk.Label(pets_frame, text="XP:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Spinbox(pets_frame, from_=0, to=999999, textvariable=self.pet_xp_var, width=8).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            ttk.Button(pets_frame, text="Apply to Selected Pet", command=self._apply_pet_fields_to_selected).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
            row += 1
            ttk.Button(pets_frame, text="Load From Selected Pet", command=self._load_pet_fields_from_selected).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=0, pady=(6, 0))

            # Fields
            self.pet_name_var = tk.StringVar()
            self.pet_custom_name_var = tk.StringVar()
            self.pet_friendship_level_var = tk.IntVar(value=0)
            self.pet_xp_var = tk.IntVar(value=0)
            # Removed: Is Following UI

            row = 0
            ttk.Label(pets_frame, text="Name (legacy):").grid(row=row, column=0, sticky=tk.W)
            ttk.Entry(pets_frame, textvariable=self.pet_name_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=5)
            row += 1
            ttk.Label(pets_frame, text="Custom Name:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Entry(pets_frame, textvariable=self.pet_custom_name_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            ttk.Label(pets_frame, text="Friendship Level:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Spinbox(pets_frame, from_=0, to=50, textvariable=self.pet_friendship_level_var, width=6).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            ttk.Label(pets_frame, text="XP:").grid(row=row, column=0, sticky=tk.W, pady=(6, 0))
            ttk.Spinbox(pets_frame, from_=0, to=999999, textvariable=self.pet_xp_var, width=8).grid(row=row, column=1, sticky=tk.W, padx=5, pady=(6, 0))
            row += 1
            # (Is Following checkbox removed)

            # Actions
            action_row = row
            ttk.Button(pets_frame, text="Apply to Selected Pet", command=self._apply_pet_fields_to_selected).grid(row=action_row, column=0, sticky=tk.W, pady=(8, 0))
            ttk.Button(pets_frame, text="Load From Selected Pet", command=self._load_pet_fields_from_selected).grid(row=action_row, column=1, sticky=tk.W, padx=5, pady=(8, 0))
            # Auto-load fields when a pet is selected in the list
            self.save_tree.bind('<<TreeviewSelect>>', lambda e: self._load_pet_fields_from_selected())
        
        # Bind double-click to edit amount
        self.save_tree.bind('<Double-Button-1>', lambda e: self.edit_item_amount())
        
        # Right-click menu for copying
        self.save_context_menu = tk.Menu(self.save_tree, tearoff=0)
        self.save_context_menu.add_command(label="Copy ID", command=self.copy_selected_save_id)
        self.save_context_menu.add_command(label="Copy Name", command=self.copy_selected_save_name)
        self.save_context_menu.add_separator()
        self.save_context_menu.add_command(label="Edit Amount", command=self.edit_item_amount)
        self.save_context_menu.add_command(label="Remove", command=self.remove_selected_items)
        self.save_tree.bind('<Button-3>', self.show_save_context_menu)

        # Removed image preview section for now
    
    def load_available_items(self):
        """Load available items into the listbox"""
        self.available_items = list(self.collection.items.values())
        self.available_items.sort(key=lambda x: x.name)
        
        self.refresh_available_list()
    
    def refresh_available_list(self, filter_text: str = ""):
        """Refresh the available items list with optional filter"""
        self.available_listbox.delete(0, tk.END)
        
        for item in self.available_items:
            if not filter_text or filter_text.lower() in item.name.lower() or str(item.id) in filter_text:
                display_text = f"{item.id} - {item.name}"
                self.available_listbox.insert(tk.END, display_text)

    # Removed image preview logic for now
    
    def refresh_save_list(self, filter_text: str = ""):
        """Refresh the save items list with optional filter"""
        # Clear tree
        for item in self.save_tree.get_children():
            self.save_tree.delete(item)
        
        # Add filtered items
        for idx, save_item in enumerate(self.save_items):
            game_item = self.collection.get_item(save_item.item_id)
            if game_item:
                name = game_item.name
                if not filter_text or filter_text.lower() in name.lower() or str(save_item.item_id) in filter_text:
                    tag = 'evenrow' if (idx % 2 == 0) else 'oddrow'
                    self.save_tree.insert('', tk.END, values=(
                        save_item.item_id,
                        name,
                        save_item.amount
                    ), tags=(tag,))
        # For PETS, auto-select the first item (if any) and populate the detail fields
        if self.category == ItemCategory.PETS:
            children = self.save_tree.get_children()
            if children:
                self.save_tree.selection_set(children[0])
                self._load_pet_fields_from_selected()
    
    def on_available_search(self, event):
        """Handle search in available items"""
        self.refresh_available_list(self.available_search_var.get())
    
    def on_save_search(self, event):
        """Handle search in save items"""
        self.refresh_save_list(self.save_search_var.get())
    
    def add_selected_items(self):
        """Add selected items to save"""
        selected_indices = self.available_listbox.curselection()
        if not selected_indices:
            logger.warning("No items selected to add")
            return
        logger.info(f"Adding selected items: {selected_indices}")
        
        # Get filter text to find correct items
        filter_text = self.available_search_var.get()
        
        # Get filtered item list
        filtered_items = []
        for item in self.available_items:
            if not filter_text or filter_text.lower() in item.name.lower() or str(item.id) in filter_text:
                filtered_items.append(item)
        
        added_count = 0
        for index in selected_indices:
            if index < len(filtered_items):
                item = filtered_items[index]
                # Skip items explicitly named "NOTHING"
                try:
                    if str(item.name).strip().upper() == 'NOTHING':
                        continue
                except Exception:
                    pass

                # Special case: Tools should be added to Player.Tools array
                if self.category == ItemCategory.TOOLS:
                    if not self.save_service.current_save_data:
                        continue
                    logger.info(f"[TOOL] Adding tool {item.id} ({item.name}) to Player.Tools array")
                    if 'original_save' not in self.save_service.current_save_data.custom_data:
                        self.save_service.current_save_data.custom_data['original_save'] = {}
                    save_dict = self.save_service.current_save_data.custom_data['original_save']
                    if 'Player' not in save_dict:
                        save_dict['Player'] = {}
                    player = save_dict['Player']
                    if 'Tools' not in player:
                        player['Tools'] = []
                    tools = player['Tools']
                    
                    # Check if tool already exists
                    if not any(tool.get('ToolItemID') == item.id for tool in tools):
                        tools.append({
                            'ToolItemID': item.id,
                            'CurrentOfType': False
                        })
                        # Add to display list
                        self.save_items.append(PlayerInventoryItem(item_id=item.id, amount=1))
                        added_count += 1
                        logger.info(f"[TOOL] Successfully added tool {item.id} ({item.name})")
                    else:
                        logger.info(f"[TOOL] Tool {item.id} ({item.name}) already exists")
                    continue

                # Pets are unique; add to save_data.pets rather than inventory
                if self.category == ItemCategory.PETS:
                    if not self.save_service.current_save_data:
                        continue
                    already = any(p.pet_item_id == item.id for p in self.save_service.current_save_data.pets)
                    if not already:
                        self.save_service.current_save_data.pets.append(PetData(pet_item_id=item.id))
                        # Reflect in local display list
                        self.save_items.append(PlayerInventoryItem(item_id=item.id, amount=1))
                        added_count += 1
                else:
                    # Check if item already exists
                    existing_item = next((si for si in self.save_items if si.item_id == item.id), None)
                    if existing_item:
                        logger.info(f"[ADD] Increasing amount for existing item {item.id} ({item.name})")
                        existing_item.amount += 1
                    else:
                        default_inventory = self._default_inventory_for_category(self.category)
                        logger.info(f"[ADD] Adding new item {item.id} ({item.name}) to inventory {default_inventory}")
                        new_item = PlayerInventoryItem(item_id=item.id, amount=1, inventory_id=default_inventory)
                        self.save_items.append(new_item)
                        # Also add to save_data's inventory_items
                        if self.save_service.current_save_data:
                            logger.info(f"[ADD] Adding item to save_data inventory")
                            self.save_service.current_save_data.inventory_items.append(new_item)
                    added_count += 1
        
        if added_count > 0:
            self.refresh_save_list(self.save_search_var.get())
    
    def add_all_items(self):
        """Add all available items to save"""
        if messagebox.askyesno("Confirm", f"Add all {len(self.available_items)} items to save?"):
            if self.category == ItemCategory.PETS:
                if self.save_service.current_save_data:
                    existing_ids = {p.pet_item_id for p in self.save_service.current_save_data.pets}
                    for item in self.available_items:
                        # Skip items explicitly named "NOTHING"
                        try:
                            if str(item.name).strip().upper() == 'NOTHING':
                                continue
                        except Exception:
                            pass
                        if item.id not in existing_ids:
                            self.save_service.current_save_data.pets.append(PetData(pet_item_id=item.id))
                            self.save_items.append(PlayerInventoryItem(item_id=item.id, amount=1))
                
                self.refresh_save_list(self.save_search_var.get())
            else:
                for item in self.available_items:
                    # Skip items explicitly named "NOTHING"
                    try:
                        if str(item.name).strip().upper() == 'NOTHING':
                            continue
                    except Exception:
                        pass
                    existing_item = next((si for si in self.save_items if si.item_id == item.id), None)
                    if not existing_item:
                        default_inventory = self._default_inventory_for_category(self.category)
                        self.save_items.append(PlayerInventoryItem(item_id=item.id, amount=1, inventory_id=default_inventory))
                self.refresh_save_list(self.save_search_var.get())
    
    def remove_selected_items(self):
        """Remove selected items from save"""
        selected_items = self.save_tree.selection()
        if not selected_items:
            return
        
        # Get item IDs to remove
        item_ids_to_remove = []
        for item in selected_items:
            values = self.save_tree.item(item, 'values')
            if values:
                item_ids_to_remove.append(int(values[0]))
        
        if self.category == ItemCategory.PETS:
            # Remove from model and local list
            if self.save_service.current_save_data:
                self.save_service.current_save_data.pets = [p for p in self.save_service.current_save_data.pets if p.pet_item_id not in item_ids_to_remove]
            self.save_items = [item for item in self.save_items if item.item_id not in item_ids_to_remove]
            self.refresh_save_list(self.save_search_var.get())
        else:
            self.save_items = [item for item in self.save_items if item.item_id not in item_ids_to_remove]
            self.refresh_save_list(self.save_search_var.get())
    
    def clear_all_items(self):
        """Clear all items from save"""
        if messagebox.askyesno("Confirm", f"Remove all {len(self.save_items)} items from save?"):
            if self.category == ItemCategory.PETS:
                if self.save_service.current_save_data:
                    self.save_service.current_save_data.pets.clear()
                self.save_items.clear()
                self.refresh_save_list(self.save_search_var.get())
            else:
                self.save_items.clear()
                self.refresh_save_list(self.save_search_var.get())
    
    def edit_item_amount(self):
        """Edit the amount of selected item"""
        selected_items = self.save_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.save_tree.item(item, 'values')
        if not values:
            return
        
        item_id = int(values[0])
        current_amount = int(values[2])
        
        # Ask for new amount
        new_amount = tk.simpledialog.askinteger(
            "Edit Amount",
            f"Enter new amount for {values[1]}:",
            initialvalue=current_amount,
            minvalue=0,
            maxvalue=999999
        )
        
        if new_amount is not None:
            # Find and update the item
            save_item = next((si for si in self.save_items if si.item_id == item_id), None)
            if save_item:
                if new_amount == 0:
                    # Remove item if amount is 0
                    self.save_items.remove(save_item)
                else:
                    save_item.amount = new_amount
                
                self.refresh_save_list(self.save_search_var.get())
    
    def load_save_data(self, save_data: SaveData):
        """Load save data and filter items for this category"""
        if self.category == ItemCategory.PETS:
            # Build pseudo-items for pets using item_id=pet_item_id and amount=1 for display
            category_items: list[PlayerInventoryItem] = []
            for pet in save_data.pets:
                category_items.append(PlayerInventoryItem(item_id=pet.pet_item_id, amount=1))
            self.save_items = category_items
            self.refresh_save_list(self.save_search_var.get())
        else:
            # Filter inventory items for this category
            category_items = []
            for inv_item in save_data.inventory_items:
                game_item = self.collection.get_item(inv_item.item_id)
                if game_item:  # Item exists in this category
                    category_items.append(inv_item)
            self.save_items = category_items
            self.refresh_save_list(self.save_search_var.get())
    
    def update_save_data(self):
        """Update the save data with current items"""
        if not self.save_service.current_save_data:
            logger.warning("No save data available to update")
            return
        logger.info(f"Updating save data for category: {self.category}")
        save_data = self.save_service.current_save_data
        
        # Special case: Tools are already updated in the original_save
        if self.category == ItemCategory.TOOLS:
            logger.info("[TOOL] Tools are managed directly in original_save, no update needed")
            return
            
        if self.category == ItemCategory.PETS:
            # Reconcile pets in model based on displayed list (unique per pet_item_id)
            desired_ids = {si.item_id for si in self.save_items}
            new_pets: list[PetData] = []
            # Keep existing pets if still present
            for pet in save_data.pets:
                if pet.pet_item_id in desired_ids:
                    new_pets.append(pet)
                    desired_ids.remove(pet.pet_item_id)
            # Add remaining
            for pid in desired_ids:
                new_pets.append(PetData(pet_item_id=pid))
            save_data.pets = new_pets
            return
        else:
            # Remove existing items of this category from save data
            save_data.inventory_items = [
                item for item in save_data.inventory_items
                if not self.collection.get_item(item.item_id)  # Keep items NOT in this category
            ]
            
            # Normalize inventory group for categories that must live in a specific ListInventories bucket
            normalized_items: List[PlayerInventoryItem] = []
            for inv_item in self.save_items:
                # Create a new item to avoid modifying the original
                new_item = PlayerInventoryItem(
                    item_id=inv_item.item_id,
                    amount=inv_item.amount,
                    state=inv_item.state,
                    inventory_id=inv_item.inventory_id
                )
                
                # Set the correct inventory ID based on category
                if self.category in {ItemCategory.HOUSE_SKINS, ItemCategory.NPC_HOUSES}:
                    new_item.inventory_id = '5'
                    logger.info(f"[HOUSE] Setting item {new_item.item_id} to inventory 5")
                elif self.category == ItemCategory.NPC_SKINS:
                    new_item.inventory_id = '7'
                    logger.info(f"[SKIN] Setting item {new_item.item_id} to inventory 7")
                elif new_item.inventory_id is None:
                    new_item.inventory_id = self._default_inventory_for_category(self.category)
                    logger.info(f"[DEFAULT] Setting item {new_item.item_id} to inventory {new_item.inventory_id}")
                
                # Force amount to 1 for certain categories
                if self.category in {ItemCategory.HOUSE_SKINS, ItemCategory.NPC_HOUSES, ItemCategory.NPC_SKINS}:
                    new_item.amount = 1
                    logger.info(f"[AMOUNT] Forcing item {new_item.item_id} amount to 1")
                
                normalized_items.append(new_item)
            
            logger.info(f"Adding {len(normalized_items)} normalized items to save data")
            save_data.inventory_items.extend(normalized_items)

    # --- Pets-specific helpers ---
    def _get_selected_pet(self) -> PetData | None:
        if not self.save_service.current_save_data:
            return None
        sel = self.save_tree.selection()
        if not sel:
            return None
        item = sel[0]
        values = self.save_tree.item(item, 'values')
        if not values:
            return None
        try:
            item_id = int(values[0])
        except Exception:
            return None
        for pet in self.save_service.current_save_data.pets:
            if pet.pet_item_id == item_id:
                return pet
        return None

    def _load_pet_fields_from_selected(self):
        pet = self._get_selected_pet()
        if not pet:
            return
        # Populate fields; prefer custom_name when present
        self.pet_name_var.set(pet.name or "")
        self.pet_custom_name_var.set(pet.custom_name or "")
        self.pet_friendship_level_var.set(pet.friendship_level or 0)
        self.pet_xp_var.set(pet.xp or 0)
        # (Is Following field removed from UI)

    def _apply_pet_fields_to_selected(self):
        pet = self._get_selected_pet()
        if not pet:
            return
        pet.name = self.pet_name_var.get().strip() or None
        pet.custom_name = self.pet_custom_name_var.get().strip() or None
        try:
            pet.friendship_level = int(self.pet_friendship_level_var.get())
        except Exception:
            pet.friendship_level = None
        try:
            pet.xp = int(self.pet_xp_var.get())
        except Exception:
            pet.xp = None
        # (Is Following field removed from UI)

    def show_available_context_menu(self, event):
        """Show context menu for available items list"""
        try:
            # Select the item under cursor if not already selected
            index = self.available_listbox.nearest(event.y)
            if index not in self.available_listbox.curselection():
                self.available_listbox.selection_clear(0, tk.END)
                self.available_listbox.selection_set(index)
            self.available_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.available_context_menu.grab_release()
    
    def show_save_context_menu(self, event):
        """Show context menu for save items tree"""
        try:
            # Select the item under cursor if not already selected
            item = self.save_tree.identify_row(event.y)
            if item and item not in self.save_tree.selection():
                self.save_tree.selection_set(item)
            self.save_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.save_context_menu.grab_release()
    
    def copy_selected_id(self):
        """Copy ID of selected item in available items list"""
        selected = self.available_listbox.curselection()
        if not selected:
            return
        
        # Get the selected text directly from the listbox
        text = self.available_listbox.get(selected[0])
        try:
            # Extract ID from "ID - Name" format
            item_id = text.split(" - ")[0].strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(item_id)
            ToastNotification(self.root, f"Copied ID: {item_id}")
        except Exception as e:
            logger.error(f"Error copying ID: {e}")
    
    def copy_selected_name(self):
        """Copy name of selected item in available items list"""
        selected = self.available_listbox.curselection()
        if not selected:
            return
        
        # Get the selected text directly from the listbox
        text = self.available_listbox.get(selected[0])
        try:
            # Extract name from "ID - Name" format
            name = text.split(" - ", 1)[1].strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            ToastNotification(self.root, f"Copied name: {name}")
        except Exception as e:
            logger.error(f"Error copying name: {e}")
    
    def copy_selected_save_id(self):
        """Copy ID of selected item in save items tree"""
        selected = self.save_tree.selection()
        if not selected:
            return
        
        values = self.save_tree.item(selected[0], 'values')
        if values:
            self.root.clipboard_clear()
            self.root.clipboard_append(values[0])  # ID is first column
            ToastNotification(self.root, f"Copied ID: {values[0]}")
    
    def copy_selected_save_name(self):
        """Copy name of selected item in save items tree"""
        selected = self.save_tree.selection()
        if not selected:
            return
        
        values = self.save_tree.item(selected[0], 'values')
        if values:
            self.root.clipboard_clear()
            self.root.clipboard_append(values[1])  # Name is second column
            ToastNotification(self.root, f"Copied name: {values[1]}")

    def _default_inventory_for_category(self, category: ItemCategory) -> str:
        """Get the default inventory ID for a category using the augmentation service."""
        # Special case: Tools should be added to Player.Tools array
        if category == ItemCategory.TOOLS:
            logger.info(f"[TOOL] Category {category} is for tools, items will be added to Player.Tools array")
            return None
            
        # Special case: Furniture must always go to inventory 0
        if category == ItemCategory.FURNITURE:
            logger.info(f"[FURNITURE] Category {category} items must go to inventory 0")
            return "0"
            
        # Map category to a sample item ID pattern
        category_to_pattern = {
            ItemCategory.PETS: 40000000,  # General items
            ItemCategory.FOOD: 40000000,  # General items
            ItemCategory.MATERIALS: 40000000,  # General items
            ItemCategory.CLOTHES_OUTFITS: 50000000,  # Clothes
            ItemCategory.CLOTHES_TOPS: 50000000,  # Clothes
            ItemCategory.CLOTHES_BOTTOMS: 50000000,  # Clothes
            ItemCategory.CLOTHES_HELMETS: 50000000,  # Clothes
            ItemCategory.CLOTHES_SHOES: 50000000,  # Clothes
            ItemCategory.CLOTHES_ACCESSORIES: 50000000,  # Clothes
            ItemCategory.CLOTHES_OTHER: 50000000,  # Clothes
            ItemCategory.HOUSE_SKINS: 20000000,  # Houses
            ItemCategory.NPC_HOUSES: 20000000,  # Houses
            ItemCategory.NPC_SKINS: 170000000,  # NPC skins
            ItemCategory.HOUSE_WALLPAPER: 160000001,  # Wallpapers (White Gold-Embossed Wall)
            ItemCategory.HOUSE_FLOORS: 160100000,  # Floors (Wooden Floor)
        }
        
        # Get a sample item ID for this category
        sample_id = category_to_pattern.get(category, 40000000)  # Default to general items
        
        # Use the augmentation service to determine the inventory
        inventory_id = InventoryType.get_inventory_for_id(sample_id)
        if inventory_id is None:
            logger.warning(f"Could not determine inventory for category {category}, using default '1'")
            return "1"
            
        logger.info(f"Category {category} mapped to inventory {inventory_id} based on pattern {sample_id}")
        return inventory_id

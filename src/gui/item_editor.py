"""
Item editor frame for editing game items
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional
import logging

from ..models.game_item import ItemCategory, ItemCollection, GameItem, SaveData, PlayerInventoryItem, PetData
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService


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
    
    def setup_save_items_panel(self):
        """Setup the items in save panel"""
        right_frame = ttk.LabelFrame(self.paned, text="Items in Save", padding=10)
        self.paned.add(right_frame, weight=1)
        
        # Search frame
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.save_search_var = tk.StringVar()
        self.save_search_entry = ttk.Entry(search_frame, textvariable=self.save_search_var)
        self.save_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.save_search_entry.bind('<KeyRelease>', self.on_save_search)
        
        # Treeview for save items (with quantity)
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Name', 'Amount')
        self.save_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
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
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="Edit Amount", command=self.edit_item_amount).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected_items).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_items).pack(side=tk.LEFT)
        ttk.Label(button_frame, text="  ").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add All", command=self.add_all_items).pack(side=tk.LEFT)

        # Pets editor panel (visible only for PETS category)
        if self.category == ItemCategory.PETS:
            pets_frame = ttk.LabelFrame(right_frame, text="Pet Details", padding=10)
            pets_frame.pack(fill=tk.X, pady=(10, 0))

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
            return
        
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
                        existing_item.amount += 1
                    else:
                        default_inventory = self._default_inventory_for_category(self.category)
                        self.save_items.append(PlayerInventoryItem(item_id=item.id, amount=1, inventory_id=default_inventory))
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
            return
        save_data = self.save_service.current_save_data
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
                if not self.collection.get_item(item.item_id)
            ]
            # Normalize inventory group for categories that must live in a specific ListInventories bucket
            normalized_items: List[PlayerInventoryItem] = []
            for inv_item in self.save_items:
                if self.category in {ItemCategory.HOUSE_SKINS, ItemCategory.NPC_HOUSES}:
                    inv_item.inventory_id = '5'
                elif self.category == ItemCategory.NPC_SKINS:
                    inv_item.inventory_id = '7'
                elif inv_item.inventory_id is None:
                    inv_item.inventory_id = self._default_inventory_for_category(self.category)
                if self.category in {ItemCategory.HOUSE_SKINS, ItemCategory.NPC_HOUSES, ItemCategory.NPC_SKINS}:
                    inv_item.amount = 1
                normalized_items.append(inv_item)
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

    def _default_inventory_for_category(self, category: ItemCategory) -> str:
        """Map categories to default inventory ids to preserve placement semantics.
        These are best-effort defaults; existing items retain their original inventory_id.
        """
        # Note: Inventory ids are based on observed DDV saves and may vary.
        # '1' often corresponds to general inventory. Specialized groups may differ.
        category_defaults = {
            ItemCategory.PETS: '1',
            ItemCategory.FURNITURE: '1',
            ItemCategory.TOOLS: '1',
            ItemCategory.FOOD: '1',
            ItemCategory.MATERIALS: '1',
            ItemCategory.CLOTHES_OUTFITS: '1',
            ItemCategory.CLOTHES_TOPS: '1',
            ItemCategory.CLOTHES_BOTTOMS: '1',
            ItemCategory.CLOTHES_HELMETS: '1',
            ItemCategory.CLOTHES_SHOES: '1',
            ItemCategory.CLOTHES_ACCESSORIES: '1',
            ItemCategory.CLOTHES_OTHER: '1',
            # House-related items (true buildings/skins) live in ListInventories['5'] in legacy app
            ItemCategory.HOUSE_SKINS: '5',
            ItemCategory.NPC_HOUSES: '5',
            # Character skins live in ListInventories['7'] in legacy app
            ItemCategory.NPC_SKINS: '7',
            # Wallpapers/Floors are not buildings; keep them in general buckets
            ItemCategory.HOUSE_WALLPAPER: '1',
            ItemCategory.HOUSE_FLOORS: '1',
        }
        return category_defaults.get(category, '1')

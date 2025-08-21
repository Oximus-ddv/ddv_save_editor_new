"""
JSON Viewer and Editor window for DDV Save Editor
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from typing import Optional, Dict, Any, Callable
from ..services.augmentation_service import add_item_to_save

logger = logging.getLogger(__name__)

class JsonTreeView(ttk.Treeview):
    """Custom tree view for JSON data"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Configure columns
        self["columns"] = ("value", "type")
        self.heading("#0", text="Key")
        self.heading("value", text="Value")
        self.heading("type", text="Type")
        
        # Set column widths
        self.column("#0", width=250)
        self.column("value", width=350)
        self.column("type", width=100)
        
        # Bind double-click to edit
        self.bind("<Double-1>", self._on_double_click)
        
    def _on_double_click(self, event):
        """Handle double-click to edit value"""
        item = self.selection()[0] if self.selection() else None
        if not item:
            return
            
        # Get current values
        key = self.item(item, "text")
        value = self.item(item, "values")[0] if self.item(item, "values") else ""
        type_name = self.item(item, "values")[1] if self.item(item, "values") else ""
        
        # Don't edit if it's a container (dict/list)
        if type_name in ("dict", "list"):
            return
            
        # Create edit dialog
        dialog = EditValueDialog(self, key, value, type_name)
        if dialog.result is not None:
            # Update the tree
            self.item(item, values=(dialog.result, type_name))
            # Notify parent
            self.event_generate("<<JsonModified>>")

class AddItemDialog:
    """Dialog for adding items to the inventory"""
    
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Item")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Add padding
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Item ID entry
        ttk.Label(frame, text="Item ID:").pack(pady=(0, 5))
        self.id_entry = ttk.Entry(frame, width=40)
        self.id_entry.pack(pady=(0, 10))
        
        # Amount entry
        ttk.Label(frame, text="Amount:").pack(pady=(0, 5))
        self.amount_entry = ttk.Entry(frame, width=40)
        self.amount_entry.insert(0, "1")
        self.amount_entry.pack(pady=(0, 10))
        
        # Inventory ID entry
        ttk.Label(frame, text="Inventory ID (optional):").pack(pady=(0, 5))
        self.inventory_entry = ttk.Entry(frame, width=40)
        self.inventory_entry.pack(pady=(0, 10))
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()//3,
            parent.winfo_rooty() + parent.winfo_height()//3
        ))
        
        # Make dialog modal
        self.id_entry.focus_set()
        self.dialog.wait_window()
        
    def _on_ok(self):
        """Validate and save the new item"""
        try:
            # Validate item ID
            item_id_str = self.id_entry.get().strip()
            if not item_id_str:
                raise ValueError("Item ID is required")
            item_id = int(item_id_str)
            if item_id <= 0:
                raise ValueError("Item ID must be a positive number")
            
            # Validate amount
            amount_str = self.amount_entry.get().strip()
            if not amount_str:
                raise ValueError("Amount is required")
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be a positive number")
            
            # Get inventory ID (optional)
            inventory_id = self.inventory_entry.get().strip()
            
            self.result = {
                'item_id': item_id,
                'amount': amount,
                'inventory_id': inventory_id if inventory_id else None
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror(
                "Invalid Input",
                str(e)
            )

class EditValueDialog:
    """Dialog for editing JSON values"""
    
    def __init__(self, parent, key: str, value: str, type_name: str):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit {key}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Add padding
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Value entry
        ttk.Label(frame, text=f"Enter new value ({type_name}):").pack(pady=(0, 5))
        self.entry = ttk.Entry(frame, width=40)
        self.entry.insert(0, value)
        self.entry.pack(pady=(0, 10))
        self.entry.select_range(0, tk.END)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)
        
        # Store type for validation
        self.type_name = type_name
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()//3,
            parent.winfo_rooty() + parent.winfo_height()//3
        ))
        
        # Make dialog modal
        self.entry.focus_set()
        self.dialog.wait_window()
        
    def _on_ok(self):
        """Validate and save the new value"""
        try:
            value = self.entry.get()
            
            # Convert value based on type
            if self.type_name == "number":
                if "." in value:
                    self.result = float(value)
                else:
                    self.result = int(value)
            elif self.type_name == "boolean":
                self.result = value.lower() == "true"
            elif self.type_name == "null":
                self.result = None
            else:
                self.result = value
                
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror(
                "Invalid Value",
                f"Could not convert value to {self.type_name}: {str(e)}"
            )

class JsonViewerWindow(tk.Toplevel):
    """Window for viewing and editing JSON data"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("JSON Viewer")
        self.geometry("800x600")
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Create main frame with padding
        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Create tree view with scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create tree view
        self.tree = JsonTreeView(tree_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.configure(command=self.tree.yview)
        hsb.configure(command=self.tree.xview)
        
        # Add Item button
        ttk.Button(toolbar, text="Add Item", command=self._add_item_dialog).pack(side=tk.LEFT, padx=5)
        
        # Search
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
    def _add_item_dialog(self):
        """Show dialog to add an item"""
        dialog = AddItemDialog(self)
        if dialog.result:
            try:
                # Get the current save data as a dictionary
                save_dict = self._get_json_data()
                if not save_dict:
                    messagebox.showerror("Error", "Could not get current save data")
                    return
                
                # Add the item using the augmentation service
                success = add_item_to_save(
                    save_dict,
                    item_id=dialog.result['item_id'],
                    amount=dialog.result['amount'],
                    inventory_id=dialog.result['inventory_id']
                )
                
                if success:
                    # Update the tree view with the new save data
                    self._load_json_data(save_dict)
                    
                    # Show success message
                    inventory_id = dialog.result['inventory_id'] or 'default'
                    messagebox.showinfo(
                        "Success",
                        f"Added item {dialog.result['item_id']} with amount {dialog.result['amount']} to inventory {inventory_id}"
                    )
                else:
                    messagebox.showerror("Error", "Failed to add item to save data")
                    
            except Exception as e:
                logger.error(f"Error adding item: {e}")
                messagebox.showerror("Error", f"Failed to add item: {str(e)}")
        
        # Expand/Collapse buttons
        ttk.Button(toolbar, text="Expand All", command=self._expand_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Collapse All", command=self._collapse_all).pack(side=tk.LEFT, padx=2)
        
        # Add item button
        ttk.Button(toolbar, text="Add Item", command=self._add_item_dialog).pack(side=tk.LEFT, padx=2)
        
        # Create frame for tree and scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tree with scrollbars
        self.tree = JsonTreeView(tree_frame)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Pack layout
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind events
        self.tree.bind("<<JsonModified>>", self._on_json_modified)
        
        # Store callback
        self.on_modified_callback: Optional[Callable] = None
        
    def load_json(self, data: Dict[str, Any]):
        """Load JSON data into the tree"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add root item
        root = self.tree.insert("", "end", text="root", values=("", "dict"))
        
        # Recursively add items
        self._add_json_items(root, data)
        
        # Expand root
        self.tree.item(root, open=True)
        
    def _add_json_items(self, parent: str, data: Any):
        """Recursively add JSON items to the tree"""
        if isinstance(data, dict):
            for key, value in data.items():
                item = self.tree.insert(
                    parent, "end",
                    text=str(key),
                    values=("", self._get_type_name(value))
                )
                if isinstance(value, (dict, list)):
                    self._add_json_items(item, value)
                else:
                    self.tree.item(item, values=(str(value), self._get_type_name(value)))
                    
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = self.tree.insert(
                    parent, "end",
                    text=str(i),
                    values=("", self._get_type_name(value))
                )
                if isinstance(value, (dict, list)):
                    self._add_json_items(item, value)
                else:
                    self.tree.item(item, values=(str(value), self._get_type_name(value)))
                    
    def _get_type_name(self, value: Any) -> str:
        """Get type name for a value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, list):
            return "list"
        elif value is None:
            return "null"
        else:
            return type(value).__name__
            
    def _on_search(self, *args):
        """Handle search text changes"""
        search_text = self.search_var.get().lower()
        
        # Show all items if search is empty
        if not search_text:
            self._show_all_items()
            return
            
        # Search and show/hide items
        self._search_items("", search_text)
        
    def _search_items(self, item_id: str, search_text: str) -> bool:
        """
        Recursively search items and show/hide based on search text
        Returns True if this item or any children match the search
        """
        # Start with root if no item_id
        children = self.tree.get_children(item_id)
        
        # Check current item
        item_matches = False
        if item_id:  # Skip root when checking text
            item = self.tree.item(item_id)
            texts = [
                str(item["text"]).lower(),
                str(item["values"][0]).lower() if item["values"] else "",
                str(item["values"][1]).lower() if item["values"] else ""
            ]
            item_matches = any(search_text in text for text in texts)
            
        # Check children
        child_matches = False
        for child in children:
            if self._search_items(child, search_text):
                child_matches = True
                
        # Show if this item or any children match
        matches = item_matches or child_matches
        if item_id:  # Don't hide root
            self.tree.detach(item_id) if not matches else self.tree.reattach(item_id, self.tree.parent(item_id), "end")
            
        return matches
        
    def _show_all_items(self):
        """Show all items"""
        def reattach_all(item_id: str):
            children = self.tree.get_children(item_id)
            for child in children:
                # Get the parent before detaching
                parent = self.tree.parent(child)
                # Reattach the item
                self.tree.reattach(child, parent, "end")
                # Process children
                reattach_all(child)
                
        reattach_all("")
        
    def _expand_all(self):
        """Expand all items"""
        def expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand(child)
        expand("")
        
    def _collapse_all(self):
        """Collapse all items"""
        def collapse(item):
            for child in self.tree.get_children(item):
                collapse(child)
            if item:  # Don't collapse root
                self.tree.item(item, open=False)
        collapse("")
        
    def _on_json_modified(self, event):
        """Handle JSON modifications"""
        if self.on_modified_callback:
            self.on_modified_callback()
            
    def _add_item_dialog(self):
        """Show dialog to add an item"""
        dialog = AddItemDialog(self)
        if dialog.result:
            # Find or create the inventory path
            inventory_id = dialog.result['inventory_id'] or '0'  # Default to inventory 0 if not specified
            
            # Find the Player node
            player_node = None
            for item in self.tree.get_children():
                if self.tree.item(item)["text"] == "Player":
                    player_node = item
                    break
            
            if not player_node:
                messagebox.showerror("Error", "Could not find Player node in save file")
                return
            
            # Find or create ContainerInventories
            container_inv_node = None
            for item in self.tree.get_children(player_node):
                if self.tree.item(item)["text"] == "ContainerInventories":
                    container_inv_node = item
                    break
            
            if not container_inv_node:
                container_inv_node = self.tree.insert(
                    player_node, "end",
                    text="ContainerInventories",
                    values=("", "dict")
                )
            
            # Find or create specific inventory
            inv_node = None
            for item in self.tree.get_children(container_inv_node):
                if self.tree.item(item)["text"] == inventory_id:
                    inv_node = item
                    break
            
            if not inv_node:
                inv_node = self.tree.insert(
                    container_inv_node, "end",
                    text=inventory_id,
                    values=("", "dict")
                )
            
            # Find or create Inventory array
            inventory_array_node = None
            for item in self.tree.get_children(inv_node):
                if self.tree.item(item)["text"] == "Inventory":
                    inventory_array_node = item
                    break
            
            if not inventory_array_node:
                inventory_array_node = self.tree.insert(
                    inv_node, "end",
                    text="Inventory",
                    values=("", "list")
                )
            
            # Add the new item
            item_node = self.tree.insert(
                inventory_array_node, "end",
                text=str(len(self.tree.get_children(inventory_array_node))),
                values=("", "dict")
            )
            
            # Add ItemID
            self.tree.insert(
                item_node, "end",
                text="ItemID",
                values=(str(dialog.result['item_id']), "number")
            )
            
            # Add Amount
            self.tree.insert(
                item_node, "end",
                text="Amount",
                values=(str(dialog.result['amount']), "number")
            )
            
            # Notify that JSON was modified
            self.tree.event_generate("<<JsonModified>>")
            
            # Show success message
            messagebox.showinfo(
                "Success",
                f"Added item {dialog.result['item_id']} with amount {dialog.result['amount']} to inventory {inventory_id}"
            )

    def get_json_data(self) -> Dict[str, Any]:
        """Convert the current tree view back to a JSON object"""
        def process_item(item_id: str) -> Any:
            item = self.tree.item(item_id)
            type_name = item["values"][1] if item["values"] else None
            
            if type_name in ("dict", "list"):
                children = self.tree.get_children(item_id)
                if type_name == "dict":
                    return {
                        self.tree.item(child)["text"]: process_item(child)
                        for child in children
                    }
                else:  # list
                    return [process_item(child) for child in children]
            else:
                # Convert value based on type
                value = item["values"][0] if item["values"] else None
                if type_name == "number":
                    return float(value) if "." in value else int(value)
                elif type_name == "boolean":
                    return value.lower() == "true"
                elif type_name == "null":
                    return None
                else:
                    return value
                    
        # Start with root's children (skip root itself)
        root = self.tree.get_children()[0]
        return process_item(root)
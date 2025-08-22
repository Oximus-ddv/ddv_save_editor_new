"""
Full JSON editor window for DDV Save Editor with key-value-description format
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from typing import Optional, Dict, Any, Callable
from ..services.dict_service import DictDataService

logger = logging.getLogger(__name__)

class FullEditorWindow(tk.Toplevel):
    """Window for viewing and editing the full save file in key-value-description format"""
    
    def __init__(self, parent, dict_service: DictDataService):
        super().__init__(parent)
        self.title("Full Editor")
        self.geometry("1000x600")
        
        self.dict_service = dict_service
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Create main frame with padding
        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Search
        ttk.Label(toolbar, text="Find:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add search button
        self.search_button = ttk.Button(toolbar, text="Search", command=self._on_search)
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bind Enter key to search
        self.search_entry.bind('<Return>', lambda e: self._on_search())
        
        # Create tree view with scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tree view with key column and enable virtual mode for performance
        self.tree = ttk.Treeview(tree_frame, columns=("value",), selectmode="extended")
        self.tree.heading("#0", text="Key")  # First column for keys
        self.tree.heading("value", text="Value")
        
        # Set column widths
        self.tree.column("#0", width=600)  # Key column
        self.tree.column("value", width=300)
        
        # Store all items in memory for faster searching
        self.all_items = []
        self.filtered_items = []
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to edit
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # Store callback
        self.on_modified_callback: Optional[Callable] = None
        
        # Dictionary to store the full paths of items
        self.item_paths = {}
        
    def load_json(self, data: Dict[str, Any]):
        """Load JSON data into the tree"""
        # Clear existing data
        self.all_items.clear()
        self.filtered_items.clear()
        self.item_paths.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Show loading cursor
        self.tree.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            # Load game database once
            game_db = self.dict_service.load_game_database()
            
            # Flatten the JSON structure first
            flat_data = {}
            self._flatten_json(data, "", flat_data)
            
            # Pre-process all items
            for key, value in flat_data.items():
                self.all_items.append((key, str(value)))
            
            # Sort items for consistent display
            self.all_items.sort(key=lambda x: x[0])  # Sort by key
            self.filtered_items = self.all_items.copy()
            
            # Add items in batches
            self._display_items()
            
        finally:
            self.tree.configure(cursor="")
        
    def _flatten_json(self, data: Any, prefix: str, result: Dict[str, Any]) -> None:
        """Convert nested JSON structure to flat key-value pairs"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._flatten_json(value, new_key, result)
                else:
                    result[new_key] = value
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_key = f"{prefix}[{i}]"
                if isinstance(value, (dict, list)):
                    self._flatten_json(value, new_key, result)
                else:
                    result[new_key] = value
        else:
            result[prefix] = data
                    
    def _get_description(self, path: str) -> str:
        """Get description for a path"""
        # Try to get item name from dictionary service
        if path.endswith("ItemID"):
            try:
                item_id = int(self.tree.set(self.tree.selection()[0], "value"))
                item = self.dict_service.get_item_by_id(item_id)
                if item:
                    return item.name
            except:
                pass
        return ""
        
    def _on_double_click(self, event):
        """Handle double-click to edit value"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
            
        # Get current value
        current_value = self.tree.set(item, "value")
        
        # Create edit dialog
        dialog = EditValueDialog(self, self.item_paths[item], current_value)
        if dialog.result is not None:
            # Update the tree
            self.tree.set(item, "value", str(dialog.result))
            
            # Update description if it's an item ID
            if self.item_paths[item].endswith("ItemID"):
                try:
                    item_id = int(dialog.result)
                    item = self.dict_service.get_item_by_id(item_id)
                    if item:
                        self.tree.set(item, "description", item.name)
                except:
                    pass
            
            # Notify that data was modified
            if self.on_modified_callback:
                self.on_modified_callback()
                
    def _display_items(self):
        """Display the current filtered items in the tree"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add items in batches
        batch_size = 1000
        for i in range(0, len(self.filtered_items), batch_size):
            batch = self.filtered_items[i:i + batch_size]
            for key, value in batch:
                item = self.tree.insert("", "end", text=key, values=(value,))
                self.item_paths[item] = key  # Store key for editing
            
            # Update UI periodically
            if i % (batch_size * 5) == 0:
                self.update_idletasks()
    
    def _on_search(self):
        """Handle search button click or Enter key"""
        search_text = self.search_var.get().lower()
        
        # Disable search controls during search
        self.search_button.configure(state="disabled")
        self.search_entry.configure(state="disabled")
        self.tree.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            if not search_text:
                # If search is empty, show all items
                self.filtered_items = self.all_items.copy()
            else:
                # Filter items
                self.filtered_items = [
                    item for item in self.all_items
                    if search_text in item[0].lower() or  # key
                       search_text in item[1].lower()     # value
                ]
            
            # Display filtered items
            self._display_items()
            
            # Select and scroll to first match if any
            if self.filtered_items:
                first = self.tree.get_children()[0]
                self.tree.selection_set(first)
                self.tree.see(first)
                
        finally:
            # Re-enable search controls
            self.search_button.configure(state="normal")
            self.search_entry.configure(state="normal")
            self.tree.configure(cursor="")
            self.search_entry.focus_set()
                
    def get_json_data(self) -> Dict[str, Any]:
        """Convert the current tree view back to a JSON object"""
        result = {}
        
        def process_path(path: str, value: str) -> None:
            """Process a path and set the value in the result dictionary"""
            parts = path.split(".")
            current = result
            
            for i, part in enumerate(parts[:-1]):
                # Handle array indices
                if "[" in part:
                    name = part[:part.index("[")]
                    index = int(part[part.index("[")+1:part.index("]")])
                    
                    if name not in current:
                        current[name] = []
                    while len(current[name]) <= index:
                        current[name].append({})
                    current = current[name][index]
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
            
            # Handle the final part
            last_part = parts[-1]
            if "[" in last_part:
                name = last_part[:last_part.index("[")]
                index = int(last_part[last_part.index("[")+1:last_part.index("]")])
                
                if name not in current:
                    current[name] = []
                while len(current[name]) <= index:
                    current[name].append(None)
                current[name][index] = self._convert_value(value)
            else:
                current[last_part] = self._convert_value(value)
        
        # Process all visible items
        for item in self.tree.get_children():
            path = self.item_paths[item]
            value = self.tree.set(item, "value")
            process_path(path, value)
            
        return result
        
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Try to convert to number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
            
        # Check for boolean
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
            
        # Check for null
        if value.lower() == "null":
            return None
            
        # Default to string
        return value

class EditValueDialog:
    """Dialog for editing values"""
    
    def __init__(self, parent, path: str, current_value: str):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Value")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Add padding
        frame = ttk.Frame(self.dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Show path
        ttk.Label(frame, text=f"Path: {path}").pack(pady=(0, 10))
        
        # Value entry
        ttk.Label(frame, text="Value:").pack(pady=(0, 5))
        self.entry = ttk.Entry(frame, width=40)
        self.entry.insert(0, current_value)
        self.entry.pack(pady=(0, 10))
        self.entry.select_range(0, tk.END)
        
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
        self.entry.focus_set()
        self.dialog.wait_window()
        
    def _on_ok(self):
        """Save the edited value"""
        self.result = self.entry.get()
        self.dialog.destroy()

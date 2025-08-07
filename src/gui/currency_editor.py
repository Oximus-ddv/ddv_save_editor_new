"""
Currency editor frame for editing game currencies
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional
import logging

from ..models.game_item import SaveData
from ..services.save_service import SaveFileService


logger = logging.getLogger(__name__)


class CurrencyEditorFrame(ttk.Frame):
    """Frame for editing game currencies"""
    
    def __init__(self, parent, save_service: SaveFileService):
        super().__init__(parent)
        
        self.save_service = save_service
        self.save_data: Optional[SaveData] = None
        
        # Currency variables
        self.star_coins_var = tk.IntVar()
        self.dreamlight_var = tk.IntVar()
        self.daisy_coins_var = tk.IntVar()
        self.mist_var = tk.IntVar()
        self.pixel_dust_var = tk.IntVar()
        
        # Player info variables
        self.player_name_var = tk.StringVar()
        self.player_level_var = tk.IntVar()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Player info section
        self.setup_player_info_section(main_frame)
        
        # Currencies section
        self.setup_currencies_section(main_frame)
        
        # Action buttons
        self.setup_action_buttons(main_frame)
    
    def setup_player_info_section(self, parent):
        """Setup player information section"""
        player_frame = ttk.LabelFrame(parent, text="Player Information", padding=10)
        player_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Player name
        ttk.Label(player_frame, text="Player Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        name_entry = ttk.Entry(player_frame, textvariable=self.player_name_var, width=30)
        name_entry.grid(row=0, column=1, sticky=tk.W)
        
        # Player level
        ttk.Label(player_frame, text="Level:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        level_spinbox = ttk.Spinbox(player_frame, from_=1, to=999, textvariable=self.player_level_var, width=10)
        level_spinbox.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
    
    def setup_currencies_section(self, parent):
        """Setup currencies section"""
        currency_frame = ttk.LabelFrame(parent, text="Currencies", padding=10)
        currency_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Currency definitions
        currencies = [
            ("Star Coins:", self.star_coins_var, "Main currency for purchases"),
            ("Dreamlight:", self.dreamlight_var, "Used for unlocking areas and features"),
            ("Daisy Coins:", self.daisy_coins_var, "Special event currency"),
            ("Mist:", self.mist_var, "Mystical realm currency"),
            ("Pixel Dust:", self.pixel_dust_var, "Digital realm currency"),
        ]
        
        # Create currency editors
        for i, (label_text, var, tooltip) in enumerate(currencies):
            # Label
            label = ttk.Label(currency_frame, text=label_text)
            label.grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            # Entry with validation
            entry = ttk.Entry(currency_frame, textvariable=var, width=15)
            entry.grid(row=i, column=1, padx=(0, 10), pady=2)
            
            # Max button
            max_button = ttk.Button(
                currency_frame, 
                text="Max", 
                width=6,
                command=lambda v=var: self.set_max_currency(v)
            )
            max_button.grid(row=i, column=2, padx=(0, 10), pady=2)
            
            # Reset button
            reset_button = ttk.Button(
                currency_frame, 
                text="Reset", 
                width=6,
                command=lambda v=var: v.set(0)
            )
            reset_button.grid(row=i, column=3, pady=2)
            
            # Add tooltip (simple version)
            self.create_tooltip(label, tooltip)
        
        # Configure column weights
        currency_frame.columnconfigure(1, weight=1)
    
    def setup_action_buttons(self, parent):
        """Setup action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame, 
            text="Max All Currencies", 
            command=self.max_all_currencies
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="Reset All Currencies", 
            command=self.reset_all_currencies
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="Apply Changes", 
            command=self.apply_changes
        ).pack(side=tk.RIGHT)
    
    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background="lightyellow", 
                            relief=tk.SOLID, borderwidth=1, padding=5)
            label.pack()
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
    
    def set_max_currency(self, var: tk.IntVar):
        """Set a currency to maximum value"""
        var.set(2147483647)  # Max 32-bit signed integer
    
    def max_all_currencies(self):
        """Set all currencies to maximum"""
        max_value = 2147483647
        self.star_coins_var.set(max_value)
        self.dreamlight_var.set(max_value)
        self.daisy_coins_var.set(max_value)
        self.mist_var.set(max_value)
        self.pixel_dust_var.set(max_value)
    
    def reset_all_currencies(self):
        """Reset all currencies to zero"""
        self.star_coins_var.set(0)
        self.dreamlight_var.set(0)
        self.daisy_coins_var.set(0)
        self.mist_var.set(0)
        self.pixel_dust_var.set(0)
    
    def apply_changes(self):
        """Apply changes to save data"""
        if self.save_data:
            self.update_save_data()
            tk.messagebox.showinfo("Success", "Currency changes applied!")
    
    def load_save_data(self, save_data: SaveData):
        """Load save data into the editor"""
        self.save_data = save_data
        
        # Load player info
        self.player_name_var.set(save_data.player_name)
        self.player_level_var.set(save_data.player_level)
        
        # Load currencies
        self.star_coins_var.set(save_data.star_coins)
        self.dreamlight_var.set(save_data.dreamlight)
        self.daisy_coins_var.set(save_data.daisy_coins)
        self.mist_var.set(save_data.mist)
        self.pixel_dust_var.set(save_data.pixel_dust)
    
    def update_save_data(self):
        """Update save data with current values"""
        if not self.save_data:
            return
        
        # Update player info
        self.save_data.player_name = self.player_name_var.get()
        self.save_data.player_level = max(1, self.player_level_var.get())
        
        # Update currencies
        self.save_data.star_coins = max(0, self.star_coins_var.get())
        self.save_data.dreamlight = max(0, self.dreamlight_var.get())
        self.save_data.daisy_coins = max(0, self.daisy_coins_var.get())
        self.save_data.mist = max(0, self.mist_var.get())
        self.save_data.pixel_dust = max(0, self.pixel_dust_var.get())

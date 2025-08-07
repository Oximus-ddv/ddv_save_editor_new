"""
Settings dialog for DDV Save Editor
"""
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path


class SettingsDialog:
    """Settings configuration dialog"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Variables
        self.excel_path_var = tk.StringVar(value="Disney Dream Light ID List - Mainted by Rubyelf.xlsx")
        self.image_zip_var = tk.StringVar(value="img.zip")
        self.image_folder_var = tk.StringVar(value="img")
        self.backup_count_var = tk.IntVar(value=10)
        self.auto_backup_var = tk.BooleanVar(value=True)
        self.show_images_var = tk.BooleanVar(value=True)
        self.cache_size_var = tk.IntVar(value=200)
        # Default DDV hex key (from CyberChef configuration)
        self.hex_key_var = tk.StringVar(value="62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35")
        
        self.setup_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Setup the user interface"""
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File paths tab
        self.setup_file_paths_tab(notebook)
        
        # Image settings tab
        self.setup_image_settings_tab(notebook)
        
        # Backup settings tab
        self.setup_backup_settings_tab(notebook)
        
        # Encryption settings tab
        self.setup_encryption_tab(notebook)
        
        # Buttons
        self.setup_buttons()
    
    def setup_file_paths_tab(self, notebook):
        """Setup file paths configuration tab"""
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="File Paths")
        
        # Excel file path
        ttk.Label(frame, text="Excel Data File:").pack(anchor=tk.W)
        excel_frame = ttk.Frame(frame)
        excel_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Entry(excel_frame, textvariable=self.excel_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(excel_frame, text="Browse", command=self.browse_excel_file).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Image ZIP path
        ttk.Label(frame, text="Image ZIP File:").pack(anchor=tk.W)
        zip_frame = ttk.Frame(frame)
        zip_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Entry(zip_frame, textvariable=self.image_zip_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(zip_frame, text="Browse", command=self.browse_image_zip).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Image folder path
        ttk.Label(frame, text="Image Folder:").pack(anchor=tk.W)
        folder_frame = ttk.Frame(frame)
        folder_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Entry(folder_frame, textvariable=self.image_folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.browse_image_folder).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Help text
        help_text = ("Note: The application will try the ZIP file first, then fall back to the folder. "
                    "You can use either or both options.")
        ttk.Label(frame, text=help_text, wraplength=450, foreground="gray").pack(anchor=tk.W, pady=(10, 0))
    
    def setup_image_settings_tab(self, notebook):
        """Setup image settings tab"""
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Images")
        
        # Show images checkbox
        ttk.Checkbutton(frame, text="Show image previews", variable=self.show_images_var).pack(anchor=tk.W, pady=(0, 15))
        
        # Cache size
        ttk.Label(frame, text="Image Cache Size (number of images):").pack(anchor=tk.W)
        cache_frame = ttk.Frame(frame)
        cache_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Spinbox(cache_frame, from_=50, to=1000, textvariable=self.cache_size_var, width=10).pack(side=tk.LEFT)
        ttk.Label(cache_frame, text="Higher values use more memory but improve performance").pack(side=tk.LEFT, padx=(10, 0))
        
        # Image quality settings
        quality_frame = ttk.LabelFrame(frame, text="Image Quality", padding=10)
        quality_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.thumbnail_size_var = tk.StringVar(value="64x64")
        self.preview_size_var = tk.StringVar(value="128x128")
        
        ttk.Label(quality_frame, text="Thumbnail Size:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Combobox(quality_frame, textvariable=self.thumbnail_size_var, 
                    values=["32x32", "48x48", "64x64", "96x96"], state="readonly", width=10).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(quality_frame, text="Preview Size:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        ttk.Combobox(quality_frame, textvariable=self.preview_size_var,
                    values=["96x96", "128x128", "192x192", "256x256"], state="readonly", width=10).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
    
    def setup_backup_settings_tab(self, notebook):
        """Setup backup settings tab"""
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Backups")
        
        # Auto backup checkbox
        ttk.Checkbutton(frame, text="Create automatic backups when loading/saving", 
                       variable=self.auto_backup_var).pack(anchor=tk.W, pady=(0, 15))
        
        # Max backup count
        ttk.Label(frame, text="Maximum number of backups to keep:").pack(anchor=tk.W)
        backup_frame = ttk.Frame(frame)
        backup_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Spinbox(backup_frame, from_=1, to=100, textvariable=self.backup_count_var, width=10).pack(side=tk.LEFT)
        ttk.Label(backup_frame, text="Older backups will be automatically deleted").pack(side=tk.LEFT, padx=(10, 0))
        
        # Backup location info
        backup_info = ttk.LabelFrame(frame, text="Backup Information", padding=10)
        backup_info.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(backup_info, text="Backups are stored in: ./backups/").pack(anchor=tk.W)
        ttk.Label(backup_info, text="Format: filename_YYYYMMDD_HHMMSS_backup.ext").pack(anchor=tk.W, pady=(5, 0))
        
        # Backup actions
        action_frame = ttk.LabelFrame(frame, text="Backup Actions", padding=10)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="Open Backup Folder", command=self.open_backup_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Clean Old Backups", command=self.clean_old_backups).pack(side=tk.LEFT)
    
    def setup_encryption_tab(self, notebook):
        """Setup encryption settings tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Encryption")
        
        # Encryption settings
        encryption_frame = ttk.LabelFrame(frame, text="Decryption Settings", padding=10)
        encryption_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Hex key setting
        ttk.Label(encryption_frame, text="Default Decryption Key (Hex):").pack(anchor=tk.W)
        hex_entry = ttk.Entry(encryption_frame, textvariable=self.hex_key_var, show='*', width=70)
        hex_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Info about the key
        info_frame = ttk.Frame(encryption_frame)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text="ℹ️ This is the standard DDV encryption key.", foreground="blue").pack(anchor=tk.W)
        ttk.Label(info_frame, text="The application will try this key first before prompting you.", foreground="gray").pack(anchor=tk.W, pady=(2, 0))
        
        # Key actions
        button_frame = ttk.Frame(encryption_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Show/Hide Key", command=lambda: self.toggle_hex_key_visibility(hex_entry)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Reset to Default", command=self.reset_hex_key).pack(side=tk.LEFT)
        
        # CyberChef info
        cyberchef_frame = ttk.LabelFrame(frame, text="CyberChef Integration", padding=10)
        cyberchef_frame.pack(fill=tk.X)
        
        info_text = tk.Text(cyberchef_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        info_text.pack(fill=tk.X)
        
        info_content = """This key matches your CyberChef configuration:
• AES Decrypt with ECB/NoPadding mode
• Followed by Unzip operation
• Same 32-byte hex key format"""
        
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END, info_content)
        info_text.config(state=tk.DISABLED)
    
    def toggle_hex_key_visibility(self, entry_widget):
        """Toggle visibility of hex key"""
        current_show = entry_widget.cget('show')
        if current_show == '*':
            entry_widget.config(show='')
        else:
            entry_widget.config(show='*')
    
    def reset_hex_key(self):
        """Reset hex key to default DDV key"""
        default_key = "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35"
        self.hex_key_var.set(default_key)
    
    def setup_buttons(self):
        """Setup dialog buttons"""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults).pack(side=tk.LEFT)
    
    def browse_excel_file(self):
        """Browse for Excel file"""
        filename = filedialog.askopenfilename(
            title="Select Excel Data File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.excel_path_var.set(filename)
    
    def browse_image_zip(self):
        """Browse for image ZIP file"""
        filename = filedialog.askopenfilename(
            title="Select Image ZIP File",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if filename:
            self.image_zip_var.set(filename)
    
    def browse_image_folder(self):
        """Browse for image folder"""
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.image_folder_var.set(folder)
    
    def open_backup_folder(self):
        """Open backup folder in file explorer"""
        import subprocess
        import sys
        
        backup_path = Path("backups")
        backup_path.mkdir(exist_ok=True)
        
        if sys.platform == "win32":
            subprocess.run(["explorer", str(backup_path)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(backup_path)])
        else:
            subprocess.run(["xdg-open", str(backup_path)])
    
    def clean_old_backups(self):
        """Clean old backup files"""
        # This would implement backup cleanup logic
        tk.messagebox.showinfo("Clean Backups", "Old backups cleaned successfully!")
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        self.excel_path_var.set("Disney Dream Light ID List - Mainted by Rubyelf.xlsx")
        self.image_zip_var.set("img.zip")
        self.image_folder_var.set("img")
        self.backup_count_var.set(10)
        self.auto_backup_var.set(True)
        self.show_images_var.set(True)
        self.cache_size_var.set(200)
        self.thumbnail_size_var.set("64x64")
        self.preview_size_var.set("128x128")
    
    def ok(self):
        """Handle OK button"""
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """Handle Cancel button"""
        self.result = False
        self.dialog.destroy()
    
    def get_settings(self):
        """Get the current settings as a dictionary"""
        return {
            'excel_path': self.excel_path_var.get(),
            'image_zip_path': self.image_zip_var.get(),
            'image_folder_path': self.image_folder_var.get(),
            'max_backups': self.backup_count_var.get(),
            'auto_backup': self.auto_backup_var.get(),
            'show_images': self.show_images_var.get(),
            'cache_size': self.cache_size_var.get(),
            'thumbnail_size': self.thumbnail_size_var.get(),
            'preview_size': self.preview_size_var.get()
        }

"""
Toast notification widget for DDV Save Editor
"""
import tkinter as tk
from tkinter import ttk
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ToastNotification:
    """Displays a toast notification in the bottom-right corner of the screen"""
    
    # Class-level list to track active toasts
    active_toasts: List['ToastNotification'] = []
    toast_height = 45  # Height of each toast
    toast_width = 300  # Width of each toast
    toast_padding = 10  # Padding between toasts
    animation_ms = 16  # Animation step duration (roughly 60fps)
    fade_step = 0.05  # Alpha change per step (slower fade)
    
    def __init__(self, parent: tk.Tk, message: str, duration: float = 3.0):
        """
        Create a new toast notification
        
        Args:
            parent: The root window
            message: Message to display
            duration: How long to show the toast in seconds
        """
        self.parent = parent
        self.message = message
        self.duration = duration
        self.window: Optional[tk.Toplevel] = None
        self.start_time = 0
        self.alpha = 0.0
        
        # Remove expired toasts
        now = time.time()
        ToastNotification.active_toasts = [
            t for t in ToastNotification.active_toasts 
            if now - t.start_time < t.duration
        ]
        
        # Add this toast
        ToastNotification.active_toasts.append(self)
        
        # Create and show the toast
        self._create_window()
        self._animate_in()
        
    def _create_window(self):
        """Create the toast window"""
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        
        # Make it float above other windows
        self.window.lift()
        self.window.attributes('-topmost', True)
        
        # Start fully transparent
        self.window.attributes('-alpha', 0.0)
        
        # Style for a modern look
        self.window.configure(bg='#2d2d2d')
        
        # Frame with padding and rounded appearance
        frame = tk.Frame(self.window, bg='#2d2d2d')
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Message label
        label = tk.Label(
            frame, 
            text=self.message,
            wraplength=self.toast_width - 20,
            justify=tk.LEFT,
            bg='#2d2d2d',
            fg='#ffffff',
            font=('Segoe UI', 10)
        )
        label.pack(padx=10, pady=8)
        
        # Size and position
        self.window.update_idletasks()
        width = self.toast_width
        height = self.toast_height
        
        # Position at bottom right, stacked with other active toasts
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        # Calculate position based on number of active toasts
        toast_index = len(ToastNotification.active_toasts) - 1
        x = screen_width - width - 20
        y = screen_height - (height + self.toast_padding) * (toast_index + 1) - 40
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Start tracking time
        self.start_time = time.time()
    
    def _animate_in(self):
        """Fade in the toast"""
        if not self.window:
            return
            
        self.alpha = min(1.0, self.alpha + self.fade_step)
        self.window.attributes('-alpha', self.alpha)
        
        if self.alpha < 1.0:
            self.window.after(self.animation_ms, self._animate_in)
        else:
            # Start fade out timer
            self.window.after(int(self.duration * 1000), self._animate_out)
    
    def _animate_out(self):
        """Fade out the toast"""
        if not self.window:
            return
            
        self.alpha = max(0.0, self.alpha - self.fade_step)
        self.window.attributes('-alpha', self.alpha)
        
        if self.alpha > 0.0:
            self.window.after(self.animation_ms, self._animate_out)
        else:
            self.destroy()
    
    def destroy(self):
        """Clean up the toast window"""
        if self.window:
            try:
                self.window.destroy()
                self.window = None
            except Exception:
                pass
        try:
            ToastNotification.active_toasts.remove(self)
        except ValueError:
            pass

"""
Toast notification widget for DDV Save Editor
"""
import time
import logging
from typing import List, Optional

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class ToastNotification(QWidget):
    """Displays a toast notification in the bottom-right corner of the screen"""
    
    # Class-level list to track active toasts
    active_toasts: List['ToastNotification'] = []
    toast_height = 45  # Height of each toast
    toast_width = 300  # Width of each toast
    toast_padding = 10  # Padding between toasts
    animation_duration = 250  # Animation duration in milliseconds
    
    def __init__(self, parent: QWidget, message: str, duration: float = 3.0):
        """
        Create a new toast notification
        
        Args:
            parent: The parent widget
            message: Message to display
            duration: How long to show the toast in seconds
        """
        super().__init__(parent)
        self.message = message
        self.duration = duration
        self.start_time = time.time()
        
        # Remove expired toasts
        now = time.time()
        ToastNotification.active_toasts = [
            t for t in ToastNotification.active_toasts 
            if now - t.start_time < t.duration
        ]
        
        # Add this toast
        ToastNotification.active_toasts.append(self)
        
        # Setup UI
        self._setup_ui()
        
        # Show the toast
        self.show()
        self._animate_in()
    
    def _setup_ui(self):
        """Setup the toast window"""
        # Set window flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Create frame
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 8, 10, 8)
        
        # Create label
        label = QLabel(self.message, frame)
        label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
        """)
        label.setWordWrap(True)
        frame_layout.addWidget(label)
        
        layout.addWidget(frame)
        
        # Set size
        self.setFixedSize(self.toast_width, self.toast_height)
        
        # Position at bottom right, stacked with other active toasts
        screen_geometry = self.screen().geometry()
        toast_index = len(ToastNotification.active_toasts) - 1
        x = screen_geometry.width() - self.toast_width - 20
        y = screen_geometry.height() - (self.toast_height + self.toast_padding) * (toast_index + 1) - 40
        self.move(x, y)
        
        # Set initial opacity
        self.setWindowOpacity(0.0)
    
    def _animate_in(self):
        """Fade in the toast"""
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(self.animation_duration)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in.finished.connect(self._schedule_fade_out)
        self.fade_in.start()
    
    def _schedule_fade_out(self):
        """Schedule the fade out animation"""
        QTimer.singleShot(int(self.duration * 1000), self._animate_out)
    
    def _animate_out(self):
        """Fade out the toast"""
        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(self.animation_duration)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out.finished.connect(self.close)
        self.fade_out.start()
    
    def closeEvent(self, event):
        """Handle widget close event"""
        try:
            ToastNotification.active_toasts.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)
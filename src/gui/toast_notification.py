"""
Toast notification widget for DDV Save Editor (PyQt6)
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QRect, Qt
from PyQt6.QtGui import QPalette, QColor

class ToastNotification(QWidget):
    """Displays a toast notification in the bottom-right corner of the screen"""
    
    def __init__(self, parent, message, duration=3000):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.ToolTip | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.layout.addWidget(self.label)

        self.setup_style()

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.show()
        self.animate_in()

        QTimer.singleShot(duration, self.animate_out)

    def setup_style(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53, 200))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.setPalette(palette)

    def animate_in(self):
        screen_geometry = self.screen().geometry()
        start_geometry = QRect(screen_geometry.width(), screen_geometry.height(), self.width(), self.height())
        end_geometry = QRect(screen_geometry.width() - self.width() - 10, screen_geometry.height() - self.height() - 40, self.width(), self.height())
        
        self.setGeometry(start_geometry)
        self.animation.setStartValue(start_geometry)
        self.animation.setEndValue(end_geometry)
        self.animation.start()

    def animate_out(self):
        start_geometry = self.geometry()
        end_geometry = QRect(start_geometry.x() + self.width(), start_geometry.y(), self.width(), self.height())

        self.animation.setStartValue(start_geometry)
        self.animation.setEndValue(end_geometry)
        self.animation.finished.connect(self.close)
        self.animation.start()
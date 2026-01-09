"""
Hover preview behavior for tree widgets
"""
from PyQt6.QtWidgets import QWidget, QLabel, QTreeWidget, QTreeWidgetItem, QApplication
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QCursor

from ..services.image_service import ImageService
from ..models.game_item import ItemCategory, GameItem, PlayerInventoryItem
import logging

logger = logging.getLogger(__name__)

class HoverPreviewBehavior(QObject):
    """
    Adds hover image preview functionality to a QTreeWidget.
    Shows an image tooltip after hovering over an item for a specified duration.
    """
    
    def __init__(self, tree_widget: QTreeWidget, image_service: ImageService, 
                 category_resolver=None):
        super().__init__(tree_widget)
        self.tree = tree_widget
        self.image_service = image_service
        self.category_resolver = category_resolver
        
        # Timer for delay
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(700) # 0.7s delay (feels better than 1s)
        self.timer.timeout.connect(self.show_preview)
        
        # State
        self.current_item = None
        self.popup = None
        
        # Install event filter on viewport to catch mouse moves
        self.tree.viewport().installEventFilter(self)
        # Enable mouse tracking to get hover events without clicking
        self.tree.setMouseTracking(True)
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.MouseMove:
            self.on_mouse_move(event.pos())
        elif event.type() == QEvent.Type.Leave:
            self.hide_preview()
        elif event.type() == QEvent.Type.MouseButtonPress:
            self.hide_preview()
            
        return super().eventFilter(source, event)
        
    def on_mouse_move(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        
        if item == self.current_item:
            return
            
        # New item or moved off item
        self.hide_preview()
        self.timer.stop()
        self.current_item = item
        
        if item:
            self.timer.start()
            
    def hide_preview(self):
        if self.popup:
            self.popup.close()
            self.popup = None
            
    def show_preview(self):
        if not self.current_item:
            return

        # Double-check that mouse is still over the item/widget
        # This handles cases where mouse moved to menu/outside quickly
        # Must use viewport coordinates because itemAt expects them
        current_pos = self.tree.viewport().mapFromGlobal(QCursor.pos())
        
        # Check if mouse is actually inside the viewport geometry
        if not self.tree.viewport().rect().contains(current_pos):
             return

        item_under_mouse = self.tree.itemAt(current_pos)
        
        # If we are not effectively hovering the same item (or mouse is outside), abort
        if item_under_mouse != self.current_item:
            return
        
        # Get ID and Category
        item_id, category = self._resolve_item_info(self.current_item)
        item_name = self.current_item.text(1) # Column 1 is Name
        
        if not item_id:
            logger.warning(f"Hover: Could not resolve ID for item: {item_name}")
            return
            
        # Default category if unknown
        if not category:
             category = ItemCategory.FURNITURE # Fallback
             
        logger.info(f"Hover: Requesting preview for '{item_name}' (ID: {item_id}, Category: {category})")
             
        # Load image
        # Use a reasonable preview size
        pixmap = self.image_service.get_item_image(
            item_id, category, size=(150, 150), for_tkinter=False
        )
        
        if not pixmap:
            logger.warning(f"Hover: ImageService returned None for {item_id}")
            return
            
        # Check if it might be a placeholder (crude check: if no log from ImageService confirms load)
        # But we already added logging in ImageService.
            
        # Create popup
        self.popup = QLabel(None, Qt.WindowType.ToolTip)
        self.popup.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Convert PIL to QPixmap
        from PyQt6.QtGui import QImage
        if pixmap.mode == "RGB":
            r, g, b = pixmap.split()
            pixmap = Image.merge("RGB", (b, g, r))
            im2 = pixmap.convert("RGBA")
            data = im2.tobytes("raw", "BGRA")
            qim = QImage(data, im2.size[0], im2.size[1], QImage.Format.Format_ARGB32)
            qt_pixmap = QPixmap.fromImage(qim)
        elif pixmap.mode == "RGBA":
            data = pixmap.tobytes("raw", "RGBA")
            qim = QImage(data, pixmap.size[0], pixmap.size[1], QImage.Format.Format_RGBA8888)
            qt_pixmap = QPixmap.fromImage(qim)
        else:
            qt_pixmap = QPixmap()

        self.popup.setPixmap(qt_pixmap)
        self.popup.setStyleSheet("border: 2px solid white; background-color: #333;")
        self.popup.resize(qt_pixmap.size())
        
        # Position near cursor
        cursor_pos = QCursor.pos()
        self.popup.move(cursor_pos.x() + 20, cursor_pos.y() + 20)
        self.popup.show()
        
    def _resolve_item_info(self, item: QTreeWidgetItem):
        # Try to extract data from UserRole
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        item_id = None
        category = None
        
        if isinstance(data, GameItem):
            item_id = data.id
            category = data.category
        elif isinstance(data, PlayerInventoryItem):
            item_id = data.item_id
            # Try to resolve category from Resolver or Text
        elif hasattr(data, 'pet_item_id'): # PetData
            item_id = data.pet_item_id
            category = ItemCategory.PETS
        
        # If ID is not found in data, try column 0 text, then column 1
        if not item_id:
            try:
                item_id = int(item.text(0))
            except (ValueError, TypeError):
                try:
                    item_id = int(item.text(1))
                except (ValueError, TypeError):
                    pass
        
        # If category not found, try Resolver
        if not category and self.category_resolver and item_id:
            category = self.category_resolver(item_id, item)
            
        return item_id, category
    
    # Need PIL Image for conversion in show_preview
    # (Importing inside method or at top)
    
from PIL import Image

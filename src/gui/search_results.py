"""
Search results tab that aggregates items across categories.
It creates a sub-tab per category using the existing ItemEditorFrame with a
temporary ItemCollection that contains only the matched items.
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget

from ..models.game_item import ItemCategory, GameItem, ItemCollection
from .item_editor import ItemEditorFrame
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService


class SearchResultsFrame(QWidget):
    def __init__(
        self,
        parent: QWidget,
        results: Dict[ItemCategory, List[GameItem]],
        image_service: ImageService,
        save_service: SaveFileService,
    ) -> None:
        super().__init__(parent)
        
        self.image_service = image_service
        self.save_service = save_service
        self.category_frames: Dict[ItemCategory, ItemEditorFrame] = {}
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        # Header with quick stats
        header_layout = QHBoxLayout()
        total = sum(len(v) for v in results.values())
        header_layout.addWidget(QLabel(f"Results: {total} items across {len(results)} categories"))
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self._build_tabs(results)
    
    def _build_tabs(self, results: Dict[ItemCategory, List[GameItem]]) -> None:
        # Clear previous tabs
        self.tab_widget.clear()
        self.category_frames.clear()
        
        # Create per-category ItemEditorFrame using a temporary ItemCollection
        for category, items in sorted(results.items(), key=lambda x: x[0].value):
            collection = ItemCollection(category=category)
            for item in items:
                collection.add_item(item)
            sub = ItemEditorFrame(self.tab_widget, category, collection, self.image_service, self.save_service)
            if self.save_service.current_save_data:
                sub.load_save_data(self.save_service.current_save_data)
            self.category_frames[category] = sub
            self.tab_widget.addTab(sub, f"{category.value.replace('_',' ').title()} ({len(collection)})")
    
    def refresh_with(self, results: Dict[ItemCategory, List[GameItem]]) -> None:
        self._build_tabs(results)
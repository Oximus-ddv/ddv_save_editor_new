"""
Search results tab that aggregates items across categories.
It creates a sub-tab per category using the existing ItemEditorFrame with a
temporary ItemCollection that contains only the matched items.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

from ..models.game_item import ItemCategory, GameItem, ItemCollection
from .item_editor import ItemEditorFrame
from ..services.image_service import ImageService
from ..services.save_service import SaveFileService


class SearchResultsFrame(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        results: Dict[ItemCategory, List[GameItem]],
        image_service: ImageService,
        save_service: SaveFileService,
    ) -> None:
        super().__init__(parent)

        self.image_service = image_service
        self.save_service = save_service
        self.category_frames: Dict[ItemCategory, ItemEditorFrame] = {}

        # Header with quick stats
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=6, pady=(6, 0))
        total = sum(len(v) for v in results.values())
        ttk.Label(header, text=f"Results: {total} items across {len(results)} categories").pack(side=tk.LEFT)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._build_tabs(results)

    def _build_tabs(self, results: Dict[ItemCategory, List[GameItem]]) -> None:
        # Clear previous tabs
        for cat, frame in list(self.category_frames.items()):
            try:
                self.nb.forget(frame)
            except Exception:
                pass
        self.category_frames.clear()

        # Create per-category ItemEditorFrame using a temporary ItemCollection
        for category, items in sorted(results.items(), key=lambda x: x[0].value):
            collection = ItemCollection(category=category)
            for item in items:
                collection.add_item(item)
            sub = ItemEditorFrame(self.nb, category, collection, self.image_service, self.save_service)
            if self.save_service.current_save_data:
                sub.load_save_data(self.save_service.current_save_data)
            self.category_frames[category] = sub
            self.nb.add(sub, text=f"{category.value.replace('_',' ').title()} ({len(collection)})")

    def refresh_with(self, results: Dict[ItemCategory, List[GameItem]]) -> None:
        self._build_tabs(results)



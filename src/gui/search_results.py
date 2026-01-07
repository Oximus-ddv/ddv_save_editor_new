"""
Search results tab that aggregates items across categories (PyQt6).
It creates a sub-tab per category using the existing ItemEditor with a
temporary ItemCollection that contains only the matched items.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel

class SearchResults(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.header_label = QLabel()
        self.layout.insertWidget(0, self.header_label)

    def set_results(self, results):
        self.tabs.clear()
        total = sum(len(v) for v in results.values()) if results else 0
        self.header_label.setText(f"Results: {total} items across {len(results)} categories")

        from .item_editor import ItemEditor # Late import to avoid circular dependency
        for category, items in sorted(results.items(), key=lambda x: x[0].value):
            # This part needs to be adapted to how ItemEditor and ItemCollection work with PyQt6
            # For now, we just create a placeholder tab
            placeholder_widget = QLabel(f"Category: {category.value}\nItems: {len(items)}")
            self.tabs.addTab(placeholder_widget, f"{category.value.replace('_',' ').title()} ({len(items)})")
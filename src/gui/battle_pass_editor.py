"""
Battle Pass editor for editing game battle pass states
"""

from typing import Dict, Any, Optional
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QFrame,
)

logger = logging.getLogger(__name__)


class BattlePassEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pass_widgets = (
            {}
        )  # Store widget references: name -> {'currency': widget, 'premium': widget, 'bundle': widget}
        self.initUI()

    def initUI(self):
        # Use a ScrollArea to handle multiple past events
        from PyQt6.QtWidgets import QScrollArea

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)  # No border

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()  # Push items to top

        scroll.setWidget(self.scroll_content)
        main_layout.addWidget(scroll)

    def setData(self, data: Optional[Dict[str, Any]]) -> None:
        if not data:
            logger.info("No data provided to BattlePassEditor.setData")
            return

        # Clear existing widgets
        # Remove all items from layout except the generic stretch
        while self.scroll_layout.count() > 1:  # Keep the stretch at the end
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.pass_widgets.clear()

        player_data = data.get("Player", {})
        battle_pass_states = player_data.get("BattlePassStates", {})
        progress = battle_pass_states.get("Progress", {})

        if not progress:
            self.scroll_layout.insertWidget(0, QLabel("No Battle Pass data found."))
            return

        # Sort keys to show newest first? Or alphabetical.
        # Usually keys like 'EventName2025' don't sort chronologically perfectly, but better than random.
        sorted_keys = sorted(progress.keys(), reverse=True)

        for event_name in sorted_keys:
            event_data = progress[event_name]
            self.create_event_widgets(event_name, event_data)

    def create_event_widgets(self, event_name: str, event_data: Dict[str, Any]):
        group = QGroupBox(event_name)
        layout = QVBoxLayout(group)

        # Currency
        currency_layout = QHBoxLayout()
        currency_layout.addWidget(QLabel("Currency Amount:"))
        currency_spin = QSpinBox()
        currency_spin.setRange(0, 999999)
        # currency_spin.setMinimumWidth(100)
        currency_val = event_data.get("CurrencyAmount", 0)
        currency_spin.setValue(int(currency_val))
        currency_layout.addWidget(currency_spin)
        currency_layout.addStretch()
        layout.addLayout(currency_layout)

        # Premium
        premium_cb = QCheckBox("Premium Active")
        premium_cb.setChecked(bool(event_data.get("IsPremiumActive", False)))
        layout.addWidget(premium_cb)

        # Bundle
        bundle_cb = QCheckBox("Bundle Bought")
        bundle_cb.setChecked(bool(event_data.get("IsBundleBought", False)))
        layout.addWidget(bundle_cb)

        # Store refs
        self.pass_widgets[event_name] = {
            "currency": currency_spin,
            "premium": premium_cb,
            "bundle": bundle_cb,
        }

        # Add to scroll layout (before the stretch)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, group)

    def getData(self) -> Dict[str, Any]:
        # We need to return the FULL structure update,
        # normally we'd merge, but here we reconstruct the 'Progress' dict

        progress_update = {}
        for event_name, widgets in self.pass_widgets.items():
            progress_update[event_name] = {
                "CurrencyAmount": widgets["currency"].value(),
                "IsPremiumActive": widgets["premium"].isChecked(),
                "IsBundleBought": widgets["bundle"].isChecked(),
            }

        return {"Player": {"BattlePassStates": {"Progress": progress_update}}}

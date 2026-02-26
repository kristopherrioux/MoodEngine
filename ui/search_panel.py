from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)


class SearchPanel(QWidget):
    """Provider search controls; emits simple callback hooks through buttons."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search images...")
        self.provider = QComboBox()
        self.provider.addItems(["Unsplash", "Wikimedia Commons"])
        self.count = QSpinBox()
        self.count.setRange(4, 100)
        self.count.setValue(20)
        self.search_btn = QPushButton("Search")
        self.send_to_sort_btn = QPushButton("Send Results to Sort Mode")

        layout.addWidget(QLabel("Search"))
        layout.addWidget(self.query_input, 2)
        layout.addWidget(self.provider)
        layout.addWidget(QLabel("Count"))
        layout.addWidget(self.count)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.send_to_sort_btn)

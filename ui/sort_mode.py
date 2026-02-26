from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QVBoxLayout, QWidget

from models.board_model import ImageItem


@dataclass
class SortCommit:
    deleted_ids: list[str]
    batch_start: int
    marks: list[bool]


class SortTile(QWidget):
    def __init__(self, idx: int) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.label = QLabel(f"{idx}")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumHeight(180)
        layout.addWidget(self.label)
        self.marked_delete = False
        self.idx = idx
        self.set_delete(False)

    def set_content(self, text: str) -> None:
        self.label.setText(text)

    def set_delete(self, value: bool) -> None:
        self.marked_delete = value
        if value:
            self.setStyleSheet("border: 4px solid #b00020; background:#252525; color:white;")
            self.label.setText(self.label.text() + "\nDELETE")
        else:
            self.setStyleSheet("border: 2px solid #444; background:#2d2d2d; color:white;")


class SortModeDialog(QDialog):
    """Keyboard-first culling dialog in 2x2 batches."""

    def __init__(self, items: list[ImageItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sort Mode")
        self.items = items
        self.batch_start = 0
        self.delete_marks = [False, False, False, False]
        self.history: list[SortCommit] = []
        self.deleted_total: list[str] = []

        outer = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.tiles = [SortTile(i + 1) for i in range(4)]
        for i, tile in enumerate(self.tiles):
            self.grid.addWidget(tile, i // 2, i % 2)
        outer.addLayout(self.grid)

        self._register_shortcuts()
        self.refresh()

    def _register_shortcuts(self) -> None:
        for idx in range(4):
            QShortcut(QKeySequence(str(idx + 1)), self, activated=lambda i=idx: self.toggle(i))
        QShortcut(QKeySequence("A"), self, activated=self.toggle_all)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.commit)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.reject)

    def current_batch(self) -> list[ImageItem]:
        return self.items[self.batch_start : self.batch_start + 4]

    def refresh(self) -> None:
        batch = self.current_batch()
        for i, tile in enumerate(self.tiles):
            if i < len(batch):
                item = batch[i]
                tile.setVisible(True)
                tile.set_content(f"{i+1}\n{item.source}\n{item.original_url[:48]}")
                tile.set_delete(self.delete_marks[i])
            else:
                tile.setVisible(False)

    def toggle(self, idx: int) -> None:
        if idx >= len(self.current_batch()):
            return
        self.delete_marks[idx] = not self.delete_marks[idx]
        self.refresh()

    def toggle_all(self) -> None:
        batch_len = len(self.current_batch())
        if batch_len == 0:
            return
        active = self.delete_marks[:batch_len]
        set_to = not all(active)
        for i in range(batch_len):
            self.delete_marks[i] = set_to
        self.refresh()

    def commit(self) -> None:
        batch = self.current_batch()
        deleted_ids = [batch[i].id for i, marked in enumerate(self.delete_marks[: len(batch)]) if marked]
        self.history.append(SortCommit(deleted_ids=deleted_ids, batch_start=self.batch_start, marks=self.delete_marks.copy()))
        self.deleted_total.extend(deleted_ids)
        self.batch_start += 4
        self.delete_marks = [False, False, False, False]
        if self.batch_start >= len(self.items):
            self.accept()
            return
        self.refresh()

    def undo(self) -> None:
        if not self.history:
            return
        last = self.history.pop()
        for image_id in last.deleted_ids:
            if image_id in self.deleted_total:
                self.deleted_total.remove(image_id)
        self.batch_start = last.batch_start
        self.delete_marks = last.marks
        self.refresh()

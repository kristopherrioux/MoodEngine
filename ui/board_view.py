from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
        QToolBar,
    QWidget,
)

from models.board_model import BoardModel, ImageGroup
from sources.commons import CommonsProvider
from sources.unsplash import UnsplashProvider
from ui.search_panel import SearchPanel
from ui.sort_mode import SortModeDialog
from utils.downloader import DownloadManager
from utils.image_cache import ImageCache


class BoardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MoodEngine MVP")
        self.resize(1200, 760)

        self.model = BoardModel()
        self.cache = ImageCache()
        self.downloader = DownloadManager(self.cache)
        self.unsplash = UnsplashProvider()
        self.commons = CommonsProvider()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.search_results: list[dict] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QGridLayout(root)

        self.search_panel = SearchPanel()
        self.search_panel.search_btn.clicked.connect(self.run_search)
        self.search_panel.send_to_sort_btn.clicked.connect(self.send_results_to_sort_mode)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(180, 180))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setSpacing(10)

        layout.addWidget(self.search_panel, 0, 0)
        layout.addWidget(self.list_widget, 1, 0)

        self._build_toolbar()
        self._bind_shortcuts()
        self.setAcceptDrops(True)
        self.apply_dark_theme()

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main")
        self.addToolBar(bar)

        save = QAction("Save", self)
        save.triggered.connect(self.save_board)
        load = QAction("Load", self)
        load.triggered.connect(self.load_board)
        sort_mode = QAction("Sort Mode", self)
        sort_mode.triggered.connect(self.open_sort_mode)
        download_sel = QAction("Download Selected", self)
        download_sel.triggered.connect(lambda: self.download_images(selected_only=True))
        download_all = QAction("Download All", self)
        download_all.triggered.connect(lambda: self.download_images(selected_only=False))

        for action in [save, load, sort_mode, download_sel, download_all]:
            bar.addAction(action)

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("G"), self, activated=self.group_selected)
        QShortcut(QKeySequence("U"), self, activated=self.ungroup_selected)
        QShortcut(QKeySequence("R"), self, activated=self.rename_selected_group)
        QShortcut(QKeySequence(Qt.Key_Tab), self, activated=self.toggle_all_groups)

    def apply_dark_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background:#1e1e1e; color:#f5f5f5; }
            QListWidget { background:#1a1a1a; border:1px solid #333; }
            QListWidget::item:selected { background:#3f3f3f; }
            QPushButton { background:#2d2d2d; border:1px solid #444; padding:4px 8px; }
            QLineEdit, QComboBox, QSpinBox { background:#2a2a2a; border:1px solid #444; }
            """
        )

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.add_local_image(url.toLocalFile())
        self.refresh_board()

    def keyPressEvent(self, event):  # noqa: N802
        if event.matches(QKeySequence.Paste):
            text = QGuiApplication.clipboard().text().strip()
            if text.startswith("http"):
                self.add_remote_image(text, source="clipboard")
        super().keyPressEvent(event)

    def add_local_image(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        self.model.add_image(source="local", original_url=p.as_uri(), thumb_path=str(p), full_path=str(p))

    def add_remote_image(self, url: str, source: str) -> None:
        def _work():
            thumb = self.cache.download_if_missing(url)
            return thumb

        future = self.executor.submit(_work)

        def _done(f):
            thumb = f.result()
            self.model.add_image(source=source, original_url=url, thumb_path=thumb)
            self.refresh_board()

        future.add_done_callback(_done)

    def refresh_board(self) -> None:
        self.list_widget.clear()
        for entry in self.model.visible_entries():
            if entry["type"] == "image":
                item = entry["item"]
                lw_item = QListWidgetItem(Path(urlparse(item.original_url).path).name or item.source)
                lw_item.setData(Qt.UserRole, item.id)
                self.list_widget.addItem(lw_item)
            elif entry["type"] == "group_header":
                group: ImageGroup = entry["group"]
                hdr = QListWidgetItem(f"▼ {group.label} ({len(group.image_ids)})")
                hdr.setData(Qt.UserRole, f"group:{group.id}")
                self.list_widget.addItem(hdr)
            elif entry["type"] == "group_collapsed":
                group = entry["group"]
                label = f"▸ {group.label} ({len(group.image_ids)}) [2x2 preview]"
                collapsed = QListWidgetItem(label)
                collapsed.setData(Qt.UserRole, f"group:{group.id}")
                self.list_widget.addItem(collapsed)

    def selected_image_ids(self) -> list[str]:
        ids = []
        for it in self.list_widget.selectedItems():
            data = it.data(Qt.UserRole)
            if isinstance(data, str) and not data.startswith("group:"):
                ids.append(data)
        return ids

    def selected_group_id(self) -> str | None:
        for it in self.list_widget.selectedItems():
            data = it.data(Qt.UserRole)
            if isinstance(data, str) and data.startswith("group:"):
                return data.split(":", 1)[1]
        return None

    def group_selected(self) -> None:
        ids = self.selected_image_ids()
        if len(ids) < 2:
            return
        label, ok = QInputDialog.getText(self, "Group", "Group label")
        if ok:
            self.model.create_group(ids, label)
            self.refresh_board()

    def ungroup_selected(self) -> None:
        group_id = self.selected_group_id()
        if group_id:
            self.model.ungroup(group_id)
            self.refresh_board()

    def rename_selected_group(self) -> None:
        group_id = self.selected_group_id()
        if not group_id:
            return
        label, ok = QInputDialog.getText(self, "Rename Group", "New label")
        if ok:
            self.model.rename_group(group_id, label)
            self.refresh_board()

    def toggle_all_groups(self) -> None:
        self.model.toggle_all_groups()
        self.refresh_board()

    def save_board(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Board", filter="JSON (*.json)")
        if path:
            self.model.save_json(path)

    def load_board(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Board", filter="JSON (*.json)")
        if path:
            self.model.load_json(path)
            self.refresh_board()

    def open_sort_mode(self) -> None:
        items = self.model.kept_images()
        if not items:
            return
        dlg = SortModeDialog(items, self)
        if dlg.exec():
            self.model.remove_images(dlg.deleted_total)
            self.refresh_board()

    def run_search(self) -> None:
        query = self.search_panel.query_input.text().strip()
        count = self.search_panel.count.value()
        if not query:
            return

        provider = self.search_panel.provider.currentText()
        try:
            if provider == "Unsplash":
                rows = self.unsplash.search(query, per_page=count)
                self.search_results = [
                    {
                        "source": "unsplash",
                        "original_url": r.photo_url,
                        "thumb_url": r.thumb_url,
                        "author": r.author,
                        "metadata": {"download_location": r.download_location, "photo_url": r.photo_url},
                    }
                    for r in rows
                ]
            else:
                rows = self.commons.search(query, limit=count)
                self.search_results = [
                    {
                        "source": "commons",
                        "original_url": r.original_url,
                        "thumb_url": r.thumb_url,
                        "author": r.author,
                        "license": r.license,
                        "metadata": {},
                    }
                    for r in rows
                ]
            self.statusBar().showMessage(f"Found {len(self.search_results)} results", 3000)
        except Exception as exc:  # network/runtime guard for MVP UX
            QMessageBox.warning(self, "Search failed", str(exc))

    def send_results_to_sort_mode(self) -> None:
        for row in self.search_results:
            try:
                thumb = self.cache.download_if_missing(row["thumb_url"] or row["original_url"])
            except Exception:
                continue
            self.model.add_image(
                source=row["source"],
                original_url=row["original_url"],
                thumb_path=thumb,
                author=row.get("author"),
                license_text=row.get("license"),
                metadata=row.get("metadata", {}),
            )

        self.refresh_board()
        self.open_sort_mode()

    def download_images(self, selected_only: bool) -> None:
        if selected_only:
            ids = self.selected_image_ids()
            items = [self.model.images[i] for i in ids if i in self.model.images]
        else:
            items = self.model.kept_images()

        if not items:
            return
        result = self.downloader.download_items(items)
        # Unsplash guideline: register download after keep/full download.
        for item in items:
            if item.source == "unsplash":
                dl = item.metadata.get("download_location")
                if dl:
                    self.unsplash.trigger_download(dl)
        self.statusBar().showMessage(f"Downloaded {len(result.downloaded)} files", 4000)

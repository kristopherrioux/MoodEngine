from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from models.board_model import ImageItem
from utils.image_cache import ImageCache


@dataclass(slots=True)
class DownloadResult:
    downloaded: list[str]
    manifest_path: str


class DownloadManager:
    """Handles full-resolution downloads and manifest creation."""

    def __init__(self, cache: ImageCache | None = None) -> None:
        self.cache = cache or ImageCache()

    def download_items(self, items: list[ImageItem], output_dir: str = "data/exports") -> DownloadResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        manifest: list[dict] = []
        downloaded_paths: list[str] = []

        for item in items:
            full_url = item.metadata.get("photo_url") or item.original_url
            local_path = self.cache.download_if_missing(full_url, full=True)
            exported = output / Path(local_path).name
            if not exported.exists():
                shutil.copy2(local_path, exported)
            manifest.append(
                {
                    "source": item.source,
                    "author": item.author,
                    "license": item.license,
                    "original_url": item.original_url,
                    "local_path": str(exported),
                }
            )
            downloaded_paths.append(str(exported))

        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return DownloadResult(downloaded=downloaded_paths, manifest_path=str(manifest_path))

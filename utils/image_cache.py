from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import hashlib
import requests


class ImageCache:
    """Simple disk cache for thumbnails and downloaded images."""

    def __init__(self, base_dir: str = "data/cache") -> None:
        self.base = Path(base_dir)
        self.thumb_dir = self.base / "thumbs"
        self.full_dir = self.base / "full"
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.full_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ext_for_url(url: str) -> str:
        path = urlparse(url).path.lower()
        if "." in path:
            ext = path.split(".")[-1]
            if len(ext) <= 5:
                return f".{ext}"
        return ".jpg"

    @staticmethod
    def _name(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def thumb_path_for(self, url: str) -> Path:
        return self.thumb_dir / f"{self._name(url)}{self._ext_for_url(url)}"

    def full_path_for(self, url: str) -> Path:
        return self.full_dir / f"{self._name(url)}{self._ext_for_url(url)}"

    def download_if_missing(self, url: str, *, full: bool = False, timeout: int = 20) -> str:
        path = self.full_path_for(url) if full else self.thumb_path_for(url)
        if path.exists():
            return str(path)
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return str(path)

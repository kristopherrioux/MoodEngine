from __future__ import annotations

from dataclasses import dataclass
import os
import time
import requests


@dataclass(slots=True)
class UnsplashImage:
    id: str
    author: str
    photo_url: str
    thumb_url: str
    download_location: str


class UnsplashProvider:
    BASE = "https://api.unsplash.com"

    def __init__(self, access_key: str | None = None) -> None:
        self.access_key = access_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.session = requests.Session()
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        delta = time.time() - self._last_call
        if delta < 0.25:
            time.sleep(0.25 - delta)
        self._last_call = time.time()

    def search(self, query: str, per_page: int = 20) -> list[UnsplashImage]:
        if not self.access_key:
            return []
        self._rate_limit()
        resp = self.session.get(
            f"{self.BASE}/search/photos",
            params={"query": query, "per_page": per_page},
            headers={"Authorization": f"Client-ID {self.access_key}"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        results = []
        for row in payload.get("results", []):
            user = row.get("user", {})
            urls = row.get("urls", {})
            links = row.get("links", {})
            results.append(
                UnsplashImage(
                    id=row.get("id", ""),
                    author=user.get("name", "Unknown"),
                    photo_url=urls.get("full") or urls.get("regular", ""),
                    thumb_url=urls.get("thumb") or urls.get("small", ""),
                    download_location=links.get("download_location", ""),
                )
            )
        return results

    def trigger_download(self, download_location: str) -> None:
        if not self.access_key or not download_location:
            return
        self._rate_limit()
        self.session.get(
            download_location,
            headers={"Authorization": f"Client-ID {self.access_key}"},
            timeout=20,
        )

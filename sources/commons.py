from __future__ import annotations

from dataclasses import dataclass
import time
import requests


HEADERS = {
    "User-Agent": "MoodEngine/0.1 (your_email@example.com)",
    "Accept": "application/json",
}


@dataclass(slots=True)
class CommonsImage:
    title: str
    thumb_url: str
    original_url: str
    author: str | None
    license: str | None


class CommonsProvider:
    BASE = "https://commons.wikimedia.org/w/api.php"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        delta = time.time() - self._last_call
        if delta < 0.25:
            time.sleep(0.25 - delta)
        self._last_call = time.time()

    def search(self, query: str, limit: int = 20) -> list[CommonsImage]:
        self._rate_limit()
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 400,
        }
        response = self.session.get(self.BASE, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()

        pages = response.json().get("query", {}).get("pages", {})
        rows: list[CommonsImage] = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            rows.append(
                CommonsImage(
                    title=page.get("title", ""),
                    thumb_url=info.get("thumburl", ""),
                    original_url=info.get("url", ""),
                    author=(meta.get("Artist") or {}).get("value"),
                    license=(meta.get("LicenseShortName") or {}).get("value"),
                )
            )
        return rows

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json
import uuid


@dataclass(slots=True)
class ImageItem:
    """Represents one image on the board."""

    id: str
    source: str
    original_url: str
    thumb_path: str
    full_path: str | None = None
    author: str | None = None
    license: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    group_id: str | None = None


@dataclass(slots=True)
class ImageGroup:
    """A collapsible group of image ids."""

    id: str
    label: str
    image_ids: list[str] = field(default_factory=list)
    collapsed: bool = False


class BoardModel:
    """Data-layer model for board state and persistence."""

    def __init__(self) -> None:
        self.images: dict[str, ImageItem] = {}
        self.groups: dict[str, ImageGroup] = {}
        self.order: list[str] = []
        self._fingerprints: set[str] = set()

    @staticmethod
    def _fingerprint(url: str, local_path: str | None = None) -> str:
        payload = url.strip().lower()
        if local_path and Path(local_path).exists():
            with open(local_path, "rb") as handle:
                payload += ":" + hashlib.sha1(handle.read()).hexdigest()
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def add_image(
        self,
        *,
        source: str,
        original_url: str,
        thumb_path: str,
        full_path: str | None = None,
        author: str | None = None,
        license_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ImageItem | None:
        fp = self._fingerprint(original_url, full_path)
        if fp in self._fingerprints:
            return None

        item_id = str(uuid.uuid4())
        item = ImageItem(
            id=item_id,
            source=source,
            original_url=original_url,
            thumb_path=thumb_path,
            full_path=full_path,
            author=author,
            license=license_text,
            metadata=metadata or {},
        )
        self.images[item_id] = item
        self.order.append(item_id)
        self._fingerprints.add(fp)
        return item

    def remove_images(self, image_ids: list[str]) -> list[ImageItem]:
        removed: list[ImageItem] = []
        for image_id in image_ids:
            item = self.images.pop(image_id, None)
            if not item:
                continue
            removed.append(item)
            if image_id in self.order:
                self.order.remove(image_id)
            if item.group_id and item.group_id in self.groups:
                grp = self.groups[item.group_id]
                if image_id in grp.image_ids:
                    grp.image_ids.remove(image_id)
        self._rebuild_fingerprints()
        self._cleanup_empty_groups()
        return removed

    def restore_images(self, images: list[ImageItem], insertion_index: int | None = None) -> None:
        idx = insertion_index if insertion_index is not None else len(self.order)
        for item in images:
            self.images[item.id] = item
            self.order.insert(min(idx, len(self.order)), item.id)
            idx += 1
        self._rebuild_fingerprints()

    def create_group(self, image_ids: list[str], label: str) -> ImageGroup | None:
        ids = [i for i in image_ids if i in self.images]
        if len(ids) < 2:
            return None
        group_id = str(uuid.uuid4())
        group = ImageGroup(id=group_id, label=label.strip() or "Group", image_ids=ids)
        self.groups[group_id] = group
        for image_id in ids:
            self.images[image_id].group_id = group_id
        return group

    def ungroup(self, group_id: str) -> None:
        group = self.groups.pop(group_id, None)
        if not group:
            return
        for image_id in group.image_ids:
            if image_id in self.images:
                self.images[image_id].group_id = None

    def rename_group(self, group_id: str, label: str) -> None:
        if group_id in self.groups and label.strip():
            self.groups[group_id].label = label.strip()

    def toggle_all_groups(self) -> None:
        if not self.groups:
            return
        should_collapse = any(not g.collapsed for g in self.groups.values())
        for group in self.groups.values():
            group.collapsed = should_collapse

    def visible_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        emitted_groups: set[str] = set()
        for image_id in self.order:
            item = self.images.get(image_id)
            if not item:
                continue
            if item.group_id and item.group_id in self.groups:
                group = self.groups[item.group_id]
                if group.id in emitted_groups:
                    continue
                if group.collapsed:
                    entries.append({"type": "group_collapsed", "group": group})
                else:
                    entries.append({"type": "group_header", "group": group})
                    for member_id in group.image_ids:
                        if member_id in self.images:
                            entries.append({"type": "image", "item": self.images[member_id]})
                emitted_groups.add(group.id)
            else:
                entries.append({"type": "image", "item": item})
        return entries

    def to_dict(self) -> dict[str, Any]:
        return {
            "images": [asdict(item) for item in self.images.values()],
            "groups": [asdict(group) for group in self.groups.values()],
            "order": self.order,
        }

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)

    def load_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.images = {img["id"]: ImageItem(**img) for img in payload.get("images", [])}
        self.groups = {grp["id"]: ImageGroup(**grp) for grp in payload.get("groups", [])}
        self.order = [oid for oid in payload.get("order", []) if oid in self.images]
        self._rebuild_fingerprints()
        self._cleanup_empty_groups()

    def kept_images(self) -> list[ImageItem]:
        return [self.images[i] for i in self.order if i in self.images]

    def _cleanup_empty_groups(self) -> None:
        for gid in list(self.groups.keys()):
            if not self.groups[gid].image_ids:
                self.groups.pop(gid)

    def _rebuild_fingerprints(self) -> None:
        self._fingerprints.clear()
        for item in self.images.values():
            self._fingerprints.add(self._fingerprint(item.original_url, item.full_path))

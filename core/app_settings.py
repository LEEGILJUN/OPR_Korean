from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .file_utils import user_data_root


class AppSettings:
    """Small key-value store for local UI preferences and session restore.

    Every operation is best-effort: a missing, unreadable, or corrupted settings
    file falls back to defaults rather than blocking the app from starting.
    """

    DEFAULTS: dict[str, Any] = {
        "guide_seen": False,
        "theme": "light",          # "light" | "dark"
        "font_scale": 100,          # percent
        "last_session": None,       # dict of the last input state
    }

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_data_root() / "app_settings.json"
        self._data: dict[str, Any] = dict(self.DEFAULTS)
        self._loaded = False

    def load(self) -> dict[str, Any]:
        """Read settings from disk once, merging over the defaults."""
        if self._loaded:
            return self._data

        self._loaded = True
        if not self.path.exists():
            return self._data

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._data

        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in self.DEFAULTS:
                    self._data[key] = value
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        self.load()
        if default is None:
            default = self.DEFAULTS.get(key)
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.load()
        self._data[key] = value
        self._write()

    def update(self, values: dict[str, Any]) -> None:
        self.load()
        self._data.update(values)
        self._write()

    def _write(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            # Preferences are a convenience — failing to persist must not break the app.
            pass

"""
Simple settings persistence service for DDV Save Editor
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple
import logging


logger = logging.getLogger(__name__)


class SettingsService:
    """Load and save user settings to a JSON file.

    Defaults are chosen to match existing application expectations so that
    behavior is unchanged if no settings file exists.
    """

    def __init__(self, settings_path: str | Path = "settings.json") -> None:
        self.settings_path = Path(settings_path)

    @staticmethod
    def default_settings() -> Dict[str, Any]:
        return {
            "excel_path": "Disney Dream Light ID List - Mainted by Rubyelf.xlsx",
            "image_zip_path": "img.zip",
            "image_folder_path": "img",
            "max_backups": 10,
            "auto_backup": True,
            "show_images": True,
            "cache_size": 200,
            "thumbnail_size": "64x64",
            "preview_size": "128x128",
            "theme": "light",
            # Default DDV key (hex, space-separated groups supported)
            "hex_key": "62 35 71 68 68 38 73 61 4A 38 55 6C 44 4A 55 7A 54 5A 58 64 32 54 67 36 6D 62 6F 38 57 38 6E 35",
        }

    def load(self) -> Dict[str, Any]:
        """Load settings from disk, merging with defaults for missing keys."""
        try:
            if not self.settings_path.exists():
                return self.default_settings()
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**self.default_settings(), **(data or {})}
            return merged
        except Exception as e:
            logger.warning(f"Failed to load settings, using defaults: {e}")
            return self.default_settings()

    def save(self, settings: Dict[str, Any]) -> bool:
        """Persist settings to disk. Returns True on success."""
        try:
            # Ensure parent exists (works even if settings_path is in CWD)
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8", newline="") as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    @staticmethod
    def parse_size(value: str, fallback: Tuple[int, int]) -> Tuple[int, int]:
        """Parse sizes like '64x64' into integer tuples."""
        try:
            parts = str(value).lower().split("x")
            if len(parts) != 2:
                return fallback
            w, h = int(parts[0]), int(parts[1])
            return (w, h)
        except Exception:
            return fallback



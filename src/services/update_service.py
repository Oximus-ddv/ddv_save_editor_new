"""
Service for checking and applying updates to the Dict data folder.
"""
from __future__ import annotations

import logging
import requests
import zipfile
from pathlib import Path
from typing import Dict, Any

from src.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# --- Configuration ---
# Replace these with your actual URLs
VERSION_URL = "https://raw.githubusercontent.com/paulp/ddv_save_editor_new/main/Dict/version.json"
DICT_ZIP_URL = "https://github.com/paulp/ddv_save_editor_new/raw/main/Dict.zip"
# --- End Configuration ---


class UpdateService:
    """Checks for and applies updates to the application's data files."""

    def __init__(self, settings_service: SettingsService, dict_root: str | Path = "Dict") -> None:
        self.settings_service = settings_service
        self.dict_root = Path(dict_root)

    def check_and_update(self) -> bool:
        """
        Check for a new version of the Dict data and apply it if available.

        Returns:
            True if an update was successfully applied, False otherwise.
        """
        logger.info("Checking for dictionary updates...")
        try:
            online_version = self._get_online_version()
            if not online_version:
                return False

            settings = self.settings_service.load()
            local_version = settings.get("dict_version", "0.0.0")

            if self._is_newer(online_version, local_version):
                logger.info(f"New version available: {online_version} (local: {local_version})")
                if self._download_and_unzip_dict():
                    settings["dict_version"] = online_version
                    self.settings_service.save(settings)
                    logger.info("Dictionary update successful.")
                    return True
            else:
                logger.info("Dictionary is up to date.")

        except Exception as e:
            logger.error(f"Error during update check: {e}")

        return False

    def _get_online_version(self) -> str | None:
        """Fetch the version number from the online version file."""
        try:
            response = requests.get(VERSION_URL, timeout=10)
            response.raise_for_status()
            return response.json().get("version")
        except requests.RequestException as e:
            logger.warning(f"Could not fetch online version: {e}")
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid version file format: {e}")
        return None

    def _is_newer(self, online_version: str, local_version: str) -> bool:
        """Compare two version strings (e.g., "1.2.3")."""
        try:
            online_parts = list(map(int, online_version.split('.')))
            local_parts = list(map(int, local_version.split('.')))
            return online_parts > local_parts
        except (ValueError, AttributeError):
            return False # Fallback on any parsing error

    def _download_and_unzip_dict(self) -> bool:
        """Download and unzip the Dict.zip file."""
        zip_path = self.dict_root.with_suffix(".zip")
        try:
            # Download
            logger.info(f"Downloading {DICT_ZIP_URL}...")
            response = requests.get(DICT_ZIP_URL, stream=True, timeout=30)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Download complete.")

            # Unzip
            logger.info(f"Unzipping to {self.dict_root}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.dict_root.parent) # Extract to parent of Dict
            logger.info("Unzip complete.")

            # Cleanup
            zip_path.unlink()
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download dictionary: {e}")
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid zip file.")
        except Exception as e:
            logger.error(f"An error occurred during unzip: {e}")
        finally:
            if zip_path.exists():
                zip_path.unlink() # Ensure cleanup even on failure

        return False

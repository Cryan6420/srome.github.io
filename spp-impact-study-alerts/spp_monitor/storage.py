"""Persistent storage for tracking seen studies."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .scraper import Study

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_PATH = Path("data/seen_studies.json")


class StudyStorage:
    """JSON-file based storage for tracking which studies have been seen."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._data: dict = {"seen": {}, "last_check": None}
        self._load()

    def _load(self):
        """Load seen studies from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._data = json.load(f)
                logger.info(
                    "Loaded %d seen studies from %s",
                    len(self._data.get("seen", {})),
                    self.storage_path,
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.error("Failed to load storage file: %s", e)
                self._data = {"seen": {}, "last_check": None}
        else:
            logger.info("No existing storage found at %s, starting fresh", self.storage_path)

    def _save(self):
        """Persist seen studies to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self._data, f, indent=2)
        logger.debug("Saved %d seen studies to %s", len(self._data["seen"]), self.storage_path)

    def is_new(self, study: Study) -> bool:
        """Check if a study has not been seen before."""
        return study.unique_id not in self._data["seen"]

    def find_new_studies(self, studies: list[Study]) -> list[Study]:
        """Filter a list of studies to only those not previously seen.

        Args:
            studies: List of studies to check.

        Returns:
            List of studies that are new (not previously seen).
        """
        new_studies = [s for s in studies if self.is_new(s)]
        logger.info("Found %d new studies out of %d total", len(new_studies), len(studies))
        return new_studies

    def mark_seen(self, studies: list[Study]):
        """Mark studies as seen and persist to disk.

        Args:
            studies: List of studies to mark as seen.
        """
        now = datetime.now(timezone.utc).isoformat()
        for study in studies:
            self._data["seen"][study.unique_id] = {
                "first_seen": now,
                "study": study.to_dict(),
            }
        self._data["last_check"] = now
        self._save()
        logger.info("Marked %d studies as seen", len(studies))

    def update_last_check(self):
        """Update the last check timestamp without marking any studies."""
        self._data["last_check"] = datetime.now(timezone.utc).isoformat()
        self._save()

    @property
    def last_check(self) -> Optional[str]:
        """Return the timestamp of the last check."""
        return self._data.get("last_check")

    @property
    def seen_count(self) -> int:
        """Return the number of seen studies."""
        return len(self._data.get("seen", {}))

    def clear(self):
        """Clear all seen studies (useful for testing/reset)."""
        self._data = {"seen": {}, "last_check": None}
        self._save()
        logger.info("Cleared all seen studies")

"""Scraper for SPP OpsPortal Generator Interconnection Studies."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://opsportal.spp.org"
STUDIES_INDEX_URL = f"{BASE_URL}/Studies/Gen"
STUDY_LIST_URL = f"{BASE_URL}/Studies/GenList"

# Headers to mimic a real browser request
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass
class Study:
    """Represents a single study entry from the SPP portal."""

    name: str
    url: str
    year_type_id: int
    year_type_label: str
    details: dict = field(default_factory=dict)

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier for this study."""
        return f"{self.year_type_id}:{self.name}:{self.url}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "year_type_id": self.year_type_id,
            "year_type_label": self.year_type_label,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Study":
        return cls(
            name=data["name"],
            url=data["url"],
            year_type_id=data["year_type_id"],
            year_type_label=data["year_type_label"],
            details=data.get("details", {}),
        )


class SPPScraper:
    """Scrapes SPP OpsPortal for generator interconnection studies."""

    def __init__(
        self,
        year_type_ids: Optional[list[int]] = None,
        request_delay: float = 2.0,
        max_retries: int = 3,
    ):
        """
        Args:
            year_type_ids: Specific yearTypeId values to monitor. If None, discovers all.
            request_delay: Seconds to wait between requests.
            max_retries: Number of retry attempts for failed requests.
        """
        self.year_type_ids = year_type_ids
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retries and exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s. Retrying in %ds...",
                    url,
                    attempt + 1,
                    self.max_retries,
                    e,
                    wait_time,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
        logger.error("All %d attempts failed for %s", self.max_retries, url)
        return None

    def discover_year_types(self) -> dict[int, str]:
        """Discover available yearTypeId values from the main studies page.

        Returns:
            Dict mapping yearTypeId -> label (e.g., {243: "DISIS 2024-001"}).
        """
        logger.info("Discovering study year types from %s", STUDIES_INDEX_URL)
        html = self._fetch_page(STUDIES_INDEX_URL)
        if not html:
            logger.error("Failed to fetch studies index page")
            return {}

        soup = BeautifulSoup(html, "html.parser")
        year_types = {}

        # Look for links to GenList pages with yearTypeId parameters
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "GenList" in href and "yearTypeId=" in href:
                try:
                    year_type_id = int(href.split("yearTypeId=")[1].split("&")[0])
                    label = link.get_text(strip=True)
                    if label:
                        year_types[year_type_id] = label
                except (ValueError, IndexError):
                    continue

        logger.info("Discovered %d study year types", len(year_types))
        return year_types

    def fetch_studies_for_year_type(
        self, year_type_id: int, year_type_label: str = ""
    ) -> list[Study]:
        """Fetch all studies for a specific yearTypeId.

        Args:
            year_type_id: The yearTypeId parameter value.
            year_type_label: Human-readable label for this year type.

        Returns:
            List of Study objects found on the page.
        """
        url = f"{STUDY_LIST_URL}?yearTypeId={year_type_id}"
        logger.info("Fetching studies from %s", url)
        html = self._fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        studies = []

        # Strategy 1: Look for table rows containing study links
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            headers = []
            for row in rows:
                cells = row.find_all(["th", "td"])
                if row.find("th"):
                    headers = [th.get_text(strip=True) for th in cells]
                    continue

                if not cells:
                    continue

                # Extract study info from table cells
                row_data = {}
                for i, cell in enumerate(cells):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    link = cell.find("a", href=True)
                    if link:
                        row_data[key] = cell.get_text(strip=True)
                        row_data[f"{key}_url"] = urljoin(BASE_URL, link["href"])
                    else:
                        row_data[key] = cell.get_text(strip=True)

                # Find the primary link/name for this study
                first_link = cells[0].find("a", href=True) if cells else None
                if first_link:
                    study_name = first_link.get_text(strip=True)
                    study_url = urljoin(BASE_URL, first_link["href"])
                elif cells:
                    study_name = cells[0].get_text(strip=True)
                    study_url = url
                else:
                    continue

                if study_name:
                    studies.append(
                        Study(
                            name=study_name,
                            url=study_url,
                            year_type_id=year_type_id,
                            year_type_label=year_type_label,
                            details=row_data,
                        )
                    )

        # Strategy 2: If no table found, look for study links in lists or divs
        if not studies:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                # Look for links to study documents (PDFs, detail pages)
                if text and (
                    "study" in text.lower()
                    or "gen-" in text.lower()
                    or "disis" in text.lower()
                    or href.endswith(".pdf")
                    or "/documents/" in href
                ):
                    studies.append(
                        Study(
                            name=text,
                            url=urljoin(BASE_URL, href),
                            year_type_id=year_type_id,
                            year_type_label=year_type_label,
                        )
                    )

        logger.info(
            "Found %d studies for yearTypeId=%d (%s)",
            len(studies),
            year_type_id,
            year_type_label,
        )
        return studies

    def fetch_all_studies(self) -> list[Study]:
        """Fetch studies from all monitored year types.

        Returns:
            Combined list of all studies found.
        """
        all_studies = []

        if self.year_type_ids:
            # Use specified year type IDs
            year_types = {ytid: f"YearType {ytid}" for ytid in self.year_type_ids}
            # Try to get labels from the index page
            discovered = self.discover_year_types()
            for ytid in self.year_type_ids:
                if ytid in discovered:
                    year_types[ytid] = discovered[ytid]
        else:
            # Discover all available year types
            year_types = self.discover_year_types()

        if not year_types:
            logger.warning("No year types found to monitor")
            return []

        for year_type_id, label in year_types.items():
            studies = self.fetch_studies_for_year_type(year_type_id, label)
            all_studies.extend(studies)
            if self.request_delay > 0:
                time.sleep(self.request_delay)

        logger.info("Total studies fetched: %d", len(all_studies))
        return all_studies

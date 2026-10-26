"""Fetch 8-K exhibits from SEC EDGAR, respecting fair access (at most 10 requests a second)."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from filing_extractor.config import sec_user_agent

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{adsh}/{name}"
MIN_INTERVAL_S = 0.15  # about 6.5 requests a second, below the 10 a second limit
PAGE_SIZE = 100


@dataclass(frozen=True)
class ExhibitHit:
    adsh: str
    cik: str
    company: str
    file_name: str
    file_type: str
    file_date: str
    description: str

    @property
    def url(self) -> str:
        return ARCHIVE_URL.format(
            cik=int(self.cik), adsh=self.adsh.replace("-", ""), name=self.file_name
        )


class SecClient:
    """A small HTTP client that spaces requests and sends the configured User-Agent."""

    def __init__(self, user_agent: str | None = None) -> None:
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent or sec_user_agent()
        self._lock = threading.Lock()
        self._last = 0.0

    def get(self, url: str, params: dict[str, str | int] | None = None) -> requests.Response:
        with self._lock:
            wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
        resp = self._session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp

    def search_exhibits(
        self, query: str, start: str, end: str, offset: int = 0
    ) -> list[ExhibitHit]:
        params: dict[str, str | int] = {
            "q": query,
            "forms": "8-K",
            "dateRange": "custom",
            "startdt": start,
            "enddt": end,
            "from": offset,
        }
        data = self.get(SEARCH_URL, params).json()
        if "hits" not in data:  # the search API answers with an error object for bad queries
            return []
        return [h for h in (_to_hit(x) for x in data["hits"]["hits"]) if h is not None]


def _to_hit(raw: dict) -> ExhibitHit | None:
    src = raw["_source"]
    file_type = src.get("file_type") or ""
    if not file_type.upper().startswith("EX-10"):
        return None
    _, _, file_name = raw["_id"].partition(":")
    if not file_name.lower().endswith((".htm", ".html")):
        return None
    name = (src.get("display_names") or ["unknown"])[0]
    company = re.sub(r"\s*\(.*$", "", name).strip()
    return ExhibitHit(
        adsh=src["adsh"],
        cik=src["ciks"][0],
        company=company,
        file_name=file_name,
        file_type=file_type,
        file_date=src.get("file_date", ""),
        description=(src.get("file_description") or "").strip(),
    )


def html_to_text(html: str) -> str:
    """Flatten an exhibit to paragraphs separated by blank lines."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    blocks = []
    for node in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "center"]):
        if node.find(["p", "div", "li", "tr", "table"]):
            continue  # only leaf blocks, so text is not duplicated
        text = " ".join(node.get_text(" ", strip=True).split())
        if text:
            blocks.append(text)
    if not blocks:
        blocks = [" ".join(soup.get_text(" ", strip=True).split())]
    return "\n\n".join(blocks)

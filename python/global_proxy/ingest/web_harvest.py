# ffp: FFP-NIMBUS2-WEB-HARVEST io-edge python
"""Web Search Engine — autonomous search-and-scrape for live proxy pools.

Uses DuckDuckGo Lite and SearXNG instances to discover unlisted proxy
endpoints, then validates and normalises the results.
"""

import asyncio
import logging
import re
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger(__name__)

# DuckDuckGo Lite (no JS required)
DDG_LITE_URL = "https://lite.duckduckgo.com/lite"
SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://searxng.ch",
]

SEARCH_QUERIES = [
    "free socks5 proxy list UK",
    "UK residential proxy list 2026",
    "fresh proxy list host port",
    "socks5 proxy list download txt",
    "UK ISP proxy endpoints",
    "rotate proxy UK residential",
]

# Inline extraction patterns
PROXY_LINE_RE = re.compile(
    r"(\d{1,3}(?:\.\d{1,3}){3})\s*[:\t]\s*(\d{2,5})"
    r"(?:\s*[:\t]\s*(\S+)\s*[:\t]\s*(\S+))?"
)
URL_PROXY_RE = re.compile(
    r"socks5?://([^:\s]+):(\d{2,5})(?:@(\S+):(\S+))?"
)

MAX_PAGES_PER_QUERY = 5
MAX_RESULTS_PER_PAGE = 20


class WebHarvester:
    """Searches the web for live proxy endpoints and normalises them."""

    def __init__(self, max_results: int = 50):
        self.max_results = max_results

    async def _fetch_ddg_lite(
        self, client: httpx.AsyncClient, query: str
    ) -> List[str]:
        """Fetch DuckDuckGo Lite search results as raw HTML strings."""
        try:
            data = {"q": query, "kl": "uk-en"}
            resp = await client.post(DDG_LITE_URL, data=data, timeout=15)
            resp.raise_for_status()
            return [resp.text]
        except Exception as exc:
            logger.debug("DDG Lite failed for '%s': %s", query, exc)
            return []

    async def _fetch_searxng(
        self, client: httpx.AsyncClient, query: str
    ) -> List[str]:
        """Fetch SearXNG JSON results from available instances."""
        results_html: List[str] = []
        for base_url in SEARXNG_INSTANCES:
            url = f"{base_url}/search"
            params = {"q": query, "format": "json", "categories": "general"}
            try:
                resp = await client.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", [])[:MAX_RESULTS_PER_PAGE]:
                    content = item.get("content", "")
                    url_str = item.get("url", "")
                    if content:
                        results_html.append(content)
                    if url_str:
                        results_html.append(f"<a href='{url_str}'>{url_str}</a>")
                break  # stop after first working instance
            except Exception as exc:
                logger.debug("SearXNG %s failed: %s", base_url, exc)
                continue
        return results_html

    async def _fetch_url_content(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[str]:
        """Fetch raw text from a discovered URL for proxy list extraction."""
        try:
            resp = await client.get(url, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type:
                return resp.text[:500_000]  # cap at 500KB
        except Exception:
            pass
        return None

    def _extract_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract proxy definitions from raw text."""
        proxies: List[Dict[str, str]] = []
        for match in PROXY_LINE_RE.finditer(text):
            host, port = match.group(1), match.group(2)
            user = match.group(3) or ""
            pwd = match.group(4) or ""
            proxies.append({
                "host": host,
                "port": port,
                "protocol": "http",
                "username": user,
                "password": pwd,
            })
        for match in URL_PROXY_RE.finditer(text):
            host, port = match.group(1), match.group(2)
            user = match.group(3) or ""
            pwd = match.group(4) or ""
            proxies.append({
                "host": host,
                "port": port,
                "protocol": "socks5",
                "username": user,
                "password": pwd,
            })
        return proxies

    def _deduplicate(self, proxies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate host:port entries."""
        seen: set = set()
        unique: List[Dict[str, str]] = []
        for p in proxies:
            key = f"{p['host']}:{p['port']}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    async def harvest(self) -> AsyncIterator[Dict[str, str]]:
        """Yield proxy dicts discovered from web search results."""
        collected: List[Dict[str, str]] = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for query in SEARCH_QUERIES:
                ddg_pages = await self._fetch_ddg_lite(client, query)
                searx_pages = await self._fetch_searxng(client, query)
                all_pages = ddg_pages + searx_pages

                for page_text in all_pages:
                    proxies = self._extract_from_text(page_text)
                    collected.extend(proxies)

                # Follow links that look like proxy lists
                url_matches = re.findall(
                    r'href="(https?://[^"]*(?:proxy|socks|list)[^"]*)"',
                    " ".join(all_pages),
                    re.IGNORECASE,
                )
                for link_url in url_matches[:MAX_PAGES_PER_QUERY]:
                    content = await self._fetch_url_content(client, link_url)
                    if content:
                        proxies = self._extract_from_text(content)
                        for p in proxies:
                            p["source"] = f"web:{link_url}"
                        collected.extend(proxies)

                if len(collected) >= self.max_results:
                    break

        for p in self._deduplicate(collected):
            if p.get("host") and p.get("port"):
                yield p

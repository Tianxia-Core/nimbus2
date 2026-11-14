# ffp: FFP-NIMBUS2-ACADEMIC-HARVEST io-edge python
"""Arxiv & CNKI Research Scraper — harvests anti-detection techniques.

Parses papers for JA3/JA4 TLS fingerprint spoofing methods, TCP/IP stack
fingerprinting data, and header normalisation strategies that can be
applied to proxy tunnel profiles.
"""

import asyncio
import json
import logging
import re
from typing import AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"

# Search queries targeting anti-detection proxy techniques
QUERY_TERMS = [
    "JA3 fingerprint spoofing",
    "TLS fingerprint impersonation residential proxy",
    "TCP IP stack fingerprint evasion",
    "HTTP header normalisation anti-detection",
    "web scraping fingerprint resistant",
]

# Patterns to extract technique metadata from paper abstracts
TECHNIQUE_RE = re.compile(
    r"(JA[34]|TLS.?fingerprint|TCP.?IP.?stack|header.?normali[sz]ation"
    r"|anti.?detect|evasion.?method|residential.?proxy)",
    re.IGNORECASE,
)

MAX_RESULTS_PER_QUERY = 10


class AcademicHarvester:
    """Scrapes Arxiv (and optionally CNKI) for anti-detection research."""

    def __init__(self, cnki_enabled: bool = False, max_results: int = 30):
        self.cnki_enabled = cnki_enabled
        self.max_results = max_results

    async def _search_arxiv(
        self, client: httpx.AsyncClient, query: str
    ) -> List[Dict[str, str]]:
        """Search the Arxiv API and return paper metadata."""
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": MAX_RESULTS_PER_QUERY,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending",
        }
        try:
            resp = await client.get(ARXIV_API, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse_arxiv_xml(resp.text)
        except Exception as exc:
            logger.warning("Arxiv search failed for '%s': %s", query, exc)
            return []

    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict[str, str]]:
        """Parse Arxiv Atom XML into structured dicts."""
        entries: List[Dict[str, str]] = []
        for block in re.split(r"<entry>", xml_text):
            if "</entry>" not in block:
                continue
            title_m = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
            summary_m = re.search(r"<summary>(.*?)</summary>", block, re.DOTALL)
            link_m = re.search(r'<id>(http[^<]+)</id>', block)
            published_m = re.search(r"<published>(.*?)</published>", block)

            title = title_m.group(1).strip().replace("\n", " ") if title_m else ""
            summary = summary_m.group(1).strip().replace("\n", " ") if summary_m else ""
            link = link_m.group(1).strip() if link_m else ""
            published = published_m.group(1).strip() if published_m else ""

            if title and summary:
                techniques = TECHNIQUE_RE.findall(summary)
                entries.append({
                    "title": title,
                    "summary": summary[:500],
                    "url": link,
                    "published": published,
                    "techniques": list(set(t.lower() for t in techniques)),
                })
        return entries

    def _extract_actionable_intel(self, paper: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Convert a paper entry into actionable proxy configuration intel."""
        techniques = paper.get("techniques", [])
        if not techniques:
            return None
        intel: Dict[str, str] = {
            "source": "arxiv",
            "title": paper.get("title", ""),
            "url": paper.get("url", ""),
            "techniques": json.dumps(techniques),
        }
        # Extract specific fingerprint details if present
        summary = paper.get("summary", "")
        ja3_match = re.search(
            r"JA3[_\s-]?[Ss]tring[:\s]+([a-fA-F0-9]{32})", summary
        )
        if ja3_match:
            intel["ja3_hash"] = ja3_match.group(1)
        ja4_match = re.search(
            r"JA4[_\s-]?[Ff]ingerprint[:\s]+([a-fA-F0-9]{16,})", summary
        )
        if ja4_match:
            intel["ja4_fingerprint"] = ja4_match.group(1)
        # Extract recommended TLS extensions
        ext_match = re.search(
            r"(?:extension|ext)[-_\s]+list[:\s]+(\[[^\]]+\])", summary, re.IGNORECASE
        )
        if ext_match:
            intel["tls_extensions"] = ext_match.group(1)
        return intel

    async def harvest(self) -> AsyncIterator[Dict[str, str]]:
        """Yield actionable anti-detection intel from academic sources."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            all_entries: List[Dict[str, str]] = []
            for query in QUERY_TERMS:
                entries = await self._search_arxiv(client, query)
                all_entries.extend(entries)
                if len(all_entries) >= self.max_results:
                    break
            # Deduplicate by URL
            seen: set = set()
            for paper in all_entries:
                url = paper.get("url", "")
                if url in seen:
                    continue
                seen.add(url)
                intel = self._extract_actionable_intel(paper)
                if intel:
                    yield intel

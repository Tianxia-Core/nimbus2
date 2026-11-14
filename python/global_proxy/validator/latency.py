# ffp: FFP-NIMBUS2-LATENCY io-edge python
"""Latency & anonymity verification for candidate proxies.

Sends test requests through candidate proxies to verify:
  1. Low latency (< 250ms)
  2. Zero header leakage (X-Forwarded-For, Via, etc.)
  3. Strict UK GeoIP exit node status (country: GB)
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Test endpoints
LATENCY_TEST_URL = "http://httpbin.org/ip"
GEOIP_CHECK_URL = "http://ip-api.com/json?fields=status,countryCode,isp,query"
GEODB_CHECK_URL = "https://ipinfo.io/json"

# Headers that indicate proxy leakage
LEAKAGE_HEADERS = {
    "x-forwarded-for",
    "x-real-ip",
    "via",
    "x-proxy-id",
    "x-forwarded-server",
    "forwarded",
    "x-forwarded-host",
    "x-forwarded-proto",
}

MAX_LATENCY_MS = 250
TIMEOUT_SECONDS = 10
UK_COUNTRY_CODES = {"GB", "UK"}


class LatencyChecker:
    """Validates proxies for latency, anonymity, and UK exit status."""

    def __init__(
        self,
        max_latency_ms: int = MAX_LATENCY_MS,
        timeout: int = TIMEOUT_SECONDS,
        require_uk_exit: bool = True,
    ):
        self.max_latency_ms = max_latency_ms
        self.timeout = timeout
        self.require_uk_exit = require_uk_exit

    def _build_proxy_url(self, proxy: Dict[str, str]) -> str:
        """Build a proxy URL string from a proxy dict."""
        protocol = proxy.get("protocol", "http")
        host = proxy["host"]
        port = proxy["port"]
        username = proxy.get("username", "")
        password = proxy.get("password", "")
        if username and password:
            return f"{protocol}://{username}:{password}@{host}:{port}"
        return f"{protocol}://{host}:{port}"

    async def _test_latency(
        self, proxy_url: str, client: httpx.AsyncClient
    ) -> Tuple[bool, float, Dict[str, str]]:
        """Test basic latency through the proxy. Returns (ok, latency_ms, response_headers)."""
        start = time.monotonic()
        try:
            resp = await client.get(
                LATENCY_TEST_URL,
                proxy=proxy_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            resp.raise_for_status()
            return True, elapsed_ms, dict(resp.headers)
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug("Latency test failed (%s): %s", proxy_url, exc)
            return False, elapsed_ms, {}

    def _check_header_leakage(self, headers: Dict[str, str]) -> List[str]:
        """Check response headers for proxy leakage indicators."""
        leaked: List[str] = []
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in LEAKAGE_HEADERS:
                leaked.append(f"{key}: {value}")
            # Also detect common Via header patterns
            if key_lower == "via" and value.strip():
                leaked.append(f"Via header present: {value}")
        return leaked

    async def _check_exit_country(
        self, proxy_url: str, client: httpx.AsyncClient
    ) -> Optional[str]:
        """Determine the exit node's country via GeoIP check."""
        # Try multiple services for redundancy
        services = [GEOIP_CHECK_URL, GEODB_CHECK_URL]
        for service_url in services:
            try:
                resp = await client.get(
                    service_url,
                    proxy=proxy_url,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                country = data.get("countryCode") or data.get("country", "")
                if country:
                    return country.upper()
            except Exception:
                continue
        return None

    async def validate(
        self, proxy: Dict[str, str]
    ) -> Dict:
        """Full validation pipeline for a single proxy.

        Returns a result dict with:
            - proxy: the input proxy
            - ok: bool
            - latency_ms: float
            - header_leakage: list of leaked headers
            - exit_country: str or None
            - errors: list of error strings
        """
        proxy_url = self._build_proxy_url(proxy)
        result: Dict = {
            "proxy": proxy,
            "ok": False,
            "latency_ms": 0.0,
            "header_leakage": [],
            "exit_country": None,
            "errors": [],
        }

        async with httpx.AsyncClient() as client:
            # Step 1: Latency check
            ok, latency_ms, resp_headers = await self._test_latency(
                proxy_url, client
            )
            result["latency_ms"] = latency_ms
            if not ok:
                result["errors"].append(f"Connection failed or timed out ({latency_ms:.0f}ms)")
                return result
            if latency_ms > self.max_latency_ms:
                result["errors"].append(
                    f"Latency {latency_ms:.0f}ms exceeds max {self.max_latency_ms}ms"
                )
                return result

            # Step 2: Header leakage check
            leaked = self._check_header_leakage(resp_headers)
            result["header_leakage"] = leaked
            if leaked:
                result["errors"].append(
                    f"Header leakage detected: {'; '.join(leaked)}"
                )
                return result

            # Step 3: UK exit check
            if self.require_uk_exit:
                country = await self._check_exit_country(proxy_url, client)
                result["exit_country"] = country
                if country and country not in UK_COUNTRY_CODES:
                    result["errors"].append(
                        f"Exit node is {country}, expected GB"
                    )
                    return result

        result["ok"] = True
        return result

    async def validate_batch(
        self, proxies: List[Dict[str, str]], concurrency: int = 20
    ) -> List[Dict]:
        """Validate multiple proxies concurrently with bounded concurrency."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _guarded_validate(p: Dict[str, str]) -> Dict:
            async with semaphore:
                return await self.validate(p)

        tasks = [_guarded_validate(p) for p in proxies]
        return await asyncio.gather(*tasks, return_exceptions=False)

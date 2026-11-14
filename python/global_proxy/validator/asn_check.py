# ffp: FFP-NIMBUS2-ASN-CHECK io-edge python
"""ASN inspection — enforces UK Residential/Mobile ASNs, rejects datacenter IPs.

Queries ipinfo.io or local GeoLite2 databases to classify IP addresses
by ASN and country. Maintains allowlists of UK residential/mobile ASNs
and blocklists of known datacenter providers.
"""

import asyncio
import logging
from typing import Dict, Optional, Set

import httpx

logger = logging.getLogger(__name__)

IPINFO_API = "https://ipinfo.io/{ip}/json"

# UK Residential & Mobile ASNs — expandable list
UK_RESIDENTIAL_ASNS: Set[str] = {
    # Virgin Media
    "AS5089", "AS174",
    # BT / BT Consumer
    "AS2856", "AS20712",
    # Sky Broadband
    "AS5607",
    # EE / BT Mobile
    "AS12576", "AS20940",
    # Vodafone UK
    "AS25152", "AS13122",
    # O2 / Telefonica UK
    "AS2856", "AS3356",
    # TalkTalk
    "AS9105", "AS13285",
    # Plusnet
    "AS2856",
    # Hyperoptic
    "AS57361",
    # Zen Internet
    "AS13037",
    # Three / Hutchison UK
    "AS3356", "AS34245",
    # Community Fibre
    "AS56458",
    # Gigaclear
    "AS56329",
}

# Datacenter ASNs — hard reject
DATACENTER_ASNS: Set[str] = {
    # M247
    "AS9009",
    # DigitalOcean
    "AS14061",
    # Hetzner
    "AS24940",
    # AWS
    "AS16509",
    # OVH
    "AS16276",
    # Vultr
    "AS20473",
    # Linode / Akamai
    "AS63949",
    # Contabo
    "AS14935",
    # Datacamp / IONOS
    "AS208093",
    # Rackspace
    "AS33070",
    # Azure
    "AS8075",
    # Google Cloud
    "AS15169",
}

# UK country code
UK_COUNTRY_CODE = "GB"


class ASNChecker:
    """Classifies IP addresses by ASN and enforces UK residential policy."""

    def __init__(
        self,
        ipinfo_token: Optional[str] = None,
        additional_uk_asns: Optional[Set[str]] = None,
        additional_dc_asns: Optional[Set[str]] = None,
    ):
        self.ipinfo_token = ipinfo_token
        self.uk_asns = UK_RESIDENTIAL_ASNS.copy()
        self.dc_asns = DATACENTER_ASNS.copy()
        if additional_uk_asns:
            self.uk_asns.update(additional_uk_asns)
        if additional_dc_asns:
            self.dc_asns.update(additional_dc_asns)
        # Cache to avoid repeated lookups
        self._cache: Dict[str, Dict[str, str]] = {}

    async def lookup(self, ip: str, client: httpx.AsyncClient) -> Optional[Dict[str, str]]:
        """Query ipinfo.io for ASN and country data."""
        if ip in self._cache:
            return self._cache[ip]

        url = IPINFO_API.format(ip=ip)
        params: Dict = {}
        if self.ipinfo_token:
            params["token"] = self.ipinfo_token

        try:
            resp = await client.get(url, params=params, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            result = {
                "ip": ip,
                "asn": data.get("org", "").split(" ")[0].replace("AS", "AS"),
                "org": data.get("org", ""),
                "country": data.get("country", ""),
                "city": data.get("city", ""),
                "region": data.get("region", ""),
            }
            self._cache[ip] = result
            return result
        except Exception as exc:
            logger.debug("ipinfo lookup failed for %s: %s", ip, exc)
            return None

    async def check_uk_residential(self, ip: str, client: httpx.AsyncClient) -> Dict:
        """Classify an IP as UK residential, datacenter, or unknown.

        Returns a dict with:
            - ip: str
            - classification: "uk_residential" | "datacenter" | "unknown"
            - asn: str
            - org: str
            - country: str
            - is_valid: bool
        """
        info = await self.lookup(ip, client)
        if not info:
            return {
                "ip": ip,
                "classification": "unknown",
                "asn": "",
                "org": "",
                "country": "",
                "is_valid": False,
            }

        asn = info.get("asn", "")
        country = info.get("country", "")
        org = info.get("org", "").lower()

        # Hard-reject datacenter ASNs
        if asn in self.dc_asns:
            return {
                "ip": ip,
                "classification": "datacenter",
                "asn": asn,
                "org": info.get("org", ""),
                "country": country,
                "is_valid": False,
            }

        # Check org for datacenter keywords
        dc_keywords = {
            "cloud", "hosting", "datacenter", "data centre",
            "virtual", "vps", "dedicated server",
        }
        if any(kw in org for kw in dc_keywords):
            return {
                "ip": ip,
                "classification": "datacenter",
                "asn": asn,
                "org": info.get("org", ""),
                "country": country,
                "is_valid": False,
            }

        # Validate UK residential
        if country != UK_COUNTRY_CODE:
            return {
                "ip": ip,
                "classification": "non_uk",
                "asn": asn,
                "org": info.get("org", ""),
                "country": country,
                "is_valid": False,
            }

        if asn in self.uk_asns:
            return {
                "ip": ip,
                "classification": "uk_residential",
                "asn": asn,
                "org": info.get("org", ""),
                "country": country,
                "is_valid": True,
            }

        # UK IP but not in known residential list — still could be residential
        return {
            "ip": ip,
            "classification": "uk_unknown_asn",
            "asn": asn,
            "org": info.get("org", ""),
            "country": country,
            "is_valid": True,  # allow with warning
        }

    def add_uk_asn(self, asn: str) -> None:
        """Dynamically add a UK residential ASN."""
        self.uk_asns.add(asn.upper() if not asn.startswith("AS") else asn)

    def add_dc_asn(self, asn: str) -> None:
        """Dynamically add a datacenter ASN to blocklist."""
        self.dc_asns.add(asn.upper() if not asn.startswith("AS") else asn)

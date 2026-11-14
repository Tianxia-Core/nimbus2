#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-VERITAS-REX io-edge python
"""
Veritas Rex — Truth Verification for Proxy Validity
Ensures proxy data is accurate and trustworthy
"""

import asyncio
import aiohttp
import json
from typing import Dict, Optional

class VeritasRex:
    """
    Veritas Rex — Truth Verification
    - Verifies proxy IP addresses
    - Checks ASN authenticity
    - Validates geographic location
    - Detects proxy chain indicators
    """
    
    UK_ASNS = [
        "AS5607",  # Virgin Media
        "AS12576",  # BT
        "AS5607",  # Sky
        "AS12576",  # EE
        "AS12576",  # Vodafone
        "AS12576",  # O2
        "AS12576",  # TalkTalk
    ]
    
    DATACENTER_ASNS = [
        "AS14061",  # DigitalOcean
        "AS24940",  # Hetzner
        "AS16509",  # AWS
        "AS16276",  # OVH
        "AS200462", # M247
    ]
    
    async def verify_ip(self, ip: str) -> Dict:
        """Verify IP address authenticity"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,isp,org,as",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    data = await resp.json()
                    return {
                        "ip": ip,
                        "valid": data.get("status") == "success",
                        "country": data.get("country", "unknown"),
                        "country_code": data.get("countryCode", "unknown"),
                        "isp": data.get("isp", "unknown"),
                        "org": data.get("org", "unknown"),
                        "asn": data.get("as", "unknown"),
                        "is_uk": data.get("countryCode") == "GB",
                        "is_datacenter": any(asn in data.get("as", "") for asn in self.DATACENTER_ASNS)
                    }
        except Exception as e:
            return {"ip": ip, "valid": False, "error": str(e)}
    
    async def verify_proxy_chain(self, proxy: str) -> Dict:
        """Verify proxy chain for anonymity"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test 1: Check for X-Forwarded-For header leakage
                async with session.get(
                    "http://httpbin.org/headers",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    headers = await resp.json()
                    has_leakage = "X-Forwarded-For" in str(headers)
                    
                    return {
                        "proxy": proxy,
                        "chain_valid": not has_leakage,
                        "leakage_detected": has_leakage,
                        "headers": headers.get("headers", {})
                    }
        except Exception as e:
            return {"proxy": proxy, "chain_valid": False, "error": str(e)}

#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-MULTI-COUNTRY-ASN io-edge python
"""
Multi-Country ASN Checker
Supports: US, UK, DE, BR, IN, JP, AU, FR, CA, ES
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional

class MultiCountryASNChecker:
    """
    Multi-Country ASN Checker
    - Supports 10+ countries
    - Real-time ASN validation
    - Datacenter detection
    """
    
    # Country-specific residential/mobile ASNs
    COUNTRY_ASNS = {
        "US": {
            "residential": ["AS7922", "AS20001", "AS7018", "AS22394", "AS11492"],
            "mobile": ["AS3356", "AS20940", "AS1299", "AS3491"],
            "datacenter": ["AS14061", "AS16509", "AS16276", "AS24940"]
        },
        "UK": {
            "residential": ["AS5607", "AS12576", "AS13335", "AS2856", "AS5089"],
            "mobile": ["AS12576", "AS13335", "AS2856"],
            "datacenter": ["AS14061", "AS16509", "AS16276", "AS24940"]
        },
        "DE": {
            "residential": ["AS3320", "AS8767", "AS8437", "AS34011"],
            "mobile": ["AS3320", "AS8767"],
            "datacenter": ["AS24940", "AS16509", "AS14061"]
        },
        "BR": {
            "residential": ["AS28573", "AS7738", "AS28598", "AS18881"],
            "mobile": ["AS28573", "AS7738"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "IN": {
            "residential": ["AS9829", "AS17813", "AS24560", "AS10158"],
            "mobile": ["AS9829", "AS17813"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "JP": {
            "residential": ["AS2516", "AS4713", "AS9351", "AS17813"],
            "mobile": ["AS2516", "AS4713"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "AU": {
            "residential": ["AS1221", "AS4826", "AS7474", "AS4637"],
            "mobile": ["AS1221", "AS4826"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "FR": {
            "residential": ["AS3215", "AS12876", "AS16347", "AS15557"],
            "mobile": ["AS3215", "AS12876"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "CA": {
            "residential": ["AS577", "AS7992", "AS852", "AS22652"],
            "mobile": ["AS577", "AS7992"],
            "datacenter": ["AS14061", "AS16509"]
        },
        "ES": {
            "residential": ["AS3352", "AS12479", "AS12715", "AS8224"],
            "mobile": ["AS3352", "AS12479"],
            "datacenter": ["AS14061", "AS16509"]
        }
    }
    
    def __init__(self, target_country: str = "US"):
        self.target_country = target_country.upper()
        self.asn_data = self.COUNTRY_ASNS.get(self.target_country, {})
    
    async def check_asn(self, ip: str) -> Dict:
        """Check ASN for IP address"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,isp,org,as",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    data = await resp.json()
                    
                    if data.get("status") == "success":
                        asn = data.get("as", "").split(" ")[0] if data.get("as") else ""
                        
                        is_residential = asn in self.asn_data.get("residential", [])
                        is_mobile = asn in self.asn_data.get("mobile", [])
                        is_datacenter = asn in self.asn_data.get("datacenter", [])
                        is_target_country = data.get("countryCode") == self.target_country
                        
                        return {
                            "ip": ip,
                            "asn": asn,
                            "country": data.get("country"),
                            "country_code": data.get("countryCode"),
                            "isp": data.get("isp"),
                            "org": data.get("org"),
                            "is_residential": is_residential,
                            "is_mobile": is_mobile,
                            "is_datacenter": is_datacenter,
                            "is_target_country": is_target_country,
                            "valid": is_target_country and (is_residential or is_mobile) and not is_datacenter
                        }
                    else:
                        return {"ip": ip, "valid": False, "error": "API error"}
        except Exception as e:
            return {"ip": ip, "valid": False, "error": str(e)}
    
    def get_supported_countries(self) -> List[str]:
        """Get list of supported countries"""
        return list(self.COUNTRY_ASNS.keys())

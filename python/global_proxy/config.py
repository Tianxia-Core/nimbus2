#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-CONFIG io-edge python
"""
UK Proxy Engine — Configuration
Working proxies and settings
"""

import json
import os

# ═══ WORKING PROXY (VERIFIED) ═══
WORKING_PROXY = {
    "id": "webshare-uk-1",
    "name": "Webshare UK Residential",
    "type": "http",
    "host": "31.59.20.176",
    "port": 6754,
    "authentication": "ip",
    "country": "GB",
    "status": "active"
}

# ═══ PROXY LIST ═══
PROXY_LIST = [
    WORKING_PROXY,
    # Add more proxies here as they are discovered
]

# ═══ SETTINGS ═══
SETTINGS = {
    "max_streams": 225,
    "chunk_size_mb": 4,
    "timeout_seconds": 10,
    "retry_count": 10,
    "retry_delay_seconds": 60,
    "keepalive_interval_seconds": 30,
    "uk_asns": ["AS5607", "AS12576", "AS13335", "AS2856", "AS5089"],
    "datacenter_reject": ["AS14061", "AS24940", "AS16509", "AS16276", "AS200462"]
}

def get_proxy_url(proxy: dict) -> str:
    """Get proxy URL for requests"""
    return f"http://{proxy['host']}:{proxy['port']}/"

def get_all_proxy_urls() -> list:
    """Get all proxy URLs"""
    return [get_proxy_url(p) for p in PROXY_LIST]

# Load config from file if exists
config_path = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        file_config = json.load(f)
        if "proxies" in file_config:
            PROXY_LIST = file_config["proxies"]
        if "settings" in file_config:
            SETTINGS.update(file_config["settings"])

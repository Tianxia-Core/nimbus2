#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-NIMBUS-TESTER io-edge python
"""
NIMBUS² Enhanced Proxy Tester
Parallel proxy testing with 225 streams
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Tuple

class NimbusProxyTester:
    """
    Nimbus² Enhanced Proxy Tester
    Tests proxies in parallel with optimal stream count
    """
    
    def __init__(self, max_streams: int = 225):
        self.max_streams = max_streams
        self.results: List[Dict] = []
        self.semaphore = asyncio.Semaphore(max_streams)
    
    async def test_proxy(self, session: aiohttp.ClientSession, 
                         proxy: str, timeout: int = 10) -> Dict:
        """Test a single proxy"""
        async with self.semaphore:
            try:
                start = time.time()
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    elapsed = time.time() - start
                    data = await resp.json()
                    return {
                        "proxy": proxy,
                        "status": "alive",
                        "latency": elapsed,
                        "ip": data.get("origin", "unknown"),
                        "response_code": resp.status
                    }
            except Exception as e:
                return {
                    "proxy": proxy,
                    "status": "dead",
                    "error": str(e)
                }
    
    async def test_batch(self, proxies: List[str]) -> List[Dict]:
        """Test multiple proxies in parallel"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.test_proxy(session, p) for p in proxies]
            results = await asyncio.gather(*tasks)
            return results
    
    def filter_alive(self, results: List[Dict]) -> List[Dict]:
        """Filter only alive proxies"""
        return [r for r in results if r["status"] == "alive"]
    
    def sort_by_latency(self, results: List[Dict]) -> List[Dict]:
        """Sort by latency (fastest first)"""
        return sorted(results, key=lambda x: x.get("latency", float("inf")))

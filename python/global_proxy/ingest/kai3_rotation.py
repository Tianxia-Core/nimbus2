#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-KAI3-ROTATION io-edge python
"""
KAI³ Pattern-Based Proxy Rotation
Intelligent rotation based on usage patterns
"""

import random
import time
from typing import List, Dict, Optional
from collections import defaultdict

class KAIRotation:
    """
    KAI³ Pattern-Based Proxy Rotation
    Selects optimal proxies based on:
    - Latency patterns
    - Success rates
    - Geographic distribution
    - Time-based patterns
    """
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.patterns: Dict[str, List] = defaultdict(list)
        self.success_history: Dict[str, int] = defaultdict(int)
        self.failure_history: Dict[str, int] = defaultdict(int)
    
    def add_proxy(self, proxy: Dict):
        """Add proxy to rotation pool"""
        self.proxies.append(proxy)
        self._update_patterns(proxy)
    
    def _update_patterns(self, proxy: Dict):
        """Update usage patterns"""
        # Geographic pattern
        geo = proxy.get("country", "unknown")
        self.patterns["geo"].append(geo)
        
        # Latency pattern
        latency = proxy.get("latency", 0)
        if latency < 100:
            self.patterns["fast"].append(proxy)
        elif latency < 250:
            self.patterns["medium"].append(proxy)
        else:
            self.patterns["slow"].append(proxy)
    
    def select_proxy(self, strategy: str = "latency") -> Optional[Dict]:
        """Select optimal proxy based on strategy"""
        if not self.proxies:
            return None
        
        if strategy == "latency":
            # Prefer fast proxies
            fast = self.patterns.get("fast", [])
            if fast:
                return random.choice(fast)
            return random.choice(self.proxies)
        
        elif strategy == "round_robin":
            # Round-robin selection
            return self.proxies[len(self.patterns["round_robin"]) % len(self.proxies)]
        
        elif strategy == "random":
            return random.choice(self.proxies)
        
        elif strategy == "success_rate":
            # Prefer proxies with high success rate
            scored = []
            for p in self.proxies:
                success = self.success_history.get(p["proxy"], 0)
                failure = self.failure_history.get(p["proxy"], 0)
                score = success / (success + failure + 1)
                scored.append((score, p))
            scored.sort(reverse=True)
            return scored[0][1] if scored else None
        
        return random.choice(self.proxies)
    
    def record_success(self, proxy: str):
        """Record successful proxy use"""
        self.success_history[proxy] += 1
    
    def record_failure(self, proxy: str):
        """Record failed proxy use"""
        self.failure_history[proxy] += 1

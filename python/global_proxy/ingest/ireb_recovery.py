#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-IREB-RECOVERY io-edge python
"""
IREB Error Recovery — Cubed Backoff
Intelligent error recovery for proxy operations
"""

import time
import asyncio
from typing import Callable, Any

class IREBRecovery:
    """
    IREB Error Recovery
    - Cubed backoff: 5min → 125min → 3.6h
    - Prevents rapid restart loops
    - Allows network recovery time
    """
    
    def __init__(self, max_retries: int = 10, base_delay: int = 300):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.failure_count = 0
        self.last_failure = 0
    
    def calculate_backoff(self) -> int:
        """Calculate cubed backoff delay"""
        delay = self.base_delay * (self.failure_count ** 3)
        return min(delay, 14400)  # Cap at 4 hours
    
    def record_failure(self):
        """Record failure and increment count"""
        self.failure_count += 1
        self.last_failure = time.time()
    
    def record_success(self):
        """Record success and reset count"""
        self.failure_count = 0
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry and cubed backoff"""
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                delay = self.calculate_backoff()
                print(f"[IREB] Attempt {attempt + 1} failed: {e}")
                print(f"[IREB] Backing off {delay}s (cubed)")
                await asyncio.sleep(delay)
        
        raise Exception(f"IREB: Failed after {self.max_retries} attempts")
    
    def should_retry(self) -> bool:
        """Check if we should retry"""
        if self.failure_count >= self.max_retries:
            return False
        
        elapsed = time.time() - self.last_failure
        if elapsed < self.calculate_backoff():
            return False
        
        return True

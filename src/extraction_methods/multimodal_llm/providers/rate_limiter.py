"""
Rate limiting handler for API calls with exponential backoff.
Extracted from optimal_two_tool_processor for reuse.
"""

import asyncio
import random
import time
from typing import Any, Callable


class RateLimitHandler:
    """
    Handles rate limiting for both DocAI and Claude APIs
    with exponential backoff and jitter.
    """
    
    def __init__(self):
        self.docai_last_request = 0
        self.claude_last_request = 0
        
        # Minimum time between requests (in seconds)
        self.docai_min_interval = 0.1  # 10 requests per second max
        self.claude_min_interval = 0.2  # 5 requests per second max
        
        # Backoff configuration
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        
    async def wait_if_needed(self, api_type: str):
        """Wait if we're sending requests too quickly"""
        current_time = time.time()
        
        if api_type == "docai":
            time_since_last = current_time - self.docai_last_request
            if time_since_last < self.docai_min_interval:
                await asyncio.sleep(self.docai_min_interval - time_since_last)
            self.docai_last_request = time.time()
            
        elif api_type == "claude":
            time_since_last = current_time - self.claude_last_request
            if time_since_last < self.claude_min_interval:
                await asyncio.sleep(self.claude_min_interval - time_since_last)
            self.claude_last_request = time.time()
    
    async def execute_with_backoff(self, func: Callable, *args, api_type: str = "claude", **kwargs) -> Any:
        """
        Execute function with exponential backoff on rate limit errors.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            api_type: "docai" or "claude" for rate limiting
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            Exception: If max retries exceeded or non-rate-limit error
        """
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await self.wait_if_needed(api_type)
                
                # Execute the function
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                is_rate_limit = (
                    "rate" in error_str or 
                    "429" in error_str or 
                    "too many requests" in error_str or
                    "quota" in error_str
                )
                
                if not is_rate_limit or attempt == self.max_retries - 1:
                    raise
                
                # Calculate backoff with jitter
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                
                print(f"  ⚠️ Rate limited on attempt {attempt + 1}/{self.max_retries}. "
                      f"Waiting {total_delay:.1f}s before retry...")
                
                await asyncio.sleep(total_delay)
        
        raise Exception(f"Max retries ({self.max_retries}) exceeded")
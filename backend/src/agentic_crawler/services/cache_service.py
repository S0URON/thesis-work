"""Caching service for tool outputs."""

import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from ..models.execution import CacheStats
from .content_normalize import normalize_langchain_content


class CacheService:
    """Service for caching tool outputs with LRU eviction."""

    def __init__(self, max_size_mb: int = 100, ttl_hours: int = 24):
        """
        Initialize cache service.

        Args:
            max_size_mb: Maximum cache size in megabytes
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl = timedelta(hours=ttl_hours)
        self.current_size = 0
        self.hits = 0
        self.misses = 0

    def _get_key(self, tool_name: str, args: dict) -> str:
        """
        Generate cache key from tool name and arguments.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            MD5 hash of tool name and arguments
        """
        args_str = json.dumps(args, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{args_str}".encode()).hexdigest()

    def get(self, tool_name: str, args: dict) -> Optional[str]:
        """
        Retrieve cached result if available and not expired.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Cached result or None if not found/expired
        """
        key = self._get_key(tool_name, args)

        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                self.hits += 1
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return entry["result"]
            else:
                # Expired entry
                self._remove(key)

        self.misses += 1
        return None

    def put(self, tool_name: str, args: dict, result: Union[str, list, Any]) -> None:
        """
        Store result in cache.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Tool result to cache (str or LangChain multimodal list)
        """
        text = normalize_langchain_content(result)
        key = self._get_key(tool_name, args)
        result_size = len(text.encode("utf-8"))

        # Evict old entries if needed (LRU)
        while self.current_size + result_size > self.max_size_bytes and self.cache:
            oldest_key = next(iter(self.cache))
            self._remove(oldest_key)

        self.cache[key] = {
            "result": text,
            "timestamp": datetime.now(),
            "size": result_size,
            "tool_name": tool_name,
        }
        self.current_size += result_size

    def _remove(self, key: str) -> None:
        """Remove entry from cache and update size."""
        if key in self.cache:
            self.current_size -= self.cache[key]["size"]
            del self.cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.current_size = 0
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats model with current statistics
        """
        return CacheStats(
            hits=self.hits,
            misses=self.misses,
            entries=len(self.cache),
            size_mb=self.current_size / 1024 / 1024,
        )

    def __len__(self) -> int:
        """Return number of cache entries."""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache

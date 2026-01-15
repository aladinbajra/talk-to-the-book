"""
Caching layer: Redis if available, otherwise in-memory LRU.

Goal: cache top-5 responses per book for identical query payloads.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional


class InMemoryLRUCache:
    def __init__(self, max_items: int = 256, ttl_seconds: int = 300):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._data.get(key)
        if not item:
            return None
        if item["expires_at"] < time.time():
            self._data.pop(key, None)
            return None
        # LRU promote
        self._data.move_to_end(key)
        return item["value"]

    def set(self, key: str, value: Dict[str, Any]) -> None:
        expires_at = time.time() + self.ttl_seconds
        self._data[key] = {"value": value, "expires_at": expires_at}
        self._data.move_to_end(key)
        while len(self._data) > self.max_items:
            self._data.popitem(last=False)


class CacheService:
    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.redis = None
        self.memory = InMemoryLRUCache(max_items=512, ttl_seconds=ttl_seconds)

        if redis_url:
            try:
                import redis  # type: ignore

                self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
                # ping
                self.redis.ping()
            except Exception:
                self.redis = None

    @staticmethod
    def make_query_hash(book_id: str, question: str, history: Any, options: Any) -> str:
        payload = {
            "book_id": book_id,
            "question": question,
            "history": history or [],
            "options": options or {},
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _key(self, book_id: str, qhash: str) -> str:
        return f"book:{book_id}:q:{qhash}"

    def get(self, book_id: str, qhash: str) -> Optional[Dict[str, Any]]:
        key = self._key(book_id, qhash)
        if self.redis is not None:
            try:
                val = self.redis.get(key)
                if not val:
                    return None
                return json.loads(val)
            except Exception:
                return None
        return self.memory.get(key)

    def set(self, book_id: str, qhash: str, value: Dict[str, Any]) -> None:
        key = self._key(book_id, qhash)
        if self.redis is not None:
            try:
                self.redis.setex(key, self.ttl_seconds, json.dumps(value, ensure_ascii=False))
                return
            except Exception:
                pass
        self.memory.set(key, value)


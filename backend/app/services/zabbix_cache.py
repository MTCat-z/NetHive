"""
Zabbix 数据缓存层 — 使用 Redis 缓存 API 响应
"""
import json
import hashlib
import logging
from typing import Optional
import redis as redis_lib
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[redis_lib.Redis] = None


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception:
            logger.warning('Redis 不可用，Zabbix 缓存禁用')
            _redis = None
    return _redis


def cache_key(method: str, params: dict = None) -> str:
    h = hashlib.md5(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()[:8]
    return f'zabbix:{method}:{h}'


def get_cached(method: str, params: dict = None) -> Optional[dict]:
    r = _get_redis()
    if not r:
        return None
    try:
        key = cache_key(method, params)
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def set_cached(method: str, params: dict, data, ttl: int = None):
    r = _get_redis()
    if not r:
        return
    try:
        key = cache_key(method, params)
        r.setex(key, ttl or settings.ZABBIX_CACHE_TTL, json.dumps(data, ensure_ascii=False, default=str))
        # 同时保存 stale 副本（5分钟TTL）
        stale_key = f'zabbix:stale:{method}:{hashlib.md5(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()[:8]}'
        r.setex(stale_key, 300, json.dumps(data, ensure_ascii=False, default=str))
    except Exception:
        pass


def get_stale(method: str, params: dict = None) -> Optional[dict]:
    r = _get_redis()
    if not r:
        return None
    try:
        stale_key = f'zabbix:stale:{method}:{hashlib.md5(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()[:8]}'
        data = r.get(stale_key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def clear_cache():
    r = _get_redis()
    if not r:
        return
    try:
        keys = r.keys('zabbix:*')
        if keys:
            r.delete(*keys)
    except Exception:
        pass

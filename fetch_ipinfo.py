#ipinfo token
from datetime import datetime, timedelta
import os
from typing import Dict, Tuple

import httpx

IPINFO_TOKEN = os.getenv("IPINFO_TOKEN", "0623c624c47f1f")
IPINFO_URL = "https://api.ipinfo.io/lite/{ip}"

_CACHE_TTL_SECONDS = 300
_cache: Dict[str, Tuple[dict, datetime]] = {}


async def fetch_ipinfo(ip: str):
    # 内网/本地 IP 直接跳过
    if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.16."):
        return {"error": "private or local ip", "ip": ip}

    #判断是否短时间查询
    now = datetime.now()
    cache= _cache.get(ip)
    if cache:
        data,expires_at = cache
        if expires_at > now:
            return data


    url = IPINFO_URL.format(ip=ip)
    params = {"token": IPINFO_TOKEN}
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        _cache[ip] = (data, now + timedelta(seconds=_CACHE_TTL_SECONDS))
        return data


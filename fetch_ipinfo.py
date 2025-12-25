#ipinfo token
IPINFO_TOKEN="0623c624c47f1f"
IPINFO_URL = "https://ipinfo.io/{ip}/json"

import httpx

async def fetch_ipinfo(ip: str):
    # 内网/本地 IP 直接跳过
    if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.16."):
        return {"error": "private or local ip", "ip": ip}


    url = IPINFO_URL.format(ip)
    params={"token": IPINFO_TOKEN}
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


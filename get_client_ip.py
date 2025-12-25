from fastapi import Request

# -------------------------
# Get client IP helper
# -------------------------
def get_client_ip(request: Request) -> str:
    """
    获取真实 IP：
    - 优先 X-Forwarded-For
    - 再 X-Real-IP
    - 最后 request.client.host
    """
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()

    return request.client.host

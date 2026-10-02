import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global


def normalize_url(url: str) -> str:
    url = url.strip()
    if any(ord(c) < 32 for c in url) or "\\" in url:
        raise ValueError("链接包含无效字符")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("请输入完整的 http 或 https 视频链接")
    if parsed.username or parsed.password:
        raise ValueError("链接不能包含用户名或密码")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("只支持标准 HTTP(S) 端口")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("不支持本机、内网或云元数据地址")
    try:
        if not public_ip(host):
            raise ValueError("不支持本机、内网或保留地址")
    except ValueError as exc:
        if "不支持" in str(exc):
            raise
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def validate_public_url(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlsplit(normalized)
    try:
        results = socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ValueError("无法解析该域名，请检查链接或网络") from exc
    if not results or any(not public_ip(r[4][0]) for r in results):
        raise ValueError("目标地址不属于公网，已拒绝请求")
    return normalized


def install_network_guard():
    """Install only in isolated extractor/download processes, never in the API.

    Validates addresses at connection-time DNS resolution, including redirects.
    yt-dlp proxies are disabled so a proxy cannot bypass this address check.
    """
    original = socket.getaddrinfo

    def guarded(host, port, *args, **kwargs):
        results = original(host, port, *args, **kwargs)
        if any(not public_ip(r[4][0]) for r in results):
            raise OSError("安全检查：禁止连接本机、内网或保留地址")
        return results

    socket.getaddrinfo = guarded

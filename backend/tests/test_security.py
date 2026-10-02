import socket

import pytest

from app.security import install_network_guard, normalize_url, public_ip, validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "https://user:password@example.com",
        "http://localhost/video",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://169.254.169.254",
        "http://[::1]",
        "http://[::ffff:127.0.0.1]",
        "https://example.com:8080/x",
        "https://a.local/x",
        "https://a.internal/x",
        "https://example.com/\nx",
        "https://example.com\\x",
    ],
)
def test_reject_unsafe_urls(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_normalize_removes_fragment():
    assert normalize_url("  https://EXAMPLE.com/video#t=30  ") == "https://example.com/video"


def test_dns_rebinding_target_rejected(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    )
    with pytest.raises(ValueError):
        validate_public_url("https://public-looking.example.com/x")


def test_connection_guard_checks_redirect_hosts(monkeypatch):
    original = socket.getaddrinfo
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]
    )
    install_network_guard()
    try:
        with pytest.raises(OSError):
            socket.getaddrinfo("redirect.example.com", 80)
    finally:
        socket.getaddrinfo = original


def test_mapped_ipv6_private():
    assert not public_ip("::ffff:10.1.1.1")
    assert public_ip("1.1.1.1")

"""
EgressFetcher — the ONLY outbound HTTP path for DigiZafe.

Policy (MASTER §9 / G1 / free-first):
- http/https only
- Resolve hostname first
- Reject private, loopback, link-local, metadata, CGNAT, etc.
- Optional host allowlist
- No redirects by default (prevents redirect-to-internal)
- Timeouts + response size cap
- Records to egress_ledger via caller (Consent/Egress service)

Residual risk: DNS rebinding TOCTOU between resolve and connect is mitigated by
no-redirects + short timeout + re-resolve optional pin. Full IP-pin + SNI for
HTTPS can be hardened further in Sprint 13; this is production-usable for MVP.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Networks we never connect to
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local + cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("2001:db8::/32"),
]


class EgressError(Exception):
    def __init__(self, message: str, code: str = "EGRESS-001") -> None:
        super().__init__(message)
        self.code = code


class EgressBlockedError(EgressError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="EGRESS-BLOCKED")


@dataclass
class EgressResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str
    resolved_ips: list[str]
    elapsed_ms: float


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return True
    if ip.is_unspecified:
        return True
    for net in _BLOCKED_NETWORKS:
        try:
            if ip in net:
                return True
        except Exception:
            continue
    # Explicit metadata
    if str(ip) in {"169.254.169.254", "metadata.google.internal"}:
        return True
    return False


def resolve_host(hostname: str) -> list[str]:
    """Resolve A/AAAA; raise if any address is blocked or none found."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise EgressError(f"DNS resolution failed for {hostname}: {e}", code="EGRESS-DNS") from e

    ips: list[str] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip_obj):
            raise EgressBlockedError(
                f"Resolved IP {addr} for {hostname} is not allowed (private/reserved/metadata)"
            )
        if addr not in ips:
            ips.append(addr)

    if not ips:
        raise EgressError(f"No usable addresses for {hostname}", code="EGRESS-DNS")
    return ips


class PinnedAsyncIOBackend(AutoBackend):
    def __init__(self, pinned_ips: list[str]) -> None:
        super().__init__()
        self.pinned_ips = pinned_ips

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any | None = None,
    ) -> httpcore.AsyncNetworkStream:
        pinned_ip = self.pinned_ips[0]
        return await super().connect_tcp(
            pinned_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class EgressFetcher:
    """Inject this into connectors / verification services. Never raw httpx elsewhere for user URLs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._global_sem = asyncio.Semaphore(20)

    def _host_sem(self, host: str) -> asyncio.Semaphore:
        if host not in self._semaphores:
            self._semaphores[host] = asyncio.Semaphore(4)
        return self._semaphores[host]

    def _validate_url(self, url: str) -> tuple[str, str, str]:
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in self.settings.egress_schemes:
            raise EgressBlockedError(f"Scheme not allowed: {scheme}")
        host = (parsed.hostname or "").lower()
        if not host:
            raise EgressError("URL missing hostname")
        # Block literal IPs that are private without DNS
        try:
            ip_obj = ipaddress.ip_address(host)
            if _is_blocked_ip(ip_obj):
                raise EgressBlockedError(f"Direct IP not allowed: {host}")
        except ValueError:
            pass  # hostname, not IP

        allow = self.settings.egress_allowlist_hosts
        if allow and host not in allow and not any(host.endswith("." + a) for a in allow):
            raise EgressBlockedError(f"Host not in allowlist: {host}")

        return scheme, host, url

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float | None = None,
        purpose: str = "generic",
    ) -> EgressResponse:
        import time

        scheme, host, url = self._validate_url(url)
        resolved = await asyncio.to_thread(resolve_host, host)

        timeout = timeout or self.settings.egress_timeout_seconds
        req_headers = {"User-Agent": f"DigiZafe-Egress/0.1 (+{purpose})"}
        if headers:
            # Prevent host override tricks
            headers = {k: v for k, v in headers.items() if k.lower() != "host"}
            req_headers.update(headers)

        transport = httpx.AsyncHTTPTransport(
            retries=0,
            verify=True,
            http2=False,
        )
        # Monkey patch network backend for DNS pinning
        transport._pool._network_backend = PinnedAsyncIOBackend(resolved)

        t0 = time.perf_counter()
        async with self._global_sem, self._host_sem(host):
            async with httpx.AsyncClient(
                transport=transport,
                timeout=httpx.Timeout(timeout),
                follow_redirects=False,  # critical
                max_redirects=0,
            ) as client:
                try:
                    # Stream the response to bound the maximum bytes read
                    max_b = self.settings.egress_max_response_bytes
                    chunks = []
                    bytes_read = 0
                    
                    async with client.stream(method.upper(), url, headers=req_headers, content=body) as resp:
                        status_code = resp.status_code
                        resp_headers = {k: v for k, v in resp.headers.items()}
                        final_url = str(resp.url)
                        
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            chunks.append(chunk)
                            bytes_read += len(chunk)
                            if bytes_read > max_b:
                                logger.warning("egress_body_truncated", url=url, max=max_b)
                                break
                                
                    content = b"".join(chunks)[:max_b]

                except httpx.HTTPError as e:
                    logger.warning("egress_http_error", url=url, host=host, error=str(e), purpose=purpose)
                    raise EgressError(f"HTTP error: {e}", code="EGRESS-HTTP") from e

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            "egress_fetch",
            purpose=purpose,
            host=host,
            status=status_code,
            resolved=resolved,
            elapsed_ms=round(elapsed, 2),
        )
        return EgressResponse(
            status_code=status_code,
            headers=resp_headers,
            body=content,
            url=final_url,
            resolved_ips=resolved,
            elapsed_ms=elapsed,
        )

    async def get_text(self, url: str, **kwargs: Any) -> str:
        r = await self.fetch(url, **kwargs)
        return r.body.decode("utf-8", errors="replace")


_fetcher: EgressFetcher | None = None


def get_egress_fetcher() -> EgressFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = EgressFetcher()
    return _fetcher

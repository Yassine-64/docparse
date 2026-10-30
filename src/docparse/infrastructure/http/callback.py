"""PUT the job outcome to the caller's URL, with retries. Mirrors the old CallbackService.

The URL comes from the API caller, so it is an SSRF surface: without checks, anyone with an API key
could make this server PUT to 169.254.169.254, localhost admin ports or the private network.
`check_callback_url` runs at submit time (422) and again before every attempt, redirects are never
followed, and only https to publicly routable addresses is allowed unless the operator opts in.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlsplit

import httpx

from docparse.application.jobs import Job

log = logging.getLogger(__name__)


class UnsafeCallbackUrl(ValueError):
    pass


def check_callback_url(url: str, allow_private: bool = False) -> None:
    """Raise UnsafeCallbackUrl unless `url` is https and every address it resolves to is global.

    ponytail: resolve-then-connect leaves a DNS-rebinding window between this check and httpx's own
    lookup; pin the resolved IP in the transport if callers are untrusted at that level."""
    parts = urlsplit(url)
    if parts.scheme != "https" and not (allow_private and parts.scheme == "http"):
        raise UnsafeCallbackUrl("callback_url must use https")
    if not parts.hostname or parts.username or parts.password:
        raise UnsafeCallbackUrl("callback_url needs a host and no credentials")
    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise UnsafeCallbackUrl(f"callback host does not resolve: {parts.hostname}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 is loopback, whatever its spelling
        if not ip.is_global:
            raise UnsafeCallbackUrl(f"callback host resolves to a non-public address: {ip}")


class HttpCallbackNotifier:
    def __init__(
        self, attempts: int = 5, timeout: float = 30.0, allow_private: bool = False
    ) -> None:
        self.attempts = attempts
        self.allow_private = allow_private
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def notify(self, job: Job) -> None:
        assert job.callback_url
        payload = {
            "job_id": job.id,
            "status": job.status,
            "filename": job.filename,
            "error": job.error,
            "passed": job.result.report.passed if job.result else None,
        }
        delay = 1.0
        for attempt in range(1, self.attempts + 1):
            # re-checked every time: the name may resolve elsewhere than it did at submit
            await asyncio.to_thread(check_callback_url, job.callback_url, self.allow_private)
            try:
                r = await self._client.put(job.callback_url, json=payload)
                r.raise_for_status()
                return
            except httpx.HTTPError as e:
                log.warning(
                    "callback attempt %d/%d for %s failed: %s", attempt, self.attempts, job.id, e
                )
                if attempt == self.attempts:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

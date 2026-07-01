from __future__ import annotations
import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Iterator
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Proxy:
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: str = "http"

    # Health tracking
    failures: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0
    is_healthy: bool = True

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def playwright_server(self) -> str:
        return f"{self.host}:{self.port}"

    def to_playwright_dict(self) -> dict:
        proxy: dict = {"server": f"{self.protocol}://{self.host}:{self.port}"}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy

    def to_selenium_dict(self) -> dict:
        return {
            "http": self.url,
            "https": self.url,
        }

    def mark_failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.is_healthy = False
            logger.warning("proxy_disabled", host=self.host, port=self.port, failures=self.failures)

    def mark_success(self) -> None:
        self.failures = 0
        self.is_healthy = True
        self.last_used = time.time()


@dataclass
class ProxyPool:
    proxies: list[Proxy] = field(default_factory=list)
    _index: int = 0

    @classmethod
    def from_list(cls, proxy_strings: list[str]) -> "ProxyPool":
        """
        Parse proxy strings in format:
          http://user:pass@host:port
          host:port
          user:pass@host:port
        """
        pool = cls()
        for raw in proxy_strings:
            try:
                pool.proxies.append(cls._parse(raw.strip()))
            except Exception as e:
                logger.warning("proxy_parse_failed", raw=raw, error=str(e))
        logger.info("proxy_pool_loaded", count=len(pool.proxies))
        return pool

    @staticmethod
    def _parse(raw: str) -> Proxy:
        protocol = "http"
        if "://" in raw:
            protocol, raw = raw.split("://", 1)

        username = password = None
        if "@" in raw:
            creds, raw = raw.rsplit("@", 1)
            if ":" in creds:
                username, password = creds.split(":", 1)

        if ":" in raw:
            host, port_str = raw.rsplit(":", 1)
            port = int(port_str)
        else:
            raise ValueError(f"Cannot parse proxy: {raw}")

        return Proxy(host=host, port=port, username=username, password=password, protocol=protocol)

    def healthy(self) -> list[Proxy]:
        return [p for p in self.proxies if p.is_healthy]

    def get_next(self) -> Proxy | None:
        """Round-robin over healthy proxies."""
        pool = self.healthy()
        if not pool:
            return None
        proxy = pool[self._index % len(pool)]
        self._index += 1
        proxy.last_used = time.time()
        return proxy

    def get_random(self) -> Proxy | None:
        pool = self.healthy()
        return random.choice(pool) if pool else None

    async def check_all(self, timeout: float = 10.0) -> dict:
        """Async health check — ping via httpx."""
        results = {"healthy": 0, "failed": 0}

        async def _check(proxy: Proxy) -> None:
            try:
                async with httpx.AsyncClient(proxies=proxy.url, timeout=timeout) as client:
                    r = await client.get("https://httpbin.org/ip")
                    if r.status_code == 200:
                        proxy.mark_success()
                        proxy.last_checked = time.time()
                        results["healthy"] += 1
                    else:
                        proxy.mark_failure()
                        results["failed"] += 1
            except Exception:
                proxy.mark_failure()
                results["failed"] += 1

        await asyncio.gather(*[_check(p) for p in self.proxies], return_exceptions=True)
        logger.info("proxy_health_check_done", **results)
        return results

    def __len__(self) -> int:
        return len(self.proxies)

    def __iter__(self) -> Iterator[Proxy]:
        return iter(self.proxies)


# Global singleton — loaded once from env/config
_proxy_pool: ProxyPool | None = None


def get_proxy_pool() -> ProxyPool:
    global _proxy_pool
    if _proxy_pool is None:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.proxy_list_url:
            # Load from remote list URL (one proxy per line)
            import urllib.request
            try:
                with urllib.request.urlopen(settings.proxy_list_url, timeout=10) as resp:
                    lines = resp.read().decode().splitlines()
                _proxy_pool = ProxyPool.from_list([l for l in lines if l.strip()])
            except Exception as e:
                logger.warning("proxy_list_load_failed", url=settings.proxy_list_url, error=str(e))
                _proxy_pool = ProxyPool()
        else:
            _proxy_pool = ProxyPool()
    return _proxy_pool

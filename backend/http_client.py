# File: app/http_client.py
import aiohttp
import logging

logger = logging.getLogger(__name__)

class HttpClientPool:
    def __init__(self):
        self.session: aiohttp.ClientSession = None

    def start(self):
        """Initializes a shared persistent connection pool with predefined limits."""
        if self.session is None or self.session.closed:
            # TCPConnector limits total open connections to 100 and caches DNS lookups
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300, keepalive_timeout=60)
            self.session = aiohttp.ClientSession(connector=connector)
            logger.info("[HTTP POOL] Shared global ClientSession pool established.")

    async def close(self):
        """Gracefully closes persistent sockets on server teardown."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[HTTP POOL] Shared global ClientSession pool closed cleanly.")

# Global singleton to be imported by all background service modules
http_pool = HttpClientPool()
"""
Enterprise MapmyIndia OAuth2 Manager.
Securely fetches and caches Bearer tokens for dynamic API calls.
Utilizes the centralized persistent HTTP client pool for scalable network throughput.
"""
import logging
import time

# PRODUCTION SCALE FIX: Import the centralized connection pool singleton
from http_client import http_pool
from config import MAPMYINDIA_CLIENT_ID, MAPMYINDIA_CLIENT_SECRET

logger = logging.getLogger(__name__)

class MapmyIndiaAuth:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    async def get_valid_token(self) -> str:
        """Returns a cached token, or fetches a new one if expired using the shared client pool."""
        current_time = time.time()
        
        # If token exists and is valid for at least 5 more minutes, return it
        if self.access_token and current_time < (self.token_expiry - 300):
            return self.access_token

        logger.info("[MapmyIndia] Token expired or missing. Negotiating new OAuth2 Bearer Token...")
        
        auth_url = "https://outpost.mapmyindia.com/api/security/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": MAPMYINDIA_CLIENT_ID,
            "client_secret": MAPMYINDIA_CLIENT_SECRET
        }
        
        # PRODUCTION SCALE FIX: Defensive initialization guard in case the manager 
        # is executed via standalone scripts or tests before the lifespan handler fires.
        if not http_pool.session or http_pool.session.closed:
            http_pool.start()
        
        try:
            # Reuses an existing open, pre-warmed TCP socket from the global connection pool
            async with http_pool.session.post(auth_url, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    # Token usually expires in 86399 seconds (24 hours)
                    expires_in = data.get("expires_in", 86399) 
                    self.token_expiry = current_time + expires_in
                    logger.info("[MapmyIndia] Enterprise Auth successful. Token cached.")
                    return self.access_token
                else:
                    error_text = await response.text()
                    logger.error(f"[MapmyIndia] Auth Failed (Status {response.status}): {error_text}")
                    raise RuntimeError("Failed to authenticate with MapmyIndia Enterprise API.")
        except Exception as e:
            logger.error(f"[MapmyIndia] Network error during authentication workflow: {e}")
            raise

# Global singleton instance
mapmyindia_auth = MapmyIndiaAuth()
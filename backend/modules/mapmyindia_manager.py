"""
Enterprise MapmyIndia OAuth2 Manager.
Securely fetches and caches Bearer tokens for dynamic API calls.
"""
import logging
import time
import aiohttp
from config import MAPMYINDIA_CLIENT_ID, MAPMYINDIA_CLIENT_SECRET

logger = logging.getLogger(__name__)

class MapmyIndiaAuth:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    async def get_valid_token(self) -> str:
        """Returns a cached token, or fetches a new one if expired."""
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
        
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, data=payload) as response:
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

# Global singleton instance
mapmyindia_auth = MapmyIndiaAuth()
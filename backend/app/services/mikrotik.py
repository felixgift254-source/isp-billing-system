import logging
import httpx
from cryptography.fernet import Fernet
from app.config import settings
from app.models import Router

logger = logging.getLogger(__name__)

class MikroTikService:
    """Async client for MikroTik RouterOS v7 REST API."""
    
    def __init__(self, router: Router):
        self.router = router
        scheme = "https" if router.use_ssl else "http"
        self.base_url = f"{scheme}://{router.ip_address}:{router.api_port}"
        
        fernet = Fernet(settings.FERNET_KEY)
        password = fernet.decrypt(router.api_password.encode()).decode()
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(router.api_username, password),
            verify=False,
            timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0)
        )
        self.router_info = f"Router {self.router.name} ({self.router.ip_address})"
        
    async def get_secrets(self) -> list[dict]:
        try:
            response = await self.client.get("/rest/ppp/secret")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error getting secrets: {e}")
            raise

    async def find_secret_by_name(self, username: str) -> dict | None:
        try:
            response = await self.client.get(f"/rest/ppp/secret?name={username}")
            response.raise_for_status()
            data = response.json()
            return data[0] if data and isinstance(data, list) else None
        except Exception as e:
            logger.error(f"[{self.router_info}] Error finding secret {username}: {e}")
            return None

    async def create_secret(self, username: str, password: str, profile: str, comment: str = '') -> dict:
        try:
            payload = {
                "name": username,
                "password": password,
                "profile": profile,
                "service": "pppoe",
                "comment": comment
            }
            response = await self.client.put("/rest/ppp/secret", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error creating secret {username}: {e}")
            raise

    async def update_secret(self, secret_id: str, **fields) -> dict:
        try:
            response = await self.client.patch(f"/rest/ppp/secret/{secret_id}", json=fields)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error updating secret {secret_id}: {e}")
            raise

    async def delete_secret(self, secret_id: str) -> None:
        try:
            response = await self.client.delete(f"/rest/ppp/secret/{secret_id}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error deleting secret {secret_id}: {e}")
            raise

    async def get_profiles(self) -> list[dict]:
        try:
            response = await self.client.get("/rest/ppp/profile")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error getting profiles: {e}")
            raise

    async def create_profile(self, name: str, rate_limit: str, **kwargs) -> dict:
        try:
            payload = {"name": name, "rate-limit": rate_limit, **kwargs}
            response = await self.client.put("/rest/ppp/profile", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error creating profile {name}: {e}")
            raise

    async def get_active_connections(self) -> list[dict]:
        try:
            response = await self.client.get("/rest/ppp/active")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error getting active connections: {e}")
            raise

    async def find_active_by_name(self, username: str) -> dict | None:
        try:
            response = await self.client.get(f"/rest/ppp/active?name={username}")
            response.raise_for_status()
            data = response.json()
            return data[0] if data and isinstance(data, list) else None
        except Exception as e:
            logger.error(f"[{self.router_info}] Error finding active connection for {username}: {e}")
            return None

    async def disconnect_user(self, active_id: str) -> None:
        try:
            response = await self.client.delete(f"/rest/ppp/active/{active_id}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[{self.router_info}] Error disconnecting active {active_id}: {e}")
            raise

    async def suspend_user(self, secret_id: str, username: str) -> None:
        try:
            await self.update_secret(secret_id, profile="suspended")
            active_conn = await self.find_active_by_name(username)
            if active_conn and ".id" in active_conn:
                await self.disconnect_user(active_conn[".id"])
        except Exception as e:
            logger.error(f"[{self.router_info}] Error suspending user {username}: {e}")
            raise

    async def reactivate_user(self, secret_id: str, username: str, profile_name: str) -> None:
        try:
            await self.update_secret(secret_id, profile=profile_name, disabled="false")
            active_conn = await self.find_active_by_name(username)
            if active_conn and ".id" in active_conn:
                await self.disconnect_user(active_conn[".id"])
        except Exception as e:
            logger.error(f"[{self.router_info}] Error reactivating user {username}: {e}")
            raise

    async def ensure_suspended_profile(self) -> None:
        try:
            profiles = await self.get_profiles()
            if not any(p.get("name") == "suspended" for p in profiles):
                await self.create_profile("suspended", "128k/128k", **{"only-one": "yes"})
        except Exception as e:
            logger.error(f"[{self.router_info}] Error ensuring suspended profile: {e}")
            raise

    async def check_connectivity(self) -> bool:
        try:
            response = await self.client.get("/rest/system/resource")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"[{self.router_info}] Connectivity check failed: {e}")
            return False

    async def close(self):
        await self.client.aclose()

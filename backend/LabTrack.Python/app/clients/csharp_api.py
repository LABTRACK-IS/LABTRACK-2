import httpx
from typing import Any, Optional

class CSharpApiClient:
    """HTTP client wrapper for the LabTrack C# backend."""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        timeout: float = 30.0,
        headers: Optional[dict[str, str]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        self._external_client = client

    def _normalize_path(self, path: str) -> str:
        p = path.lstrip("/")
        if p.startswith("api/repairs"):
            p = p.replace("api/repairs", "api/v1/repair-tickets", 1)
        elif p.startswith("api/assets"):
            p = p.replace("api/assets", "api/v1/assets", 1)
        elif p.startswith("api/") and not p.startswith("api/v1/"):
            p = "api/v1/" + p[4:]
        return f"{self.base_url}/{p}"

    def _unwrap(self, payload: Any) -> Any:
        if isinstance(payload, dict) and "data" in payload and "success" in payload:
            return payload["data"]
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = self._normalize_path(path)
        if self._external_client is not None:
            response = await self._external_client.request(method, url, params=params, json=json, headers=self.headers)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return self._unwrap(response.json())
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.request(method, url, params=params, json=json)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return self._unwrap(response.json())

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Optional[dict[str, Any]] = None, json_data: Optional[dict[str, Any]] = None) -> Any:
        return await self._request("POST", path, json=json if json is not None else json_data)

    async def put(self, path: str, json: Optional[dict[str, Any]] = None, json_data: Optional[dict[str, Any]] = None) -> Any:
        return await self._request("PUT", path, json=json if json is not None else json_data)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

"""Asana API client with auth, pagination, and rate-limit retry."""

import time

import httpx

BASE_URL = "https://app.asana.com/api/1.0"
MAX_RETRIES = 3


class AsanaAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AsanaAuthError(AsanaAPIError):
    pass


class AsanaNotFoundError(AsanaAPIError):
    pass


class AsanaClient:
    def __init__(self, token: str):
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        for attempt in range(MAX_RETRIES):
            resp = self._client.request(method, path, **kwargs)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                if attempt < MAX_RETRIES - 1:
                    time.sleep(retry_after)
                    continue
                raise AsanaAPIError("Rate limited — retries exhausted", 429)

            if resp.status_code == 401:
                raise AsanaAuthError("Not authorized — check your token")
            if resp.status_code == 403:
                raise AsanaAuthError("Forbidden — insufficient permissions")
            if resp.status_code == 404:
                raise AsanaNotFoundError("Resource not found")

            if resp.status_code >= 400:
                body = resp.json() if resp.content else {}
                errors = body.get("errors", [])
                msg = errors[0]["message"] if errors else resp.text
                raise AsanaAPIError(msg, resp.status_code)

            if resp.status_code == 204 or not resp.content:
                return {}

            body = resp.json()
            return body.get("data", body)

        raise AsanaAPIError("Request failed after retries")

    def get(self, path: str, params: dict | None = None) -> dict | list:
        return self._request("GET", path, params=params)

    def get_all(
        self,
        path: str,
        params: dict | None = None,
        *,
        no_paginate: bool = False,
    ) -> list:
        """GET with automatic pagination. Returns all results."""
        params = dict(params or {})
        if no_paginate:
            params.setdefault("limit", 100)
            result = self._request("GET", path, params=params)
            return result if isinstance(result, list) else [result]

        params.setdefault("limit", 100)
        results: list = []
        while True:
            resp = self._client.request("GET", path, params=params)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                time.sleep(retry_after)
                continue

            if resp.status_code >= 400:
                # Delegate error handling to _request
                return self._request("GET", path, params=params)

            body = resp.json()
            data = body.get("data", [])
            results.extend(data)

            next_page = body.get("next_page")
            if not next_page or not next_page.get("offset"):
                break
            params["offset"] = next_page["offset"]

        return results

    def post(self, path: str, data: dict | None = None) -> dict:
        return self._request("POST", path, json={"data": data or {}})

    def put(self, path: str, data: dict | None = None) -> dict:
        return self._request("PUT", path, json={"data": data or {}})

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def close(self) -> None:
        self._client.close()

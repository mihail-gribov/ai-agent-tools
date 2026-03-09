"""ClickUp API client with auth, pagination, and rate-limit retry."""

import time

import httpx

BASE_URL = "https://api.clickup.com/api/v2"
MAX_RETRIES = 3


class ClickUpAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ClickUpAuthError(ClickUpAPIError):
    pass


class ClickUpNotFoundError(ClickUpAPIError):
    pass


class ClickUpClient:
    def __init__(self, token: str):
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        for attempt in range(MAX_RETRIES):
            resp = self._client.request(method, path, **kwargs)

            if resp.status_code == 429:
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset and attempt < MAX_RETRIES - 1:
                    wait = max(int(reset) - int(time.time()), 1)
                    time.sleep(wait)
                    continue
                raise ClickUpAPIError("Rate limited — retries exhausted", 429)

            if resp.status_code == 401:
                raise ClickUpAuthError("Not authorized — check your token")
            if resp.status_code == 403:
                raise ClickUpAuthError("Forbidden — insufficient permissions")
            if resp.status_code == 404:
                raise ClickUpNotFoundError("Resource not found")

            if resp.status_code >= 400:
                body = resp.json() if resp.content else {}
                msg = body.get("err", resp.text)
                raise ClickUpAPIError(msg, resp.status_code)

            if resp.status_code == 204 or not resp.content:
                return {}

            return resp.json()

        raise ClickUpAPIError("Request failed after retries")

    def get(self, path: str, params: dict | None = None) -> dict | list:
        return self._request("GET", path, params=params)

    def get_all(
        self,
        path: str,
        params: dict | None = None,
        *,
        no_paginate: bool = False,
        key: str = "tasks",
        page_size: int = 100,
    ) -> list:
        """GET with page-based pagination. Returns all results.

        Args:
            key: JSON key containing the array (e.g. "tasks", "spaces").
            page_size: Expected max items per page (100 for tasks).
        """
        params = dict(params or {})

        if no_paginate:
            result = self._request("GET", path, params=params)
            if isinstance(result, dict):
                data = result.get(key, result)
            else:
                data = result
            return data if isinstance(data, list) else [data]

        results: list = []
        page = 0
        while True:
            params["page"] = page
            resp = self._client.request("GET", path, params=params)

            if resp.status_code == 429:
                reset = resp.headers.get("X-RateLimit-Reset")
                wait = max(int(reset) - int(time.time()), 1) if reset else 5
                time.sleep(wait)
                continue

            if resp.status_code >= 400:
                # Delegate error handling to _request
                return self._request("GET", path, params=params)

            body = resp.json()
            data = body.get(key, []) if isinstance(body, dict) else body
            if not isinstance(data, list):
                data = [data] if data else []
            results.extend(data)

            if len(data) < page_size:
                break
            page += 1

        return results

    def post(self, path: str, data: dict | None = None) -> dict:
        return self._request("POST", path, json=data or {})

    def put(self, path: str, data: dict | None = None) -> dict:
        return self._request("PUT", path, json=data or {})

    def delete(self, path: str, data: dict | None = None) -> dict:
        kwargs: dict = {}
        if data:
            kwargs["json"] = data
        return self._request("DELETE", path, **kwargs)

    def close(self) -> None:
        self._client.close()

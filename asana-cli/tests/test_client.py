import httpx
import pytest
import respx

from asana_cli.client import (
    AsanaAPIError,
    AsanaAuthError,
    AsanaClient,
    AsanaNotFoundError,
)


def test_get(mock_api, client):
    mock_api.get("/tasks/123").mock(
        return_value=httpx.Response(200, json={"data": {"gid": "123", "name": "Test"}})
    )
    result = client.get("/tasks/123")
    assert result == {"gid": "123", "name": "Test"}


def test_get_all_single_page(mock_api, client):
    mock_api.get("/tasks").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"gid": "1"}, {"gid": "2"}],
                "next_page": None,
            },
        )
    )
    result = client.get_all("/tasks", {"project": "456"})
    assert result == [{"gid": "1"}, {"gid": "2"}]


def test_get_all_pagination(mock_api, client):
    mock_api.get("/tasks").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"gid": "1"}],
                    "next_page": {"offset": "abc", "uri": "..."},
                },
            ),
            httpx.Response(
                200,
                json={
                    "data": [{"gid": "2"}],
                    "next_page": None,
                },
            ),
        ]
    )
    result = client.get_all("/tasks")
    assert result == [{"gid": "1"}, {"gid": "2"}]


def test_post(mock_api, client):
    mock_api.post("/tasks").mock(
        return_value=httpx.Response(
            201, json={"data": {"gid": "999", "name": "New Task"}}
        )
    )
    result = client.post("/tasks", {"name": "New Task"})
    assert result == {"gid": "999", "name": "New Task"}


def test_put(mock_api, client):
    mock_api.put("/tasks/123").mock(
        return_value=httpx.Response(
            200, json={"data": {"gid": "123", "completed": True}}
        )
    )
    result = client.put("/tasks/123", {"completed": True})
    assert result == {"gid": "123", "completed": True}


def test_delete(mock_api, client):
    mock_api.delete("/tasks/123").mock(
        return_value=httpx.Response(200, json={"data": {}})
    )
    result = client.delete("/tasks/123")
    assert result == {}


def test_auth_error(mock_api, client):
    mock_api.get("/tasks/123").mock(
        return_value=httpx.Response(401, json={"errors": [{"message": "Unauthorized"}]})
    )
    with pytest.raises(AsanaAuthError, match="Not authorized"):
        client.get("/tasks/123")


def test_not_found_error(mock_api, client):
    mock_api.get("/tasks/999").mock(
        return_value=httpx.Response(404, json={"errors": [{"message": "Not found"}]})
    )
    with pytest.raises(AsanaNotFoundError, match="not found"):
        client.get("/tasks/999")


def test_generic_api_error(mock_api, client):
    mock_api.get("/tasks/123").mock(
        return_value=httpx.Response(
            400, json={"errors": [{"message": "Invalid request"}]}
        )
    )
    with pytest.raises(AsanaAPIError, match="Invalid request"):
        client.get("/tasks/123")


def test_rate_limit_retry(mock_api, client):
    mock_api.get("/tasks/123").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"data": {"gid": "123"}}),
        ]
    )
    result = client.get("/tasks/123")
    assert result == {"gid": "123"}


def test_auth_header(mock_api, client):
    route = mock_api.get("/workspaces").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    client.get("/workspaces")
    assert route.calls[0].request.headers["authorization"] == "Bearer test-token"

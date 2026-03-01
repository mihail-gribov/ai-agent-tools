import pytest
import respx

from asana_cli.client import AsanaClient


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://app.asana.com/api/1.0") as api:
        yield api


@pytest.fixture
def client():
    return AsanaClient("test-token")

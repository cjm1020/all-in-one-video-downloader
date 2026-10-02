import socket
import sys

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Config


@pytest.fixture
def client(tmp_path, monkeypatch):
    isolated = Config(data_dir=tmp_path)
    for name, module in list(sys.modules.items()):
        if name.startswith("app.") and hasattr(module, "config"):
            monkeypatch.setattr(module, "config", isolated)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    with TestClient(main.app) as instance:
        yield instance


@pytest.fixture
def task(client):
    response = client.post("/api/tasks", json={"urls": ["https://example.com/video.mp4"]})
    assert response.status_code == 201
    return response.json()["added"][0]

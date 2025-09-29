import pytest
from fastapi.testclient import TestClient

from heraclis.api import app

client = TestClient(app)


def test_empty_db():
    response = client.get("/exercises")
    assert response.status_code == 404
    assert response.json() == {"detail": "No exercises found"}


if __name__ == "__main__":
    pytest.main(["-vv"])

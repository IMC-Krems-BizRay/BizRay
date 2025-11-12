from fastapi.testclient import TestClient
from backend_api.main import app

client = TestClient(app)

def test_confirm_connection():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Status" in data
    assert data["Status"] == "Active"


def test_search_by_name():
    company_name = "signa"
    response = client.get(f"/search/{company_name}?page=1")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], dict)
    result = data["result"]
    assert "total_pages" in result
    assert isinstance(result["total_pages"], int)
    assert "companies" in result
    assert isinstance(result["companies"], list)

def test_search_by_fnr():
    test_fnr = "583360h"
    response = client.get(f"/search/{test_fnr}?page=1")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], dict)
    result = data["result"]
    assert "total_pages" in result
    assert isinstance(result["total_pages"], int)
    assert "companies" in result
    assert isinstance(result["companies"], list)
    assert len(result["companies"]) == 1
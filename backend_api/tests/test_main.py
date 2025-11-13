from fastapi.testclient import TestClient
from backend_api.main import app
from config import TEST_COMPANY_NAME, TEST_COMPANY_FNR

client = TestClient(app)

def test_confirm_connection():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Status" in data
    assert data["Status"] == "Active"


def test_search_by_name():
    response = client.get(f"/search/{TEST_COMPANY_NAME}?page=1")
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
    response = client.get(f"/search/{TEST_COMPANY_FNR}?page=1")
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
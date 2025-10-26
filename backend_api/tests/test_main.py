from fastapi.testclient import TestClient
from backend_api.main import app

client = TestClient(app)

def test_confirm_connection():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Status" in data
    assert data["Status"] == "Active"

def test_search_no_headers():
    headers = {}
    # Use a test company name that exists in your SOAP API
    response = client.get("/search/signa", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "Results" in data
    assert isinstance(data["Results"], list)

def test_search_by_name():
    headers = {
        "name_or_fnr": "name",
        "exact_search": "1"
    }
    # Use a test company name that exists in your SOAP API
    company_name = "signa"
    response = client.get(f"/search/{company_name}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "Results" in data
    assert isinstance(data["Results"], list)

def test_search_by_fnr():
    headers = {
        "name_or_fnr": "fnr"
    }

    test_fnr = "583360h"
    response = client.get(f"/search/{test_fnr}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "Results" in data
    assert isinstance(data["Results"], dict)

def test_search_invalid_fnr():
    headers = {
        "name_or_fnr": "fnr"
    }

    test_fnr = "signa"
    response = client.get(f"/search/{test_fnr}", headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Firmenbuchnummer ist ungültig! (max. 6 Ziffern plus Prüfzeichen) "


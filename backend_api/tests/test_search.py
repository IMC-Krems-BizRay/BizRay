from backend_api.search import search_by_name, search_by_fnr
from config import TEST_COMPANY_NAME, TEST_COMPANY_FNR


def test_search_by_name_output():
    result = search_by_name(TEST_COMPANY_NAME)
    assert isinstance(result, list)
    unit = result[0]
    assert isinstance(unit, dict)

    assert "fnr" in unit
    assert "status" in unit
    assert unit["status"] == "active" or unit["status"] == "inactive"

    assert "name" in unit
    assert isinstance(unit["name"], list)
    assert isinstance(unit["name"][0], str)

    assert "location" in unit

    assert "legal_form" in unit
    assert "code" in unit["legal_form"]
    assert "text" in unit["legal_form"]

    assert "legal_status" in unit
    assert unit["legal_status"] == "active" or unit["legal_status"] == "inactive"

    assert "responsible_court" in unit
    assert "code" in unit["responsible_court"]
    assert "text" in unit["responsible_court"]

def test_search_by_fnr_output():
    company = search_by_fnr(TEST_COMPANY_FNR)
    assert isinstance(company, dict)

    assert "fnr" in company
    assert "location" in company
    assert "status" in company
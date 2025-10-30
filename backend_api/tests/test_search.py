from backend_api.search import search_by_name, search_by_fnr

def test_search_by_name_output():
    result = search_by_name("signa", True)
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
    company = search_by_fnr("583360h")
    assert isinstance(company, dict)

    assert "fnr" in company
    assert "location" in company

    assert "legal_form" in company
    if company["legal_form"] is not None:
        assert "code" in company["legal_form"]
        assert "text" in company["legal_form"]

    assert "legal_status" in company
    assert company["legal_status"] == "active" or company["legal_status"] == "inactive"
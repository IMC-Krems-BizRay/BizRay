from backend_api.company_information import company_info
from config import TEST_COMPANY_FNR

def test_company_info():
    result = company_info(TEST_COMPANY_FNR)
    assert isinstance(result, dict)

    assert "basic_info" in result
    basic_info = result["basic_info"]
    assert isinstance(basic_info, dict)
    assert "company_name" in basic_info
    assert "legal_form" in basic_info
    assert "company_number" in basic_info
    assert "european_id" in basic_info

    assert "location" in result
    assert isinstance(result["location"], dict)

    assert "management" in result
    assert isinstance(result["management"], list)

    assert "financial" in result
    assert isinstance(result["financial"], dict)

    assert "history" in result
    assert isinstance(result["history"], list)
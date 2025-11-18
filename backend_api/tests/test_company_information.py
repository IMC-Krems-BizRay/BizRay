from backend_api.company_information import company_info
from backend_api.search import search_by_name
from backend_api.tests.config import TEST_COMPANY_NAME
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

# very long but gives a lot of test cases
def test_bulk_company_info():
    companies = search_by_name(TEST_COMPANY_NAME)

    errors = ""
    for company in companies:
        fnr = company["fnr"]
        try:
            company_info(fnr)
        except Exception as e:
            errors += f"{fnr}: {e}\n=============================\n";

    print(errors)
    assert errors == ""
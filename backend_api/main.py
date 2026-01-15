import base64
import re
from fastapi import FastAPI, HTTPException
from zeep.exceptions import Fault

from .search import search
from .company_information import get_document_data
from .NETWORK import GET_COMPANY, GET_NEIGHBOURS, GET_ADJ


# Boot: uvicorn backend_api.main:app --reload
app = FastAPI()


@app.get("/")
def confirm_connection():
    return {
        "Status": "Active",
        "Available endpoints": [
            "/search/{term}",
            "/view/{company_fnr}",
            "/node/{node_id}?label=Label",
        ],
    }


@app.get("/search/{term}")
def search_companies(term: str, page: int):
    try:
        result = search(term, page)
        return {"result": result}
    except Fault as e:
        raise HTTPException(status_code=400, detail=e.message)


def format_company_fnr(fnr):
    fnr = fnr.strip()

    match = re.fullmatch(r"(\d{1,6})(\w)", fnr)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    return fnr


@app.get("/view/{company_fnr}")
def view_company(company_fnr: str):
    company_fnr = format_company_fnr(company_fnr)

    company = GET_COMPANY(company_fnr)
    """
    companies = GET_ADJ(company_fnr)
    companies_masseverwalter = 0
    companies_high_risk = 0
    companies_medium_risk = 0
    companies_low_risk = 0
    print(len(companies))
    for info in (GET_COMPANY(company["other"]["company_id"]) for company in companies):
        print(f"looking at company {info["basic_info"]["company_number"]}")
        if info["risk_indicators"]["has_masseverwalter"]:
            companies_masseverwalter += 1
        match info["risk_indicators"]["risk_level"]:
            case "H":
                companies_high_risk += 1
            case "M":
                companies_medium_risk += 1
            case "L":
                companies_low_risk += 1

    company["network"] = {
        "connected": len(companies),
        "masseverwalter": companies_masseverwalter,
        "high_risk": companies_high_risk,
        "medium_risk": companies_medium_risk,
        "low_risk": companies_low_risk,
    }
    """

    return {"result": company}


@app.get("/node/{node_id}")
def get_node_neighbours(node_id: str, label: str):
    neighbours = GET_NEIGHBOURS(node_id, label)
    return {"neighbours": neighbours}


@app.get("/document/{document_id}")
def get_document(document_id: str):
    pdf_bytes = get_document_data(document_id)
    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    return {"result": encoded}


@app.post("/enrich/neighbours/{company_id}")
def enrich_neighbours(company_id: str):
    neighbours = GET_ADJ(company_id)

    enriched = 0
    failed = 0

    # include center + neighbours
    targets = [company_id] + neighbours

    for cid in targets:
        try:
            view_company(cid)
            enriched += 1
        except Exception as e:
            failed += 1

    return {"center": company_id, "enriched": enriched, "failed": failed}

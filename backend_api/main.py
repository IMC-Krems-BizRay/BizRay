import base64
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


@app.get("/view/{company_fnr}")
def view_company(company_fnr: str):
    company = GET_COMPANY(company_fnr)

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


@app.get("/get_adj/{fnr}")
def adjcom(fnr: str):
    a = GET_ADJ(fnr)
    # print(a)
    return {"companies": a}


@app.get("/repopulate")
def repop():
    for i in company_ids:
        view_company(i)


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


# to repopulate
company_ids = [
    "435836 k",
    "570748 k",
    "284723 k",
    "318490 v",
    "331076 b",
    "583360 h",
    "79297 p",
    "35684 b",
    "631134 p",
    "211940 b",
    "145474 h",
    "452749 h",
    "274088 x",
    "615869 s",
    "444429 y",
    "667306 h",
    "33158 m",
    "56247 t",
    "244788 h",
    "245251 p",
    "485948 f",
    "581091 x",
    "441584 p",
    "486131 z",
    "297115 i",
    "291020 x",
    "406164 a",
    "447820 i",
    "426513 a",
    "547370 g",
    "278713 y",
    "444428 x",
    "278717 d",
    "504855 i",
    "562240 z",
    "566577 b",
    "359363 a",
    "628511 g",
    "333252 b",
    "480722 w",
    "574012 k",
    "242833 h",
    "509899 b",
    "509901 f",
    "516642 v",
    "542081 d",
    "542720 v",
    "574011 i",
    "360689 a",
    "388427 t",
    "353543 t",
    "574279 d",
    "280545 t",
    "279489 p",
    "280833 s",
    "445407 k",
    "404487 i",
    "162991 v",
    "164602 m",
    "257415 b",
    "340535 m",
    "180213 w",
    "627820 s",
    "414769 f",
    "647957 d",
    "434465 w",
    "449074 d",
]

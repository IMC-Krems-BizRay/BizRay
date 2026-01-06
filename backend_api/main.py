import base64
from fastapi import FastAPI, HTTPException
from zeep.exceptions import Fault
from fastapi.encoders import jsonable_encoder
import datetime
import json

from .search import search
from .company_information import company_info, get_document_data
from .NETWORK import CREATE_COMPANY, SEARCH_COMPANY, GET_NEIGHBOURS


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
    fromdb = SEARCH_COMPANY(company_fnr)
    if fromdb:
        if fromdb['updated_at'] > datetime.datetime.now().timestamp() - 30 * 24 * 60 * 60: #data must be newer than one month
            print("got result from db")
            return {"result": fromdb}

    data = company_info(company_fnr)
    CREATE_COMPANY(jsonable_encoder(data))
    print('got result from api')
    print(data)
    return {"result": data}


@app.get("/node/{node_id}")
def get_node_neighbours(node_id: str, label: str):
    neighbours = GET_NEIGHBOURS(node_id, label)
    return {"neighbours": neighbours}


@app.get("/document/{document_id}")
def get_document(document_id: str):
    pdf_bytes = get_document_data(document_id)
    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    return {"result": encoded}


@app.get("/repopulate")
def repop():
    for i in company_ids:
        view_company(i)


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

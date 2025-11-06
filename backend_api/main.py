from fastapi import FastAPI, Request, HTTPException
from zeep.exceptions import Fault

from .search import search_by_name, search_by_fnr
from .company_information import company_info, get_document_data

# Boot: uvicorn backend_api.main:app --reload
app = FastAPI()

def get_header_or_default(request: Request, header: str, default: str) -> str:
    header_value = request.headers.get(header)
    if not header_value:
        return default
    return header_value

@app.get('/')
def confirm_connection():
    return {"Status": "Active", "Available endpoints": ['/search/{company_name}', '/view/{company_fnr}']}

@app.get('/search/{company_name}')
def search_companies(company_name: str, request: Request):
    # if we have exact_search present only in 'name' search, perhaps it's possible
    # to omit 'name_or_fnr' header and distinct the search only based on exact_search?

    # Possible values: 'name' or 'fnr'
    name_or_fnr = get_header_or_default(request, "name_or_fnr", "name")

    try:
        if name_or_fnr == "name":
            # Possible values: '0' or '1'
            exact_search = get_header_or_default(request, "exact_search", "1") == "1"

            result = search_by_name(company_name, exact_search)
            return {"result": result}
        elif name_or_fnr == "fnr":
            result = search_by_fnr(company_name)
            return {"result": result}
        else:
            raise HTTPException(status_code=400, detail="Invalid 'name_or_fnr' header value.")
    except Fault as e:
        raise HTTPException(status_code=400, detail=e.message)

@app.get('/view/{company_fnr}')
def view_company(company_fnr: str, request: Request):
    return {"result": company_info(company_fnr)}


@app.get('/docs/{fnr}') #for testing, don't use on frontend
def docs(fnr):
    return {"res": get_document_data(fnr)}

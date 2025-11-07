from fastapi import FastAPI, HTTPException
from zeep.exceptions import Fault

from .search import search
from .company_information import company_info, get_document_data

# Boot: uvicorn backend_api.main:app --reload
app = FastAPI()
@app.get('/')
def confirm_connection():
    return {"Status": "Active", "Available endpoints": ['/search/{term}', '/view/{company_fnr}']}

@app.get('/search/{term}')
def search_companies(term: str):
    try:
        result = search(term)
        return {"result": result}
    except Fault as e:
        raise HTTPException(status_code=400, detail=e.message)

@app.get('/view/{company_fnr}')
def view_company(company_fnr: str):
    return {"result": company_info(company_fnr)}


@app.get('/docs/{fnr}') #for testing, don't use on frontend
def docs(fnr):
    return {"res": get_document_data(fnr)}

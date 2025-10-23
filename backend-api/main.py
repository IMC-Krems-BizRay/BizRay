from fastapi import FastAPI, Request

from search import search_by_name


app = FastAPI()


@app.get('/')
def confirm_connection():
    return {"Status": "Active", "Available endpoints": ['/search/{company_name}']}

@app.get("/search/{company_name}") #todo: !!!IMPORTANT ADD SEARCH BY ID!!!
def search_companies(company_name: str, req: Request):
    headers = req.headers
    exact_search = headers.get('exact_search')
    name_or_fnr = headers.get('name_or_fnr')

    if name_or_fnr == 'name':
        r = search_by_name(company_name, exact_search)
        return {"Results": r}
    else:
        #fnr search
        return



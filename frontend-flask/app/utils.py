import base64
from flask import Response
import requests


def response_to_data(response: Response):
    payload = response.json()

    if payload is None:
        raise Exception(f"Incorrect payload: {payload}")
    if "result" not in payload:
        raise Exception(f"Incorrect payload: {payload}")

    return payload["result"]


def fetch_companies(term: str, page: int):
    # Backend expects /search/{query} and headers, not query params
    url = f"http://127.0.0.1:8000/search/{term}"
    params = {"page": page}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []  # no matches route or not found
        resp.raise_for_status()

        data = response_to_data(resp)

        return data
    except Exception as e:
        print(f"API error: {e}")
        return []


def get_company_data(fnr):
    res = requests.get(f"http://127.0.0.1:8000/view/{fnr}")
    if res.status_code != 200:
        raise Exception(f"Could not get company '{fnr}' data")
    res.raise_for_status()
    return response_to_data(res)


def get_node_neighbours(key: str, label: str = "Company"):
    """
    Call the FastAPI /node endpoint and return its raw JSON.
    This endpoint returns {"neighbours": [...]} – no 'result' wrapper.
    """
    url = f"http://127.0.0.1:8000/node/{key}"
    params = {"label": label}
    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"API error (get_node_neighbours): {e}")
        # Frontend expects at least this shape
        return {"neighbours": []}


def fetch_original_pdf(doc_id: str):
    """
    Fetches the document from the backend.
    Since the backend returns Base64 encoded JSON, we must decode it here.
    """
    url = f"http://127.0.0.1:8000/document/{doc_id}"
    
    try:
        # Request the data
        res = requests.get(url, timeout=45)
        
        if res.status_code != 200:
            print(f"Backend error {res.status_code}")
            return None
        
        # 1. Parse JSON response
        data = res.json()
        
        # 2. Extract the Base64 string (Backend sends {"result": "..."})
        if "result" not in data:
            print("Payload missing 'result' key")
            return None
            
        b64_string = data["result"]
        
        # 3. Decode back to raw bytes
        return base64.b64decode(b64_string)

    except Exception as e:
        print(f"Error decoding PDF: {e}")
        return None
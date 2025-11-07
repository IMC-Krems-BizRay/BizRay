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


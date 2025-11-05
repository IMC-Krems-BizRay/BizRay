from flask import Response
import requests
import re


def response_to_data(response: Response):
    payload = response.json()

    if payload is None:
        raise Exception(f"Incorrect payload: {payload}")
    if "result" not in payload:
        raise Exception(f"Incorrect payload: {payload}")

    return payload["result"]

def detect_search_mode(input_str: str) -> str:
    s = input_str.strip()
    return "fnr" if re.fullmatch(r"\d{6,7}[a-zA-Z]", s) else "name"

def fetch_companies(query: str, exact: bool = True, mode: str = "name"):
    # Backend expects /search/{query} and headers, not query params
    url = f"http://127.0.0.1:8000/search/{query}"
    headers = {
        "exact_search": str(exact).lower(), # "true" or "false"
        "name_or_fnr": mode,                # "name" or "fnr"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return []  # no matches route or not found
        resp.raise_for_status()

        data = response_to_data(resp)

        # Wrap a single result in a list (fnr search case)
        if isinstance(data, dict):
            return [data]

        return data
    except Exception as e:
        print(f"API error: {e}")
        return []


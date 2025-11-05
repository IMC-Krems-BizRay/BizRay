# routes.py
from flask import Blueprint, render_template, request
import requests
import re
import math

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html", page = 'index')

@main.route("/login")
def login():
    return render_template("login.html", page = 'login')


def detect_search_mode(input_str: str) -> str:
    s = input_str.strip()
    return "fnr" if re.fullmatch(r"\d{6,7}[a-zA-Z]", s) else "name"

def _normalize_companies(payload):
    """Return a list of company dicts from various shapes."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        # common keys your backend might use
        for key in ("Results", "results", "data", "items", "companies"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        # mapping id -> object
        if payload and all(isinstance(v, dict) for v in payload.values()):
            return list(payload.values())
    # single object fallback
    return [payload]

def fetch_companies(query: str, exact: bool = True, mode: str = "name"):
    # Backend expects /search/{query} and headers, not query params
    url = f"http://127.0.0.1:8000/search/{query}"
    headers = {
        "exact_search": str(exact).lower(),  # "true"/"false"
        "name_or_fnr": mode,                 # "name" or "fnr"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return []  # no matches route or not found
        resp.raise_for_status()
        data = resp.json()
        return _normalize_companies(data)  # <- keep the normalizer from earlier
    except Exception as e:
        print(f"API error: {e}")
        return []


@main.route("/search_results")
def search_results():
    query = request.args.get("query", "", type=str)
    mode = detect_search_mode(query)
    companies = fetch_companies(query, exact=False, mode=mode)

    # pagination
    per_page = 15
    total = len(companies)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(request.args.get("page", 1, type=int), total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    companies_paginated = companies[start:end]

    return render_template(
        "search_results.html",
        companies=companies_paginated,
        page=page,
        total_pages=total_pages,
        title="Search Results",
        query=query,
        total=total,
        per_page=per_page,
        show_back_button=True 
    )

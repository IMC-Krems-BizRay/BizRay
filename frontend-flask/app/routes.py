from flask import Blueprint, render_template, request
from .utils import fetch_companies, detect_search_mode
import math

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html", page = 'index')

@main.route("/login")
def login():
    return render_template("login.html", page = 'login')


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

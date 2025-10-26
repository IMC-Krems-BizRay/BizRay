from flask import Blueprint, render_template
from flask import request
import requests



main = Blueprint('main', __name__)

@main.route("/")
def index():
    return render_template("index.html")


def fetch_companies(query, exact=True, mode="name"):
    url = f"http://127.0.0.1:8000/search/{query}"
    headers = {
        "exact_search": str(exact).lower(),  # Convert to "true"/"false"
        "name_or_fnr": mode
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("Results", [])  # Return only the list
        else:
            return []
    except Exception as e:
        print(f"API error: {e}")
        return []


@main.route("/search_results")
def search_results():
    query = request.args.get("query", "")  # Get the query from the form
    companies = fetch_companies(query, exact=False, mode="name")


    # Pagination setup
    page = request.args.get('page', 1, type=int)  # Get current page from URL
    per_page = 15  # Items per page
    total_pages = (len(companies) + per_page - 1) // per_page  # Total pages

    # Slice the list to get only the companies for this page
    companies_paginated = companies[(page - 1) * per_page: page * per_page]

    return render_template(
        "search_results.html",
        companies=companies_paginated,
        page=page,
        total_pages=total_pages,
        title="Search Results",
        query=query
    )

from flask import Blueprint, render_template
from flask import request

main = Blueprint('main', __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/search_results")
def search_results():
    # Simulated company list (replace with API later)
    companies = [
        {"name": "Red Bull GmbH", "fnr": "56247 t"},
        {"name": "1Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "2Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "3Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "4Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "5Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "6Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "7Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "8Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "9Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "10Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "11Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "12Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "13Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "14Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "15Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "16Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "17Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "18Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "19Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "20Red Bull Studios GmbH", "fnr": "504855 i"},
        {"name": "21Red Bull Studios GmbH", "fnr": "504855 i"}
        # Add more companies here for testing
    ]
    companies2 = []

    # Pagination setup
    page = request.args.get('page', 1, type=int)  # Get current page from URL
    per_page = 10  # Items per page
    total_pages = (len(companies) + per_page - 1) // per_page  # Total pages

    # Slice the list to get only the companies for this page
    companies_paginated = companies[(page - 1) * per_page: page * per_page]

    return render_template(
        "search_results.html",
        companies=companies_paginated,
        page=page,
        total_pages=total_pages,
        title="Search Results"
    )

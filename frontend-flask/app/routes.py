from flask import Blueprint, render_template, request
from .utils import fetch_companies
import math

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html", page = 'index')

@main.route("/login")
def login():
    return render_template("login.html", page = 'login')

@main.route("/register")
def register():
    return render_template("register.html", page="register")


@main.route("/search_results")
def search_results():
    query = request.args.get("query", "", type=str)
    page = request.args.get("page", 1, type=int)
    result = fetch_companies(query, page)

    return render_template(
        "search_results.html",
        companies=result["companies"],
        page=page,
        total_pages=result["total_pages"],
        title="Search Results",
        query=query,
        show_back_button=True 
    )

from .utils import fetch_companies, get_company_data
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from .models import db, User, bcrypt

main = Blueprint("main", __name__)



@main.route("/")
def index():
    return render_template("index.html", page='index', logged_in=session.get("logged_in"))

@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session["logged_in"] = True
            session.permanent = False
            session["user_id"] = user.id
            flash("Login successful!", "success")

            next_url = request.form.get("next") or request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("main.index"))

        flash("Login failed. Check your email and password.", "danger")
        return redirect(url_for("main.login"))

    return render_template("login.html", page="login", logged_in=session.get("logged_in"))


@main.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user_id", None)
    flash("Logout successful.", "info")
    return redirect(url_for("main.index"))

@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("main.register"))

        # Graceful duplicate handling: if user exists, tell them to log in
        existing = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing:
            flash("This user is already registered. Please log in.", "info")
            return redirect(url_for("main.login"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", page="register")


@main.route("/search_results")
def search_results():
    query = request.args.get("query", "", type=str)
    page = request.args.get("page", 1, type=int)

    try:
        result = fetch_companies(query, page)
        print(result)

        # Safely extract values
        companies = result.get("companies", [])
        total_pages = result.get("total_pages", 0)

    except Exception as e:
        print(f"Error while fetching or processing results: {e}")
        # fallback values if something goes wrong
        result = {'total_pages': 1, 'companies': []}


    return render_template(
        "search_results.html",
        companies=result["companies"],
        page=page,
        total_pages=result["total_pages"],
        title="Search Results",
        query=query,
        show_back_button=True
    )



@main.route('/view/<fnr>')
def view_company(fnr):
    # If NOT logged in: render locked view (no sensitive data)
    if not session.get("logged_in"):
        company_stub = {
            "basic_info": {"company_name": "Login required"},
            "location": {"street": "", "house_number": "", "postal_code": "", "city": "", "country": ""},
            "management": [],
            "financial": {"director_name": "", "total_assets": ""},
            "history": []
        }
        return render_template(
            "company_view.html",
            locked=True,
            login_next=request.full_path,   # so login can send them back here
            company=company_stub,           # minimal structure so template doesn't crash
            title="Company view",
            show_back_button=True
        )

    # Logged in: fetch and normalize real data
    result = get_company_data(fnr)

    # normalize to a single dict
    if isinstance(result, list):
        if not result:
            abort(404, description="Company not found")
        company = result[0]
    elif isinstance(result, dict):
        if "Results" in result and isinstance(result["Results"], list):
            if not result["Results"]:
                abort(404, description="Company not found")
            company = result["Results"][0]
        else:
            company = result
    else:
        abort(500, description="Unexpected data shape from get_company_data")

    # normalize address (street sometimes a list)
    loc = company.get("location", {})
    street = loc.get("street")
    if isinstance(street, list):
        loc["street"] = " ".join([s for s in street if s])
    company["location"] = loc

    return render_template(
        "company_view.html",
        locked=False,
        company=company,
        title="Company view",
        show_back_button=True
    )

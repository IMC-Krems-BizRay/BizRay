from .utils import fetch_companies, get_company_data, get_risk_indicators
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
            "location": None,
            "management": [],
            "financial": [],
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
    # result = get_company_data(fnr)

    # This literally cannot happen

    # normalize to a single dict
    # if isinstance(result, list):
    #     if not result:
    #         abort(404, description="Company not found")
    #     company = result[0]
    # elif isinstance(result, dict):
    #     if "Results" in result and isinstance(result["Results"], list):
    #         if not result["Results"]:
    #             abort(404, description="Company not found")
    #         company = result["Results"][0]
    #     else:
    #         company = result
    # else:
    #     abort(500, description="Unexpected data shape from get_company_data")

    company = get_company_data(fnr)

    for year in company["financial"]:
        # Default values to avoid division by zero
        current_assets = year.get('current_assets', 0) or 0
        liabilities = year.get('liabilities', 0) or 0
        equity = year.get('equity', 0) or 0
        total_capital = year.get('total_liabilities', 0) or 0
        deferred_income = year.get('deferred_income', 0) or 0
        total_liabilities = year.get('total_liabilities', 0) or 0
        fixed_assets = year.get('fixed_assets', 0) or 0
        total_assets = year.get('total_assets', 0) or 0
        cash = year.get('cash_and_bank_balances', 0) or 0
        securities = year.get('securities', 0) or 0
        receivables = year.get('receivables', 0) or 0

        # Working Capital
        year['working_capital'] = {
            'value': current_assets - deferred_income,
            'description': "Current assets minus current liabilities - indicates short-term financial health.",
            'is_percent': False
        }

        # Debt-to-Equity Ratio
        if equity != 0:
            year['debt_to_equity_ratio'] = {
                'value': liabilities / equity,
                'description': "Proportion of debt in relation to equity — shows how much debt is used to finance the company compared to its own capital.",
                'is_percent': False
            }
        else:
            year['debt_to_equity_ratio'] = {
                'value': None,
                'description': "Proportion of debt in relation to equity — shows how much debt is used to finance the company compared to its own capital.",
                'is_percent': False
            }

        # Leverage Ratio / Equity Ratio
        if total_capital != 0:
            year['equity_ratio'] = {
                'value': (equity / total_capital) * 100,
                'description': "Proportion of equity in relation to total capital - shows how much of the company is financed by its own capital.",
                'is_percent': True
            }
        else:
            year['equity_ratio'] = {
                'value': None,
                'description': "Proportion of equity in relation to total capital - shows how much of the company is financed by its own capital.",
                'is_percent': True
            }

        # Liquidity Ratio
        if deferred_income != 0:
            quick_assets = cash + securities + receivables
            liquidity = current_assets / deferred_income
            year['liquidity_ratio'] = {
                'value': liquidity,
                'description': "Ability to cover short-term obligations — compares liquid assets to short-term liabilities.",
                'is_percent': False
            }
            year['current_ratio'] = {
                'value': liquidity,  # same as liquidity ratio
                'description': "Measures the ability to cover short-term obligations using all current assets.",
                'is_percent': False
            }
            year['cash_ratio'] = {
                'value': cash / deferred_income,
                'description': "Measures immediate liquidity — compares cash to short-term liabilities.",
                'is_percent': False
            }
            year['quick_ratio'] = {
                'value': quick_assets / deferred_income,
                'description': "Ability to cover short-term obligations using cash, securities, and receivables — excludes inventories.",
                'is_percent': False
            }
        else:
            year['liquidity_ratio'] = {'value': None,
                                       'description': "Ability to cover short-term obligations — compares liquid assets to short-term liabilities.",
                'is_percent': False}
            year['current_ratio'] = {'value': None,
                                     'description': "Measures the ability to cover short-term obligations using all current assets.",
                'is_percent': False
                                     }
            year['cash_ratio'] = {
                'value': None,
                'description': "Measures immediate liquidity — compares cash to short-term liabilities.",
                'is_percent': False
            }
            year['quick_ratio'] = {
                'value': None,
                'description': "Ability to cover short-term obligations using cash, securities, and receivables — excludes inventories.",
                'is_percent': False
            }



        # Equity-to-Assets Ratio
        if fixed_assets != 0:
            year['fixed_asset_coverage'] = {
                'value': (equity / fixed_assets) * 100,
                'description': "Measures how much of the company’s fixed assets are financed by equity — shows the solidity of long-term financing.",
                'is_percent': True
            }
        else:
            year['fixed_asset_coverage'] = {
                'value': None,
                'description': "Measures how much of the company’s fixed assets are financed by equity — shows the solidity of long-term financing.",
                'is_percent': True
            }

    return render_template(
        "company_view.html",
        locked=False,
        company=company,
        title="Company view",
        show_back_button=True
    )

@main.route('/view/<fnr>/risk_indicators')
def risk_indicators(fnr):
    risk_indicators = get_risk_indicators(fnr)
    return render_template(
        "risk_indicators.html",
        risk_indicators=risk_indicators,
      fnr=fnr 
    )   



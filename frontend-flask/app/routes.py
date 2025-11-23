from .utils import fetch_companies, get_company_data, get_risk_indicators
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from .models import db, User, bcrypt, SearchHistory
from datetime import datetime

main = Blueprint("main", __name__)



@main.route("/")
def index():
    user_id = session.get("user_id")
    recent = []

    if user_id:
        recent = (
            SearchHistory.query
            .filter_by(user_id=user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(5)
            .all()
        )

    return render_template(
        "index.html",
        page='index',
        logged_in=session.get("logged_in"),
        recent_searches=recent
    )


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

    # Store search for logged-in users (only once per query, when on page 1)
    if session.get("logged_in") and query and page == 1:
        user_id = session.get("user_id")
        if user_id:
            entry = SearchHistory(search_text=query, user_id=user_id)
            db.session.add(entry)
            db.session.commit()


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
            login_next=request.full_path,
            company=company_stub,
            title="Company view",
            show_back_button=True
        )

    # Logged in: fetch and normalize real data
    company = get_company_data(fnr)

    financial_years = company.get("financial", [])

    # ---------- FINANCIAL RATIOS PER YEAR ----------
    for year in financial_years:
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
            dte_val = liabilities / equity
        else:
            dte_val = None
        year['debt_to_equity_ratio'] = {
            'value': dte_val,
            'description': "Proportion of debt in relation to equity — shows how much debt is used to finance the company compared to its own capital.",
            'is_percent': False
        }

        # Equity Ratio
        if total_capital != 0:
            er_val = (equity / total_capital) * 100
        else:
            er_val = None
        year['equity_ratio'] = {
            'value': er_val,
            'description': "Proportion of equity in relation to total capital - shows how much of the company is financed by its own capital.",
            'is_percent': True
        }

        # Liquidity / current / quick / cash ratios
        if deferred_income != 0:
            quick_assets = cash + securities + receivables
            liquidity = current_assets / deferred_income
            year['liquidity_ratio'] = {
                'value': liquidity,
                'description': "Ability to cover short-term obligations — compares liquid assets to short-term liabilities.",
                'is_percent': False
            }
            year['current_ratio'] = {
                'value': liquidity,
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
            year['liquidity_ratio'] = {
                'value': None,
                'description': "Ability to cover short-term obligations — compares liquid assets to short-term liabilities.",
                'is_percent': False
            }
            year['current_ratio'] = {
                'value': None,
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

        # Fixed asset coverage (equity / fixed assets)
        if fixed_assets != 0:
            fac_val = (equity / fixed_assets) * 100
        else:
            fac_val = None
        year['fixed_asset_coverage'] = {
            'value': fac_val,
            'description': "Measures how much of the company’s fixed assets are financed by equity — shows the solidity of long-term financing.",
            'is_percent': True
        }

    # ---------- TREND INDICATORS ----------
    overview_trend = {}
    if len(financial_years) > 1:
        # sort oldest -> newest
        financial_years.sort(key=lambda y: y["fiscal_year"]["start"])

        # Per-year YoY trends (for Financial tab)
        for i in range(1, len(financial_years)):
            prev = financial_years[i - 1]
            curr = financial_years[i]

            prev_total_assets = prev.get("total_assets")
            curr_total_assets = curr.get("total_assets")

            prev_equity = prev.get("equity")
            curr_equity = curr.get("equity")

            prev_equity_ratio = (prev.get("equity_ratio") or {}).get("value")
            curr_equity_ratio = (curr.get("equity_ratio") or {}).get("value")

            prev_wc = (prev.get("working_capital") or {}).get("value")
            curr_wc = (curr.get("working_capital") or {}).get("value")

            prev_cr = (prev.get("current_ratio") or {}).get("value")
            curr_cr = (curr.get("current_ratio") or {}).get("value")

            prev_dte = (prev.get("debt_to_equity_ratio") or {}).get("value")
            curr_dte = (curr.get("debt_to_equity_ratio") or {}).get("value")

            # Asset Growth Rate (YoY)
            if prev_total_assets and prev_total_assets != 0 and curr_total_assets is not None:
                agr_val = ((curr_total_assets - prev_total_assets) / prev_total_assets) * 100
            else:
                agr_val = None
            curr["asset_growth_rate"] = {
                "value": agr_val,
                "description": "Shows the year-over-year change in total assets — indicates company growth or contraction.",
                "is_percent": True,
            }

            # Equity Growth Rate (YoY)
            if prev_equity and prev_equity != 0 and curr_equity is not None:
                egr_val = ((curr_equity - prev_equity) / prev_equity) * 100
            else:
                egr_val = None
            curr["equity_growth_rate"] = {
                "value": egr_val,
                "description": "Measures year-over-year change in equity — declining equity signals rising financial risk.",
                "is_percent": True,
            }

            # Equity Ratio Trend (YoY diff, p.p.)
            if prev_equity_ratio is not None and curr_equity_ratio is not None:
                ert_val = curr_equity_ratio - prev_equity_ratio
            else:
                ert_val = None
            curr["equity_ratio_trend"] = {
                "value": ert_val,
                "description": "Tracks how the share of equity in total capital develops compared to the previous year.",
                "is_percent": True,
            }

            # Total Assets Trend (YoY abs)
            if prev_total_assets is not None and curr_total_assets is not None:
                tat_val = curr_total_assets - prev_total_assets
            else:
                tat_val = None
            curr["total_assets_trend"] = {
                "value": tat_val,
                "description": "Absolute change in total assets compared to the previous year.",
                "is_percent": False,
            }

            # Working Capital Trend (YoY abs)
            if prev_wc is not None and curr_wc is not None:
                wct_val = curr_wc - prev_wc
            else:
                wct_val = None
            curr["working_capital_trend"] = {
                "value": wct_val,
                "description": "Change in working capital compared to the previous year.",
                "is_percent": False,
            }

            # Current Ratio Development (YoY)
            if prev_cr is not None and curr_cr is not None:
                crd_val = curr_cr - prev_cr
            else:
                crd_val = None
            curr["current_ratio_development"] = {
                "value": crd_val,
                "description": "Change in current ratio compared to the previous year.",
                "is_percent": False,
            }

            # Debt-to-Equity Trend (YoY)
            if prev_dte is not None and curr_dte is not None:
                det_val = curr_dte - prev_dte
            else:
                det_val = None
            curr["debt_to_equity_trend"] = {
                "value": det_val,
                "description": "Change in debt-to-equity ratio compared to the previous year.",
                "is_percent": False,
            }

        # ---------- MULTI-YEAR OVERALL TREND FOR OVERVIEW ----------
        first = financial_years[0]
        last = financial_years[-1]

        first_total_assets = first.get("total_assets")
        last_total_assets = last.get("total_assets")

        first_equity = first.get("equity")
        last_equity = last.get("equity")

        first_er = (first.get("equity_ratio") or {}).get("value")
        last_er = (last.get("equity_ratio") or {}).get("value")

        first_wc = (first.get("working_capital") or {}).get("value")
        last_wc = (last.get("working_capital") or {}).get("value")

        first_cr = (first.get("current_ratio") or {}).get("value")
        last_cr = (last.get("current_ratio") or {}).get("value")

        first_dte = (first.get("debt_to_equity_ratio") or {}).get("value")
        last_dte = (last.get("debt_to_equity_ratio") or {}).get("value")

        # Multi-year Asset Growth
        if first_total_assets and first_total_assets != 0 and last_total_assets is not None:
            mg_agr = ((last_total_assets - first_total_assets) / first_total_assets) * 100
        else:
            mg_agr = None
        overview_trend["asset_growth_rate"] = {
            "value": mg_agr,
            "description": "Total asset growth over the available reporting period.",
            "is_percent": True,
        }

        # Multi-year Equity Growth
        if first_equity and first_equity != 0 and last_equity is not None:
            mg_egr = ((last_equity - first_equity) / first_equity) * 100
        else:
            mg_egr = None
        overview_trend["equity_growth_rate"] = {
            "value": mg_egr,
            "description": "Equity development over the available reporting period.",
            "is_percent": True,
        }

        # Multi-year Equity Ratio Trend
        if first_er is not None and last_er is not None:
            mg_ert = last_er - first_er
        else:
            mg_ert = None
        overview_trend["equity_ratio_trend"] = {
            "value": mg_ert,
            "description": "Change in equity ratio over the available reporting period.",
            "is_percent": True,
        }

        # Multi-year Total Assets Trend (absolute)
        if first_total_assets is not None and last_total_assets is not None:
            mg_tat = last_total_assets - first_total_assets
        else:
            mg_tat = None
        overview_trend["total_assets_trend"] = {
            "value": mg_tat,
            "description": "Change in total assets over the available reporting period.",
            "is_percent": False,
        }

        # Multi-year Working Capital Trend
        if first_wc is not None and last_wc is not None:
            mg_wct = last_wc - first_wc
        else:
            mg_wct = None
        overview_trend["working_capital_trend"] = {
            "value": mg_wct,
            "description": "Change in working capital over the available reporting period.",
            "is_percent": False,
        }

        # Multi-year Current Ratio Development
        if first_cr is not None and last_cr is not None:
            mg_crd = last_cr - first_cr
        else:
            mg_crd = None
        overview_trend["current_ratio_development"] = {
            "value": mg_crd,
            "description": "Change in current ratio over the available reporting period.",
            "is_percent": False,
        }

        # Multi-year Debt-to-Equity Trend
        if first_dte is not None and last_dte is not None:
            mg_det = last_dte - first_dte
        else:
            mg_det = None
        overview_trend["debt_to_equity_trend"] = {
            "value": mg_det,
            "description": "Change in debt-to-equity ratio over the available reporting period.",
            "is_percent": False,
        }

    # ---------- COMPLIANCE INDICATORS (overall period) ----------
    compliance_overview = {}
    filing_delays = []
    late_count = 0
    years_end = []

    def _parse_date_safe(s):
        if not s:
            return None
        if hasattr(s, "year") and hasattr(s, "month") and hasattr(s, "day"):
            return datetime(s.year, s.month, s.day)
        if isinstance(s, str):
            try:
                return datetime.fromisoformat(s[:10])
            except Exception:
                return None
        return None

    for year in financial_years:
        fy = year.get("fiscal_year") or {}
        fiscal_end_raw = fy.get("end")
        sub_raw = year.get("submission_date")

        fiscal_end = _parse_date_safe(fiscal_end_raw)
        submission = _parse_date_safe(sub_raw)

        if fiscal_end:
            years_end.append(fiscal_end.year)

        if fiscal_end and submission:
            delay_days = (submission - fiscal_end).days
            filing_delays.append(delay_days)
            if delay_days >= 273:
                late_count += 1

    if filing_delays:
        avg_delay = sum(filing_delays) / len(filing_delays)
        max_delay = max(filing_delays)
        late_freq = (late_count / len(filing_delays)) * 100.0
    else:
        avg_delay = None
        max_delay = None
        late_freq = None

    if years_end:
        first_year_end = min(years_end)
        last_year_end = max(years_end)
        expected_years = last_year_end - first_year_end + 1
        reported_years = len(set(years_end))
        missing_years = max(expected_years - reported_years, 0)
    else:
        missing_years = None

    compliance_overview["avg_filing_delay"] = {
        "label": "Average Filing Delay (days)",
        "value": avg_delay,
        "description": "Average number of days between fiscal year end and submission date over the full period.",
        "is_percent": False,
    }

    compliance_overview["max_filing_delay"] = {
        "label": "Max Filing Delay (days)",
        "value": max_delay,
        "description": "Longest observed filing delay in days.",
        "is_percent": False,
    }

    compliance_overview["late_filing_frequency"] = {
        "label": "Late Filing Frequency",
        "value": late_freq,
        "description": "Share of years where filing delay exceeded 9 months (273 days).",
        "is_percent": True,
    }

    compliance_overview["missing_reporting_years"] = {
        "label": "Missing Reporting Years",
        "value": missing_years,
        "description": "Number of expected fiscal years without available reports in the continuous period.",
        "is_percent": False,
    }

    # ---------- PER-YEAR COMPLIANCE DETAILS ----------
    compliance_years = []
    if financial_years:
        for year in financial_years:
            fy = year.get("fiscal_year") or {}
            start_str = fy.get("start") or ""
            end_str = fy.get("end") or ""

            start_year = start_str[:4] if len(start_str) >= 4 else ""
            end_year = end_str[:4] if len(end_str) >= 4 else ""

            if start_year and end_year:
                label = f"{start_year} / {end_year}" if start_year != end_year else start_year
            else:
                label = "Unknown period"

            fiscal_end = _parse_date_safe(end_str)
            submission = _parse_date_safe(year.get("submission_date"))

            if fiscal_end and submission:
                delay_days = (submission - fiscal_end).days
                is_late = delay_days >= 273
            else:
                delay_days = None
                is_late = None

            ta = year.get("total_assets")
            tl = year.get("total_liabilities")
            bs_available = (ta is not None and tl is not None)

            compliance_years.append({
                "label": label,
                "delay_days": delay_days,
                "is_late": is_late,
                "balance_sheet_available": bs_available,
            })

    return render_template(
        "company_view.html",
        locked=False,
        company=company,
        title="Company view",
        show_back_button=True,
        overview_trend=overview_trend,
        compliance_overview=compliance_overview,
        compliance_years=compliance_years,
    )





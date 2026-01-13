from .client import client

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date, datetime
from charset_normalizer import from_bytes

# import base64


def json_date(date):
    """
    Convert YYYYMMDD to YYYY-MM-DD
    """
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


#########################LEVEL 1#################################################################
def company_info(fnr: str):
    suche_params = {"FNR": fnr, "STICHTAG": date.today(), "UMFANG": "Kurzinformation"}

    info = client.service.AUSZUG_V2_(**suche_params)
    # print(info)

    result = extract_company_data(info)

    return result


def extract_company_data(info):
    """
    Result has the following structure:
    {
        basic_info: {
            company_name: str,
            legal_form: null | str,
            company_number: str,
            european_id: null | str,
            is_deleted: bool
        },
        location: null | {
            street: null | str,
            house_number: null | str,
            postal_code: str,
            city: str,
            country: str
        },
        management: [
            {
                pnr: str,
                name: str,
                date_of_birth: null | str(date),
                role: str,
                appointed_on: null | str(date)
            },
            ...
        ],
        financial: [
            {
                submission_date: str(date),
                fiscal_year: {
                    start: str(date),
                    end: str(date)
                },
                currency: str,
                director_name: str,
                fixed_assets: float,
                intangible_assets: float,
                tangible_assets: float,
                financial_assets: float,
                current_assets: float,
                inventories: float,
                receivables: float,
                securities: float,
                cash_and_bank_balances: float,
                prepaid_expenses: float,
                deferred_tax_assets: float,
                total_assets: float,
                equity: float,
                share_capital: float,
                capital_reserves: float,
                revenue_reserves: float,
                retained_earnings: float,
                retained_earnings_subitem: float,
                liabilities: float,
                deferred_income: float,
                deferred_tax_liabilities: float,
                total_liabilities: float

                // Calculated for risks
                quick_assets: float,

                // 'level' is risk level of the company
                // H stands for High, M stands for Medium, L stands for Low
                // Indicators:
                indicators: {
                    working_capital: {
                        value: float,
                        level: "H" | "L"
                    }
                    debt_to_equity_ratio: null | {
                        value: float,
                        level: "H" | "M" | "L"
                    }
                    equity_ratio: null | {
                        value: float,
                        level: "H" | "M" | "L"
                    },
                    current_ratio: null | {
                        value: float,
                        level: "H" | "M" | "L"
                    },
                    cash_ratio: null | {
                        value: float,
                        level: "H" | "M" | "L"
                    },
                    quick_ratio: {
                        value: float,
                        level: "H" | "M" | "L"
                    },
                    fixed_asset_coverage: null | {
                        value: float,
                        level: "H" | "M" | "L"
                    },
                    profit_loss: {
                        value: float,
                        level: "H" | "L"
                    },
                },

                // Trends: can be absent for the first year
                trends: null | {
                    asset_growth_rate: float,
                    equity_growth_rate: float,
                    profit_loss_development: float,
                    equity_ratio_trend: float,
                    total_assets_trend: float,
                    working_capital_trend: float,
                    current_ratio_development: float,
                    debt_to_equity_trend: float
                }
            },
            ...
        ],
        history: [
            {
                event_number: str,
                event_date: str,
                event: str,
                court: str,
                filed_date: str(date)
            },
            ...
        ],
        compliance_indicators: {
            filing_delays: [
                {
                    fiscal_year: {
                        start: str(date),
                        end: str(date)
                    },
                    days: int,
                    is_late: bool
                }
            ],
            calculations: {
                avg_filing_delay: null | {
                    value: float,
                    level: "H" | "M" | "L"
                },
                max_filing_delay: null | {
                    value: int,
                    level: "H" | "M" | "L"
                },
                late_filing_frequency: null | {
                    value: float,
                    level: "H" | "M" | "L"
                },
                missing_reporting_years: int
            }
        },
        documents: [
            {
                id: str,
                type: str,
                date: str(date)
            },
        ...
        ],
        risk_indicators: {
            has_masseverwalter: bool,
            risk_level: null | "H" | "M" | "L"
        }
    }
    """

    management = extract_management_info(info)
    history = extract_company_history(info)

    pdf_ids, xml_report_ids, total_reports = get_doc_ids(info.FNR)
    financial = [  # limit to 3 last reports
        get_xml_data(id) for id in xml_report_ids[-3:]
    ]
    calculate_financial_indicators(financial)

    compliance_indicators, is_deleted = extract_compliance_indicators(
        financial, history, total_reports
    )
    risk_indicators = extract_risk_indicators(
        management, financial[-1]["indicators"] if financial else None
    )

    data = {
        "basic_info": {
            "company_name": (
                info.FIRMA.FI_DKZ02[0].BEZEICHNUNG[0] if info.FIRMA.FI_DKZ02 else None
            ),
            "legal_form": (
                info.FIRMA.FI_DKZ07[0].RECHTSFORM.TEXT if info.FIRMA.FI_DKZ07 else None
            ),
            "company_number": info.FNR,
            "european_id": info.EUID[0].EUID if info.EUID else None,
            "is_deleted": is_deleted,
        },
        "location": extract_location_info(info),
        "management": management,
        "financial": financial,
        "history": history,
        "compliance_indicators": compliance_indicators,
        "documents": pdf_ids,
        "risk_indicators": risk_indicators,
    }

    return data


def calculate_financial_indicators(financial_years):
    """
    Mutates the passed in list by appending additional data to it
    """
    if financial_years:
        financial_years[0]["trends"] = None
    else:
        return

    for year in financial_years:
        divide_or_none = lambda numerator, denominator: (
            year[numerator] / year[denominator] if year[denominator] else None
        )

        # This one is used for calculation of others
        year["quick_assets"] = (
            year["cash_and_bank_balances"] + year["securities"] + year["receivables"]
        )

        indicators = year["indicators"] = {}

        value = year["current_assets"] - year["deferred_income"]
        indicators["working_capital"] = {
            "value": value,
            "level": "L" if value > 0 else "H",
        }

        value = divide_or_none("liabilities", "equity")
        indicators["debt_to_equity_ratio"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value < 1 else "M" if value <= 2 else "H",
            }
        )

        value = divide_or_none("equity", "total_liabilities")  # wrong
        indicators["equity_ratio"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value > 0.50 else "M" if value >= 0.25 else "H",
            }
        )

        value = divide_or_none("current_assets", "deferred_income")
        indicators["current_ratio"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value > 2 else "M" if value >= 1 else "H",
            }
        )

        value = divide_or_none("cash_and_bank_balances", "deferred_income")
        indicators["cash_ratio"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value > 1 else "M" if value >= 0.2 else "H",
            }
        )

        value = divide_or_none("quick_assets", "deferred_income")
        indicators["quick_ratio"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value > 1 else "M" if value >= 0.5 else "H",
            }
        )

        value = divide_or_none("equity", "fixed_assets")
        indicators["fixed_asset_coverage"] = (
            None
            if not value
            else {
                "value": value,
                "level": "L" if value > 1.00 else "M" if value >= 0.50 else "H",
            }
        )

        value = year["retained_earnings"] - year["retained_earnings_subitem"]
        indicators["profit_loss"] = {
            "value": value,
            "level": "L" if value >= 0 else "H",
        }

    for prev, curr in zip(financial_years, financial_years[1:]):

        def growth_rate_or_none(metric, is_indicator):
            # Get this man a True...
            if is_indicator:
                if (
                    prev["indicators"][metric] is None
                    or curr["indicators"][metric] is None
                ):
                    return None
                prev_value = prev["indicators"][metric]["value"]
                if prev_value == 0:
                    return None

                return (curr["indicators"][metric]["value"] - prev_value) / prev_value

            if not prev[metric] or not curr[metric]:
                return None
            return (curr[metric] - prev[metric]) / prev[metric]

        trends = curr["trends"] = {}

        trends["asset_growth_rate"] = growth_rate_or_none("total_assets", False)
        trends["equity_growth_rate"] = growth_rate_or_none("equity", False)
        trends["profit_loss_development"] = growth_rate_or_none("profit_loss", True)

        def trend_or_none(metric, is_indicator):
            if is_indicator:
                if (
                    prev["indicators"][metric] is None
                    or curr["indicators"][metric] is None
                ):
                    return None

                return (
                    prev["indicators"][metric]["value"]
                    - curr["indicators"][metric]["value"]
                )
            if not prev[metric] or not curr[metric]:
                return None
            return prev[metric] - curr[metric]

        trends["equity_ratio_trend"] = trend_or_none("equity_ratio", True)
        trends["total_assets_trend"] = trend_or_none("total_assets", False)
        trends["working_capital_trend"] = trend_or_none("working_capital", True)
        trends["current_ratio_development"] = trend_or_none("current_ratio", True)
        trends["debt_to_equity_trend"] = trend_or_none("debt_to_equity_ratio", True)


def extract_compliance_indicators(financial, history, total_reports):
    filing_delays = []
    for sheet in financial:
        days = filing_delay(sheet)
        filing_delays.append(
            {
                "fiscal_year": sheet["fiscal_year"],
                "days": days,
                # approximately 9 months
                "is_late": days > 273,
            }
        )

    if filing_delays:
        days = [year["days"] for year in filing_delays]

        value = sum(days) / len(days)
        avg_filing_delay = {
            "value": value,
            "level": "L" if value <= 90 else "M" if value <= 273 else "H",
        }

        value = max(days)
        max_filing_delay = {
            "value": value,
            "level": "L" if value <= 180 else "M" if value <= 273 else "H",
        }

        value = sum(fd["is_late"] for fd in filing_delays) / len(filing_delays)
        late_filing_frequency = {
            "value": value,
            "level": "L" if value < 0.2 else "M" if value <= 0.5 else "H",
        }
    else:
        avg_filing_delay = None
        max_filing_delay = None
        late_filing_frequency = None

    # top 10 epic gamer fornite moments
    is_deleted = "löschung" in history[-1]["event"].lower()
    # the first history event is always a company creation
    first_year = history[0]["event_date"].year
    last_year = history[-1]["event_date"].year if is_deleted else date.today().year

    expected_reports = last_year - first_year
    value = expected_reports - total_reports
    missing_reporting_years = {
        "value": value,
        "level": "L" if value <= 0 else "M" if value <= 2 else "H",
    }

    return {
        "filing_delays": filing_delays,
        "calculations": {
            "avg_filing_delay": avg_filing_delay,
            "max_filing_delay": max_filing_delay,
            "late_filing_frequency": late_filing_frequency,
            "missing_reporting_years": missing_reporting_years,
        },
    }, is_deleted


def extract_location_info(info):
    if not info.FIRMA.FI_DKZ03:
        return None

    address = info.FIRMA.FI_DKZ03[0]

    data = {
        "street": address.STRASSE,
        "house_number": address.HAUSNUMMER,
        "postal_code": address.PLZ,
        "city": address.ORT,
        "country": address.STAAT,
    }

    return data


def extract_management_info(info):
    if not info.FUN:
        return []

    people = []
    for i in info.FUN:
        pnr = i.PNR
        personal_info = next(j for j in info.PER if j.PNR == pnr)  # easier
        # print(personal_info)

        if personal_info:
            date_of_birth = personal_info.PE_DKZ02[0].GEBURTSDATUM

            formatted_name = personal_info.PE_DKZ02[0].NAME_FORMATIERT
            name = (
                formatted_name[0]
                if formatted_name is not None
                else personal_info.PE_DKZ02[0].BEZEICHNUNG[0]
            )

            appointed_on = i.FU_DKZ10[0].DATVON

            data = {
                "pnr": pnr,  # not globally unique
                "name": name,
                "date_of_birth": json_date(date_of_birth) if date_of_birth else None,
                "role": i.FKENTEXT,
                "appointed_on": json_date(appointed_on) if appointed_on else None,
            }
            people.append(data)

    return people


def extract_company_history(info):
    if not info.VOLLZ:
        return []

    history = []

    for event in info.VOLLZ:
        history.append(
            {
                "event_number": event.VNR,
                "event_date": event.VOLLZUGSDATUM,
                "event": event.ANTRAGSTEXT[0],
                "court": event.HG.TEXT,
                "filed_date": event.EINGELANGTAM,
            }
        )

    return history


######################LEVEL 2##########################################################


def get_text_or_none(element: ET.Element | None) -> str | None:
    if element is None:
        return None

    return element.text


def get_document_data(id):
    suche_params = {
        "KEY": id,
        # "SICHTAG": datetime.datetime.today()
    }

    res = client.service.URKUNDE(**suche_params)
    if id.endswith("XML"):
        detection = from_bytes(res["DOKUMENT"]["CONTENT"]).best()
        if detection is None:
            raise ValueError("Could not detect encoding")

        return str(detection)
    else:
        return res["DOKUMENT"]["CONTENT"]


ns = {"ns0": "https://finanzonline.bmf.gv.at/bilanz"}


def get_xml_data(id):
    global ns
    xml_content = get_document_data(id)

    root = ET.fromstring(xml_content)

    # with open(id + ".xml", "w", encoding="utf-8") as f:
    #     f.write(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  "))

    date_info = root.find(".//ns0:INFO_DATEN", ns)
    other_info = root.find(".//ns0:BILANZ_GLIEDERUNG", ns)

    general = other_info.find("./ns0:ALLG_JUSTIZ", ns)
    balance = other_info.find("./ns0:BILANZ", ns)
    if balance is None:
        balance = other_info.find("./ns0:HGB_Form_2", ns)

    fiscal_year = general.find("./ns0:GJ", ns)
    director = general.find("./ns0:UNTER", ns)

    def search_balance(term):
        node = balance.find(f".//ns0:{term}/ns0:POSTENZEILE/ns0:BETRAG", ns)
        if node is None:
            # Probably wrong but calculations require it.
            return 0.0

        return float(node.text)

    # pdf files
    # notes = other_info.find('./ns0:VERMERKE', ns)
    # for elem in note.iter():
    #     tag_name = elem.tag[elem.tag.index('}') + 1:]
    #     if tag_name == "VERMERKE":
    #         continue
    #
    #     decoded = base64.b64decode(elem.text)
    #
    #     with open(tag_name + ".pdf", "wb") as f:
    #         f.write(decoded)

    data = {
        "submission_date": (
            date_info.find("./ns0:DATUM_ERSTELLUNG", ns).text
            if date_info
            else director.find("./ns0:DAT_UNT", ns).text
        ),
        "fiscal_year": {
            "start": fiscal_year.find("./ns0:BEGINN", ns).text,
            "end": fiscal_year.find("./ns0:ENDE", ns).text,
        },
        "currency": general.find("./ns0:WAEHRUNG", ns).text,
        "director_name": director.find("./ns0:V_NAME", ns).text
        + " "
        + director.find("./ns0:Z_NAME", ns).text,
        "fixed_assets": search_balance("HGB_224_2_A"),
        "intangible_assets": search_balance("HGB_224_2_A_I"),
        "tangible_assets": search_balance("HGB_224_2_A_II"),
        "financial_assets": search_balance("HGB_224_2_A_III"),
        "current_assets": search_balance("HGB_224_2_B"),
        "inventories": search_balance("HGB_224_2_B_I"),
        "receivables": search_balance("HGB_224_2_B_II"),
        "securities": search_balance("HGB_224_2_B_III"),
        "cash_and_bank_balances": search_balance("HGB_224_2_B_IV"),
        "prepaid_expenses": search_balance("HGB_224_2_C"),
        "deferred_tax_assets": search_balance("HGB_224_2_D"),
        "total_assets": search_balance("HGB_224_2"),
        "equity": search_balance("HGB_224_3_A"),
        "share_capital": search_balance("HGB_229_1_A_I"),
        # Unused
        # 'share_capital_subitem': search_balance("HGB_224_3_A_I_a"),
        # 'share_capital_subitem_detail': search_balance("HGB_229_1_A_I_a"),
        "capital_reserves": search_balance("HGB_224_3_A_II"),
        "revenue_reserves": search_balance("HGB_224_3_A_III"),
        "retained_earnings": search_balance("HGB_224_3_A_IV"),
        "retained_earnings_subitem": search_balance("HGB_224_3_A_IV_x"),
        "liabilities": search_balance("HGB_224_3_C"),
        "deferred_income": search_balance("HGB_224_3_D"),
        "deferred_tax_liabilities": search_balance("HGB_224_3_E"),
        "total_liabilities": search_balance("HGB_224_3"),
    }

    return data


def get_doc_ids(fnr) -> tuple[list[dict], list[str], int]:
    suche_params = {"FNR": fnr, "AZ": ""}
    results: list = client.service.SUCHEURKUNDE(**suche_params).ERGEBNIS
    # The results are divided into 2 sections: PDF and XML
    # Sections are ordered by date from oldest to latest
    # PDFs come first, XMLs come afterwards

    # Example .KEY: '435836_5690342302057_000___000_30_30137347_XML'
    #               '435836_5690342302057_000__  _000 _30 _30137347_XML'
    # (_ if empty)   FNR   _AZ           _ZNR_PNR_FKEN_UNR_DKZURKID_ContentType(PDF/XML)
    # The same document can be distincted by AZ
    # The FNR and AZ are fixed size and must always be present
    # which means that AZ always lays in the range [7:20] (exclusive)
    # It's important to receive XMLs first since the first document takes it's uniqueness
    keys = set()
    pdf_ids = []
    xml_report_ids = []
    total_years = 0
    for result in results:
        is_xml = result.KEY.endswith("XML")

        if not is_xml:
            pdf_ids.append(
                {
                    "id": result.KEY,
                    "type": result.DOKUMENTART.TEXT,
                    "date": result.STICHTAG,
                }
            )

        if result.DOKUMENTART.TEXT != "Jahresabschluss":
            continue

        if is_xml:
            xml_report_ids.append(result.KEY)

        AZ = result.KEY[7:20]
        if AZ not in keys:
            keys.add(AZ)
            total_years += 1
    pdf_ids.sort(key=lambda x: x["date"] or date(2000, 1, 1))

    return pdf_ids, xml_report_ids, total_years


def filing_delay(sheet) -> int:
    submission = datetime.strptime(sheet["submission_date"], "%Y-%m-%d")
    year_end = datetime.strptime(sheet["fiscal_year"]["end"], "%Y-%m-%d")

    return (submission - year_end).days


def extract_risk_indicators(management, indicators):
    for manager in management:
        if manager["role"] == "MASSEVERWALTER/IN":
            return {"has_masserverwalter": True, "risk_level": "H"}

    if not indicators:
        return {"has_masserverwalter": False, "risk_level": None}

    high_risk_metrics = 0
    for metric in indicators.values():
        if metric and metric["level"] == "H":
            high_risk_metrics += 1

    return {
        "has_masserverwalter": False,
        "risk_level": (
            "L" if high_risk_metrics <= 2 else "M" if high_risk_metrics <= 4 else "H"
        ),
    }

from .client import client

import re
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
    suche_params = {
        "FNR": fnr,
        "STICHTAG": date.today(),
        "UMFANG": "Kurzinformation"
    }

    info = client.service.AUSZUG_V2_(**suche_params)
    #print(info)

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
            european_id: null | str
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
                share_capital_subitem: float,
                share_capital_subitem_detail: float,
                capital_reserves: float,
                revenue_reserves: float,
                retained_earnings: float,
                retained_earnings_subitem: float,
                liabilities: float,
                deferred_income: float,
                deferred_tax_liabilities: float,
                total_liabilities: float
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
        risk_indicators: {
            filling_delay: int[](days)
            late_filling_frequency: null | float(0.0-1.0)
            missing_reporting_years: int
        }
    }
    """

    history = extract_company_history(info)

    doc_ids, total_reports = get_doc_ids(info.FNR)
    financial = [get_document_data(id) for id in doc_ids[:3]]  # limit to 3 last reports

    filling_delays = [filling_delay(sheet) for sheet in financial]
    if filling_delays:
                                                                            # approximately 9 months
        late_filling_frequency = sum(1 for delay in filling_delays if delay > 273) / len(filling_delays)
    else:
        late_filling_frequency = None

    # the first history event is always a company creation
    first_year = history[0]['filed_date'].year
    expected_reports = date.today().year - first_year
    missing_reporting_years = expected_reports - total_reports

    data = {
        'basic_info': {
            'company_name': info.FIRMA.FI_DKZ02[0].BEZEICHNUNG[0] if info.FIRMA.FI_DKZ02 else None,
            'legal_form': info.FIRMA.FI_DKZ07[0].RECHTSFORM.TEXT if info.FIRMA.FI_DKZ07 else None,
            'company_number': info.FNR,
            'european_id': info.EUID[0].EUID if info.EUID else None,
        },
        'location': extract_location_info(info),
        'management': extract_management_info(info),
        'financial': financial,
        'history': history,
        'risk_indicators': {
            'filling_delay': filling_delays,
            'late_filling_frequency': late_filling_frequency,
            'missing_reporting_years': missing_reporting_years
        }
    }

    return data

def extract_location_info(info):
    if not info.FIRMA.FI_DKZ03:
        return None

    address = info.FIRMA.FI_DKZ03[0]

    data = {
        'street': address.STRASSE,
        'house_number': address.HAUSNUMMER,
        'postal_code': address.PLZ,
        'city': address.ORT,
        'country':  address.STAAT
    }

    return data

def extract_management_info(info):
    if not info.FUN:
        return []

    people = []
    for i in info.FUN:
        pnr = i.PNR
        personal_info = next(j for j in info.PER if j.PNR == pnr) #easier
        #print(personal_info)

        if personal_info:
            date_of_birth = personal_info.PE_DKZ02[0].GEBURTSDATUM

            formatted_name = personal_info.PE_DKZ02[0].NAME_FORMATIERT
            name = formatted_name[0] if formatted_name is not None else personal_info.PE_DKZ02[0].BEZEICHNUNG[0]

            appointed_on = i.FU_DKZ10[0].DATVON

            data = {
                'pnr': pnr, #not globally unique
                'name': name,
                'date_of_birth': json_date(date_of_birth) if date_of_birth else None,
                'role': i.FKENTEXT,
                'appointed_on': json_date(appointed_on) if appointed_on else None,
            }
            people.append(data)

    return people

def extract_company_history(info):
    if not info.VOLLZ:
        return []

    history = []

    for event in info.VOLLZ:
        history.append({
            'event_number': event.VNR,
            'event_date': event.VOLLZUGSDATUM,
            'event': event.ANTRAGSTEXT[0],
            'court': event.HG.TEXT,
            'filed_date': event.EINGELANGTAM
        })

    return history

######################LEVEL 2##########################################################

def get_text_or_none(element: ET.Element | None) -> str | None:
    if element is None:
        return None

    return element.text

def get_xml_data(id):
    suche_params = {
        "KEY": id,
        #"SICHTAG": datetime.datetime.today()
    }

    res = client.service.URKUNDE(**suche_params)

    detection = from_bytes(res['DOKUMENT']['CONTENT']).best()
    if detection is None:
        raise ValueError("Could not detect encoding")

    return str(detection)

ns = {'ns0': 'https://finanzonline.bmf.gv.at/bilanz'}
def get_document_data(id):
    global ns
    xml_content = get_xml_data(id)

    root = ET.fromstring(xml_content)

    # with open(id + ".xml", "w", encoding="utf-8") as f:
    #     f.write(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  "))

    date_info = root.find('.//ns0:INFO_DATEN', ns)
    other_info = root.find('.//ns0:BILANZ_GLIEDERUNG', ns)

    general = other_info.find('./ns0:ALLG_JUSTIZ', ns)
    balance = other_info.find('./ns0:BILANZ', ns)
    if balance is None:
        balance = other_info.find('./ns0:HGB_Form_2', ns)

    fiscal_year = general.find('./ns0:GJ', ns)
    director = general.find('./ns0:UNTER', ns)

    def search_balance(term):
        node = balance.find(f".//ns0:{term}/ns0:POSTENZEILE/ns0:BETRAG", ns)
        if node is None:
            return None

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
        'submission_date': date_info.find('./ns0:DATUM_ERSTELLUNG', ns).text if date_info
            else director.find('./ns0:DAT_UNT', ns).text,
        'fiscal_year': {
            'start': fiscal_year.find('./ns0:BEGINN', ns).text,
            'end': fiscal_year.find('./ns0:ENDE', ns).text,
        },
        'currency': general.find('./ns0:WAEHRUNG', ns).text,
        'director_name': director.find('./ns0:V_NAME', ns).text + " " + director.find('./ns0:Z_NAME', ns).text,

        'fixed_assets': search_balance("HGB_224_2_A"),
        'intangible_assets': search_balance("HGB_224_2_A_I"),
        'tangible_assets': search_balance("HGB_224_2_A_II"),
        'financial_assets': search_balance("HGB_224_2_A_III"),
        'current_assets': search_balance("HGB_224_2_B"),
        'inventories': search_balance("HGB_224_2_B_I"),
        'receivables': search_balance("HGB_224_2_B_II"),
        'securities': search_balance("HGB_224_2_B_III"),
        'cash_and_bank_balances': search_balance("HGB_224_2_B_IV"),
        'prepaid_expenses': search_balance("HGB_224_2_C"),
        'deferred_tax_assets': search_balance("HGB_224_2_D"),
        'total_assets': search_balance("HGB_224_2"),

        'equity': search_balance("HGB_224_3_A"),
        'share_capital': search_balance("HGB_229_1_A_I"),
        'share_capital_subitem': search_balance("HGB_224_3_A_I_a"),
        'share_capital_subitem_detail': search_balance("HGB_229_1_A_I_a"),
        'capital_reserves': search_balance("HGB_224_3_A_II"),
        'revenue_reserves': search_balance("HGB_224_3_A_III"),
        'retained_earnings': search_balance("HGB_224_3_A_IV"),
        'retained_earnings_subitem': search_balance("HGB_224_3_A_IV_x"),
        'liabilities': search_balance("HGB_224_3_C"),
        'deferred_income': search_balance("HGB_224_3_D"),
        'deferred_tax_liabilities': search_balance("HGB_224_3_E"),
        'total_liabilities': search_balance("HGB_224_3")
    }

    return data

def get_doc_ids(fnr) -> tuple[list[str], int]:
    suche_params = {
        "FNR": fnr,
        "AZ": ""
    }
    results: list = client.service.SUCHEURKUNDE(**suche_params).ERGEBNIS
    # The results are divided into 2 sections: PDF and XML
    # Sections are ordered by date from oldest to latest
    # PDFs come first, XMLs come afterwards
    # By reversing this list we can receive latest XMLs first
    # There is always a PDF alternative to the XML, but not the opposite
    # That's why it's important to also account for PDF documents to calculate
    # The total number of reports
    results.reverse()
    print(results)

    doc_ids = [result.KEY for result in results if result.DOKUMENTART.TEXT == "Jahresabschluss"]

    # Example .KEY: '435836_5690342302057_000___000_30_30137347_XML'
    #               '435836_5690342302057_000__  _000 _30 _30137347_XML'
    # (_ if empty)   FNR   _AZ           _ZNR_PNR_FKEN_UNR_DKZURKID_ContentType(PDF/XML)
    # The same document can be distincted by AZ
    # The FNR and AZ are fixed size and must always be present
    # which means that AZ always lays in the range [7:20] (exclusive)
    # It's important to receive XMLs first since the first document takes it's uniqueness
    keys = set()
    doc_ids = []
    total_years = 0
    for result in results:
        if result.DOKUMENTART.TEXT != "Jahresabschluss":
            continue

        AZ = result.KEY[7:20]
        print(AZ)
        if AZ in keys:
            continue

        keys.add(AZ)
        total_years += 1
        if result.KEY.endswith("XML"):
            doc_ids.append(result.KEY)

    return doc_ids, total_years


def filling_delay(sheet) -> int:
    submission = datetime.strptime(sheet['submission_date'], "%Y-%m-%d")
    year_end = datetime.strptime(sheet['fiscal_year']['end'], "%Y-%m-%d")

    return (submission - year_end).days


######################LEVEL 3##########################################################


def network_metrics(info):
    pass
from .client import client

import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime
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
        "STICHTAG": datetime.date.today(),
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
        ]
    }
    """

    data = {
        'basic_info': {
            'company_name': info.FIRMA.FI_DKZ02[0].BEZEICHNUNG[0] if len(info.FIRMA.FI_DKZ02) > 0 else None,
            'legal_form': info.FIRMA.FI_DKZ07[0].RECHTSFORM.TEXT if len(info.FIRMA.FI_DKZ07) > 0 else None,
            'company_number': info.FNR,
            'european_id': info.EUID[0].EUID if len(info.EUID) > 0 else None,
        },
        'location': extract_location_info(info),
        'management': extract_management_info(info),
        'financial': get_financial_data(info.FNR),
        'history': extract_company_history(info),
    }

    return data

def extract_location_info(info):
    if len(info.FIRMA.FI_DKZ03) < 1:
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
    if len(info.FUN) < 1:
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
    if len(info.VOLLZ) < 1:
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

def get_financial_data(fnr):
    suche_params = {
        "FNR": fnr,
        "AZ": ""
    }
    results = client.service.SUCHEURKUNDE(**suche_params).ERGEBNIS

    print(results)

    # FNR_AZ_ZNR_PNR(_ if empty)_FKEN_UNR_DKZURKID_ContentType(PDF/XML)
    # for some reason the content of the documents repeats
    #  [
    #     '435836_5690342302057_000___000_30_30137347_XML', 1
    #     '435836_5690342302057_000___000_30_30137348_XML', 1
    #     '435836_5690342302057_000___000_30_30137350_XML', 1
    #     '435836_5690342400412_000___000_30_32334332_XML', 2
    #     '435836_5690342400412_000___000_30_32334333_XML', 2
    #     '435836_5690342400412_000___000_30_32334335_XML', 2
    #     '435836_5690682501107_000___000_30_35209228_XML', 3
    #     '435836_5690682501107_000___000_30_35209229_XML', 3
    #     '435836_5690682501107_000___000_30_35209230_XML'  3
    # ]
    # I would assume the uniqueness depends on the AZ

    pattern = re.compile(r'^\d+_(\d+)_.*XML$')
    keys = set()
    doc_ids = []
    for result in results:
        match = pattern.fullmatch(result.KEY)
        if not match:
            continue

        key = match.group(1)
        if key in keys:
            continue

        keys.add(key)
        doc_ids.append(result.KEY)
                                            # limit to 3 last reports
    return [get_document_data(id) for id in doc_ids[-3:]]


######################LEVEL 3##########################################################


def network_metrics(info):
    pass
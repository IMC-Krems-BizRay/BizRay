import xml.etree.ElementTree as ET
# from xml.dom import minidom
# import base64

from .client import create_client
import datetime
from charset_normalizer import from_bytes

def json_date(date):
    """
    Convert YYYYMMDD to YYYY-MM-DD
    """
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"

#########################LEVEL 1#################################################################
def company_info(fnr: str):
    client = create_client()

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
            legal_form: str,
            company_number: str,
            european_id: str
        },
        location: {
            street: str,
            house_number: str,
            postal_code: str,
            city: str,
            country:  str
        },
        management: [
            {
                PNR: str,
                name: str,
                DOB: str,
                role: str,
                appointed_on: str
            },
            ...
        ],
        financial: {
            director_name: str,
            total_assets: str
        },
        history: [
            {
                event_number: str,
                event_date: str,
                event: str,
                court: str,
                filed_date: str
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
        'financial': get_document_data(info.FNR),
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
            data = {
                'pnr': pnr, #not globally unique
                'name': personal_info.PE_DKZ02[0].NAME_FORMATIERT[0],
                'date_of_birth': json_date(personal_info.PE_DKZ02[0].GEBURTSDATUM),
                'role': i.FKENTEXT,
                'appointed_on': json_date(i.FU_DKZ10[0].DATVON),
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

def get_document_data(fnr):
    client = create_client()

    suche_params = {
        "FNR": fnr,
        "AZ": ""
    }
    res = client.service.SUCHEURKUNDE(**suche_params).ERGEBNIS


    doc_ids = [i.KEY for i in res if 'XML' in i.KEY]
    if not doc_ids:
        return None

    xml_content = get_xml_data(doc_ids[0]) #for now
    root = ET.fromstring(xml_content)

    ns = {'ns0': 'https://finanzonline.bmf.gv.at/bilanz'}



    date_info = root.find('.//ns0:INFO_DATEN', ns)
    other_info = root.find('.//ns0:BILANZ_GLIEDERUNG', ns)

    general = other_info.find('./ns0:ALLG_JUSTIZ', ns)
    balance = other_info.find('./ns0:BILANZ', ns)

    fiscal_year = general.find('./ns0:GJ', ns)
    director = general.find('./ns0:UNTER', ns)

    # print(balance.find(".//ns0:HGB_224_2/ns0:POSTENZEILE/ns0:BETRAG", ns).text)
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
        'submission': {
            'date': date_info.find('./ns0:DATUM_ERSTELLUNG', ns).text,
            'time': date_info.find('./ns0:UHRZEIT_ERSTELLUNG', ns).text,
        },
        'fiscal_year': {
            'start': fiscal_year.find('./ns0:BEGINN', ns).text,
            'end': fiscal_year.find('./ns0:ENDE', ns).text,
        },
        'currency': general.find('./ns0:WAEHRUNG', ns).text,
        'director': {
            'name': director.find('./ns0:V_NAME', ns).text + " " + director.find('./ns0:Z_NAME', ns).text,
            'date_of_birth': get_text_or_none(director.find('./ns0:GEB_DAT', ns)),
            'title': get_text_or_none(director.find('./ns0:TITEL', ns)),
        },
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




def get_xml_data(id):
    client = create_client()

    suche_params = {
        "KEY": id,
        #"SICHTAG": datetime.datetime.today()
    }

    res = client.service.URKUNDE(**suche_params)

    detection = from_bytes(res['DOKUMENT']['CONTENT']).best()
    if detection is None:
        raise ValueError("Could not detect encoding")

    return str(detection)



######################LEVEL 3##########################################################


def network_metrics(info):
    pass
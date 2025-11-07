import math

from cachetools import TTLCache
from .client import create_client
from datetime import date

import re
from enum import Enum

class SearchMode(Enum):
    NAME = 0,
    FNR = 1

# LRU cache with 10 minutes of expiry (the time limit is to prevent frequently used items to never update)
name_search_cache = TTLCache(maxsize=128, ttl=600)

def check_name_search_cache(term):
    global name_search_cache
    # Ignore case
    term = term.lower()
    if term in name_search_cache:
        return name_search_cache[term]

    result = search_by_name(term)
    name_search_cache[term] = result
    return result

def detect_search_mode(term: str) -> SearchMode:
    term = term.strip()
    return SearchMode.FNR if re.fullmatch(r"\d{6,7}[a-zA-Z]", term) else SearchMode.NAME

def search(term: str, page: int) -> dict:
    mode = detect_search_mode(term)
    if mode == SearchMode.NAME:
        companies = check_name_search_cache(term)

        # pagination
        per_page = 15
        total = len(companies)
        total_pages = max(1, math.ceil(total / per_page))
        page = max(1, min(page, total_pages))

        start = (page - 1) * per_page
        end = start + per_page

        # Can send more info if needed
        return {
            "total_pages": total_pages,
            "companies": companies[start:end]
        }
    # This ideally should redirect towards the company view page and it's not autosuggested
    elif mode == SearchMode.FNR:
        return {
            "total_pages": 1,
            "companies": [search_by_fnr(term)]
        }

def search_by_name(company_name) -> list[dict]:
    client = create_client() #for now

    #SUCHFIRMA finds the ids of companies with the name like FIRMENWORTLAUT
    suche_params = {
        "FIRMENWORTLAUT": company_name,
        "EXAKTESUCHE": False, #we can change this later
        "SUCHBEREICH": 1, #can change later
        "GERICHT": "", #DO LATER !?!?
        "RECHTSFORM": "",
        "RECHTSEIGENSCHAFT": "",
        "ORTNR": ""
    }

    suche_response = client.service.SUCHEFIRMA(**suche_params)

    ergebnisse = suche_response.ERGEBNIS

    print(f"Found {len(ergebnisse)} companies for '{company_name}'---------------------------------------------------\n\n\n") #for debugging
    #print(ergebnisse[0])
    #print(type(suche_response))
    results = []
    for ergebnis in ergebnisse:
        company_info = { #included this for english translation and in case we decide to remove some fields later
            "fnr": ergebnis.FNR,
            "status": "active" if "STATUS" in ergebnis else "inactive",
            "name": ergebnis.NAME,
            "location": ergebnis.SITZ,
            "legal_form": {"code": ergebnis.RECHTSFORM.CODE, "text": ergebnis.RECHTSFORM.TEXT},
            "legal_status": "active" if "RECHTSEIGENSCHAFT" in ergebnis else "inactive",
            "responsible_court": {"code": ergebnis.GERICHT.CODE, "text": ergebnis.GERICHT.TEXT}
        }
        results.append(company_info)


    return results

def search_by_fnr(company_fnr) -> dict:
    client = create_client()

    suche_params = {
        "FNR": company_fnr,
        "STICHTAG": date.today(),
        "UMFANG": "Kurzinformation"
    }

    suche_response = client.service.AUSZUG_V2_(**suche_params)
    firma = suche_response.FIRMA

    # legal_form_entry = firma.FI_DKZ07[0] if len(firma.FI_DKZ07) > 0 else None

    return {
        "fnr": company_fnr,
        "status": "active", # for now
        "name": firma.FI_DKZ02[0].BEZEICHNUNG,
        "location": firma.FI_DKZ06[0].SITZ,
        # Not needed
        # "legal_form": {"code": legal_form_entry.RECHTSFORM.CODE, "text": legal_form_entry.RECHTSFORM.TEXT} if legal_form_entry else None,
        # "legal_status": "active" if legal_form_entry and legal_form_entry.AUFRECHT else "inactive"
    }
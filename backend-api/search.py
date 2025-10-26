from client import create_client
from datetime import date

def search_by_name(company_name, exact_search = True):
    client = create_client() #for now

    #SUCHFIRMA finds the ids of companies with the name like FIRMENWORTLAUT
    suche_params = {
        "FIRMENWORTLAUT": company_name,
        "EXAKTESUCHE": exact_search, #we can change this later
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

def search_by_fnr(company_fnr):
    client = create_client()

    suche_params = {
        "FNR": company_fnr,
        "STICHTAG": date.today(),
        "UMFANG": "Kurzinformation"
    }

    suche_response = client.service.AUSZUG_V2_(**suche_params)

    firma = suche_response.FIRMA

    legal_form_entry = firma.FI_DKZ07 if len(firma.FI_DKZ07) > 0 else None

    return {
        "fnr": company_fnr,
        "name": firma.FI_DKZ02[0].BEZEICHNUNG,
        "location": firma.FI_DKZ06[0].SITZ,
        "legal_form": {"code": legal_form_entry.RECHTSFORM.CODE, "text": legal_form_entry.RECHTSFORM.TEXT} if legal_form_entry else None,
        "legal_status": "active" if legal_form_entry and legal_form_entry.AUFRECHT else "inactive"
    }
from client import create_client


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
            "status": ergebnis.STATUS,
            "name": ergebnis.NAME,
            "location": ergebnis.SITZ,
            "legal_form": {"code": ergebnis.RECHTSFORM.CODE, "text": ergebnis.RECHTSFORM.TEXT},
            "legal_status": ergebnis.RECHTSEIGENSCHAFT,
            "responsible_court": {"code": ergebnis.GERICHT.CODE, "text": ergebnis.GERICHT.TEXT}
        }
        results.append(company_info)


    return results

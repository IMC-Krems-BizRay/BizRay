from .client import create_client
import datetime

def basic_company_info(fnr: str):
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
    data = {
        'basic_info': {
            'company_name': info.FIRMA.FI_DKZ02[0].BEZEICHNUNG[0],
            'legal_form': info.FIRMA.FI_DKZ07[0].RECHTSFORM.TEXT,
            'company_number': info.FNR,
            'european_id': info.EUID[0].EUID,
        },
        'location': extract_location_info(info),
        'management': extract_management_info(info),
        #'financial': DO LATER!,
        'history': extract_company_history(info),
    }

    return data




def extract_location_info(info):
    address = info.FIRMA.FI_DKZ03[0]

    data = {
        'street': address.STELLE,
        'house_number': address.HAUSNUMMER,
        'postal_code': address.PLZ,
        'city': address.ORT,
        'country':  address.STAAT
    }

    return data

def extract_management_info(info):


    people = []
    for i in info.FUN:


        pnr = i.PNR
        personal_info = next(j for j in info.PER if j.PNR == pnr) #easier
        print(personal_info)

        if personal_info:
            data = {
                'PNR': pnr, #not globally unique
                'name': personal_info.PE_DKZ02[0].NAME_FORMATIERT[0],
                'DOB': personal_info.PE_DKZ02[0].GEBURTSDATUM,
                'role': i.FKENTEXT,
                'appointed_on': i.FU_DKZ10[0].DATVON,
            }
            people.append(data)


    return people



def extract_company_history(info):
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





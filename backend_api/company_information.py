import xml.etree.ElementTree as ET
from .client import create_client
import datetime
from charset_normalizer import from_bytes

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
        location: str,
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
            'company_name': info.FIRMA.FI_DKZ02[0].BEZEICHNUNG[0] if len(info.FIRMA.FI_DKZ02) > 0 else "NO DATA",
            'legal_form': info.FIRMA.FI_DKZ07[0].RECHTSFORM.TEXT if len(info.FIRMA.FI_DKZ07) > 0 else "NO DATA",
            'company_number': info.FNR,
            'european_id': info.EUID[0].EUID if len(info.EUID) > 0 else "NO DATA",
        },
        # move location in basic_info since it's just a string?
        'location': extract_location_info(info),
        'management': extract_management_info(info),
        'financial': get_document_data(info.FNR),
        'history': extract_company_history(info),
    }

    return data

def extract_location_info(info):
    if len(info.FIRMA.FI_DKZ03) < 1:
        return "NO DATA"

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
    if len(info.FUN)  < 1:
        return "NO DATA"

    people = []
    for i in info.FUN:
        pnr = i.PNR
        personal_info = next(j for j in info.PER if j.PNR == pnr) #easier
        #print(personal_info)

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
    if len(info.VOLLZ) < 1:
        return "NO DATA"

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


def get_document_data(fnr):
    client = create_client()

    suche_params = {
        "FNR": fnr,
        "AZ": ""
    }
    res = client.service.SUCHEURKUNDE(**suche_params).ERGEBNIS


    doc_ids = [i.KEY for i in res if 'XML' in i.KEY]
    if not doc_ids:
        return {
            'director_name': "NO XML DATA",
            'total_assets': "NO XML DATA"
        }

    xml_content = get_xml_data(doc_ids[0]) #for now


    #print(type(xml_content))
    root = ET.fromstring(xml_content)


    ns = {'ns0': 'https://finanzonline.bmf.gv.at/bilanz'}

   # print("All elements in root:")
    #for e in root.iter():
   #     print(e.tag)
  #  print('----------------------------------------------------------------')


    data = {
        'director_name': root.find('.//ns0:UNTER/ns0:V_NAME', ns).text + " " + root.find('.//ns0:UNTER/ns0:Z_NAME', ns).text,
        'total_assets': root.find('.//ns0:HGB_224_2/ns0:POSTENZEILE/ns0:BETRAG', ns).text,
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
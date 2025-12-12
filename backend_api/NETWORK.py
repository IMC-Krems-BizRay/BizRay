from neo4j import GraphDatabase
import json
from backend_api.config import DB_USER, DB_PASS, URI, DB
 
driver = GraphDatabase.driver(URI, auth=(DB_USER, DB_PASS))

def make_manager_key(m):
    date_of_birth = m["date_of_birth"]
    if not date_of_birth:
        return "Date of birth is unavailable"

    name = m["name"]
    return f'{date_of_birth}|{name}'.strip()


#TODO: This doesn't always work properly
def make_address_key(loc):
    if not loc:
        return "Unknown Address"

    street = (loc.get("street") or "").strip()
    house_number = (loc.get("house_number") or "").strip()
    postal_code = (loc.get("postal_code") or "").strip()
    city = (loc.get("city") or "").strip()

    parts = []

    line1 = " ".join(p for p in [street, house_number] if p)
    if line1:
        parts.append(line1)

    line2 = " ".join(p for p in [postal_code, city] if p)
    if line2:
        parts.append(line2)

    if not parts:
        return "Unknown Address"

    return ", ".join(parts)



#THIS SHOULD ONLY BE RUN AT THE START!
def create_indexes():
    cypher_list = [
        "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_id IS UNIQUE",
        "CREATE CONSTRAINT manager_key_unique IF NOT EXISTS FOR (m:Manager) REQUIRE m.manager_key IS UNIQUE",
        "CREATE CONSTRAINT address_key_unique IF NOT EXISTS FOR (a:Address) REQUIRE a.address_key IS UNIQUE"
    ]

    with driver.session(database=DB) as session:
        for c in cypher_list:
            session.run(c)


#todo: this is just to confirm functionality, must correct it later
def get_risk_indicators(data):
    '''
    company_id

    company_name


     #Status: active / not active
     #last submitted XML report: 20XX
     financial indicators classified red: x/8
     #missing reporting years: x/8
    # profit/loss 20xx: xx
    '''

    company_id = data["basic_info"]["company_number"]
    company_name = data["basic_info"]["company_name"]
    is_deleted = data["basic_info"]["is_deleted"]

    if not data["financial"]:
        return {
            "company_id": company_id,
            "company_name": company_name,
            "deleted": is_deleted,
            "error": "Financial data is unavailable"
        }
   
    last_filed_doc = data["financial"][-1]["submission_date"] #most recent year
    missing_years = data["compliance_indicators"]["missing_reporting_years"]
    profit_loss = data["financial"][-1]["profit_loss"] 

    return {
        "company_id": company_id,
        "company_name": company_name,
        "deleted": is_deleted,
        "last_file": last_filed_doc,
        "missing_years": missing_years,
        "profit_loss": profit_loss
    }


def CREATE_COMPANY(data):


    #data = company_json["result"]
    #print(data)
    company_id = data["basic_info"]["company_number"]


    mgr_keys = [make_manager_key(m) for m in data["management"]]

    addr_key = make_address_key(data.get("location"))

    glance = json.dumps(get_risk_indicators(data))
    #print(glance)

    information = json.dumps(data)
    cypher = """
    MERGE (c:Company {company_id: $company_id})
      SET c.data = $information
      SET c.glance = $glance

    MERGE (a:Address {address_key: $addr_key})
    MERGE (c)-[:LOCATED_AT]->(a)

    WITH c
    UNWIND $mgr_keys AS mk
      MERGE (m:Manager {manager_key: mk})
      MERGE (c)-[:HAS_MANAGER]->(m)

    RETURN c
    """

    with driver.session(database=DB) as session:
        session.run(
            cypher,
            company_id=company_id,
            information = information,
            addr_key=addr_key,
            mgr_keys=mgr_keys,
            glance = glance
        )
        #print('created company!')


def SEARCH_COMPANY(company_id):

    #print(company_id)
    #TODO: this doesn't seem like the best way of doing this
    company_id = company_id[:-1] + " " + company_id[-1]
    #print(company_id)

    #Debugging
    #with driver.session(database=DB) as session:
     #   all_companies = session.run("MATCH (c:Company) RETURN c.company_id AS id").values()
      #  print(f"All company IDs in DB: {all_companies}")



    cypher = """
    MATCH (c:Company {company_id: $company_id})
    RETURN c.data AS data
    """

    with driver.session(database=DB) as session:
        result = session.run(
            cypher, company_id=company_id).single()
        #print(result)

        if result:
            data_str = result["data"]
            return json.loads(data_str) if data_str else None
        return None


def GET_NEIGHBOURS(node_id, label):
    '''
    label: Company
    node_id: FNR
    '''
    #print(label, node_id)
    #todo
    node_type = {
        "Company": "company_id",
        "Address": "address_key",
        "Manager": "manager_key"
    }



    cypher = f"""
        MATCH (n:{label} {{{node_type[label]}: $node_id}})--(connected)
        
        RETURN
        CASE
             WHEN 'Company' IN labels(connected) THEN connected.glance
             ELSE connected
             END AS result
        """





    with driver.session(database=DB) as session:
        result = session.run(cypher, node_id=node_id).data()
        print(result)
        return result


if __name__ == "__main__":
    driver.verify_connectivity()
    #create_indexes()

    #SEARCH_COMPANY("583360h")

    print(GET_NEIGHBOURS("1963-05-06|Gerardus van Loon", "Manager"))



    with driver.session(database=DB) as s:
        res = s.run("MATCH (c:Company) RETURN count(c) AS cnt").single()
        print("company count (read check):", res["cnt"])




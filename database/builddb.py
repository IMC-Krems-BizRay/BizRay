import zipfile
import io
import json
import os
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET
import datetime
from types import SimpleNamespace


BATCH_SIZE = 1000
PROGRESS_FILE = "progress.txt"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "test1234567")


driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=NEO4J_AUTH,
)


CYPHER = """
UNWIND $rows AS row

MERGE (c:Company {company_id: row.company_id})
SET c.data   = row.information,
    c.glance = row.glance,
    c.updated_at = $datetime

MERGE (a:Address {address_key: row.addr_key})
MERGE (c)-[:LOCATED_AT]->(a)

WITH c, row
UNWIND row.mgr_keys AS mk
  MERGE (m:Manager {manager_key: mk})
  MERGE (c)-[:HAS_MANAGER]->(m)
"""


def write_batch(batch):
    with driver.session() as session:
        session.run(
            CYPHER, rows=batch, datetime=datetime.datetime(2000, 1, 1).timestamp()
        )  # if it breaks we can blame y2k


# in case of crash
def load_processed():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(company_ids):
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        for fnr in company_ids:
            f.write(fnr + "\n")


def json_date(date):
    """
    Convert YYYYMMDD to YYYY-MM-DD
    """
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


# namespace
NS = {"ns1": "ns://firmenbuch.justiz.gv.at/Abfrage/v2/AuszugResponse"}


def extract_glance(root):
    firma = root.find("ns1:FIRMA", NS)
    company_name_elem = firma.find("ns1:FI_DKZ02/ns1:BEZEICHNUNG", NS)
    legal_form_elem = firma.find("ns1:FI_DKZ07/ns1:RECHTSFORM/ns1:TEXT", NS)
    euid_elem = root.find("ns1:EUID/ns1:EUID", NS)

    company_number = root.attrib.get(
        "{ns://firmenbuch.justiz.gv.at/Abfrage/v2/AuszugResponse}FNR"
    )

    return {
        "company_id": company_number,
        "company_name": (
            company_name_elem.text if company_name_elem is not None else None
        ),
        "legal_form": legal_form_elem.text if legal_form_elem is not None else None,
        "company_number": company_number,
        "european_id": euid_elem.text if euid_elem is not None else None,
    }


def extract_location_info(root):
    fi_dkz03 = root.find("ns1:FIRMA/ns1:FI_DKZ03", NS)
    if fi_dkz03 is not None:
        street = ", ".join(
            i.text
            for i in (
                fi_dkz03.findall("ns1:STRASSE", NS) + fi_dkz03.findall("ns1:STELLE", NS)
            )
            if i.text
        )

        house_no = fi_dkz03.findtext("ns1:HAUSNUMMER", default="", namespaces=NS)
        plz = fi_dkz03.findtext("ns1:PLZ", default="", namespaces=NS)
        city = fi_dkz03.findtext("ns1:ORT", default="", namespaces=NS)

        left = " ".join(i for i in [street, house_no] if i).strip()
        right = " ".join(i for i in [plz, city] if i).strip()

        if left and right:
            return f"{left}, {right}"
        return left or right or None

    fi_dkz06 = root.find("ns1:FIRMA/ns1:FI_DKZ06", NS)
    if fi_dkz06 is not None:
        city = fi_dkz06.findtext(
            "ns1:SITZ", default=None, namespaces=NS
        ) or fi_dkz06.findtext("ns1:ORTNR/ns1:TEXT", default=None, namespaces=NS)
        return city

    return None


def extract_management_info(root):
    management_list = []

    persons = {
        p.attrib.get("{ns://firmenbuch.justiz.gv.at/Abfrage/v2/AuszugResponse}PNR"): p
        for p in root.findall("ns1:PER", NS)
    }

    for fun in root.findall("ns1:FUN", NS):
        pnr = fun.attrib.get(
            "{ns://firmenbuch.justiz.gv.at/Abfrage/v2/AuszugResponse}PNR"
        )

        person = persons.get(pnr)
        if person is None:
            continue

        pe_dkz02 = person.find("ns1:PE_DKZ02", NS)
        if pe_dkz02 is None:
            continue

        name = pe_dkz02.findtext("ns1:NAME_FORMATIERT", default=None, namespaces=NS)

        if not name:
            first = pe_dkz02.findtext("ns1:VORNAME", "", NS)
            last = pe_dkz02.findtext("ns1:NACHNAME", "", NS)
            name = f"{first} {last}".strip() or None

        dob = pe_dkz02.findtext("ns1:GEBURTSDATUM", default=None, namespaces=NS)
        dob = json_date(dob) if dob else ""

        if name:
            management_list.append(f"{dob}|{name}")

    return management_list


def find_zip_path():
    for filename in os.listdir("."):
        if filename.startswith("auszuege") and filename.endswith(".zip"):
            return filename
    raise Exception("Zip could not be found")


def process_zip(zip_path, processed):
    batch = []
    total = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue

            if not entry.filename.endswith(".xml"):
                continue

            with zf.open(entry) as f:
                try:
                    root = ET.fromstring(f.read())
                except ET.ParseError:
                    continue

                glance = extract_glance(root)
                company_id = glance["company_number"]

                if not company_id or company_id in processed:
                    continue

                location = extract_location_info(root)
                managers = extract_management_info(root)

                row = {
                    "company_id": company_id,
                    "information": json.dumps(
                        {"glance": glance, "location": location, "management": managers}
                    ),
                    "glance": json.dumps(glance),
                    "addr_key": location or "UNKNOWN",
                    "mgr_keys": managers,
                }

                batch.append(row)

                if len(batch) >= BATCH_SIZE:
                    write_batch(batch)
                    mark_processed([r["company_id"] for r in batch])
                    processed.update(r["company_id"] for r in batch)
                    total += len(batch)
                    print(f"Inserted {total} companies")
                    batch.clear()

    if batch:
        write_batch(batch)
        mark_processed(r["company_id"] for r in batch)
        total += len(batch)
        print(f"Inserted {total} companies (final)")


if __name__ == "__main__":
    zip_path = find_zip_path()
    processed = load_processed()
    process_zip(zip_path, processed)
    driver.close()

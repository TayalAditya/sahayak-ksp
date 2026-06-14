"""
Create Catalyst Data Store tables and upload the crime dataset.

Run after deploying to Catalyst:
    python tools/catalyst_datastore_setup.py

Uses the Catalyst REST API to:
  1. Create all 17 tables (mirroring schema.sql)
  2. Upload CSV data from data/csv/ via bulk insert
"""

import csv, json, os, sys, urllib.request, urllib.parse, urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.engine import config
config.load_dotenv()

PROJECT_ID = config.get("CATALYST_PROJECT_ID")
ORG_ID     = config.get("ZOHO_ORG_ID")
DC         = config.get("ZOHO_DC", "in")
CSV_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "csv")

def get_token():
    from backend.engine.llm import CatalystQwenProvider
    p = CatalystQwenProvider()
    p._refresh_access_token()
    return p._access_token

def api(method, path, body=None, token=None):
    url = f"https://api.catalyst.zoho.{DC}/baas/v1/project/{PROJECT_ID}/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json",
        "CATALYST-ORG": ORG_ID,
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:200]}

# ZCQL column type mappings from SQLite types
TYPE_MAP = {"INTEGER": "number", "TEXT": "string", "REAL": "number"}

# Table definitions: (table_name, [(col_name, catalyst_type), ...])
TABLES = [
    ("districts",            [("name","string"),("name_kn","string"),("region","string"),("population","number"),("urbanization","string")]),
    ("police_stations",      [("code","string"),("name","string"),("name_kn","string"),("district_id","number"),("latitude","number"),("longitude","number")]),
    ("legal_sections",       [("act","string"),("section_code","string"),("crime_head","string"),("title","string"),("is_cognizable","number"),("is_violent","number")]),
    ("ipc_bns_map",          [("ipc_section_id","number"),("bns_section_id","number"),("crime_head","string")]),
    ("persons",              [("full_name","string"),("full_name_kn","string"),("gender","string"),("age","number"),("occupation","string"),("education_level","string"),("income_band","string"),("address","string"),("district_id","number"),("phone","string"),("is_repeat_offender","number")]),
    ("firs",                 [("fir_number","string"),("police_station_id","number"),("district_id","number"),("reported_date","string"),("occurrence_date","string"),("occurrence_time","string"),("crime_head","string"),("modus_operandi","string"),("description","string"),("latitude","number"),("longitude","number"),("status","string"),("investigating_officer","string")]),
    ("fir_sections",         [("fir_id","number"),("legal_section_id","number")]),
    ("fir_persons",          [("fir_id","number"),("person_id","number"),("role","string")]),
    ("arrests",              [("person_id","number"),("fir_id","number"),("arrest_date","string"),("bail_status","string")]),
    ("associations",         [("person_a_id","number"),("person_b_id","number"),("association_type","string"),("gang_name","string"),("strength","number")]),
    ("vehicles",             [("registration_no","string"),("type","string"),("make","string"),("color","string"),("owner_person_id","number")]),
    ("fir_vehicles",         [("fir_id","number"),("vehicle_id","number"),("role","string")]),
    ("properties",           [("fir_id","number"),("type","string"),("description","string"),("value_inr","number"),("status","string")]),
    ("financial_accounts",   [("person_id","number"),("account_no_masked","string"),("bank","string"),("account_type","string")]),
    ("transactions",         [("from_account_id","number"),("to_account_id","number"),("amount_inr","number"),("txn_date","string"),("channel","string"),("is_flagged","number"),("linked_fir_id","number")]),
    ("investigation_events", [("fir_id","number"),("event_date","string"),("event_type","string"),("note","string")]),
    ("users",                [("name","string"),("role","string"),("police_station_id","number"),("district_id","number"),("username","string")]),
    ("audit_log",            [("user_id","number"),("asked_at","string"),("nl_question","string"),("generated_query","string"),("row_count","number"),("role_at_time","string")]),
]

def upload_csv(table_name, token, batch=200):
    csv_path = os.path.join(CSV_DIR, f"{table_name}.csv")
    if not os.path.exists(csv_path):
        print(f"  [skip] no CSV for {table_name}")
        return
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"  {table_name}: uploading {len(rows)} rows...", end=" ")
    ok = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i+batch]
        result = api("POST", f"table/{table_name}/row", body=chunk, token=token)
        if "error" not in result:
            ok += len(chunk)
    print(f"{ok} OK")

def main():
    print("Catalyst Data Store setup — Sahayak")
    token = get_token()
    print(f"Token: {token[:20]}...\n")

    # 1. Create tables
    print("Creating tables...")
    for tname, cols in TABLES:
        col_defs = [{"column_name": c, "data_type": t} for c, t in cols]
        result = api("POST", "table", body={"table_name": tname, "columns": col_defs}, token=token)
        status = "OK" if "error" not in result else f"SKIP/EXISTS ({result.get('error','')})"
        print(f"  {tname}: {status}")

    # 2. Upload data
    print("\nUploading CSV data...")
    for tname, _ in TABLES:
        upload_csv(tname, token)

    print("\nDone. Verify in Catalyst console → Data Store.")

if __name__ == "__main__":
    main()

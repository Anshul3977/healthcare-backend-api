"""
Healthcare API Test Script (Enhanced)
======================================
Creates 5 patients, 3 doctors, assigns multiple doctors to each patient,
and prints a summary table of all relationships.

Usage:
    python test_api.py                          # default localhost:8000
    python test_api.py http://your-server:port  # custom base URL
"""

import sys
import json
import urllib.request
import urllib.error
import random

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
API = f"{BASE_URL}/api"

# ── Helpers ──────────────────────────────────────────────────────────

def pretty(data):
    return json.dumps(data, indent=2, default=str)

def api_call(method, url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

def report(label, status, body, verbose=True):
    icon = "✅" if 200 <= status < 300 else "❌"
    print(f"\n{icon}  {label}  [HTTP {status}]")
    if verbose:
        print(pretty(body))
    return 200 <= status < 300

# ── Test Data ────────────────────────────────────────────────────────

PATIENTS = [
    {
        "first_name": "John",    "last_name": "Doe",
        "date_of_birth": "1990-05-15", "gender": "M",
        "phone": "9876543210",
        "address": "123 Health St, Medical City",
        "medical_history": "No known allergies"
    },
    {
        "first_name": "Sarah",   "last_name": "Johnson",
        "date_of_birth": "1985-08-22", "gender": "F",
        "phone": "9876543220",
        "address": "456 Wellness Ave, Health Town",
        "medical_history": "Mild asthma"
    },
    {
        "first_name": "Raj",     "last_name": "Patel",
        "date_of_birth": "1978-11-03", "gender": "M",
        "phone": "9876543230",
        "address": "789 Care Blvd, Healing City",
        "medical_history": "Type 2 diabetes, controlled"
    },
    {
        "first_name": "Emily",   "last_name": "Chen",
        "date_of_birth": "2000-02-14", "gender": "F",
        "phone": "9876543240",
        "address": "321 Recovery Rd, Cure Town",
        "medical_history": "None"
    },
    {
        "first_name": "Alex",    "last_name": "Rivera",
        "date_of_birth": "1995-07-30", "gender": "O",
        "phone": "9876543250",
        "address": "654 Therapy Ln, Remedy City",
        "medical_history": "Seasonal allergies, minor surgery 2020"
    },
]

DOCTORS = [
    {
        "first_name": "Jane",    "last_name": "Smith",
        "specialization": "Cardiology",
        "phone": "9876543311",
        "email": "dr.jane.smith@hospital.com",
        "years_of_experience": 12
    },
    {
        "first_name": "Michael", "last_name": "Brown",
        "specialization": "Neurology",
        "phone": "9876543312",
        "email": "dr.michael.brown@hospital.com",
        "years_of_experience": 8
    },
    {
        "first_name": "Priya",   "last_name": "Sharma",
        "specialization": "Orthopedics",
        "phone": "9876543313",
        "email": "dr.priya.sharma@hospital.com",
        "years_of_experience": 15
    },
]

# Assignment plan: each patient gets 2 doctors
ASSIGNMENTS = [
    (0, 0, "Primary cardiologist"),
    (0, 1, "Neurological evaluation"),
    (1, 0, "Cardiac screening"),
    (1, 2, "Joint pain assessment"),
    (2, 1, "Neuropathy consultation"),
    (2, 2, "Knee replacement follow-up"),
    (3, 0, "Annual heart screening"),
    (3, 1, "Migraine management"),
    (4, 1, "Headache evaluation"),
    (4, 2, "Spine consultation"),
]

# ══════════════════════════════════════════════════════════════════════
#  Main test flow
# ══════════════════════════════════════════════════════════════════════

# unique email so re-runs don't collide
EMAIL = f"testuser_{random.randint(1000,9999)}@test.com"

section("1. Register user")
status, body = api_call("POST", f"{API}/auth/register/", {
    "name": "Test User", "email": EMAIL,
    "password": "Test123!", "password2": "Test123!"
})
report("Register", status, body)

section("2. Login")
status, body = api_call("POST", f"{API}/auth/login/", {
    "email": EMAIL, "password": "Test123!"
})
report("Login", status, body)
TOKEN = body.get("tokens", {}).get("access", "")
if not TOKEN:
    print("⚠️  No token — aborting"); sys.exit(1)
print(f"🔑  Token saved (first 40 chars): {TOKEN[:40]}…")

# ── Create patients ──────────────────────────────────────────────────

section("3. Create 5 patients")
patient_ids = []
for p in PATIENTS:
    status, body = api_call("POST", f"{API}/patients/", p, token=TOKEN)
    ok = report(f"Patient: {p['first_name']} {p['last_name']}", status, body, verbose=False)
    if ok:
        patient_ids.append(body["id"])
        print(f"   📋  ID = {body['id']}")
    else:
        patient_ids.append(None)
        print(f"   ⚠️  Response: {body}")

# ── Create doctors ───────────────────────────────────────────────────

section("4. Create 3 doctors")
doctor_ids = []
for d in DOCTORS:
    status, body = api_call("POST", f"{API}/doctors/", d, token=TOKEN)
    ok = report(f"Doctor: Dr. {d['first_name']} {d['last_name']} ({d['specialization']})", status, body, verbose=False)
    if ok:
        doctor_ids.append(body["id"])
        print(f"   🩺  ID = {body['id']}")
    else:
        doctor_ids.append(None)
        print(f"   ⚠️  Response: {body}")

# ── Create mappings ──────────────────────────────────────────────────

section("5. Assign doctors to patients (10 mappings)")
mapping_ids = []
for pi, di, notes in ASSIGNMENTS:
    pid = patient_ids[pi]
    did = doctor_ids[di]
    if pid is None or did is None:
        print(f"   ⚠️  Skipped — missing patient or doctor")
        continue
    status, body = api_call("POST", f"{API}/mappings/", {
        "patient": pid, "doctor": did, "notes": notes
    }, token=TOKEN)
    pname = f"{PATIENTS[pi]['first_name']} {PATIENTS[pi]['last_name']}"
    dname = f"Dr. {DOCTORS[di]['first_name']} {DOCTORS[di]['last_name']}"
    ok = report(f"{pname} → {dname}", status, body, verbose=False)
    if ok:
        mapping_ids.append(body["id"])
    else:
        print(f"   ⚠️  {body}")

# ── List patients ────────────────────────────────────────────────────

section("6. List all patients")
status, body = api_call("GET", f"{API}/patients/", token=TOKEN)
report("List Patients", status, body, verbose=False)
results = body.get("results", [])
print(f"   Total patients returned: {len(results)}")

# ── Get doctors for each patient ─────────────────────────────────────

section("7. Doctors assigned to each patient")
for i, pid in enumerate(patient_ids):
    if pid is None:
        continue
    status, body = api_call("GET", f"{API}/mappings/patient/{pid}/", token=TOKEN)
    pname = f"{PATIENTS[i]['first_name']} {PATIENTS[i]['last_name']}"
    docs = body.get("doctors", [])
    doc_names = [d.get("doctor_name", "?") for d in docs]
    print(f"   📋  {pname} (ID {pid}) → {', '.join(doc_names) if doc_names else 'none'}")

# ══════════════════════════════════════════════════════════════════════
#  Summary Table
# ══════════════════════════════════════════════════════════════════════

section("Summary Table")

# Column widths
W_PAT  = 20
W_DOC  = 35
W_NOTE = 30

hdr = f"{'Patient':<{W_PAT}} │ {'Doctor':<{W_DOC}} │ {'Notes':<{W_NOTE}}"
sep = f"{'─'*W_PAT}─┼─{'─'*W_DOC}─┼─{'─'*W_NOTE}"
print(hdr)
print(sep)

for pi, di, notes in ASSIGNMENTS:
    pid = patient_ids[pi]
    did = doctor_ids[di]
    if pid is None or did is None:
        continue
    pname = f"{PATIENTS[pi]['first_name']} {PATIENTS[pi]['last_name']}"
    dname = f"Dr. {DOCTORS[di]['first_name']} {DOCTORS[di]['last_name']} ({DOCTORS[di]['specialization'][:10]})"
    print(f"{pname:<{W_PAT}} │ {dname:<{W_DOC}} │ {notes:<{W_NOTE}}")

print(f"\n✅  Done — {len(patient_ids)} patients, {len(doctor_ids)} doctors, {len(mapping_ids)} mappings created.")

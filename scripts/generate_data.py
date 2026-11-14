"""
Generates the synthetic healthcare claims dataset used in this project.

All data is fake. No real patients, providers or payers.
The random seed is fixed, so running the script again gives the same CSV files.

Usage:
    python scripts/generate_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 7
NUM_PATIENTS = 200
NUM_CLAIMS = 1000
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 6, 30)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

random.seed(SEED)

# ---------------------------------------------------------------------------
# Procedures (CPT codes). The charges are rounded, illustrative values.
# ---------------------------------------------------------------------------
PROCEDURES = [
    # cpt_code, description, service_type, standard_charge
    ("99213", "Office visit, established patient, low complexity", "Office Visit", 150),
    ("99214", "Office visit, established patient, moderate complexity", "Office Visit", 220),
    ("99215", "Office visit, established patient, high complexity", "Office Visit", 300),
    ("99203", "Office visit, new patient, low complexity", "Office Visit", 200),
    ("71046", "Chest X-ray, 2 views", "Imaging", 320),
    ("72148", "MRI lumbar spine without contrast", "Imaging", 1200),
    ("74177", "CT abdomen and pelvis with contrast", "Imaging", 1500),
    ("93000", "Electrocardiogram (ECG), complete", "Cardiology", 210),
    ("93306", "Echocardiogram, complete", "Cardiology", 950),
    ("97110", "Therapeutic exercises, 15 minutes", "Physical Therapy", 180),
    ("97140", "Manual therapy, 15 minutes", "Physical Therapy", 160),
    ("80053", "Comprehensive metabolic panel", "Lab", 90),
    ("85025", "Complete blood count (CBC)", "Lab", 60),
]

# Which specialty performs which service types.
SPECIALTY_SERVICES = {
    "Family Medicine": ["Office Visit", "Lab"],
    "Internal Medicine": ["Office Visit", "Lab"],
    "Radiology": ["Imaging"],
    "Cardiology": ["Cardiology", "Office Visit"],
    "Physical Therapy": ["Physical Therapy"],
}

PROVIDERS = [
    # provider_id, provider_name, specialty, state
    ("PR001", "Sunrise Family Clinic", "Family Medicine", "TX"),
    ("PR002", "Lakeside Imaging", "Radiology", "FL"),
    ("PR003", "Northside Cardiology", "Cardiology", "TX"),
    ("PR004", "Bayview Physical Therapy", "Physical Therapy", "CA"),
    ("PR005", "Pine Valley Medical Group", "Internal Medicine", "AZ"),
    ("PR006", "Riverside Family Practice", "Family Medicine", "FL"),
    ("PR007", "Desert Sun Radiology", "Radiology", "AZ"),
    ("PR008", "Golden Coast Heart Center", "Cardiology", "CA"),
    ("PR009", "Harbor Rehab & Therapy", "Physical Therapy", "FL"),
    ("PR010", "Maple Street Clinic", "Family Medicine", "NY"),
    ("PR011", "Empire Diagnostic Imaging", "Radiology", "NY"),
    ("PR012", "Lone Star Internal Medicine", "Internal Medicine", "TX"),
    # PR013 exists but has no claims, on purpose (good for LEFT JOIN practice).
    ("PR013", "Westfield Physical Therapy", "Physical Therapy", "NY"),
]
PROVIDERS_WITH_CLAIMS = [p for p in PROVIDERS if p[0] != "PR013"]

# A few claims point to provider IDs that do not exist (orphan records).
ORPHAN_PROVIDER_IDS = ["PR099", "PR104"]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Carlos", "Maria", "Luis", "Ana", "Jorge", "Sofia", "Daniel",
    "Laura", "Kevin", "Emily", "Brian", "Ashley", "Anthony", "Michelle", "Elena", "Diego",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
]
STATES = ["TX", "FL", "CA", "NY", "AZ"]

# Share of each insurance plan, and the share of the billed amount it pays.
INSURANCE_PLANS = ["Medicare", "Medicaid", "Commercial"]
PLAN_WEIGHTS = [0.35, 0.25, 0.40]
PLAN_PAY_RATE = {"Medicare": (0.55, 0.65), "Medicaid": (0.45, 0.55), "Commercial": (0.70, 0.85)}

# Chance that a claim is denied. Imaging needs prior authorization more often,
# and Medicaid has more eligibility problems, so they are denied more.
BASE_DENIAL_RATE = {
    "Office Visit": 0.07,
    "Lab": 0.05,
    "Cardiology": 0.12,
    "Physical Therapy": 0.18,
    "Imaging": 0.26,
}
PLAN_DENIAL_EXTRA = {"Medicare": 0.00, "Medicaid": 0.10, "Commercial": 0.03}
PENDING_RATE = 0.06

DENIAL_REASONS = {
    "Imaging": ["Missing prior authorization"] * 6 + ["Service not covered"] * 2 + ["Patient not eligible"],
    "Physical Therapy": ["Missing prior authorization"] * 3 + ["Service not covered"] * 3 + ["Duplicate claim"],
    "default": ["Patient not eligible"] * 3 + ["Missing information"] * 3 + ["Duplicate claim"] + ["Service not covered"],
}


def random_date(start, end):
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def make_patients():
    patients = []
    for i in range(1, NUM_PATIENTS + 1):
        birth = random_date(date(1940, 1, 1), date(2005, 12, 31))
        plan = random.choices(INSURANCE_PLANS, PLAN_WEIGHTS)[0]
        # Most Medicare patients are 65 or older.
        if plan == "Medicare" and birth.year > 1961:
            birth = birth.replace(year=random.randint(1940, 1961))
        patients.append({
            "patient_id": f"PA{i:04d}",
            "patient_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "date_of_birth": birth.isoformat(),
            "insurance_plan": plan,
            "state": random.choice(STATES),
        })
    return patients


def make_claims(patients):
    procedures_by_type = {}
    for proc in PROCEDURES:
        procedures_by_type.setdefault(proc[2], []).append(proc)

    claims = []
    for i in range(1, NUM_CLAIMS + 1):
        patient = random.choice(patients)
        provider = random.choice(PROVIDERS_WITH_CLAIMS)
        service_type = random.choice(SPECIALTY_SERVICES[provider[2]])
        cpt_code, _, _, charge = random.choice(procedures_by_type[service_type])

        provider_id = provider[0]
        if random.random() < 0.006:
            provider_id = random.choice(ORPHAN_PROVIDER_IDS)

        billed = round(charge * random.uniform(0.95, 1.10))
        plan = patient["insurance_plan"]
        denial_chance = BASE_DENIAL_RATE[service_type] + PLAN_DENIAL_EXTRA[plan]

        roll = random.random()
        if roll < PENDING_RATE:
            status, paid, reason = "Pending", None, None
        elif roll < PENDING_RATE + denial_chance:
            reasons = DENIAL_REASONS.get(service_type, DENIAL_REASONS["default"])
            status, paid, reason = "Denied", 0, random.choice(reasons)
        else:
            low, high = PLAN_PAY_RATE[plan]
            status, paid, reason = "Paid", round(billed * random.uniform(low, high)), None

        claims.append({
            "patient_id": patient["patient_id"],
            "provider_id": provider_id,
            "date_of_service": random_date(START_DATE, END_DATE),
            "cpt_code": cpt_code,
            "billed_amount": billed,
            "paid_amount": paid,
            "claim_status": status,
            "denial_reason": reason,
        })

    # Claim IDs follow the date of service, like in a real billing system.
    claims.sort(key=lambda c: c["date_of_service"])
    numbered = []
    for i, c in enumerate(claims, start=1):
        c["date_of_service"] = c["date_of_service"].isoformat()
        numbered.append({"claim_id": f"CL{i:05d}", **c})
    return numbered


def write_csv(name, rows, columns):
    path = DATA_DIR / name
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    patients = make_patients()
    claims = make_claims(patients)

    providers = [dict(zip(["provider_id", "provider_name", "specialty", "state"], p)) for p in PROVIDERS]
    procedures = [dict(zip(["cpt_code", "description", "service_type", "standard_charge"], p)) for p in PROCEDURES]

    write_csv("patients.csv", patients, list(patients[0].keys()))
    write_csv("providers.csv", providers, list(providers[0].keys()))
    write_csv("procedures.csv", procedures, list(procedures[0].keys()))
    write_csv("claims.csv", claims, list(claims[0].keys()))


if __name__ == "__main__":
    main()

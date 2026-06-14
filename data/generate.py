"""
Sahayak — synthetic CCTNS-shaped crime dataset generator.

Pure Python standard library (no pip install needed). Deterministic (seeded), so every
run produces the same database — important for reproducible demos and tests.

Outputs:
  data/ksp_crime.db      SQLite database (schema from schema.sql)
  data/csv/*.csv         CSV export of every table (for Catalyst Data Store import)

Design intent (why the data looks the way it does):
  * IPC vs BNS:  BNS replaced the IPC on 2024-07-01. Each FIR is charged under IPC if it
                 occurred before that date, BNS if on/after. A query like "all theft cases"
                 must therefore span both codes — the cross-walk table makes that possible.
  * Networks:    ~15 gangs with shared co-offending, plus family/associate links, so the
                 criminal-network tool has real structure to surface.
  * Money trail: gang members funnel funds to a kingpin; some txns flagged + FIR-linked.
  * Seasonality: theft/burglary spike in the Oct–Nov festival season → visible trends.
  * Realism:     bilingual (EN + Kannada) names & districts, plausible Karnataka geography,
                 case status that ages over time (old cases mostly resolved).
"""

import csv
import os
import random
import sqlite3
from datetime import date, timedelta

# --------------------------------------------------------------------------- config
SEED = 20260614
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "ksp_crime.db")
CSV_DIR = os.path.join(HERE, "csv")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")

N_PERSONS = 6000
N_FIRS = 3500
N_VEHICLES = 2500
N_GANGS = 15

START = date(2019, 1, 1)
END = date(2026, 6, 10)
BNS_START = date(2024, 7, 1)  # IPC -> BNS transition

random.seed(SEED)

# --------------------------------------------------------------------------- reference data

# (name_en, name_kn, region, population, urbanization)
DISTRICTS = [
    ("Bengaluru Urban", "ಬೆಂಗಳೂರು ನಗರ", "South Karnataka", 9621551, "Urban"),
    ("Bengaluru Rural", "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ", "South Karnataka", 990923, "Semi-Urban"),
    ("Mysuru", "ಮೈಸೂರು", "South Karnataka", 3001127, "Urban"),
    ("Dakshina Kannada", "ದಕ್ಷಿಣ ಕನ್ನಡ", "Coastal Karnataka", 2089649, "Urban"),
    ("Belagavi", "ಬೆಳಗಾವಿ", "North Karnataka", 4779661, "Semi-Urban"),
    ("Dharwad", "ಧಾರವಾಡ", "North Karnataka", 1847023, "Urban"),
    ("Kalaburagi", "ಕಲಬುರಗಿ", "North Karnataka", 2566326, "Semi-Urban"),
    ("Ballari", "ಬಳ್ಳಾರಿ", "North Karnataka", 2452595, "Semi-Urban"),
    ("Vijayapura", "ವಿಜಯಪುರ", "North Karnataka", 2177331, "Rural"),
    ("Davanagere", "ದಾವಣಗೆರೆ", "Central Karnataka", 1945497, "Semi-Urban"),
    ("Shivamogga", "ಶಿವಮೊಗ್ಗ", "Central Karnataka", 1755512, "Semi-Urban"),
    ("Tumakuru", "ತುಮಕೂರು", "South Karnataka", 2678980, "Rural"),
    ("Udupi", "ಉಡುಪಿ", "Coastal Karnataka", 1177361, "Semi-Urban"),
    ("Hassan", "ಹಾಸನ", "South Karnataka", 1776421, "Rural"),
    ("Mandya", "ಮಂಡ್ಯ", "South Karnataka", 1805769, "Rural"),
    ("Kolar", "ಕೋಲಾರ", "South Karnataka", 1536401, "Rural"),
]

# approx district centroids (lat, lng) for plausible geo-clustering
DISTRICT_CENTER = {
    "Bengaluru Urban": (12.97, 77.59), "Bengaluru Rural": (13.20, 77.55),
    "Mysuru": (12.30, 76.64), "Dakshina Kannada": (12.87, 74.84),
    "Belagavi": (15.85, 74.50), "Dharwad": (15.46, 75.01),
    "Kalaburagi": (17.33, 76.83), "Ballari": (15.14, 76.92),
    "Vijayapura": (16.83, 75.71), "Davanagere": (14.47, 75.92),
    "Shivamogga": (13.93, 75.57), "Tumakuru": (13.34, 77.10),
    "Udupi": (13.34, 74.74), "Hassan": (13.00, 76.10),
    "Mandya": (12.52, 76.90), "Kolar": (13.13, 78.13),
}

AREA_WORDS = [
    "City", "Town", "Market", "Rural", "Cantonment", "Railway", "Industrial Area",
    "North", "South", "East", "West", "Extension", "Nagar", "Layout", "Cross",
]
BENGALURU_LOCALITIES = [
    "Whitefield", "Jayanagar", "Malleshwaram", "Indiranagar", "Koramangala",
    "Yelahanka", "Banashankari", "Hebbal", "Marathahalli", "Electronic City",
]

MALE_FIRST = [
    ("Manjunath", "ಮಂಜುನಾಥ"), ("Suresh", "ಸುರೇಶ್"), ("Ramesh", "ರಮೇಶ್"),
    ("Prakash", "ಪ್ರಕಾಶ್"), ("Mahesh", "ಮಹೇಶ್"), ("Ravi", "ರವಿ"),
    ("Kiran", "ಕಿರಣ್"), ("Naveen", "ನವೀನ್"), ("Santosh", "ಸಂತೋಷ್"),
    ("Girish", "ಗಿರೀಶ್"), ("Basavaraj", "ಬಸವರಾಜ್"), ("Shivakumar", "ಶಿವಕುಮಾರ್"),
    ("Nagaraj", "ನಾಗರಾಜ್"), ("Venkatesh", "ವೆಂಕಟೇಶ್"), ("Lokesh", "ಲೋಕೇಶ್"),
    ("Harish", "ಹರೀಶ್"), ("Anand", "ಆನಂದ್"), ("Mohan", "ಮೋಹನ್"),
    ("Vinay", "ವಿನಯ್"), ("Chandru", "ಚಂದ್ರು"), ("Praveen", "ಪ್ರವೀಣ್"),
    ("Yogesh", "ಯೋಗೇಶ್"), ("Darshan", "ದರ್ಶನ್"), ("Arun", "ಅರುಣ್"),
]
FEMALE_FIRST = [
    ("Lakshmi", "ಲಕ್ಷ್ಮಿ"), ("Geetha", "ಗೀತಾ"), ("Savitha", "ಸವಿತಾ"),
    ("Roopa", "ರೂಪಾ"), ("Pooja", "ಪೂಜಾ"), ("Divya", "ದಿವ್ಯಾ"),
    ("Ananya", "ಅನನ್ಯಾ"), ("Bhavya", "ಭವ್ಯಾ"), ("Kavya", "ಕಾವ್ಯಾ"),
    ("Shwetha", "ಶ್ವೇತಾ"), ("Nanda", "ನಂದಾ"), ("Sushma", "ಸುಷ್ಮಾ"),
    ("Rekha", "ರೇಖಾ"), ("Sridevi", "ಶ್ರೀದೇವಿ"), ("Mamatha", "ಮಮತಾ"),
    ("Vidya", "ವಿದ್ಯಾ"), ("Asha", "ಆಶಾ"), ("Deepa", "ದೀಪಾ"),
]
SURNAMES = [
    ("Gowda", "ಗೌಡ"), ("Shetty", "ಶೆಟ್ಟಿ"), ("Hegde", "ಹೆಗ್ಡೆ"),
    ("Rao", "ರಾವ್"), ("Kumar", "ಕುಮಾರ್"), ("Naik", "ನಾಯಕ್"),
    ("Patil", "ಪಾಟೀಲ್"), ("Reddy", "ರೆಡ್ಡಿ"), ("Murthy", "ಮೂರ್ತಿ"),
    ("Bhat", "ಭಟ್"), ("Acharya", "ಆಚಾರ್ಯ"), ("Kulkarni", "ಕುಲಕರ್ಣಿ"),
    ("Desai", "ದೇಸಾಯಿ"), ("Jain", "ಜೈನ್"), ("Pujari", "ಪೂಜಾರಿ"),
    ("Nayak", "ನಾಯಕ್"), ("Hiremath", "ಹಿರೇಮಠ"), ("Poojary", "ಪೂಜಾರಿ"),
]

OCCUPATIONS = [
    "Daily Wage Labourer", "Farmer", "Driver", "Shopkeeper", "Student",
    "Software Engineer", "Auto Driver", "Mechanic", "Unemployed", "Vendor",
    "Construction Worker", "Businessman", "Homemaker", "Security Guard", "Clerk",
]
EDUCATION = ["Illiterate", "Primary", "Secondary", "Higher Secondary", "Graduate", "Postgraduate"]
INCOME_BANDS = ["Low", "Lower-Middle", "Middle", "High"]

# (head, ipc_code, bns_code, cognizable, violent, weight)
CRIME_HEADS = [
    ("Theft", "379", "303(2)", 1, 0, 22),
    ("House-Breaking / Burglary", "457", "331(4)", 1, 0, 10),
    ("Robbery", "392", "309(4)", 1, 1, 7),
    ("Dacoity", "395", "310(2)", 1, 1, 2),
    ("Murder", "302", "103(1)", 1, 1, 3),
    ("Attempt to Murder", "307", "109", 1, 1, 3),
    ("Death by Negligence", "304A", "106(1)", 1, 0, 4),
    ("Grievous Hurt", "325", "117(2)", 1, 1, 5),
    ("Voluntarily Causing Hurt", "323", "115(2)", 0, 1, 6),
    ("Assault / Criminal Force", "352", "131", 1, 1, 4),
    ("Cheating", "420", "318(4)", 1, 0, 9),
    ("Criminal Breach of Trust", "406", "316(2)", 1, 0, 4),
    ("Extortion", "384", "308(2)", 1, 1, 3),
    ("Forgery", "465", "336(2)", 1, 0, 2),
    ("Kidnapping / Abduction", "363", "137(2)", 1, 1, 3),
    ("Rape", "376", "64", 1, 1, 2),
    ("Outraging Modesty of Woman", "354", "74", 1, 1, 3),
    ("Criminal Intimidation", "506", "351(2)", 0, 0, 4),
    ("Rioting", "147", "191(2)", 1, 1, 2),
    ("Mischief", "425", "324(4)", 0, 0, 3),
]
# Special acts — no IPC/BNS dual coding; section applies regardless of date.
SPECIAL_HEADS = [
    ("Cyber Fraud", "IT Act 66D", 1, 0, 6),
    ("Drug Offence (NDPS)", "NDPS Act 20", 1, 0, 4),
    ("Child Sexual Offence (POCSO)", "POCSO Act 8", 1, 1, 2),
]

MO_TEMPLATES = {
    "Theft": [
        "Two-wheeler parked outside residence stolen during night hours",
        "Mobile phone snatched in crowded market area",
        "Cash and valuables stolen from locked house",
        "Pickpocketing inside a crowded city bus",
    ],
    "House-Breaking / Burglary": [
        "House lock broken and gold ornaments stolen while family away",
        "Entry through rear window; cash and jewellery taken at night",
    ],
    "Robbery": [
        "Chain snatching by two persons on a motorcycle",
        "Cash robbed at knife-point near ATM",
    ],
    "Dacoity": [
        "Armed gang looted a jewellery shop in five-person group",
        "Highway dacoity targeting a goods truck",
    ],
    "Murder": [
        "Victim found dead with stab wounds following property dispute",
        "Homicide arising from prior enmity",
    ],
    "Cheating": [
        "Fraudulent investment scheme promising high returns",
        "Cheated by personation while selling a vehicle online",
    ],
    "Cyber Fraud": [
        "Victim duped via fake UPI payment link",
        "OTP fraud leading to unauthorised bank debit",
        "Fake job offer fraud collecting registration fees",
    ],
    "Extortion": [
        "Demand for protection money from local shopkeepers",
        "Threat calls demanding money citing old enmity",
    ],
}
DEFAULT_MO = ["Offence reported as per complainant statement", "Details under investigation"]

STATUSES = ["Under Investigation", "Charge-Sheeted", "Convicted", "Acquitted", "Closed-Undetected"]
BAIL_STATUSES = ["In Custody", "On Bail", "Absconding", "Released"]
VEHICLE_TYPES = ["Two-Wheeler", "Car", "Auto", "Truck"]
VEHICLE_MAKES = ["Honda", "Bajaj", "TVS", "Hero", "Maruti", "Hyundai", "Tata", "Mahindra", "Royal Enfield"]
COLORS = ["Black", "White", "Silver", "Red", "Blue", "Grey"]
PROPERTY_TYPES = ["Cash", "Gold", "Mobile", "Vehicle", "Documents", "Electronics"]
BANKS = ["SBI", "Canara Bank", "Karnataka Bank", "HDFC Bank", "ICICI Bank", "Union Bank", "Axis Bank"]
CHANNELS = ["UPI", "NEFT", "IMPS", "Cash Deposit"]
GANG_NAMES = [
    "Chikpet Gang", "KR Market Group", "Hosur Road Syndicate", "Vijayanagar Crew",
    "Peenya Network", "Majestic Gang", "Tilaknagar Group", "RT Nagar Syndicate",
    "Hubli Crew", "Mysuru Bandits", "Gulbarga Gang", "Mangaluru Network",
    "Yeshwanthpur Group", "Shivajinagar Crew", "Belagavi Syndicate",
]

# --------------------------------------------------------------------------- helpers

def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def iso(d):
    return d.isoformat()


def weighted_choice(items_with_weights):
    items, weights = zip(*items_with_weights)
    return random.choices(items, weights=weights, k=1)[0]


def jitter(center, spread=0.12):
    lat, lng = center
    return round(lat + random.uniform(-spread, spread), 5), round(lng + random.uniform(-spread, spread), 5)


def make_name(gender):
    pool = MALE_FIRST if gender == "Male" else FEMALE_FIRST
    fn_en, fn_kn = random.choice(pool)
    sn_en, sn_kn = random.choice(SURNAMES)
    return f"{fn_en} {sn_en}", f"{fn_kn} {sn_kn}"


def status_for(occurrence_d, has_accused):
    age_days = (END - occurrence_d).days
    if age_days < 120:
        return random.choices(["Under Investigation", "Charge-Sheeted"], weights=[85, 15])[0]
    if not has_accused:
        return random.choices(["Under Investigation", "Closed-Undetected"], weights=[40, 60])[0]
    if age_days < 365:
        return random.choices(["Under Investigation", "Charge-Sheeted"], weights=[40, 60])[0]
    return random.choices(
        ["Charge-Sheeted", "Convicted", "Acquitted", "Closed-Undetected"],
        weights=[35, 35, 20, 10],
    )[0]


# --------------------------------------------------------------------------- build

def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())

    # --- districts
    district_ids = {}
    for i, (name, kn, region, pop, urb) in enumerate(DISTRICTS, start=1):
        cur.execute(
            "INSERT INTO districts (id, name, name_kn, region, population, urbanization) VALUES (?,?,?,?,?,?)",
            (i, name, kn, region, pop, urb),
        )
        district_ids[name] = i

    # --- police stations (population-weighted count per district)
    stations = []  # (id, district_name, lat, lng)
    ps_id = 0
    for name, kn, region, pop, urb in DISTRICTS:
        d_id = district_ids[name]
        n_stations = max(3, min(10, pop // 600000))
        localities = BENGALURU_LOCALITIES if name.startswith("Bengaluru Urban") else AREA_WORDS
        used = random.sample(localities, min(n_stations, len(localities)))
        if len(used) < n_stations:
            used += [f"Zone {k}" for k in range(1, n_stations - len(used) + 1)]
        for area in used:
            ps_id += 1
            lat, lng = jitter(DISTRICT_CENTER[name], 0.15)
            code = f"{name[:3].upper()}-{area[:3].upper()}-{ps_id:02d}"
            cur.execute(
                "INSERT INTO police_stations (id, code, name, name_kn, district_id, latitude, longitude) VALUES (?,?,?,?,?,?,?)",
                (ps_id, code, f"{area} Police Station", f"{area} ಪೊಲೀಸ್ ಠಾಣೆ", d_id, lat, lng),
            )
            stations.append((ps_id, name, lat, lng))

    # --- legal sections + IPC<->BNS map
    sec_id = 0
    head_to_sections = {}  # head -> {'ipc': id, 'bns': id} or {'special': id}
    for head, ipc, bns, cog, viol, _w in CRIME_HEADS:
        sec_id += 1
        ipc_id = sec_id
        cur.execute(
            "INSERT INTO legal_sections (id, act, section_code, crime_head, title, is_cognizable, is_violent) VALUES (?,?,?,?,?,?,?)",
            (ipc_id, "IPC", ipc, head, f"IPC {ipc} — {head}", cog, viol),
        )
        sec_id += 1
        bns_id = sec_id
        cur.execute(
            "INSERT INTO legal_sections (id, act, section_code, crime_head, title, is_cognizable, is_violent) VALUES (?,?,?,?,?,?,?)",
            (bns_id, "BNS", bns, head, f"BNS {bns} — {head}", cog, viol),
        )
        cur.execute(
            "INSERT INTO ipc_bns_map (ipc_section_id, bns_section_id, crime_head) VALUES (?,?,?)",
            (ipc_id, bns_id, head),
        )
        head_to_sections[head] = {"ipc": ipc_id, "bns": bns_id}
    for head, code, cog, viol, _w in SPECIAL_HEADS:
        sec_id += 1
        cur.execute(
            "INSERT INTO legal_sections (id, act, section_code, crime_head, title, is_cognizable, is_violent) VALUES (?,?,?,?,?,?,?)",
            (sec_id, "SPECIAL", code, head, f"{code} — {head}", cog, viol),
        )
        head_to_sections[head] = {"special": sec_id}

    # --- persons
    person_district = {}
    for pid in range(1, N_PERSONS + 1):
        gender = random.choices(["Male", "Female", "Other"], weights=[68, 31, 1])[0]
        if gender == "Other":
            gender_for_name = random.choice(["Male", "Female"])
        else:
            gender_for_name = gender
        name_en, name_kn = make_name(gender_for_name)
        d_name = random.choices([d[0] for d in DISTRICTS], weights=[d[3] for d in DISTRICTS])[0]
        d_id = district_ids[d_name]
        person_district[pid] = d_id
        cur.execute(
            "INSERT INTO persons (id, full_name, full_name_kn, gender, age, occupation, education_level, income_band, address, district_id, phone, is_repeat_offender) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
            (
                pid, name_en, name_kn, gender, random.randint(18, 70),
                random.choice(OCCUPATIONS), random.choice(EDUCATION),
                random.choices(INCOME_BANDS, weights=[40, 30, 22, 8])[0],
                f"{random.randint(1, 250)}, {random.choice(AREA_WORDS)}, {d_name}",
                d_id, f"9{random.randint(100000000, 999999999)}",
            ),
        )

    # --- gangs (criminal networks)
    gang_members = {}  # gang_name -> [person_ids]
    assoc_id = 0
    all_persons = list(range(1, N_PERSONS + 1))
    used_for_gangs = set()
    for g in range(N_GANGS):
        gname = GANG_NAMES[g % len(GANG_NAMES)]
        size = random.randint(3, 7)
        members = random.sample(all_persons, size)
        gang_members[gname] = members
        used_for_gangs.update(members)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                assoc_id += 1
                cur.execute(
                    "INSERT INTO associations (id, person_a_id, person_b_id, association_type, gang_name, strength) VALUES (?,?,?,?,?,?)",
                    (assoc_id, members[i], members[j], "Gang Member", gname, random.randint(1, 5)),
                )

    organized_heads = {"Robbery", "Dacoity", "Extortion", "Theft", "Cyber Fraud", "House-Breaking / Burglary"}
    head_pool = [(h[0], h[5]) for h in CRIME_HEADS] + [(h[0], h[4]) for h in SPECIAL_HEADS]

    # --- FIRs + fir_sections + fir_persons + arrests + vehicles + property + events
    fir_year_counter = {}
    accused_count = {}        # person_id -> # accused roles  (for repeat-offender flag)
    coaccused_pairs = {}      # (a,b) -> shared fir count
    fir_id = 0
    fp_id = 0
    arrest_id = 0
    prop_id = 0
    event_id = 0
    veh_used = 0
    officer_names = [make_name("Male")[0] for _ in range(40)]

    # pre-create a vehicle pool
    vehicles = []  # vehicle_id
    for vid in range(1, N_VEHICLES + 1):
        owner = random.choice(all_persons)
        cur.execute(
            "INSERT INTO vehicles (id, registration_no, type, make, color, owner_person_id) VALUES (?,?,?,?,?,?)",
            (vid, f"KA{random.randint(1,70):02d}{random.choice('ABCDEFGHJKLMNPQR')}{random.choice('ABCDEFGHJKLMNPQR')}{random.randint(1000,9999)}",
             random.choice(VEHICLE_TYPES), random.choice(VEHICLE_MAKES), random.choice(COLORS), owner),
        )
        vehicles.append(vid)

    for _ in range(N_FIRS):
        fir_id += 1
        ps_id, d_name, ps_lat, ps_lng = random.choice(stations)
        d_id = district_ids[d_name]
        head = weighted_choice(head_pool)

        occ = rand_date(START, END)
        # seasonality: theft/burglary cluster in Oct-Nov festival season
        if head in ("Theft", "House-Breaking / Burglary") and random.random() < 0.4:
            yr = random.randint(START.year, END.year)
            mo = random.choice([10, 11])
            try:
                occ = date(yr, mo, random.randint(1, 28))
            except ValueError:
                pass
            if occ > END:
                occ = rand_date(START, END)
        reported = occ + timedelta(days=random.randint(0, 5))
        if reported > END:
            reported = END

        year = occ.year
        fir_year_counter[year] = fir_year_counter.get(year, 0) + 1
        fir_number = f"{fir_year_counter[year]:04d}/{year}"

        # accused assignment (drives network + status)
        accused = []
        solved_prob = 0.7 if head not in ("Theft", "House-Breaking / Burglary") else 0.45
        if random.random() < solved_prob:
            if head in organized_heads and random.random() < 0.45:
                gname = random.choice(list(gang_members.keys()))
                pool = gang_members[gname]
                k = min(len(pool), random.randint(2, 4))
                accused = random.sample(pool, k)
            else:
                accused = random.sample(all_persons, random.randint(1, 3))

        status = status_for(occ, bool(accused))
        lat, lng = jitter((ps_lat, ps_lng), 0.05)
        mo = random.choice(MO_TEMPLATES.get(head, DEFAULT_MO))
        io = random.choice(officer_names)
        cur.execute(
            "INSERT INTO firs (id, fir_number, police_station_id, district_id, reported_date, occurrence_date, occurrence_time, crime_head, modus_operandi, description, latitude, longitude, status, investigating_officer) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fir_id, fir_number, ps_id, d_id, iso(reported), iso(occ),
             f"{random.randint(0,23):02d}:{random.choice(['00','15','30','45'])}",
             head, mo, f"{head} reported at {d_name}. {mo}.", lat, lng, status, io),
        )

        # sections: IPC if pre-BNS, BNS if on/after; special acts always their own section
        secs = head_to_sections[head]
        if "special" in secs:
            cur.execute("INSERT INTO fir_sections (fir_id, legal_section_id) VALUES (?,?)", (fir_id, secs["special"]))
        else:
            chosen = secs["ipc"] if occ < BNS_START else secs["bns"]
            cur.execute("INSERT INTO fir_sections (fir_id, legal_section_id) VALUES (?,?)", (fir_id, chosen))

        # persons on the FIR
        victim = random.choice(all_persons)
        complainant = victim if random.random() < 0.7 else random.choice(all_persons)
        fp_id += 1
        cur.execute("INSERT INTO fir_persons (id, fir_id, person_id, role) VALUES (?,?,?,?)", (fp_id, fir_id, victim, "Victim"))
        fp_id += 1
        cur.execute("INSERT INTO fir_persons (id, fir_id, person_id, role) VALUES (?,?,?,?)", (fp_id, fir_id, complainant, "Complainant"))
        for a in accused:
            fp_id += 1
            cur.execute("INSERT INTO fir_persons (id, fir_id, person_id, role) VALUES (?,?,?,?)", (fp_id, fir_id, a, "Accused"))
            accused_count[a] = accused_count.get(a, 0) + 1
            # arrest record for some
            if status in ("Charge-Sheeted", "Convicted") or random.random() < 0.5:
                arrest_id += 1
                cur.execute(
                    "INSERT INTO arrests (id, person_id, fir_id, arrest_date, bail_status) VALUES (?,?,?,?,?)",
                    (arrest_id, a, fir_id, iso(occ + timedelta(days=random.randint(1, 40))),
                     random.choices(BAIL_STATUSES, weights=[25, 45, 15, 15])[0]),
                )
        # track co-accused pairs
        for i in range(len(accused)):
            for j in range(i + 1, len(accused)):
                key = tuple(sorted((accused[i], accused[j])))
                coaccused_pairs[key] = coaccused_pairs.get(key, 0) + 1

        # vehicles
        if head in ("Theft", "Robbery") and random.random() < 0.5:
            veh_used += 1
            cur.execute("INSERT INTO fir_vehicles (fir_id, vehicle_id, role) VALUES (?,?,?)",
                        (fir_id, random.choice(vehicles), "Stolen" if head == "Theft" else "Used in Crime"))

        # property
        if head in ("Theft", "Robbery", "House-Breaking / Burglary", "Dacoity"):
            for _ in range(random.randint(1, 3)):
                prop_id += 1
                ptype = random.choice(PROPERTY_TYPES)
                recovered = status in ("Charge-Sheeted", "Convicted") and random.random() < 0.5
                cur.execute(
                    "INSERT INTO properties (id, fir_id, type, description, value_inr, status) VALUES (?,?,?,?,?,?)",
                    (prop_id, fir_id, ptype, f"{ptype} reported in {head}",
                     round(random.uniform(2000, 500000), 2), "Recovered" if recovered else "Stolen"),
                )

        # investigation timeline
        event_id += 1
        cur.execute("INSERT INTO investigation_events (id, fir_id, event_date, event_type, note) VALUES (?,?,?,?,?)",
                    (event_id, fir_id, iso(reported), "FIR Registered", f"FIR {fir_number} registered."))
        event_id += 1
        cur.execute("INSERT INTO investigation_events (id, fir_id, event_date, event_type, note) VALUES (?,?,?,?,?)",
                    (event_id, fir_id, iso(reported + timedelta(days=random.randint(1, 7))), "Site Inspection", "Scene of crime examined."))
        if accused:
            event_id += 1
            cur.execute("INSERT INTO investigation_events (id, fir_id, event_date, event_type, note) VALUES (?,?,?,?,?)",
                        (event_id, fir_id, iso(occ + timedelta(days=random.randint(5, 60))), "Arrest", f"{len(accused)} accused arrested."))
        if status in ("Charge-Sheeted", "Convicted", "Acquitted"):
            event_id += 1
            cur.execute("INSERT INTO investigation_events (id, fir_id, event_date, event_type, note) VALUES (?,?,?,?,?)",
                        (event_id, fir_id, iso(occ + timedelta(days=random.randint(60, 200))), "Charge Sheet Filed", "Final report filed before court."))

    # --- co-accused associations (derived from shared FIRs)
    for (a, b), strength in coaccused_pairs.items():
        assoc_id += 1
        cur.execute(
            "INSERT INTO associations (id, person_a_id, person_b_id, association_type, gang_name, strength) VALUES (?,?,?,?,?,?)",
            (assoc_id, a, b, "Co-Accused", None, strength),
        )
    # --- a few family / known-associate links
    for _ in range(400):
        a, b = random.sample(all_persons, 2)
        assoc_id += 1
        cur.execute(
            "INSERT INTO associations (id, person_a_id, person_b_id, association_type, gang_name, strength) VALUES (?,?,?,?,?,?)",
            (assoc_id, a, b, random.choice(["Family", "Known Associate"]), None, 1),
        )

    # --- repeat-offender flag
    for pid, cnt in accused_count.items():
        if cnt >= 3:
            cur.execute("UPDATE persons SET is_repeat_offender = 1 WHERE id = ?", (pid,))

    # --- financial accounts (gang members + a sample of others)
    acct_id = 0
    person_accounts = {}
    fin_persons = set()
    for members in gang_members.values():
        fin_persons.update(members)
    fin_persons.update(random.sample(all_persons, 800))
    for pid in fin_persons:
        acct_id += 1
        cur.execute(
            "INSERT INTO financial_accounts (id, person_id, account_no_masked, bank, account_type) VALUES (?,?,?,?,?)",
            (acct_id, pid, f"XXXX{random.randint(1000,9999)}", random.choice(BANKS),
             random.choice(["Savings", "Current", "Wallet"])),
        )
        person_accounts.setdefault(pid, []).append(acct_id)

    # --- transactions: gang money-trails (funnel to a kingpin) + noise
    txn_id = 0
    for members in gang_members.values():
        accts = [person_accounts[p][0] for p in members if p in person_accounts]
        if len(accts) < 2:
            continue
        kingpin = accts[0]
        for src in accts[1:]:
            for _ in range(random.randint(2, 6)):
                txn_id += 1
                cur.execute(
                    "INSERT INTO transactions (id, from_account_id, to_account_id, amount_inr, txn_date, channel, is_flagged, linked_fir_id) VALUES (?,?,?,?,?,?,?,?)",
                    (txn_id, src, kingpin, round(random.uniform(10000, 300000), 2),
                     iso(rand_date(START, END)), random.choice(CHANNELS), 1, None),
                )
    # background noise transactions
    all_accts = list(range(1, acct_id + 1))
    for _ in range(5000):
        a, b = random.sample(all_accts, 2)
        txn_id += 1
        cur.execute(
            "INSERT INTO transactions (id, from_account_id, to_account_id, amount_inr, txn_date, channel, is_flagged, linked_fir_id) VALUES (?,?,?,?,?,?,?,?)",
            (txn_id, a, b, round(random.uniform(500, 80000), 2), iso(rand_date(START, END)),
             random.choice(CHANNELS), 0, None),
        )

    # --- users / officers (RBAC)
    roles_plan = (
        [("Investigator", True)] * 10 + [("Analyst", False)] * 5 +
        [("Supervisor", True)] * 3 + [("Policymaker", False)] * 2
    )
    for uid, (role, station_scoped) in enumerate(roles_plan, start=1):
        ps = random.choice(stations) if station_scoped else None
        nm = make_name(random.choice(["Male", "Female"]))[0]
        cur.execute(
            "INSERT INTO users (id, name, role, police_station_id, district_id, username) VALUES (?,?,?,?,?,?)",
            (uid, nm, role, ps[0] if ps else None,
             district_ids[ps[1]] if ps else None, f"{role[:3].lower()}{uid:02d}"),
        )

    conn.commit()
    export_csv(conn)
    summary(conn)
    conn.close()


def export_csv(conn):
    os.makedirs(CSV_DIR, exist_ok=True)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tables:
        rows = cur.execute(f"SELECT * FROM {t}").fetchall()
        cols = [d[0] for d in cur.description]
        with open(os.path.join(CSV_DIR, f"{t}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)


def summary(conn):
    cur = conn.cursor()
    print("\n=== Sahayak synthetic dataset built ===")
    print(f"DB: {DB_PATH}\n")
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in sorted(tables):
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:24s} {n:>8,}")
    print("\nIPC vs BNS split (by FIR occurrence date):")
    for act, n in cur.execute(
        "SELECT ls.act, COUNT(*) FROM firs f JOIN fir_sections fs ON fs.fir_id=f.id "
        "JOIN legal_sections ls ON ls.id=fs.legal_section_id GROUP BY ls.act ORDER BY ls.act"
    ).fetchall():
        print(f"  {act:10s} {n:>8,}")


if __name__ == "__main__":
    build()

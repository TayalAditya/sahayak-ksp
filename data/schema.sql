-- ============================================================================
-- Sahayak — CCTNS-shaped crime database schema
-- Target: SQLite (local dev). Designed to port cleanly to Catalyst Data Store (ZCQL).
--
-- ZCQL portability notes:
--   * No spatial/geometry types in Data Store (confirmed in Catalyst workshop Q&A) —
--     latitude/longitude are plain REAL columns; hotspot/distance math is done in code.
--   * Dates stored as ISO-8601 TEXT ('YYYY-MM-DD') for portability.
--   * Keep queries to SELECT/WHERE/JOIN/GROUP BY (the ZCQL-supported core).
--   * In Data Store every table also gets system columns (ROWID, CREATEDTIME, ...);
--     we model our own explicit integer PKs so dev and prod stay aligned.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---- Reference / geography ------------------------------------------------

CREATE TABLE districts (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    name_kn         TEXT NOT NULL,          -- Kannada
    region          TEXT NOT NULL,          -- e.g. 'South Karnataka'
    population      INTEGER,                -- for socio-demographic context
    urbanization    TEXT                    -- 'Urban' | 'Semi-Urban' | 'Rural'
);

CREATE TABLE police_stations (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL,          -- e.g. 'BNG-WHF-01'
    name            TEXT NOT NULL,
    name_kn         TEXT NOT NULL,
    district_id     INTEGER NOT NULL REFERENCES districts(id),
    latitude        REAL,
    longitude       REAL
);

-- ---- Legal codes (IPC + BNS cross-walk) -----------------------------------

CREATE TABLE legal_sections (
    id              INTEGER PRIMARY KEY,
    act             TEXT NOT NULL,          -- 'IPC' | 'BNS' | 'SPECIAL'
    section_code    TEXT NOT NULL,          -- e.g. '379', '303(2)', 'NDPS 20'
    crime_head      TEXT NOT NULL,          -- normalized head, e.g. 'Theft'
    title           TEXT NOT NULL,
    is_cognizable   INTEGER NOT NULL,       -- 0/1
    is_violent      INTEGER NOT NULL        -- 0/1  (helps trend/severity analysis)
);

-- Maps a pre-2024 IPC section to its post-2024 BNS equivalent (and vice-versa).
-- BNS replaced IPC on 2024-07-01; FIRs span both, so the cross-walk is essential.
CREATE TABLE ipc_bns_map (
    ipc_section_id  INTEGER NOT NULL REFERENCES legal_sections(id),
    bns_section_id  INTEGER NOT NULL REFERENCES legal_sections(id),
    crime_head      TEXT NOT NULL,
    PRIMARY KEY (ipc_section_id, bns_section_id)
);

-- ---- People (accused / victims / complainants / witnesses) ----------------

CREATE TABLE persons (
    id              INTEGER PRIMARY KEY,
    full_name       TEXT NOT NULL,
    full_name_kn    TEXT NOT NULL,
    gender          TEXT NOT NULL,          -- 'Male' | 'Female' | 'Other'
    age             INTEGER,
    occupation      TEXT,
    education_level TEXT,                    -- socio-demographic attributes
    income_band     TEXT,                    -- 'Low' | 'Lower-Middle' | 'Middle' | 'High'
    address         TEXT,
    district_id     INTEGER REFERENCES districts(id),
    phone           TEXT,
    is_repeat_offender INTEGER DEFAULT 0     -- denormalized flag, recomputed in analytics
);

-- ---- FIRs (First Information Reports) — the central record ----------------

CREATE TABLE firs (
    id              INTEGER PRIMARY KEY,
    fir_number      TEXT NOT NULL,          -- e.g. '0142/2025'
    police_station_id INTEGER NOT NULL REFERENCES police_stations(id),
    district_id     INTEGER NOT NULL REFERENCES districts(id),
    reported_date   TEXT NOT NULL,          -- ISO date
    occurrence_date TEXT NOT NULL,          -- ISO date (drives IPC vs BNS)
    occurrence_time TEXT,                    -- 'HH:MM'
    crime_head      TEXT NOT NULL,
    modus_operandi  TEXT,
    description     TEXT,
    latitude        REAL,
    longitude       REAL,
    status          TEXT NOT NULL,          -- 'Under Investigation'|'Charge-Sheeted'|'Convicted'|'Acquitted'|'Closed-Undetected'
    investigating_officer TEXT
);

CREATE TABLE fir_sections (
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    legal_section_id INTEGER NOT NULL REFERENCES legal_sections(id),
    PRIMARY KEY (fir_id, legal_section_id)
);

CREATE TABLE fir_persons (
    id              INTEGER PRIMARY KEY,
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    person_id       INTEGER NOT NULL REFERENCES persons(id),
    role            TEXT NOT NULL           -- 'Accused'|'Victim'|'Complainant'|'Witness'
);

CREATE TABLE arrests (
    id              INTEGER PRIMARY KEY,
    person_id       INTEGER NOT NULL REFERENCES persons(id),
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    arrest_date     TEXT,
    bail_status     TEXT                    -- 'In Custody'|'On Bail'|'Absconding'|'Released'
);

-- ---- Criminal network (link analysis) -------------------------------------

CREATE TABLE associations (
    id              INTEGER PRIMARY KEY,
    person_a_id     INTEGER NOT NULL REFERENCES persons(id),
    person_b_id     INTEGER NOT NULL REFERENCES persons(id),
    association_type TEXT NOT NULL,         -- 'Co-Accused'|'Family'|'Known Associate'|'Gang Member'
    gang_name       TEXT,                   -- nullable; set for organized groups
    strength        INTEGER DEFAULT 1       -- e.g. # of shared FIRs
);

-- ---- Property & vehicles --------------------------------------------------

CREATE TABLE vehicles (
    id              INTEGER PRIMARY KEY,
    registration_no TEXT,
    type            TEXT,                   -- 'Two-Wheeler'|'Car'|'Auto'|'Truck'
    make            TEXT,
    color           TEXT,
    owner_person_id INTEGER REFERENCES persons(id)
);

CREATE TABLE fir_vehicles (
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(id),
    role            TEXT NOT NULL,          -- 'Stolen'|'Used in Crime'|'Recovered'
    PRIMARY KEY (fir_id, vehicle_id)
);

CREATE TABLE properties (
    id              INTEGER PRIMARY KEY,
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    type            TEXT NOT NULL,          -- 'Cash'|'Gold'|'Mobile'|'Vehicle'|'Documents'
    description     TEXT,
    value_inr       REAL,
    status          TEXT NOT NULL           -- 'Stolen'|'Recovered'|'Seized'
);

-- ---- Financial crime / transaction links ----------------------------------

CREATE TABLE financial_accounts (
    id              INTEGER PRIMARY KEY,
    person_id       INTEGER NOT NULL REFERENCES persons(id),
    account_no_masked TEXT,
    bank            TEXT,
    account_type    TEXT                    -- 'Savings'|'Current'|'Wallet'
);

CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY,
    from_account_id INTEGER REFERENCES financial_accounts(id),
    to_account_id   INTEGER REFERENCES financial_accounts(id),
    amount_inr      REAL NOT NULL,
    txn_date        TEXT NOT NULL,
    channel         TEXT,                   -- 'UPI'|'NEFT'|'IMPS'|'Cash Deposit'
    is_flagged      INTEGER DEFAULT 0,      -- suspicious-transaction flag
    linked_fir_id   INTEGER REFERENCES firs(id)
);

-- ---- Investigation timeline (case summaries / decision support) -----------

CREATE TABLE investigation_events (
    id              INTEGER PRIMARY KEY,
    fir_id          INTEGER NOT NULL REFERENCES firs(id),
    event_date      TEXT NOT NULL,
    event_type      TEXT NOT NULL,          -- 'FIR Registered'|'Site Inspection'|'Arrest'|'Charge Sheet Filed'|...
    note            TEXT
);

-- ---- Users / officers (RBAC + audit) --------------------------------------

CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,          -- 'Investigator'|'Analyst'|'Supervisor'|'Policymaker'
    police_station_id INTEGER REFERENCES police_stations(id),
    district_id     INTEGER REFERENCES districts(id),
    username        TEXT UNIQUE NOT NULL
);

-- Audit log of every query the conversational agent runs (accountability).
CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    asked_at        TEXT NOT NULL,
    nl_question     TEXT,
    generated_query TEXT,
    row_count       INTEGER,
    role_at_time    TEXT
);

-- ---- Helpful indexes (dev only; Data Store manages its own) ---------------
CREATE INDEX idx_firs_ps        ON firs(police_station_id);
CREATE INDEX idx_firs_district  ON firs(district_id);
CREATE INDEX idx_firs_head      ON firs(crime_head);
CREATE INDEX idx_firs_occ       ON firs(occurrence_date);
CREATE INDEX idx_firp_fir       ON fir_persons(fir_id);
CREATE INDEX idx_firp_person    ON fir_persons(person_id);
CREATE INDEX idx_assoc_a        ON associations(person_a_id);
CREATE INDEX idx_txn_from       ON transactions(from_account_id);

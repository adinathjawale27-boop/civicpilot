"""SQLite persistence and fictional demo data for CivicPilot AI."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "civicpilot.db"


def get_db_path() -> Path:
    """Look up the path dynamically so tests and local demos stay isolated."""
    return Path(os.getenv("CIVICPILOT_DB_PATH", str(DEFAULT_DB_PATH)))


def connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS schemes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short_description TEXT NOT NULL,
    authority_name TEXT NOT NULL,
    source_label TEXT NOT NULL,
    benefit TEXT,
    deadline TEXT,
    category TEXT,
    is_demo INTEGER NOT NULL DEFAULT 1,
    required_documents_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scheme_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_id TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    operator TEXT NOT NULL,
    rule_value TEXT NOT NULL,
    display_text TEXT NOT NULL,
    FOREIGN KEY (scheme_id) REFERENCES schemes(id) ON DELETE CASCADE,
    UNIQUE(scheme_id, rule_key)
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    scheme_id TEXT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    document_type TEXT NOT NULL,
    text_excerpt TEXT,
    extraction_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scheme_id) REFERENCES schemes(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    scheme_id TEXT NOT NULL,
    applicant_json TEXT NOT NULL,
    uploaded_document_ids_json TEXT NOT NULL,
    status TEXT NOT NULL,
    demo_reference TEXT,
    demo_payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scheme_id) REFERENCES schemes(id)
);
CREATE TABLE IF NOT EXISTS application_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT NOT NULL,
    step_key TEXT NOT NULL,
    label TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    UNIQUE(application_id, step_key)
);
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);
"""


DEMO_SCHEMES: list[dict[str, Any]] = [
    {
        "id": "maha-merit-demo",
        "name": "Maharashtra Merit Support Scholarship",
        "short_description": "Fictional state scholarship for eligible higher-secondary and undergraduate students.",
        "authority_name": "CivicPilot Demonstration Council",
        "source_label": "Fictional demonstration rules · v1.0",
        "benefit": "₹25,000 / academic year",
        "deadline": "2026-12-31",
        "category": "Merit & Means",
        "required_documents": [
            {"type": "identity", "label": "Government-issued photo ID", "required": True, "reference": "Demo rule D-01"},
            {"type": "income", "label": "Family income certificate", "required": True, "reference": "Demo rule D-02"},
            {"type": "marksheet", "label": "Latest marksheet", "required": True, "reference": "Demo rule D-03"},
            {"type": "residence", "label": "Maharashtra residence proof", "required": True, "reference": "Demo rule D-04"},
            {"type": "bank", "label": "Bank account details for demo review", "required": False, "reference": "Demo rule D-05"},
        ],
        "rules": [
            ("state", "equals", "Maharashtra", "Applicant must be a Maharashtra resident."),
            ("family_income", "less_than_or_equal", "250000", "Annual family income must not exceed ₹2,50,000."),
            ("percentage", "greater_than_or_equal", "60", "Latest examination score must be at least 60%."),
            ("current_level", "one_of", json.dumps(["12", "undergraduate"]), "Applicant must be in Class 12 or an undergraduate course."),
        ],
    },
    {
        "id": "stem-access-demo",
        "name": "National STEM Access Grant",
        "short_description": "Fictional grant supporting students starting an eligible STEM undergraduate programme.",
        "authority_name": "CivicPilot National Innovation Cell",
        "source_label": "Fictional demonstration rules · v1.0",
        "benefit": "₹50,000 tuition grant + digital study device",
        "deadline": "2026-11-30",
        "category": "STEM Education",
        "required_documents": [
            {"type": "identity", "label": "Government-issued photo ID", "required": True, "reference": "Demo rule S-01"},
            {"type": "marksheet", "label": "Class 12 marksheet", "required": True, "reference": "Demo rule S-02"},
            {"type": "admission", "label": "STEM programme admission letter", "required": True, "reference": "Demo rule S-03"},
            {"type": "income", "label": "Family income declaration", "required": True, "reference": "Demo rule S-04"},
        ],
        "rules": [
            ("family_income", "less_than_or_equal", "400000", "Annual family income must not exceed ₹4,00,000."),
            ("percentage", "greater_than_or_equal", "70", "Class 12 score must be at least 70%."),
            ("study_field", "contains", "stem", "Programme must be identified as STEM in this fictional demo."),
            ("current_level", "equals", "undergraduate", "Applicant must be starting or enrolled in undergraduate study."),
        ],
    },
    {
        "id": "pragati-girls-demo",
        "name": "Pragati Girl Child Higher Education Scheme",
        "short_description": "Fictional initiative empowering female students pursuing polytechnic, diploma, or degree courses.",
        "authority_name": "CivicPilot Women in Higher Education Directorate",
        "source_label": "Fictional demonstration rules · v1.0",
        "benefit": "₹30,000 annual contingency allowance",
        "deadline": "2026-12-15",
        "category": "Women Empowerment",
        "required_documents": [
            {"type": "identity", "label": "Government-issued photo ID", "required": True, "reference": "Demo rule P-01"},
            {"type": "income", "label": "Family income certificate", "required": True, "reference": "Demo rule P-02"},
            {"type": "admission", "label": "College enrollment / admission receipt", "required": True, "reference": "Demo rule P-03"},
            {"type": "marksheet", "label": "Previous qualifying exam marksheet", "required": True, "reference": "Demo rule P-04"},
        ],
        "rules": [
            ("gender", "equals", "female", "Applicant must identify as female."),
            ("family_income", "less_than_or_equal", "300000", "Annual family income must not exceed ₹3,00,000."),
            ("percentage", "greater_than_or_equal", "55", "Previous qualifying exam score must be at least 55%."),
            ("current_level", "one_of", json.dumps(["diploma", "undergraduate", "polytechnic"]), "Enrolled in an eligible diploma, polytechnic, or undergraduate course."),
        ],
    },
]


def initialize_database() -> None:
    """Create storage and seed only clearly labelled, fictional data."""
    with connect() as db:
        db.executescript(SCHEMA)
        # Migrate columns if DB existed prior to new schema
        existing_cols = {r["name"] for r in db.execute("PRAGMA table_info(schemes)").fetchall()}
        for col in ("benefit", "deadline", "category"):
            if col not in existing_cols:
                try:
                    db.execute(f"ALTER TABLE schemes ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass

        for scheme in DEMO_SCHEMES:
            db.execute(
                """INSERT INTO schemes
                (id, name, short_description, authority_name, source_label, benefit, deadline, category, required_documents_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    short_description = excluded.short_description,
                    authority_name = excluded.authority_name,
                    source_label = excluded.source_label,
                    benefit = excluded.benefit,
                    deadline = excluded.deadline,
                    category = excluded.category,
                    required_documents_json = excluded.required_documents_json""",
                (
                    scheme["id"],
                    scheme["name"],
                    scheme["short_description"],
                    scheme["authority_name"],
                    scheme["source_label"],
                    scheme.get("benefit"),
                    scheme.get("deadline"),
                    scheme.get("category"),
                    json.dumps(scheme["required_documents"]),
                ),
            )
            for key, operator, value, display_text in scheme["rules"]:
                db.execute(
                    """INSERT OR IGNORE INTO scheme_rules
                    (scheme_id, rule_key, operator, rule_value, display_text) VALUES (?, ?, ?, ?, ?)""",
                    (scheme["id"], key, operator, value, display_text),
                )

        # Seed initial demo application and activity if database is brand new
        apps_count = db.execute("SELECT COUNT(*) AS count FROM applications").fetchone()["count"]
        if apps_count == 0:
            app1_id = "demo-app-asha-001"
            app2_id = "demo-app-rahul-002"
            now = "2026-11-22T10:00:00Z"
            asha_applicant = {
                "name": "Asha Patel",
                "email": "asha.patel@example.com",
                "state": "Maharashtra",
                "family_income": "180000",
                "percentage": "78.2",
                "current_level": "undergraduate",
                "study_field": "Computer Science & Engineering (STEM)",
            }
            rahul_applicant = {
                "name": "Rahul Deshmukh",
                "email": "rahul.stem@example.com",
                "state": "Maharashtra",
                "family_income": "240000",
                "percentage": "84.5",
                "current_level": "undergraduate",
                "study_field": "Artificial Intelligence & Data Science (STEM)",
            }
            demo_payload = {
                "environment": "local_simulated_portal",
                "scheme_name": "Maharashtra Merit Support Scholarship",
                "filled_fields": asha_applicant,
                "validation_errors": [],
                "submission_performed": False,
                "simulation_only": True,
                "browser_engine": "playwright_local_page",
                "browser_validation_passed": True,
            }
            db.execute(
                """INSERT INTO applications
                (id, scheme_id, applicant_json, uploaded_document_ids_json, status, demo_reference, demo_payload_json, created_at, updated_at)
                VALUES (?, 'maha-merit-demo', ?, '["doc-sample-1","doc-sample-2"]', 'demo_submitted', 'CP-DEMO-20261122-ASHA01', ?, ?, ?)""",
                (app1_id, json.dumps(asha_applicant), json.dumps(demo_payload), now, now),
            )
            db.execute(
                """INSERT INTO applications
                (id, scheme_id, applicant_json, uploaded_document_ids_json, status, demo_reference, demo_payload_json, created_at, updated_at)
                VALUES (?, 'stem-access-demo', ?, '[]', 'draft', NULL, NULL, ?, ?)""",
                (app2_id, json.dumps(rahul_applicant), now, now),
            )
            # Steps for Asha (all completed)
            steps_asha = [
                (app1_id, "profile", "Profile details", 1, "completed", now),
                (app1_id, "eligibility", "Eligibility check", 2, "completed", now),
                (app1_id, "documents", "Document checklist", 3, "completed", now),
                (app1_id, "review", "Review application", 4, "completed", now),
                (app1_id, "demo_fill", "Local portal pre-fill", 5, "completed", now),
                (app1_id, "demo_submit", "Demo approval", 6, "completed", now),
            ]
            db.executemany("INSERT INTO application_steps (application_id, step_key, label, step_order, status, updated_at) VALUES (?, ?, ?, ?, ?, ?)", steps_asha)
            # Steps for Rahul (partially completed)
            steps_rahul = [
                (app2_id, "profile", "Profile details", 1, "completed", now),
                (app2_id, "eligibility", "Eligibility check", 2, "completed", now),
                (app2_id, "documents", "Document checklist", 3, "pending", now),
                (app2_id, "review", "Review application", 4, "pending", now),
                (app2_id, "demo_fill", "Local portal pre-fill", 5, "pending", now),
                (app2_id, "demo_submit", "Demo approval", 6, "locked", now),
            ]
            db.executemany("INSERT INTO application_steps (application_id, step_key, label, step_order, status, updated_at) VALUES (?, ?, ?, ?, ?, ?)", steps_rahul)
            # Initial Activity logs
            db.execute("INSERT INTO activity_logs (application_id, action, details_json, created_at) VALUES (?, 'demo_acknowledgement_recorded', '{\"reference\":\"CP-DEMO-20261122-ASHA01\"}', ?)", (app1_id, now))
            db.execute("INSERT INTO activity_logs (application_id, action, details_json, created_at) VALUES (?, 'application_draft_created', '{\"scheme_id\":\"stem-access-demo\"}', ?)", (app2_id, now))
            db.execute("INSERT INTO activity_logs (application_id, action, details_json, created_at) VALUES (NULL, 'system_initialized', '{\"schemes_loaded\":3}', ?)", (now,))


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def log_activity(application_id: str | None, action: str, details: dict[str, Any]) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO activity_logs (application_id, action, details_json) VALUES (?, ?, ?)",
            (application_id, action, json.dumps(details)),
        )

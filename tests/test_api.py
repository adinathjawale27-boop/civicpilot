"""Core API and safety-workflow tests for the fictional CivicPilot demo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend import database
from backend.main import app


def client_for(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPILOT_DB_PATH", str(tmp_path / "test-civicpilot.db"))
    monkeypatch.setenv("CIVICPILOT_UPLOAD_DIR", str(tmp_path / "uploads"))
    database.initialize_database()
    return TestClient(app)


def test_health_and_seeded_schemes(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    assert client.get("/api/health").json()["status"] == "ok"
    identifiers = {item["id"] for item in client.get("/api/schemes").json()["schemes"]}
    assert {"maha-merit-demo", "stem-access-demo"} <= identifiers


def test_deterministic_eligibility(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    eligible = client.post("/api/eligibility/check", json={"scheme_id": "maha-merit-demo", "applicant": {"state": "Maharashtra", "family_income": 200000, "percentage": 78, "current_level": "undergraduate"}})
    assert eligible.status_code == 200
    assert eligible.json()["decision"] == "eligible"
    incomplete = client.post("/api/eligibility/check", json={"scheme_id": "maha-merit-demo", "applicant": {"state": "Maharashtra"}})
    assert incomplete.json()["decision"] == "needs_information"
    rejected = client.post("/api/eligibility/check", json={"scheme_id": "maha-merit-demo", "applicant": {"state": "Goa", "family_income": 500000, "percentage": 50, "current_level": "12"}})
    assert rejected.json()["decision"] == "not_eligible"


def test_demo_requires_two_explicit_approvals(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    create = client.post("/api/applications", json={"scheme_id": "maha-merit-demo", "applicant": {"name": "Asha Demo", "email": "asha@example.test", "state": "Maharashtra"}})
    assert create.status_code == 201
    application_id = create.json()["application"]["id"]
    assert client.post(f"/api/applications/{application_id}/prepare-demo", json={"confirmed_review": False}).status_code == 400
    assert client.post(f"/api/applications/{application_id}/prepare-demo", json={"confirmed_review": True}).status_code == 200
    assert client.post(f"/api/applications/{application_id}/approve-demo", json={"approved": False}).status_code == 400
    approved = client.post(f"/api/applications/{application_id}/approve-demo", json={"approved": True, "acknowledgement": "I understand this is a simulation."})
    assert approved.status_code == 200
    assert approved.json()["acknowledgement"]["reference"].startswith("CP-DEMO-")


def test_chat_does_not_guess_without_sources(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post("/api/chat", json={"message": "What is the closing date for a real scholarship?"})
    assert response.status_code == 200
    assert "do not have a matching source" in response.json()["answer"].casefold()


def test_applications_list_includes_created_draft(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    payload = {
        "scheme_id": "maha-merit-demo",
        "applicant": {
            "name": "List Test Student",
            "email": "list@example.com",
            "state": "Maharashtra",
            "family_income": 180000,
            "percentage": 78,
            "current_level": "Undergraduate",
            "study_field": "Engineering",
        },
        "uploaded_document_ids": [],
    }
    created = client.post("/api/applications", json=payload)
    assert created.status_code == 201
    app_id = created.json()["application"]["id"]

    listing = client.get("/api/applications")
    assert listing.status_code == 200
    apps = listing.json()["applications"]
    assert any(app["id"] == app_id for app in apps)


def test_sample_document_and_acknowledgment_slip(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    sample_res = client.post("/api/documents/sample", json={"sample_type": "marksheet", "scheme_id": "maha-merit-demo"})
    assert sample_res.status_code == 201
    doc = sample_res.json()["document"]
    assert doc["document_type"] == "marksheet"

    created = client.post("/api/applications", json={"scheme_id": "maha-merit-demo", "applicant": {"name": "Asha Patel", "email": "asha@example.com", "state": "Maharashtra"}})
    app_id = created.json()["application"]["id"]

    # Test slip generation
    slip_res = client.get(f"/api/applications/{app_id}/slip")
    assert slip_res.status_code == 200
    assert "CIVICPILOT" in slip_res.text
    assert "Asha Patel" in slip_res.text

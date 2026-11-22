"""FastAPI entry point for the CivicPilot AI hackathon MVP."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .automation import render_acknowledgment_slip, render_local_portal, run_local_demo_fill
from .database import connect, initialize_database, log_activity, row_to_dict
from .services import (
    classify_document,
    create_sample_document,
    decode_json,
    document_checklist,
    evaluate_eligibility,
    extract_text,
    generate_grounded_answer,
    get_scheme,
    list_schemes,
    normalise_applicant,
    retrieve_context,
)

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
UPLOAD_DIR = Path(os.getenv("CIVICPILOT_UPLOAD_DIR", str(BACKEND_DIR / "data" / "uploads")))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

app = FastAPI(title="CivicPilot AI API", version="1.0.0", description="Fictional civic-service demonstration; it never submits to real portals.")
app.add_middleware(CORSMiddleware, allow_origins=[item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    scheme_id: str | None = None
    language: str = Field(default="en", max_length=12)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)
    conversation: list[ChatTurn] = Field(default_factory=list, max_length=12)


class SchemeQuestion(BaseModel):
    scheme_id: str
    question: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", max_length=12)


class EligibilityRequest(BaseModel):
    scheme_id: str
    applicant: dict[str, Any] = Field(default_factory=dict)


class ApplicationCreate(BaseModel):
    scheme_id: str
    applicant: dict[str, Any] = Field(default_factory=dict)
    uploaded_document_ids: list[str] = Field(default_factory=list, max_length=20)
    documents: list[str] = Field(default_factory=list, max_length=20)


class ReviewApproval(BaseModel):
    confirmed_review: bool = False


class DemoApproval(BaseModel):
    approved: bool = False
    acknowledgement: str = Field(default="", max_length=500)


class SampleDocumentRequest(BaseModel):
    sample_type: str = Field(default="marksheet", max_length=50)
    scheme_id: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def not_found(kind: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{kind} was not found.")


@app.on_event("startup")
def startup() -> None:
    initialize_database()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health() -> dict[str, Any]:
    initialize_database()
    return {"status": "ok", "service": "CivicPilot AI", "mode": "fictional_demo_only", "gemini_configured": bool(os.getenv("GEMINI_API_KEY")), "timestamp": utc_now()}


@app.get("/api/schemes")
def schemes() -> dict[str, Any]:
    initialize_database()
    return {"schemes": list_schemes(), "disclaimer": "All seeded schemes are fictional CivicPilot demonstrations."}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    initialize_database()
    with connect() as db:
        applications = db.execute("SELECT COUNT(*) AS count FROM applications").fetchone()["count"]
        documents = db.execute("SELECT COUNT(*) AS count FROM documents").fetchone()["count"]
        pending = db.execute("SELECT COUNT(*) AS count FROM applications WHERE status != 'demo_submitted'").fetchone()["count"]
        submitted = db.execute("SELECT COUNT(*) AS count FROM applications WHERE status = 'demo_submitted'").fetchone()["count"]
        activity = db.execute(
            "SELECT action, details_json, created_at FROM activity_logs ORDER BY id DESC LIMIT 8"
        ).fetchall()
    return {
        "scheme_count": len(list_schemes()),
        "application_count": applications,
        "document_count": documents,
        "pending_application_count": pending,
        "submitted_application_count": submitted,
        "recent_activity": [
            {"action": row["action"], "details": decode_json(row["details_json"], {}), "created_at": row["created_at"]}
            for row in activity
        ],
        "demo_notice": "Fictional data and local simulations only.",
    }


@app.post("/api/documents/sample", status_code=status.HTTP_201_CREATED)
def sample_document_endpoint(request: SampleDocumentRequest) -> dict[str, Any]:
    initialize_database()
    if request.scheme_id and not get_scheme(request.scheme_id):
        raise not_found("Scheme")
    doc_res = create_sample_document(request.sample_type, request.scheme_id)
    return {
        "document": doc_res,
        "notice": doc_res.get("notice", "Fictional demonstration sample document for testing extraction and verification."),
    }


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    initialize_database()
    if request.scheme_id and not get_scheme(request.scheme_id):
        raise not_found("Scheme")
    history = request.history or request.conversation
    context = retrieve_context(request.scheme_id, request.message)
    answer, engine = generate_grounded_answer(request.message, context, request.language)
    missing_information = not bool(context)
    return {
        "answer": answer,
        "engine": engine,
        "language": request.language,
        "history_count": len(history),
        "sources": [{"reference": item["reference"], "content": item["content"][:240]} for item in context],
        "needs_more_information": missing_information,
        "safety_notice": "CivicPilot uses only available sources and does not provide official government confirmation.",
    }


@app.post("/api/schemes/ask")
def ask_scheme(request: SchemeQuestion) -> dict[str, Any]:
    return chat(ChatRequest(message=request.question, scheme_id=request.scheme_id, language=request.language))


@app.post("/api/schemes/upload", status_code=status.HTTP_201_CREATED)
async def upload_scheme_document(file: UploadFile = File(...), scheme_id: str | None = Form(default=None)) -> dict[str, Any]:
    initialize_database()
    original_name = Path(file.filename or "uploaded-document").name
    suffix = Path(original_name).suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG, JPG, JPEG, or WEBP file.")
    if scheme_id and not get_scheme(scheme_id):
        raise not_found("Scheme")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid.uuid4())
    destination_path = UPLOAD_DIR / f"{document_id}{suffix}"
    received = 0
    try:
        with destination_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                received += len(chunk)
                if received > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
                destination.write(chunk)
    except HTTPException:
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    mime_type = file.content_type or "application/octet-stream"
    text, extraction_status = extract_text(destination_path, mime_type)
    document_type = classify_document(original_name, text)
    with connect() as db:
        db.execute("""INSERT INTO documents
        (id, scheme_id, original_filename, stored_filename, mime_type, document_type, text_excerpt, extraction_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (document_id, scheme_id, original_name, destination_path.name, mime_type, document_type, text, extraction_status))
    log_activity(None, "document_uploaded", {"document_id": document_id, "filename": original_name, "scheme_id": scheme_id})
    return {"document": {"id": document_id, "filename": original_name, "document_type": document_type, "extraction_status": extraction_status, "text_preview": text[:500]}, "notice": "Text extraction is best-effort. This upload is not authenticated or verified as an official document."}


@app.post("/api/eligibility/check")
def check_eligibility(request: EligibilityRequest) -> dict[str, Any]:
    initialize_database()
    scheme = get_scheme(request.scheme_id)
    if not scheme:
        raise not_found("Scheme")
    result = evaluate_eligibility(scheme, request.applicant)
    result["document_checklist"] = document_checklist(scheme)
    log_activity(None, "eligibility_checked", {"scheme_id": request.scheme_id, "decision": result["decision"]})
    return result


@app.get("/api/documents/checklist/{scheme_id}")
def get_document_checklist(scheme_id: str, document_types: str = "") -> dict[str, Any]:
    initialize_database()
    scheme = get_scheme(scheme_id)
    if not scheme:
        raise not_found("Scheme")
    supplied = [item.strip() for item in document_types.split(",") if item.strip()]
    return {"scheme_id": scheme_id, "scheme_name": scheme["name"], "checklist": document_checklist(scheme, supplied), "notice": "Listed items are a checklist only; CivicPilot does not authenticate documents."}


def get_application(application_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        application = row_to_dict(row)
        if not application:
            return None
        steps = db.execute("SELECT step_key, label, step_order, status, updated_at FROM application_steps WHERE application_id = ? ORDER BY step_order", (application_id,)).fetchall()
        activity = db.execute("SELECT action, details_json, created_at FROM activity_logs WHERE application_id = ? ORDER BY id DESC LIMIT 15", (application_id,)).fetchall()
    application["applicant"] = decode_json(application.pop("applicant_json"), {})
    application["uploaded_document_ids"] = decode_json(application.pop("uploaded_document_ids_json"), [])
    application["demo_payload"] = decode_json(application.pop("demo_payload_json"), None)
    application["steps"] = [dict(step) for step in steps]
    application["activity"] = [{"action": row["action"], "details": decode_json(row["details_json"], {}), "created_at": row["created_at"]} for row in activity]
    return application


def set_step(application_id: str, step_key: str, new_status: str) -> None:
    with connect() as db:
        db.execute("UPDATE application_steps SET status = ?, updated_at = ? WHERE application_id = ? AND step_key = ?", (new_status, utc_now(), application_id, step_key))


def application_response(application_id: str) -> dict[str, Any]:
    application = get_application(application_id)
    if not application:
        raise not_found("Application")
    scheme = get_scheme(application["scheme_id"])
    application["scheme"] = {"id": scheme["id"], "name": scheme["name"]} if scheme else None
    return application


@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def create_application(request: ApplicationCreate) -> dict[str, Any]:
    initialize_database()
    scheme = get_scheme(request.scheme_id)
    if not scheme:
        raise not_found("Scheme")
    applicant = normalise_applicant(request.applicant)
    if not applicant.get("name"):
        raise HTTPException(status_code=422, detail="Applicant name is required to create a draft.")
    uploaded_ids = request.uploaded_document_ids or request.documents
    application_id, now = str(uuid.uuid4()), utc_now()
    steps = [
        ("profile", "Profile details", 1, "completed"),
        ("eligibility", "Eligibility check", 2, "completed"),
        ("documents", "Document checklist", 3, "completed" if uploaded_ids else "pending"),
        ("review", "Review application", 4, "completed"),
        ("demo_fill", "Local portal pre-fill", 5, "pending"),
        ("demo_submit", "Demo approval", 6, "locked"),
    ]
    with connect() as db:
        db.execute(
            """INSERT INTO applications
            (id, scheme_id, applicant_json, uploaded_document_ids_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?)""",
            (application_id, request.scheme_id, json.dumps(applicant), json.dumps(uploaded_ids), now, now),
        )
        db.executemany(
            "INSERT INTO application_steps (application_id, step_key, label, step_order, status, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(application_id, *step, now) for step in steps],
        )
    log_activity(application_id, "application_draft_created", {"scheme_id": request.scheme_id, "uploaded_document_count": len(uploaded_ids)})
    return {"application": application_response(application_id), "notice": "Draft saved locally. No application has been submitted."}


@app.get("/api/applications")
def list_applications() -> dict[str, Any]:
    initialize_database()
    with connect() as db:
        rows = db.execute(
            "SELECT id, scheme_id, status, demo_reference, updated_at, created_at FROM applications ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    items = []
    for row in rows:
        application = get_application(row["id"])
        if not application:
            continue
        completed = sum(1 for step in application["steps"] if step["status"] == "completed")
        items.append(
            {
                "id": application["id"],
                "scheme_id": application["scheme_id"],
                "scheme_name": (application.get("scheme") or {}).get("name"),
                "status": application["status"],
                "demo_reference": application.get("demo_reference"),
                "updated_at": row["updated_at"],
                "created_at": row["created_at"],
                "progress": {"completed": completed, "total": len(application["steps"])},
                "applicant_name": (application.get("applicant") or {}).get("name"),
            }
        )
    return {"applications": items}


@app.get("/api/applications/{application_id}")
def get_application_endpoint(application_id: str) -> dict[str, Any]:
    initialize_database()
    return {"application": application_response(application_id)}


@app.post("/api/applications/{application_id}/prepare-demo")
def prepare_demo(application_id: str, request: ReviewApproval) -> dict[str, Any]:
    """Pre-fill a local portal only after explicit draft-review confirmation."""
    initialize_database()
    if not request.confirmed_review:
        raise HTTPException(status_code=400, detail="Set confirmed_review to true after reviewing the draft before local demo preparation.")
    application = get_application(application_id)
    if not application:
        raise not_found("Application")
    if application["status"] == "demo_submitted":
        raise HTTPException(status_code=409, detail="This demo application already has an acknowledgement.")
    scheme = get_scheme(application["scheme_id"])
    if not scheme:
        raise not_found("Scheme")
    payload, now = run_local_demo_fill(application, scheme), utc_now()
    with connect() as db:
        db.execute("UPDATE applications SET status = 'demo_prepared', demo_payload_json = ?, updated_at = ? WHERE id = ?", (json.dumps(payload), now, application_id))
    set_step(application_id, "review", "completed")
    set_step(application_id, "demo_fill", "completed" if not payload["validation_errors"] else "attention")
    set_step(application_id, "demo_submit", "pending")
    log_activity(application_id, "demo_portal_prepared", {"engine": payload["browser_engine"]})
    return {"application": application_response(application_id), "portal_url": f"/demo-portal/{application_id}", "notice": "The local simulated portal is pre-filled for review only; it cannot submit to a government portal."}


@app.post("/api/applications/{application_id}/approve-demo")
def approve_demo(application_id: str, request: DemoApproval) -> dict[str, Any]:
    """Record a separate demo acknowledgement, never a real submission."""
    initialize_database()
    if not request.approved:
        raise HTTPException(status_code=400, detail="Explicit approved=true is required before recording a demo acknowledgement.")
    application = get_application(application_id)
    if not application:
        raise not_found("Application")
    if application["status"] != "demo_prepared":
        raise HTTPException(status_code=409, detail="Prepare and review the local demo portal before approval.")
    reference = application.get("demo_reference") or f"CP-DEMO-{datetime.now(timezone.utc):%Y%m%d}-{application_id[:6].upper()}"
    now = utc_now()
    with connect() as db:
        db.execute("UPDATE applications SET status = 'demo_submitted', demo_reference = ?, updated_at = ? WHERE id = ?", (reference, now, application_id))
    set_step(application_id, "demo_submit", "completed")
    log_activity(application_id, "demo_acknowledgement_recorded", {"reference": reference, "acknowledgement": request.acknowledgement})
    return {"application": application_response(application_id), "acknowledgement": {"reference": reference, "label": "SIMULATED DEMO ACKNOWLEDGEMENT — NOT A GOVERNMENT APPLICATION", "created_at": now}}


@app.get("/api/applications/{application_id}/status")
def application_status(application_id: str) -> dict[str, Any]:
    initialize_database()
    application = application_response(application_id)
    completed = sum(step["status"] == "completed" for step in application["steps"])
    return {"application_id": application_id, "status": application["status"], "demo_reference": application["demo_reference"], "steps": application["steps"], "progress": {"completed": completed, "total": len(application["steps"])}, "notice": "This tracks only a local fictional demo workflow."}


@app.get("/demo-portal/{application_id}", response_class=HTMLResponse)
def demo_portal(application_id: str) -> HTMLResponse:
    application = get_application(application_id)
    if not application:
        raise not_found("Application")
    scheme = get_scheme(application["scheme_id"])
    if not scheme:
        raise not_found("Scheme")
    if not application.get("demo_payload"):
        raise HTTPException(status_code=409, detail="Prepare the local demo before viewing the portal.")
    return HTMLResponse(render_local_portal(application, scheme))


@app.get("/api/applications/{application_id}/slip", response_class=HTMLResponse)
def application_acknowledgment_slip(application_id: str) -> HTMLResponse:
    initialize_database()
    application = get_application(application_id)
    if not application:
        raise not_found("Application")
    scheme = get_scheme(application["scheme_id"])
    if not scheme:
        raise not_found("Scheme")
    return HTMLResponse(render_acknowledgment_slip(application, scheme))


# Let `uvicorn backend.main:app --reload` serve the vanilla same-origin app when
# the frontend directory exists. API and demo routes above win by registration order.
frontend_dir = PROJECT_DIR / "frontend"
if frontend_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

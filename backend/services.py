"""Deterministic rules and source-grounded helper functions."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .database import connect, log_activity, row_to_dict

BACKEND_DIR = Path(__file__).resolve().parent

def get_upload_dir() -> Path:
    path = Path(os.getenv("CIVICPILOT_UPLOAD_DIR", str(BACKEND_DIR / "data" / "uploads")))
    path.mkdir(parents=True, exist_ok=True)
    return path

SYSTEM_PROMPT = """You are CivicPilot AI, an intelligent government service assistant.

Help citizens understand government schemes and prepare applications.

Always:

- Use simple language.
- Support English, Hindi, and Marathi.
- Explain eligibility criteria using supplied official documents.
- Ask questions when information is missing.
- Never invent deadlines, scheme benefits, or eligibility rules.
- Provide document references when available.
- Clearly communicate uncertainty.
- Never claim that an application was submitted without confirmation.
- Never request passwords or OTPs.
- Never initiate an irreversible action without explicit user approval.

All schemes and portals in this MVP are fictional demonstrations; treat supplied materials as the only available sources."""


def decode_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def get_scheme(scheme_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,)).fetchone()
        scheme = row_to_dict(row)
        if not scheme:
            return None
        rules = db.execute(
            "SELECT rule_key, operator, rule_value, display_text FROM scheme_rules WHERE scheme_id = ? ORDER BY id",
            (scheme_id,),
        ).fetchall()
    scheme["required_documents"] = decode_json(scheme.pop("required_documents_json"), [])
    scheme["rules"] = [dict(rule) for rule in rules]
    return scheme


def list_schemes() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM schemes ORDER BY created_at, name").fetchall()
    result = []
    for row in rows:
        scheme = dict(row)
        scheme["required_documents"] = decode_json(scheme.pop("required_documents_json"), [])
        result.append(scheme)
    return result


def normalise_applicant(payload: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "annual_family_income": "family_income", "income": "family_income",
        "marks": "percentage", "exam_percentage": "percentage",
        "education_level": "current_level", "course_level": "current_level",
        "course": "study_field", "program": "study_field",
    }
    return {aliases.get(key, key): value for key, value in payload.items() if value is not None and value != ""}


def _text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


def friendly_field_label(key: str) -> str:
    labels = {
        "family_income": "Annual Family Income (₹)",
        "percentage": "Latest Examination Percentage (%)",
        "state": "State of Residence",
        "current_level": "Current Education Level",
        "study_field": "Course / Study Field",
        "gender": "Gender Identity",
    }
    return labels.get(key, key.replace("_", " ").title())


def evaluate_eligibility(scheme: dict[str, Any], applicant_payload: dict[str, Any]) -> dict[str, Any]:
    """Perform transparent, deterministic evaluation without an LLM."""
    applicant = normalise_applicant(applicant_payload)
    checks, missing, failures = [], [], []
    for rule in scheme["rules"]:
        key, operator, expected = rule["rule_key"], rule["operator"], rule["rule_value"]
        actual = applicant.get(key)
        label = friendly_field_label(key)
        if actual is None or actual == "":
            missing.append({"field": key, "reason": rule["display_text"]})
            checks.append({
                "field": key,
                "label": label,
                "rule": rule["display_text"],
                "status": "needs_information",
                "provided_value": None,
                "expected_value": expected,
                "detail": f"Missing information for requirement: {rule['display_text']}",
            })
            continue
        passed = False
        if operator == "equals":
            passed = _text(actual) == _text(expected)
        elif operator == "contains":
            passed = _text(expected) in _text(actual)
        elif operator == "less_than_or_equal":
            actual_number, expected_number = _number(actual), _number(expected)
            passed = actual_number is not None and expected_number is not None and actual_number <= expected_number
        elif operator == "greater_than_or_equal":
            actual_number, expected_number = _number(actual), _number(expected)
            passed = actual_number is not None and expected_number is not None and actual_number >= expected_number
        elif operator == "one_of":
            passed = _text(actual) in {_text(item) for item in decode_json(expected, [])}
        
        detail_msg = f"Provided {actual} satisfies requirement: {rule['display_text']}" if passed else f"Provided {actual} does not satisfy requirement: {rule['display_text']}"
        checks.append({
            "field": key,
            "label": label,
            "rule": rule["display_text"],
            "status": "passed" if passed else "failed",
            "provided_value": actual,
            "expected_value": expected,
            "detail": detail_msg,
        })
        if not passed:
            failures.append(rule["display_text"])
    decision = "not_eligible" if failures else "needs_information" if missing else "eligible"
    summary = {
        "eligible": "The supplied information meets all deterministic fictional demo rules. This is not an official decision.",
        "needs_information": "More information is needed before the fictional demo rules can be evaluated.",
        "not_eligible": "The supplied information does not meet one or more fictional demo rules.",
    }[decision]
    return {
        "scheme_id": scheme["id"], "scheme_name": scheme["name"], "decision": decision,
        "eligible": decision == "eligible", "summary": summary, "checks": checks,
        "missing_information": missing, "missing_fields": [entry["field"] for entry in missing],
        "failed_rules": failures, "reasons": failures or [entry["reason"] for entry in missing],
        "disclaimer": "Eligibility uses local fictional demo rules, not an official government determination.",
    }


def document_checklist(scheme: dict[str, Any], supplied_types: list[str] | None = None) -> list[dict[str, Any]]:
    supplied = {_text(item) for item in (supplied_types or [])}
    result = []
    for document in scheme["required_documents"]:
        item = dict(document)
        item["status"] = "provided" if _text(item["type"]) in supplied else "missing"
        item["description"] = item.get("reference", f"Required item: {item.get('label')}")
        result.append(item)
    return result


SAMPLE_DOCUMENTS: dict[str, dict[str, Any]] = {
    "marksheet": {
        "filename": "Class12_HigherSecondary_Marksheet_Asha.pdf",
        "mime_type": "application/pdf",
        "document_type": "marksheet",
        "content": (
            "BOARD OF HIGHER SECONDARY EDUCATION\n"
            "STATEMENT OF MARKS - HIGHER SECONDARY CERTIFICATE EXAMINATION\n"
            "Candidate Name: Asha Patel | Seat No: MH-2024-884910\n"
            "School/College: Shivaji Higher Secondary Science Vidyalaya, Pune\n"
            "Subject Scores:\n"
            "- Physics: 78/100\n"
            "- Chemistry: 82/100\n"
            "- Mathematics: 85/100\n"
            "- English: 72/100\n"
            "Total Aggregate Marks: 391 / 500\n"
            "Calculated Percentage: 78.20%\n"
            "Result Classification: FIRST CLASS WITH DISTINCTION (PASSED)"
        ),
    },
    "income": {
        "filename": "Tahsil_Office_Income_Certificate_2024_25.pdf",
        "mime_type": "application/pdf",
        "document_type": "income",
        "content": (
            "GOVERNMENT OF MAHARASHTRA - REVENUE DEPARTMENT\n"
            "OFFICE OF THE TAHSILDAR & EXECUTIVE MAGISTRATE, HAVELI, PUNE\n"
            "ANNUAL FAMILY INCOME CERTIFICATE (FINANCIAL YEAR 2024-2025)\n"
            "Certificate No: MH/INC/2024/77419\n"
            "This is to certify that Shri Ramesh Patel, father of Miss Asha Patel,\n"
            "residing at Flat 302, Green Meadows, Kothrud, Pune - 411038, has a total\n"
            "verified annual family income from all combined sources of ₹1,80,000/- (Rupees One Lakh Eighty Thousand Only).\n"
            "Issued for educational scholarship applications."
        ),
    },
    "residence": {
        "filename": "Maharashtra_State_Domicile_Certificate.pdf",
        "mime_type": "application/pdf",
        "document_type": "residence",
        "content": (
            "COMPETENT CITIZEN FACILITATION CENTRE - DISTRICT PUNE\n"
            "STATE RESIDENCE AND DOMICILE CERTIFICATE\n"
            "Reference ID: DOM-MH-2024-11029\n"
            "Certified that Miss Asha Patel is a permanent resident and bonafide citizen\n"
            "domiciled in the State of Maharashtra for more than 15 consecutive years."
        ),
    },
    "admission": {
        "filename": "STEM_Engineering_Admission_Receipt.pdf",
        "mime_type": "application/pdf",
        "document_type": "admission",
        "content": (
            "GOVERNMENT COLLEGE OF ENGINEERING & RESEARCH, PUNE\n"
            "PROVISIONAL ADMISSION ALLOTMENT LETTER - B.TECH UNDERGRADUATE\n"
            "Student Name: Asha Patel | Application No: ENG-STEM-2024-942\n"
            "Program / Discipline: B.Tech Computer Engineering (STEM Field)\n"
            "Current Academic Year: First Year Undergraduate (2024-2025)\n"
            "Allotment Status: Confirmed under General Merit Quota"
        ),
    },
}


def create_sample_document(sample_type: str, scheme_id: str | None = None) -> dict[str, Any]:
    """Generate and persist a demonstration document into the local SQLite store."""
    import uuid
    sample = SAMPLE_DOCUMENTS.get(sample_type) or SAMPLE_DOCUMENTS["marksheet"]
    upload_dir = get_upload_dir()
    doc_id = str(uuid.uuid4())
    stored_name = f"{doc_id}_{sample['filename']}"
    file_path = upload_dir / stored_name
    file_path.write_text(sample["content"], encoding="utf-8")
    
    with connect() as db:
        db.execute(
            """INSERT INTO documents
            (id, scheme_id, original_filename, stored_filename, mime_type, document_type, text_excerpt, extraction_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                scheme_id,
                sample["filename"],
                stored_name,
                sample["mime_type"],
                sample["document_type"],
                sample["content"],
                "demo_sample_extracted",
            ),
        )
    log_activity(None, "sample_document_created", {"document_id": doc_id, "type": sample["document_type"], "scheme_id": scheme_id})
    return {
        "id": doc_id,
        "filename": sample["filename"],
        "document_type": sample["document_type"],
        "extraction_status": "demo_sample_extracted",
        "text_preview": sample["content"][:500],
        "notice": "Fictional demonstration sample document for testing extraction and verification.",
    }


def classify_document(filename: str, text: str) -> str:
    normalized = f"{filename} {text}".casefold()
    labels = {
        "marksheet": ("marksheet", "mark sheet", "percentage", "grade"),
        "income": ("income", "salary", "family income"),
        "identity": ("passport", "identity", "id card", "aadhaar"),
        "residence": ("residence", "address", "domicile"),
        "admission": ("admission", "enrollment", "enrolment", "college"),
        "bank": ("bank", "account number", "ifsc"),
    }
    for document_type, terms in labels.items():
        if any(term in normalized for term in terms):
            return document_type
    return "unclassified"


def extract_text(path: Path, mime_type: str) -> tuple[str, str]:
    """Best-effort extraction; it never claims an upload is authentic."""
    suffix = path.suffix.casefold()
    if suffix == ".pdf" or mime_type == "application/pdf":
        try:
            import fitz
            with fitz.open(path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)
            return text[:12000], "pdf_text_extracted" if text.strip() else "pdf_has_no_extractable_text"
        except ImportError:
            return "", "pdf_extraction_dependency_unavailable"
        except Exception:
            return "", "pdf_text_extraction_failed"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"} or mime_type.startswith("image/"):
        try:
            from PIL import Image
            import pytesseract
            text = pytesseract.image_to_string(Image.open(path))
            return text[:12000], "image_ocr_extracted" if text.strip() else "image_ocr_no_text"
        except ImportError:
            return "", "image_ocr_dependency_unavailable"
        except Exception:
            return "", "image_ocr_failed"
    return "", "unsupported_file_type"


STOPWORDS = {
    "the", "and", "for", "are", "with", "what", "when", "where", "which", "who",
    "how", "can", "you", "your", "about", "from", "this", "that", "have", "has",
    "please", "tell", "need", "want", "real", "official", "government",
}


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w-]{3,}", value.casefold()) if token not in STOPWORDS}


def retrieve_context(scheme_id: str | None, question: str) -> list[dict[str, str]]:
    """Small lexical RAG layer over scheme metadata, rules, and uploaded excerpts."""
    terms = _tokens(question)
    with connect() as db:
        condition, params = (" WHERE scheme_id = ?", (scheme_id,)) if scheme_id else ("", ())
        documents = db.execute(
            f"SELECT original_filename, text_excerpt FROM documents{condition} ORDER BY created_at DESC",
            params,
        ).fetchall()
        schemes = db.execute(
            "SELECT name, short_description, authority_name, source_label, benefit, deadline, category, required_documents_json FROM schemes"
            + (" WHERE id = ?" if scheme_id else ""),
            params,
        ).fetchall()
        rules = db.execute(
            "SELECT display_text FROM scheme_rules" + (" WHERE scheme_id = ?" if scheme_id else ""),
            params,
        ).fetchall()

    candidates: list[dict[str, str]] = []
    for row in schemes:
        r_dict = dict(row)
        docs = decode_json(r_dict.get("required_documents_json"), [])
        doc_labels = ", ".join(item.get("label", item.get("type", "document")) for item in docs[:6])
        b_txt = f" Benefit: {r_dict['benefit']}." if r_dict.get("benefit") else ""
        d_txt = f" Application deadline: {r_dict['deadline']}." if r_dict.get("deadline") else ""
        content = f"{r_dict['name']}: {r_dict['short_description']}.{b_txt}{d_txt}"
        if doc_labels:
            content += f" Required documents: {doc_labels}."
        candidates.append({"reference": f"{r_dict['name']} ({r_dict.get('source_label', 'Demo')})", "content": content})
    for row in documents:
        excerpt = (row["text_excerpt"] or "").strip()
        if excerpt:
            candidates.append({"reference": f"Uploaded document: {row['original_filename']}", "content": excerpt[:1200]})
    candidates.extend({"reference": "Fictional demonstration rule", "content": row["display_text"]} for row in rules)

    if terms:
        ranked = [(len(terms & _tokens(item["content"])), item) for item in candidates]
        min_score = 1 if scheme_id else 2
        ranked = [entry for entry in ranked if entry[0] >= min_score]
        ranked.sort(key=lambda entry: entry[0], reverse=True)
        return [item for _, item in ranked[:4]]
    return []


def offline_grounded_answer(question: str, context: list[dict[str, str]], language: str) -> str:
    if not context:
        return "I do not have a matching source for that question yet. Please choose a fictional demo scheme or upload a source document. I will not guess official rules, dates, benefits, or submission status. What scheme or applicant detail should I help with?"
    facts = " ".join(item["content"] for item in context if item["content"]).strip()[:900]
    refs = "; ".join(dict.fromkeys(item["reference"] for item in context if item.get("reference")))
    language = language.casefold()
    if language.startswith("hi"):
        answer = f"उपलब्ध डेमो स्रोतों के अनुसार: {facts}"
        if refs:
            answer += f" (संदर्भ: {refs})"
        answer += " यह आधिकारिक निर्णय नहीं है। यदि कोई जानकारी अधूरी है, तो कृपया योजना या अपनी स्थिति बताएं।"
        return answer
    if language.startswith(("mr", "mar")):
        answer = f"उपलब्ध डेमो स्रोतांनुसार: {facts}"
        if refs:
            answer += f" (संदर्भ: {refs})"
        answer += " हा अधिकृत निर्णय नाही. काही माहिती अपुरी असल्यास कृपया योजना किंवा तुमची माहिती सांगा."
        return answer
    answer = f"Based on the available CivicPilot demo sources: {facts}"
    if refs:
        answer += f" (References: {refs})"
    answer += " This is not an official government determination. If anything is missing, tell me your scheme and applicant details so I can guide you."
    return answer


def generate_grounded_answer(question: str, context: list[dict[str, str]], language: str) -> tuple[str, str]:
    """Call Gemini only when configured; fallback remains source-grounded offline."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return offline_grounded_answer(question, context, language), "offline_source_grounded"
    source_text = "\n".join(f"[{item['reference']}] {item['content']}" for item in context) if context else "No matching source was retrieved."
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            f"{SYSTEM_PROMPT}\n\nRequested language: {language}\n"
            f"Retrieved sources:\n{source_text}\n\n"
            f"User question: {question}\n\n"
            "Instructions: answer using only the retrieved sources. If sources are missing or insufficient, say so clearly and ask for the missing information. "
            "Do not invent deadlines, benefits, eligibility rules, or submission status."
        )
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        answer = (getattr(response, "text", None) or "").strip()
        if answer:
            return answer, "gemini_source_grounded"
    except Exception:
        pass
    return offline_grounded_answer(question, context, language), "offline_source_grounded"

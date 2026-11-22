# CivicPilot AI

**Tagline:** Your Intelligent Government Service Assistant.  
**Track:** Civic Pulse – Digital Governance & Public Information.

CivicPilot AI is a functional hackathon MVP that helps students and citizens understand government schemes, check eligibility, prepare documents, and complete a **local simulated** application flow with AI assistance. It is built with FastAPI, vanilla HTML/CSS/JavaScript, SQLite, and optional Google Gemini / Playwright integrations.

> **Important safety notice:** This project uses **fictional demonstration data** and a **local simulated scholarship portal only**. It does not connect to, submit to, or automate any real government portal. It never bypasses CAPTCHA, OTP, or security mechanisms, never requests passwords/OTPs, and never claims a real application was submitted. Document extraction is best-effort and does **not** authenticate documents.

## Core features

- **AI Government Assistant:** grounded chat over supplied/scheme documents in English, Hindi, and Marathi (`/api/chat`, `/api/schemes/ask`). Uses Gemini when `GEMINI_API_KEY` is configured; otherwise uses a source-grounded offline fallback.
- **Smart Scholarship Eligibility Checker:** deterministic rule-based decisions with explanations, missing information, and supporting document references (`/api/eligibility/check`).
- **Intelligent Document Processing:** upload PDF/image documents, extract text (PyMuPDF / OCR where available), classify document type, show extraction status/preview, and generate document checklists (`/api/schemes/upload`, `/api/documents/checklist/{scheme_id}`).
- **AI-Powered Application Preparation:** collect/validate applicant info, save drafts, review before proceeding, and prepare a local demo form (`/api/applications`, `/api/applications/{id}/prepare-demo`).
- **Autonomous Browser Automation (local demo):** Playwright (with safe fallback) fills a local simulated portal, reports validation issues, and requires **separate explicit approval** before recording a simulated demo acknowledgement (`/api/applications/{id}/approve-demo`, `/demo-portal/{id}`).
- **Application Tracking Dashboard:** draft/progress/history/status, completed/pending steps, and demo reference numbers (`/api/applications`, `/api/applications/{id}`, `/api/applications/{id}/status`, `/api/dashboard`).
- **Frontend pages/views:** Landing Page, User Dashboard, AI Chat Assistant, Scholarship Explorer, Eligibility Checker, Document Upload, Application Preparation, Browser Automation Status, Application Tracking, About CivicPilot AI.

## Architecture

```text
USER
  |
  v
FRONTEND (HTML, CSS, JavaScript)
  |
  v
FASTAPI BACKEND
  |
  v
CIVICPILOT AI ORCHESTRATOR
  |-- Gemini AI Assistant (optional, grounded)
  |-- Scheme Document Retrieval (lexical RAG)
  |-- Eligibility Checking Engine (deterministic)
  |-- Document Processing Engine (PyMuPDF / OCR best-effort)
  |-- Playwright Browser Agent (local simulated portal only)
  |-- Human Approval Workflow (review confirm + demo approval)
  |
  v
SQLITE DATABASE
  |
  v
APPLICATION TRACKING DASHBOARD
```

AI-generated explanations are kept separate from deterministic eligibility decisions.

## Project layout

```text
backend/
  main.py         FastAPI app, API endpoints, static frontend mount, demo portal route
  database.py     SQLite schema, connection helpers, seeded fictional schemes/rules
  services.py     Eligibility rules, document checklist/extraction, lexical RAG, Gemini/fallback answers
  automation.py   Local simulated Playwright/fallback form fill and portal rendering
frontend/
  index.html      App shell, navigation, landing/app layout
  app.js          SPA routing, API integration, UI rendering and workflows
  styles.css      Premium responsive dashboard styling
tests/
  test_api.py     Core API/business-logic and workflow tests
.env.example      Environment variable template
requirements.txt  Python dependencies
```

## Setup and run

### Prerequisites
- Python 3.11+ (tested with Python 3.13)
- Optional: Tesseract OCR for image OCR extraction
- Optional: Playwright Chromium browser for browser automation mode (`python -m playwright install chromium`)

### 1) Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
# Optional, enables Playwright browser engine for the local demo portal:
python -m playwright install chromium
```

### 3) Configure environment variables

```bash
# Windows
copy .env.example .env
# macOS/Linux
cp .env.example .env
```

Edit `.env` as needed:
- `GEMINI_API_KEY` – optional; enables Gemini-backed grounded responses
- `GEMINI_MODEL` – optional model name (default used by backend)
- `CIVICPILOT_DB_PATH` – optional SQLite path (default: `backend/data/civicpilot.db`)
- `CIVICPILOT_UPLOAD_DIR` – optional upload directory
- `CORS_ORIGINS` – optional CORS origins

Keep API keys in backend environment variables only (never in frontend code).

### 4) Run the application

```bash
uvicorn backend.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The FastAPI app serves the frontend and mounts the API under `/api/*`. The local simulated demo portal is served at `/demo-portal/{application_id}`.

## Run tests

```bash
pytest -q
```

Core tests cover health/seeded schemes, deterministic eligibility decisions, two-step explicit demo approvals, grounded chat behavior when no matching source is available, and application listing.

## Demo workflow (end-to-end)

1. Open the dashboard and explore seeded fictional scholarships.
2. Ask the AI assistant questions (EN/HI/MR); answers are grounded in available sources or clearly state uncertainty.
3. (Optional) Upload a scheme-related PDF/image in **Document Upload** and review extraction/checklist.
4. Use **Eligibility Checker** for deterministic rule-based results and explanations.
5. Create an application draft in **Application Preparation** and review it.
6. Confirm review to prepare the **local simulated** portal (`confirmed_review=true`); inspect the pre-filled demo form.
7. Provide separate explicit approval to record a **simulated demo acknowledgement** (`approved=true`).
8. View progress, steps, and demo reference in **Application Tracking / Automation Status**.

## API overview

- `GET /api/health`
- `GET /api/schemes`
- `GET /api/dashboard`
- `POST /api/chat`
- `POST /api/schemes/ask`
- `POST /api/schemes/upload`
- `POST /api/eligibility/check`
- `GET /api/documents/checklist/{scheme_id}`
- `POST /api/applications`
- `GET /api/applications`
- `GET /api/applications/{application_id}`
- `POST /api/applications/{application_id}/prepare-demo`
- `POST /api/applications/{application_id}/approve-demo`
- `GET /api/applications/{application_id}/status`
- `GET /demo-portal/{application_id}` (local simulated portal page)

## Notes

- Seeded schemes and rules are fictional and for demonstration only.
- Eligibility outcomes are computed by deterministic backend rules, not by the LLM.
- Chat/RAG responses should cite available sources and avoid inventing official facts.
- The demo automation flow is local-only and requires explicit human approvals.

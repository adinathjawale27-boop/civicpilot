"""Safe local-only Playwright demonstration automation.

It never visits a government site, bypasses security, or submits an application.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any


def run_local_demo_fill(application: dict[str, Any], scheme: dict[str, Any]) -> dict[str, Any]:
    applicant = application.get("applicant", {})
    fields = {
        "name": str(applicant.get("name") or applicant.get("applicant_name") or ""),
        "email": str(applicant.get("email") or ""),
        "state": str(applicant.get("state") or ""),
        "family_income": str(applicant.get("family_income") or ""),
        "percentage": str(applicant.get("percentage") or ""),
        "current_level": str(applicant.get("current_level") or ""),
        "study_field": str(applicant.get("study_field") or ""),
    }
    validation_errors = []
    if not fields["name"]:
        validation_errors.append("Applicant name is required by the local demo portal.")
    if not fields["email"]:
        validation_errors.append("Email is required by the local demo portal.")

    now = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "environment": "local_simulated_portal",
        "scheme_name": scheme["name"],
        "scheme_id": scheme.get("id"),
        "filled_fields": fields,
        "validation_errors": validation_errors,
        "submission_performed": False,
        "simulation_only": True,
        "prepared_at": now,
        "notes": "Simulated local form fill executed in safe local test sandbox.",
        "safety_notice": "No government site was opened. No CAPTCHA, OTP, password, or real submission was attempted.",
    }
    try:
        from playwright.sync_api import sync_playwright
        markup = """
        <form id='demo-app-form'>
            <input id='name' name='name' required>
            <input id='email' name='email' type='email' required>
            <input id='state' name='state'>
            <input id='income' name='income'>
            <input id='percentage' name='percentage'>
            <input id='level' name='level'>
            <input id='field' name='field'>
        </form>
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(markup)
            page.fill("#name", fields["name"])
            page.fill("#email", fields["email"])
            page.fill("#state", fields["state"])
            page.fill("#income", fields["family_income"])
            page.fill("#percentage", fields["percentage"])
            page.fill("#level", fields["current_level"])
            page.fill("#field", fields["study_field"])
            result["browser_engine"] = "playwright_local_page"
            result["browser_validation_passed"] = bool(page.eval_on_selector("#demo-app-form", "form => form.checkValidity()"))
            browser.close()
    except Exception:
        result["browser_engine"] = "safe_local_fallback"
        result["browser_validation_passed"] = not validation_errors
    return result


def render_local_portal(application: dict[str, Any], scheme: dict[str, Any]) -> str:
    payload = application.get("demo_payload") or {}
    fields = payload.get("filled_fields", {})
    errors = payload.get("validation_errors", [])
    status = application.get("status", "draft")
    ref = application.get("demo_reference") or "PENDING-APPROVAL"

    errors_html = (
        "".join(f"<li class='err'>{escape(item)}</li>" for item in errors)
        if errors
        else "<li class='ok'>All demo form input validations passed successfully.</li>"
    )

    is_submitted = status == "demo_submitted"
    badge_label = f"DEMO ACKNOWLEDGED: {escape(ref)}" if is_submitted else "SIMULATED PRE-FILL · AWAITING REVIEW APPROVAL"
    badge_class = "badge-success" if is_submitted else "badge-pending"

    return f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>CivicPilot Simulated Portal · {escape(scheme['name'])}</title>
  <style>
    :root {{
      --bg: #f0f4f9;
      --card-bg: #ffffff;
      --primary: #0e3768;
      --accent: #2563eb;
      --border: #d2dce8;
      --text: #1a2738;
      --muted: #5e6f84;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 820px;
      margin: 0 auto;
      background: var(--card-bg);
      border-radius: 16px;
      border: 1px solid var(--border);
      box-shadow: 0 10px 30px rgba(10,35,68,0.08);
      overflow: hidden;
    }}
    .sim-bar {{
      background: #fef3c7;
      color: #92400e;
      border-bottom: 1px solid #fde68a;
      padding: 10px 20px;
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .portal-header {{
      padding: 28px 32px 20px;
      background: linear-gradient(135deg, #092040 0%, #133c6f 100%);
      color: white;
    }}
    .portal-header h1 {{
      margin: 6px 0 4px;
      font-size: 22px;
    }}
    .portal-header p {{
      margin: 0;
      color: #cbdcf2;
      font-size: 13px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .4px;
      margin-top: 10px;
    }}
    .badge-pending {{ background: #fef3c7; color: #92400e; }}
    .badge-success {{ background: #d1fae5; color: #065f46; }}
    .content {{
      padding: 32px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 18px;
    }}
    .field {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .field.full {{
      grid-column: 1 / -1;
    }}
    label {{
      font-size: 12px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .5px;
    }}
    .input-box {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 14px;
      font-weight: 600;
      color: #0f172a;
    }}
    .card-section {{
      margin-top: 24px;
      padding: 18px;
      background: #f8fafc;
      border-radius: 12px;
      border: 1px solid var(--border);
    }}
    .card-section h3 {{
      margin: 0 0 10px;
      font-size: 14px;
      color: var(--primary);
    }}
    ul.check-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 6px;
      font-size: 13px;
    }}
    ul.check-list li.ok {{ color: #059669; font-weight: 600; }}
    ul.check-list li.err {{ color: #dc2626; font-weight: 600; }}
    .actions {{
      margin-top: 28px;
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--border);
      padding-top: 20px;
    }}
    .btn {{
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid transparent;
      text-decoration: none;
    }}
    .btn-disabled {{
      background: #e2e8f0;
      color: #64748b;
      cursor: not-allowed;
    }}
    .btn-print {{
      background: #0e3768;
      color: white;
    }}
    .footer-note {{
      margin-top: 24px;
      padding: 14px;
      background: #eef4fb;
      border-radius: 8px;
      font-size: 11px;
      color: #4b6282;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class='container'>
    <div class='sim-bar'>
      <span>⚠️</span>
      <span>SIMULATED DEMONSTRATION PORTAL · LOCAL CIVICPILOT TESTBED ONLY · NO REAL SUBMISSION</span>
    </div>

    <div class='portal-header'>
      <div style='font-size: 11px; letter-spacing: 1px; color: #8cb8eb; font-weight: 700;'>STATE SCHOLARSHIP PORTAL (LOCAL SIMULATION)</div>
      <h1>{escape(scheme['name'])}</h1>
      <p>Simulated Application ID: <b>{escape(application['id'])}</b> · Authority: {escape(scheme.get('authority_name', 'CivicPilot Demo'))}</p>
      <span class='badge {badge_class}'>{badge_label}</span>
    </div>

    <div class='content'>
      <div class='card-section'>
        <h3>Pre-filled Applicant Record (Playwright Browser Fill)</h3>
        <div class='grid'>
          <div class='field'>
            <label>Applicant Full Name</label>
            <div class='input-box'>{escape(fields.get('name', '—'))}</div>
          </div>
          <div class='field'>
            <label>Registered Email</label>
            <div class='input-box'>{escape(fields.get('email', '—'))}</div>
          </div>
          <div class='field'>
            <label>State of Residence</label>
            <div class='input-box'>{escape(fields.get('state', '—'))}</div>
          </div>
          <div class='field'>
            <label>Annual Family Income</label>
            <div class='input-box'>₹{escape(str(fields.get('family_income', '—')))}</div>
          </div>
          <div class='field'>
            <label>Latest Examination Score</label>
            <div class='input-box'>{escape(str(fields.get('percentage', '—')))}%</div>
          </div>
          <div class='field'>
            <label>Education Level</label>
            <div class='input-box'>{escape(fields.get('current_level', '—'))}</div>
          </div>
          <div class='field full'>
            <label>Discipline / Program</label>
            <div class='input-box'>{escape(fields.get('study_field', '—'))}</div>
          </div>
        </div>
      </div>

      <div class='card-section'>
        <h3>Local Simulated Validation Audit</h3>
        <ul class='check-list'>
          {errors_html}
        </ul>
      </div>

      <div class='actions'>
        <div>
          <button onclick='window.print()' class='btn btn-print'>Print / Save Portal Copy</button>
        </div>
        <div>
          <button class='btn btn-disabled' disabled aria-disabled='true'>
            { "Demo Submitted via API" if is_submitted else "Submission Gated — Requires CivicPilot Human Approval" }
          </button>
        </div>
      </div>

      <div class='footer-note'>
        Safety Guarantee: CivicPilot AI operates strictly in a local sandbox for this demonstration.
        It does not interact with government databases or bypass identity authentication.
      </div>
    </div>
  </div>
</body>
</html>"""


def render_acknowledgment_slip(application: dict[str, Any], scheme: dict[str, Any]) -> str:
    applicant = application.get("applicant", {})
    demo_ref = application.get("demo_reference") or f"CP-DEMO-{application['id'][:8].upper()}"
    status = application.get("status", "draft")
    updated_at = application.get("updated_at") or datetime.now(timezone.utc).isoformat()
    steps = application.get("steps", [])

    steps_rows = "".join(
        f"<tr><td>{escape(s.get('label', s.get('step_key', '')))}</td>"
        f"<td><span style='color:{'#059669' if s.get('status')=='completed' else '#d97706'};font-weight:700'>{escape(s.get('status',''))}</span></td>"
        f"<td>{escape(s.get('updated_at','—'))}</td></tr>"
        for s in steps
    )

    return f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <title>Acknowledgment Receipt · {escape(demo_ref)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eaeff5; margin: 0; padding: 28px; color: #1e293b; }}
    .slip-container {{ max-width: 750px; margin: 0 auto; background: white; border-radius: 14px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border: 2px solid #cbd5e1; overflow: hidden; }}
    .watermark {{ background: #fef3c7; color: #92400e; padding: 10px 20px; font-size: 12px; font-weight: 800; text-align: center; letter-spacing: 1px; border-bottom: 2px dashed #f59e0b; }}
    .header {{ padding: 28px; background: #07172d; color: white; display: flex; justify-content: space-between; align-items: flex-start; }}
    .header h1 {{ margin: 0 0 6px; font-size: 20px; }}
    .header p {{ margin: 0; font-size: 13px; color: #93c5fd; }}
    .ref-badge {{ background: #1e3a8a; border: 1px solid #3b82f6; border-radius: 8px; padding: 10px 14px; text-align: right; }}
    .ref-badge span {{ font-size: 10px; color: #93c5fd; display: block; text-transform: uppercase; font-weight: 700; }}
    .ref-badge b {{ font-size: 15px; color: #ffffff; font-family: monospace; letter-spacing: 1px; }}
    .body {{ padding: 28px; }}
    h3 {{ margin: 20px 0 10px; font-size: 14px; color: #0f172a; text-transform: uppercase; letter-spacing: .5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
    .info-table th, .info-table td {{ padding: 8px 12px; font-size: 13px; text-align: left; border-bottom: 1px solid #f1f5f9; }}
    .info-table th {{ width: 35%; color: #64748b; font-weight: 600; background: #f8fafc; }}
    .info-table td {{ color: #0f172a; font-weight: 600; }}
    .stamp-box {{ margin-top: 24px; padding: 16px; border-radius: 8px; background: #f0fdf4; border: 1px solid #bbf7d0; display: flex; align-items: center; justify-content: space-between; }}
    .stamp-text b {{ color: #166534; display: block; font-size: 14px; }}
    .stamp-text span {{ color: #15803d; font-size: 12px; }}
    .qr-fake {{ width: 64px; height: 64px; background: #07172d; color: #fff; font-size: 9px; display: grid; place-items: center; text-align: center; border-radius: 6px; font-weight: 800; }}
    .actions {{ margin-top: 24px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 18px; }}
    .btn {{ background: #07172d; color: white; padding: 10px 20px; border-radius: 8px; border: 0; font-weight: 700; cursor: pointer; text-decoration: none; font-size: 13px; }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .slip-container {{ box-shadow: none; border: 1px solid #000; }}
      .actions {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class='slip-container'>
    <div class='watermark'>⚠️ CIVICPILOT SIMULATION DEMO ONLY · NOT AN OFFICIAL GOVERNMENT DOCUMENT</div>
    <div class='header'>
      <div>
        <div style='font-size:11px; font-weight:700; color:#60a5fa; letter-spacing:1px; margin-bottom:4px'>CIVICPILOT AI · DIGITAL GOVERNANCE DEMONSTRATION</div>
        <h1>Application Acknowledgment Receipt</h1>
        <p>{escape(scheme.get('name', 'Demonstration Scheme'))}</p>
      </div>
      <div class='ref-badge'>
        <span>Reference Number</span>
        <b>{escape(demo_ref)}</b>
      </div>
    </div>
    <div class='body'>
      <h3>Applicant Profile</h3>
      <table class='info-table'>
        <tr><th>Full Name</th><td>{escape(applicant.get('name', '—'))}</td></tr>
        <tr><th>Email Address</th><td>{escape(applicant.get('email', '—'))}</td></tr>
        <tr><th>State of Residence</th><td>{escape(applicant.get('state', '—'))}</td></tr>
        <tr><th>Annual Family Income</th><td>₹{escape(str(applicant.get('family_income', '—')))}</td></tr>
        <tr><th>Academic Percentage</th><td>{escape(str(applicant.get('percentage', '—')))}%</td></tr>
        <tr><th>Education Level / Course</th><td>{escape(applicant.get('current_level', '—'))} ({escape(applicant.get('study_field', 'General'))})</td></tr>
      </table>

      <h3>Scheme & Verification Details</h3>
      <table class='info-table'>
        <tr><th>Scheme Name</th><td>{escape(scheme.get('name', '—'))}</td></tr>
        <tr><th>Authority / Cell</th><td>{escape(scheme.get('authority_name', '—'))}</td></tr>
        <tr><th>Category</th><td>{escape(scheme.get('category', 'Education Grant'))}</td></tr>
        <tr><th>Estimated Demo Benefit</th><td>{escape(scheme.get('benefit', 'Standard demo allowance'))}</td></tr>
        <tr><th>Audit Status</th><td><span style='color:#059669;font-weight:700'>{escape(status.upper())}</span></td></tr>
        <tr><th>Acknowledged Timestamp</th><td>{escape(updated_at)}</td></tr>
      </table>

      <h3>Workflow Execution Log</h3>
      <table class='info-table'>
        <thead><tr style='background:#f8fafc'><th style='width:40%'>Workflow Step</th><th>Status</th><th>Updated</th></tr></thead>
        <tbody>{steps_rows}</tbody>
      </table>

      <div class='stamp-box'>
        <div class='stamp-text'>
          <b>✓ SIMULATED HUMAN-APPROVED DEMO ACKNOWLEDGEMENT</b>
          <span>This receipt confirms completion of the 2-step explicit human-in-the-loop review workflow in CivicPilot.</span>
        </div>
        <div class='qr-fake'>VERIFIED<br>DEMO</div>
      </div>

      <div class='actions'>
        <button onclick='window.print()' class='btn'>🖨️ Print Receipt</button>
        <span style='font-size:11px;color:#64748b'>CivicPulse - Digital Governance & Public Information</span>
      </div>
    </div>
  </div>
</body>
</html>"""

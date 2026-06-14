# Eluno AI — Order Management System

AI-powered order management system for an eyewear brand. Built for the Eluno AI take-home.

## Stack

- **Backend**: FastAPI (Python 3.12)
- **Templates**: Jinja2 + HTMX + Tailwind (CDN, no build step)
- **Database**: Supabase (Postgres)
- **AI**: Google Gemini 2.0 Flash — prescription Vision parsing + TAT risk reasoning
- **Alerts**: Resend (email) + Twilio (WhatsApp sandbox)
- **Deploy**: Render (free tier)

## Modules

1. **Lens Inventory + Order Intake** — Rx photo -> Gemini Vision -> inventory match (exact / tolerance / cut-from-blank / source)
2. **Dashboard** — filterable order list, SLA countdown, status transitions, audit trail
3. **TAT Prediction & Alerts** — Gemini reasons about breach risk; high-risk orders fire email + WhatsApp

## Local dev (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# fill in keys, then:
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Project layout

```
app/
  main.py            # FastAPI entry
  templates/         # Jinja2 + HTMX
scripts/
  schema.sql         # Supabase schema
  seed.py            # Realistic seed data
```

# Resume Generator API (Flask + Gemini)

A Python/Flask REST API that extracts text from user resumes (PDF/JPG/PNG), leverages Google Gemini (Generative AI) to generate a structured, ATS‑friendly resume tailored to a provided job description, and stores results in a SQL database. Includes JWT‑based auth middleware, CORS, and SQLite/PostgreSQL support.


## Tech Stack
- Language: Python 3.10+
- Framework: Flask
- ORM/DB: SQLAlchemy + Flask‑SQLAlchemy
  - Development default: SQLite (file `database2.db`)
  - Production ready: PostgreSQL (via `DATABASE_URL`)
- Auth: JSON Web Tokens (HS256, python‑jose)
- AI: Google Generative AI (Gemini)
- File/Image/PDF: Pillow (PIL), PyMuPDF (fitz)
- Config: python‑dotenv
- CORS: flask‑cors

Package manager: pip (requirements.txt)


## Overview
This API accepts a resume file and a job description, extracts text (PDF/image), and asks Gemini to produce a structured JSON resume with an ATS score and feedback. Results are stored and can be retrieved later. Some endpoints require a Bearer JWT.


## Requirements
- Python 3.10 or newer
- A Google AI Studio API key for Gemini (GEMINI_API_KEY)
- Optional: PostgreSQL database (otherwise SQLite is used by default)
- Windows, macOS, or Linux (commands below show Windows PowerShell)


## Getting Started

1) Clone and enter the project directory
- Place your shell at the project root: `F:\AtsCv` (Windows path shown)

2) Create and activate a virtual environment (PowerShell)
- python -m venv .venv
- .\.venv\Scripts\Activate.ps1

3) Install dependencies
- pip install -r requirements.txt

4) Configure environment variables
Create a `.env` file in the project root with values relevant to your environment. Example:

GEMINI_API_KEY=your_gemini_api_key_here
# Used by jwt_auth.py for verifying incoming Bearer tokens (HS256)
JWT_SECRET_KEY=your_very_long_random_secret
# Optional: shared secret used somewhere else in your stack
SECRET_KEY=your_shared_secret_with_node
# Database (defaults to SQLite if not set)
# For Postgres on Render/Heroku, you might get postgres:// — code will rewrite to postgresql:// automatically
DATABASE_URL=sqlite:///database2.db
# CORS allowed origin. If not set, CORS is open for /api/* in dev.
ALLOWED_ORIGINS=http://localhost:5173
# Port to bind (defaults to 5008)
PORT=5008

5) Run the server
- python app.py
- The server binds to 0.0.0.0 on PORT (default 5008). Example: http://localhost:5008/

The app will auto‑create tables on first run.


## API Endpoints
All responses are JSON. Routes under /api/* support CORS (see ALLOWED_ORIGINS).

- GET /
  - Health/identity ping.
  - Response: { status, service, version, timestamp }

- GET /api/health
  - Checks DB connectivity.
  - Response: { status, database, timestamp }

- POST /api/generate-resume (Auth required)
  - Headers: Authorization: Bearer <JWT>
  - Content-Type: multipart/form-data
  - Form fields:
    - resume_file: file (pdf|png|jpg|jpeg), max 16 MB
    - job_description: string (required)
  - Behavior:
    - Extracts text from resume (PDF via PyMuPDF; images via Pillow)
    - Calls Gemini (model: gemini-2.0-flash-exp) to return structured JSON with ATS score and feedback
    - Stores full result in DB
    - Returns: { success, message, resume_id, preview: { name, ats_score } }

- POST /api/resume/<resume_id> (Auth required)
  - Headers: Authorization: Bearer <JWT>
  - Content-Type: application/x-www-form-urlencoded or multipart/form-data
  - Form fields:
    - payment: "1" for full access; anything else returns a limited preview
  - Returns stored structured data; limited fields if payment != "1".

- GET /api/user-resumes (Auth required)
  - Headers: Authorization: Bearer <JWT>
  - Returns latest resumes for the authenticated user, with brief metadata.


## Authentication
- Middleware: jwt_auth.require_auth
- Algorithm: HS256
- Secret: JWT_SECRET_KEY (from environment). If not set, a hardcoded default is used (not recommended for production).
- Required claims in token payload:
  - email (required)
  - username or user_id (optional; used for display)

Example payload:
{
  "email": "user@example.com",
  "username": "jdoe"
}


## Database
- Default: SQLite file `database2.db` in the project root when `DATABASE_URL` is not provided.
- Production: Set `DATABASE_URL` to your Postgres connection string. If it starts with `postgres://`, the app will rewrite it to `postgresql://` for SQLAlchemy.
- Models are defined in `models.py` (CandidateProfile, Resume, and others for interviews/analysis). Tables are created on app startup.


## Running in Production
- The app exposes Flask on 0.0.0.0:PORT. Use a production WSGI server or process manager of your choice (e.g., gunicorn, waitress, uvicorn with ASGI wrappers). Example commands are not included in repo scripts; typical usage:
  - pip install waitress
  - python -c "from app import app, init_db; init_db(); from waitress import serve; serve(app, host='0.0.0.0', port=5008)"
- Ensure environment variables are set and that `GEMINI_API_KEY` and `JWT_SECRET_KEY` are securely provided.


## Useful Commands (PowerShell)
- Create venv: python -m venv .venv
- Activate venv: .\.venv\Scripts\Activate.ps1
- Install deps: pip install -r requirements.txt
- Run dev server: python app.py


## Environment Variables
- GEMINI_API_KEY: Google AI Studio API key (required for resume generation)
- JWT_SECRET_KEY: Secret for verifying HS256 JWTs (strongly recommended to set in all envs)
- SECRET_KEY: Optional shared secret used in the app (default provided in code)
- DATABASE_URL: SQLAlchemy URL. Defaults to `sqlite:///database2.db`
- ALLOWED_ORIGINS: CORS allowlist for /api/* (e.g., your frontend URL). If unset, CORS is open in dev.
- PORT: Port to bind Flask (default 5008)


## Testing
No automated tests are included. You can manually exercise endpoints with curl or Postman.

Examples (PowerShell):

# Health
curl http://localhost:5008/api/health

# Generate JWT (example shown conceptually — use your own JWT tool) and set $TOKEN
# $TOKEN = "<your HS256 JWT with email claim>"

# Generate resume (multipart form)
curl -X POST http://localhost:5008/api/generate-resume `
  -H "Authorization: Bearer $TOKEN" `
  -F "resume_file=@C:\\path\\to\\resume.pdf" `
  -F "job_description=Senior Python Developer at Acme"

# Fetch full resume (payment=1)
curl -X POST http://localhost:5008/api/resume/1 `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  --data "payment=1"

# List user resumes
curl -H "Authorization: Bearer $TOKEN" http://localhost:5008/api/user-resumes


## Project Structure
- app.py — Flask app, routes, Gemini integration, DB init
- db.py — SQLAlchemy init and DATABASE_URL normalization
- models.py — ORM models (CandidateProfile, Resume, and related entities)
- jwt_auth.py — JWT middleware (HS256)
- requirements.txt — Python dependencies
- instance/database2.db — Example SQLite DB file (dev use; safe to delete/regenerate)


## Notes & Limits
- Max upload size: 16 MB (configured via Flask MAX_CONTENT_LENGTH in code)
- Allowed resume file types: pdf, png, jpg, jpeg
- Gemini model used: gemini-2.0-flash-exp
- If `ALLOWED_ORIGINS` is not set, CORS for /api/* is open in development.



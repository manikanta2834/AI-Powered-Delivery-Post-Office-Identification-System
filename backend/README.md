# AI Postal Intelligence API

FastAPI backend foundation for the AI-Powered Delivery Post Office Identification System.

## Local setup

1. Copy `backend/.env.example` to `.env`.
2. Start PostgreSQL/PostGIS/pgvector and Redis from the repository root:

```powershell
docker compose up -d
```

3. Install dependencies into the active Python environment:

```powershell
python -m pip install -r backend/requirements.txt
```

4. Run the API from the repository root:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --app-dir backend
```

The API is available at `http://localhost:8000`.

- `GET /api/v1/health` checks the process.
- `GET /api/v1/ready` checks PostgreSQL and Redis.
- `GET /docs` opens the OpenAPI UI.

Set `AUTO_CREATE_SCHEMA=true` for local prototyping when the database is reachable. Use migrations before production deployment.

## Authentication and operations

- `POST /api/v1/auth/signup` creates an operator account with Argon2 password hashing.
- `POST /api/v1/auth/login` returns a short-lived JWT and rotating refresh token.
- `POST /api/v1/auth/refresh` rotates a refresh session.
- `GET /api/v1/auth/me` returns the authenticated operator.
- `GET /api/v1/audit-logs` returns that operator's recent security and workflow events.

New tables:

- `users` and `user_sessions`: account identity, roles, active status, and revocable sessions.
- `audit_logs`: append-only operational/security events without storing passwords or tokens.
- `address_analyses`: raw/normalized address, language, conflicts, confidence, and model metadata.
- `analysis_candidates`: ranked post-office candidates and per-factor explanations.

For production, set a long random `JWT_SECRET` in `.env`, keep `AUTO_CREATE_SCHEMA=false`, and apply a versioned migration.

## Database foundation

The initial schema includes:

- `post_offices`: PIN, district, state, geospatial point, and vector embedding.
- `localities`: normalized locality records linked to post offices.
- `locality_aliases`: multilingual and misspelled locality aliases.
- `human_corrections`: human-in-the-loop corrections for future learning.

The database container enables PostGIS and pgvector through the `pgvector/pgvector` image.

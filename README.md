# Model Registry

Full-stack application for registering, ingesting, rating, and serving ML artifacts (models, datasets, code). The project includes both backend APIs (Flask) and a frontend (served alongside the API) plus ingestion workers/Lambda integration.

## Features
- Register artifacts (model/dataset/code) with duplicate detection and optional synchronous ingestion in dev/test.
- Secure download URLs (S3 presigned) and artifact CRUD with creator/admin checks.
- Artifact ingestion worker with scoring, metadata collection, and audit logging.
- License compatibility checks, cost estimation, lineage graph traversal, and regex search.
- JWT authentication with role-based authorization and request limiting.
- Audit trail for creates, updates, downloads, deletes, and content changes.

## Tech Stack
- Backend: Python 3.12, Flask, Flask-JWT-Extended, Flask-CORS
- Frontend: React + Vite (TypeScript) UI served from the repo
- Data: SQLAlchemy + Alembic (SQLite by default, configurable via `DATABASE_URL`)
- Cloud: boto3 (S3 uploads/presigned URLs), AWS Lambda trigger for ingestion
- Auth/Security: PyJWT, bcrypt, python-dotenv
- Tooling: pytest, flake8, mypy

## Setup
```bash
git clone <repo>
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

## Configuration
Create a `.env` in `backend/` (python-dotenv is used). Common variables:
- `JWT_SECRET_KEY` – secret for JWT signing
- `DATABASE_URL` – SQLAlchemy URL (default: local SQLite)
- `AWS_REGION`, `S3_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` – S3 access
- `INGESTION_LAMBDA_NAME` – Lambda name for async ingestion (prod)
- `HUGGINGFACE_HUB_TOKEN` – passed to HF client requests
- `HOST`, `PORT`, `DEBUG`, `UPLOAD_DIR`, `MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS`
- Rating/ingestion tuning: `RATING_WAIT_TIMEOUT_SECONDS`, `RATING_WAIT_POLL_SECONDS`

## Running the API
```bash
cd backend
FLASK_APP=app flask run  # or python -m app
```
The API is namespaced under `/api` (e.g., `/api/artifact/...`, `/api/artifacts/...`, `/api/ratings`, `/api/lineage`, `/api/auth/...`).

## Usage Examples
- Register artifact: `POST /api/artifact/<type>` with JSON `{"url": "...", "name": "optional"}` (JWT with `X-Authorization: Bearer <token>`).
- Fetch artifact: `GET /api/artifacts/<type>/<id>` returns metadata and presigned `download_url` when available.
- Update artifact: `PUT /api/artifacts/<type>/<id>` (creator/admin only) to rename or change source URL.
- Delete artifact: `DELETE /api/artifacts/<type>/<id>` (creator/admin only), logs audit event.
- License check: `POST /api/artifact/model/<id>/license-check` with GitHub URL payload.
- Lineage: `GET /api/artifact/<type>/<id>/lineage`.
- Regex search: `POST /api/artifact/byRegEx` with `{"regex": "pattern"}`.

## Project Structure (high level)
- `app/api/` – HTTP routes (`artifact(s)`, ratings, lineage, auth, health, reset)
- `app/services/` – business logic (artifact, ratings, lineage, auth, storage, HF clients)
- `app/dals/` – data access layers (artifacts, ratings, users, audit)
- `app/db/` – models, session management
- `app/workers/ingestion_worker/` – ingestion logic and scoring pipeline
- `app/auth/` – auth routes, JWT handlers, rate limiting
- `frontend/` (or equivalent) – UI assets served by the app
- `tests/` – API, services, worker, DAL, and utility tests

## Tests & Linting
```bash
cd backend
pytest --cov=app
black .
flake8 .
isort .
mypy .
```

## Contribution Guidelines
- Use feature branches and keep changes focused.
- Add/adjust tests for new behavior; keep flake8/mypy/pytest green.
- Follow existing patterns (service/DAL separation, short lines for flake8).
- Prefer environment-driven configuration and avoid hardcoding secrets.

## Contributors
- Noddie Mgbodille
- Trevor Ju
- Anna Stark
- Will Ott

## License

This project is licensed under the MIT License. See the LICENSE file for details.

SHELL := bash
BACKEND_DIR := backend
VENV := $(BACKEND_DIR)/venv
PYTHON := python3.12
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Gunicorn entrypoint; change to your module if different
# e.g., APP_MODULE := app:app  OR  app:wsgi_app
APP_MODULE := app:wsgi_app
GUNICORN_OPTS := -w 2 -k gthread -b 0.0.0.0:8000

# Coverage threshold
COV := 60

# -------- Phony targets --------
.PHONY: help setup install clean lint format typecheck test test-unit test-int \
        cov-html run dev migrate-new migrate-up migrate-down precommit seed-admin reset

help:
	@echo "make setup         - Create venv (Python 3.12) and install backend deps (.[dev])"
	@echo "make lint          - Run black/isort/flake8"
	@echo "make format        - Auto-format with black + isort"
	@echo "make typecheck     - Run mypy"
	@echo "make test          - Run unit tests w/ coverage (threshold $(COV)%)"
	@echo "make test-unit     - Run only unit tests"
	@echo "make test-int      - Run only integration tests"
	@echo "make cov-html      - Build HTML coverage report (htmlcov/)"
	@echo "make run           - Run API with gunicorn on :8000"
	@echo "make dev           - Flask dev server (if you prefer)"
	@echo "make migrate-new   - Alembic autogenerate a new migration"
	@echo "make migrate-up    - Alembic upgrade head"
	@echo "make migrate-down  - Alembic downgrade -1"
	@echo "make precommit     - Install pre-commit hooks"
	@echo "make seed-admin    - Create default admin user"
	@echo "make reset         - Reset system (danger!)"
	@echo "make clean         - Remove caches, build artifacts"

setup:
	@echo ">>> Creating venv in $(VENV) with $(PYTHON)"
	@cd $(BACKEND_DIR) && $(PYTHON) -m venv venv
	@$(PIP) -V >/dev/null || (echo "venv missing?"; exit 1)
	@$(PIP) install --upgrade pip
	@$(PIP) install -e $(BACKEND_DIR)/.[dev]

install: setup  ## alias

# -------- Quality gates --------
lint:
	@cd $(BACKEND_DIR) && $(VENV)/bin/black --check .
	@cd $(BACKEND_DIR) && $(VENV)/bin/isort --check-only --diff .
	@cd $(BACKEND_DIR) && $(VENV)/bin/flake8 .

# Autoformat python code. Some Flake8 rules may need to be handled manually
format:
	@cd $(BACKEND_DIR) && $(VENV)/bin/isort .
	@cd $(BACKEND_DIR) && $(VENV)/bin/black .

typecheck:
	@cd $(BACKEND_DIR) && $(VENV)/bin/mypy --config-file=pyproject.toml

# -------- Tests --------
test:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q --maxfail=1 --disable-warnings \
		-m "not integration and not e2e and not perf" \
		--cov=app --cov-report=term-missing \
		--cov-report=xml:coverage.xml --cov-fail-under=$(COV)

test-unit:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q -m "unit"

test-int:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q -m "integration"

cov-html:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest --cov=app --cov-report=html

# Run API
run:
	@cd $(BACKEND_DIR) && $(VENV)/bin/gunicorn $(APP_MODULE) -c gunicorn.conf.py $(GUNICORN_OPTS)

# If you prefer Flask dev server (ensure FLASK_APP is set, e.g. app/wsgi.py)
dev:
	@cd $(BACKEND_DIR) && FLASK_APP=$(APP_MODULE) FLASK_ENV=development $(VENV)/bin/flask run --host=0.0.0.0 --port=8000

# Migrations
# migrate-new:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic revision --autogenerate -m "$$(date +'%Y-%m-%d %H:%M:%S')"

# migrate-up:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic upgrade head

# migrate-down:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic downgrade -1

# Repo hygiene
precommit:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pre-commit install

# seed-admin:
# 	@$(PY) scripts/seed_default_admin.py

# reset:
# 	@$(PY) scripts/reset_system.py

clean:
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.mypy_cache \
		$(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/coverage.xml $(BACKEND_DIR)/model_registry.egg-info

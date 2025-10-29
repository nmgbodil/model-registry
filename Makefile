SHELL := bash
BACKEND_DIR := backend
VENV := $(BACKEND_DIR)/venv
PYTHON := python3.12
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# coverage threshold for make test
COV := 60

# EDIT THIS if your Flask app entrypoint isn't app/__init__.py:app
FLASK_APP := app
FLASK_PORT := 8000
FLASK_HOST := 0.0.0.0

.PHONY: help setup install clean lint format typecheck test test-unit test-int \
        cov-html run dev migrate-new migrate-up migrate-down precommit \
        seed-admin reset

help:
	@echo "make setup         - Create venv and install backend deps (.[dev])"
	@echo "make run           - Run Flask dev server with debug/reload"
	@echo "make lint          - Run black/isort/flake8"
	@echo "make format        - Auto-format with black + isort"
	@echo "make typecheck     - Run mypy"
	@echo "make test          - Run unit tests w/ coverage (threshold $(COV)%)"
	@echo "make test-unit     - Run only unit tests"
	@echo "make test-int      - Run only integration tests"
	@echo "make cov-html      - Build HTML coverage report"
	@echo "make migrate-new   - Alembic autogenerate new migration"
	@echo "make migrate-up    - Alembic upgrade head"
	@echo "make migrate-down  - Alembic downgrade -1"
	@echo "make precommit     - Install pre-commit hooks"
	@echo "make seed-admin    - Create default admin user"
	@echo "make reset         - Reset system (danger!)"
	@echo "make clean         - Clean caches/artifacts"

# ----- env / install -----

setup:
	@echo ">>> Creating venv in $(VENV) with $(PYTHON)"
	@cd $(BACKEND_DIR) && $(PYTHON) -m venv venv
	@$(PIP) -V >/dev/null || (echo "venv missing?"; exit 1)
	@$(PIP) install --upgrade pip
	@cd $(BACKEND_DIR) && $(PIP) install -e .[dev]

install: setup

# ----- run app (Flask debug server) -----

run:
	@echo ">>> Starting Flask in debug mode on http://$(FLASK_HOST):$(FLASK_PORT)"
	@cd $(BACKEND_DIR) && \
		source venv/bin/activate && \
		export FLASK_APP=$(FLASK_APP) && \
		export FLASK_ENV=development && \
		export FLASK_DEBUG=1 && \
		flask run --host=$(FLASK_HOST) --port=$(FLASK_PORT)

# Keep `dev` as alias to `run`
dev: run

# ----- quality gates -----

lint:
	@cd $(BACKEND_DIR) && $(VENV)/bin/black --check .
	@cd $(BACKEND_DIR) && $(VENV)/bin/isort --check-only --diff .
	@cd $(BACKEND_DIR) && $(VENV)/bin/flake8 .

format:
	@cd $(BACKEND_DIR) && $(VENV)/bin/isort .
	@cd $(BACKEND_DIR) && $(VENV)/bin/black .

typecheck:
	@cd $(BACKEND_DIR) && $(VENV)/bin/mypy --config-file=pyproject.toml

# ----- tests -----

test:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q --maxfail=1 --disable-warnings \
		-m "not integration and not e2e and not perf" \
		--cov=app --cov-report=term-missing \
		--cov-report=xml:coverage.xml --cov-fail-under=$(COV)

test-unit:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q -m "unit"

# test-int:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest -q -m "integration"

cov-html:
	@cd $(BACKEND_DIR) && $(VENV)/bin/pytest --cov=app --cov-report=html

# ----- migrations -----

# migrate-new:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic revision --autogenerate -m "$$(date +'%Y-%m-%d %H:%M:%S')"

# migrate-up:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic upgrade head

# migrate-down:
# 	@cd $(BACKEND_DIR) && $(VENV)/bin/alembic downgrade -1

# ----- repo hygiene / ops -----

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
		$(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/coverage.xml

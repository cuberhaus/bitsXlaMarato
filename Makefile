# bitsXlaMarato – Aorta Segmentation
# ===================================

PYTHON       ?= python3
PIP          ?= pip
NPM          ?= npm
BACKEND_DIR   = web/backend
FRONTEND_DIR  = web/frontend
BACKEND_PORT ?= 8001
VENV          = .venv

# ── Setup ──────────────────────────────────────────────

.PHONY: install install-backend install-frontend venv

venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Activate with: source $(VENV)/bin/activate"

install: install-backend install-frontend

install-backend:
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

install-frontend:
	cd $(FRONTEND_DIR) && $(NPM) install

# ── Development ────────────────────────────────────────

.PHONY: dev dev-backend dev-frontend

dev-backend:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app:app --reload --port $(BACKEND_PORT)

dev-frontend:
	cd $(FRONTEND_DIR) && NG_CLI_ANALYTICS=false $(NPM) start

dev: install
	-@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	-@lsof -ti:4200 | xargs kill -9 2>/dev/null || true
	@trap 'kill 0' EXIT; \
	(cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app:app --reload --port $(BACKEND_PORT)) & \
	(cd $(FRONTEND_DIR) && NG_CLI_ANALYTICS=false $(NPM) start) & \
	wait

# ── Build ──────────────────────────────────────────────

.PHONY: build build-frontend

build-frontend:
	cd $(FRONTEND_DIR) && $(NPM) run build

build: build-frontend

# ── Production ─────────────────────────────────────────

.PHONY: serve

serve: build-frontend
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app:app --host 0.0.0.0 --port $(BACKEND_PORT)

# ── Cleanup ────────────────────────────────────────────

.PHONY: clean clean-jobs

clean-jobs:
	rm -rf $(BACKEND_DIR)/jobs

clean: clean-jobs
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Help ───────────────────────────────────────────────

.PHONY: help

help:
	@echo "Usage:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo "  make dev              Install deps + launch backend (:8001) and frontend (:4200)"
	@echo "  make dev-backend      Start FastAPI backend only on :8001"
	@echo "  make dev-frontend     Start Angular dev server only on :4200"
	@echo "  make build            Build Angular frontend for production"
	@echo "  make serve            Build frontend + start production server on :8001"
	@echo "  make clean-jobs       Remove processed job data"
	@echo "  make clean            Remove all generated files"

PYTHON ?= python3
VENV_PYTHON ?= backend/.venv/bin/python
PIP ?= backend/.venv/bin/pip

.PHONY: help venv install run run-lan smoke smoke-http compile test labs-quality recompact-intel

help:
	@echo "Available targets:"
	@echo "  make venv            - create backend/.venv"
	@echo "  make install         - install backend dependencies"
	@echo "  make run             - start FastAPI on localhost:8000"
	@echo "  make run-lan         - start FastAPI on 0.0.0.0:8000"
	@echo "  make smoke           - run smoke_labs.py"
	@echo "  make smoke-http      - run smoke_tests.py against a running backend"
	@echo "  make compile         - compile backend/app and scripts"
	@echo "  make test            - run pytest"
	@echo "  make labs-quality    - validate lab determinism and report drafts"
	@echo "  make recompact-intel - rebuild previously ingested knowledge briefs"

venv:
	$(PYTHON) -m venv backend/.venv

install:
	$(PIP) install -r backend/requirements.txt

run:
	cd backend && .venv/bin/uvicorn app.main:app --reload

run-lan:
	cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

smoke:
	$(VENV_PYTHON) scripts/smoke_labs.py

smoke-http:
	$(VENV_PYTHON) scripts/smoke_tests.py --base-url http://127.0.0.1:8000 --skip-chat

compile:
	$(PYTHON) -m compileall backend/app scripts

test:
	$(VENV_PYTHON) -m pytest tests

labs-quality:
	$(VENV_PYTHON) scripts/labs_quality_gate.py

recompact-intel:
	$(VENV_PYTHON) scripts/recompact_knowledge_briefs.py

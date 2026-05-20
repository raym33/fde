PYTHON ?= python3
VENV_PYTHON ?= backend/.venv/bin/python
PIP ?= backend/.venv/bin/pip

.PHONY: help venv install run run-lan smoke smoke-http compile recompact-intel

help:
	@echo "Targets disponibles:"
	@echo "  make venv            - crea backend/.venv"
	@echo "  make install         - instala dependencias del backend"
	@echo "  make run             - levanta FastAPI en localhost:8000"
	@echo "  make run-lan         - levanta FastAPI en 0.0.0.0:8000"
	@echo "  make smoke           - ejecuta smoke_labs.py"
	@echo "  make smoke-http      - ejecuta smoke_tests.py contra un backend en marcha"
	@echo "  make compile         - compila backend/app y scripts"
	@echo "  make recompact-intel - recompone briefs ya ingeridos"

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

recompact-intel:
	$(VENV_PYTHON) scripts/recompact_knowledge_briefs.py

.PHONY: setup install test lint clean ingest run

# Variáveis do Projeto
PYTHON = .venv/bin/python
VENV = .venv

setup:
	$(PYTHON) -m venv $(VENV)
	@echo "Rode 'source $(VENV)/bin/activate' e depois 'make install'"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	pre-commit install

format:
	.venv/bin/black src/ tests/
	.venv/bin/isort src/ tests/

lint:
	.venv/bin/flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503,E501,W291,F841,F541 --exclude=src/dashboard/




test:
	PYTHONPATH=. .venv/bin/pytest tests/ -v


ingest:
	PYTHONPATH=. $(PYTHON) src/ingestion/extract.py --year 2025 --gp "Bahrain" --session "Race"
	PYTHONPATH=. $(PYTHON) src/ingestion/process.py --year 2025 --gp "Bahrain" --session "Race"

ingest-all:
	PYTHONPATH=. $(PYTHON) src/ingestion/extract.py --year 2025 --gp "all" --session "Race"
	PYTHONPATH=. $(PYTHON) src/ingestion/process.py --year 2025 --gp "all" --session "Race"


clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .pre-commit-config.yaml.cache
	rm -rf data/bronze/*
	rm -rf data/silver/*
	rm -rf data/gold/*
	rm -rf data/quarantine/*

run:
	PYTHONPATH=. .venv/bin/uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8001


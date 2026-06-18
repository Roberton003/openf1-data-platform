.PHONY: setup install format lint test security validate clean ingest run ci-check ci-heal handoff

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
	.venv/bin/ruff format src/ tests/
lint:
	.venv/bin/ruff check src/ tests/

security:
	.venv/bin/detect-secrets scan src/ tests/ --exclude-files '.*__pycache__.*' 2>/dev/null || true
	.venv/bin/bandit -r src/ -f json -o bandit-report.json 2>/dev/null || true
	.venv/bin/safety check -r requirements.txt --output json 2>/dev/null || true

validate: lint test security
	@echo "=== All checks passed ==="

test:
	PYTHONPATH=. .venv/bin/pytest tests/ -v


ingest:
	PYTHONPATH=. $(PYTHON) src/ingestion/extract.py --year 2025 --gp "Bahrain" --session "Race"
	PYTHONPATH=. $(PYTHON) src/ingestion/process.py --year 2025 --gp "Bahrain" --session "Race"

ingest-all:
	PYTHONPATH=. $(PYTHON) src/ingestion/extract.py --year 2025 --gp "all" --session "Race"
	PYTHONPATH=. $(PYTHON) src/ingestion/process.py --year 2025 --gp "all" --session "Race"

compact-bronze:
	PYTHONPATH=. $(PYTHON) src/ingestion/compress_bronze.py


clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .pre-commit-config.yaml.cache
	rm -rf data/bronze/*
	rm -rf data/silver/*
	rm -rf data/gold/*
	rm -rf data/quarantine/*

run:
	PYTHONPATH=. .venv/bin/uvicorn src.web.main:app --reload --host 127.0.0.1 --port 8001

ci-check:
	PYTHONPATH=. $(PYTHON) -c "from src.web.ci_monitor import check_and_heal_ci; check_and_heal_ci()"

ci-heal:
	PYTHONPATH=. $(PYTHON) -c "from src.web.ci_monitor import execute_healing_action; execute_healing_action([], 0)"

handoff:
	@test -n "$(TITLE)" || (echo "Use TITLE='...' make handoff" && exit 1)
	PYTHONPATH=. $(PYTHON) scripts/codex/record_handoff.py "$(TITLE)" --project "OpenF1 Data Platform"

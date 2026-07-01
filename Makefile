.PHONY: setup install test lint clean ingest run

# Variáveis do Projeto
PYTHON = python3
VENV = .venv

setup:
	$(PYTHON) -m venv $(VENV)
	@echo "Rode 'source $(VENV)/bin/activate' e depois 'make install'"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dagster.txt

test-runtime:
	$(PYTHON) -m pytest \
		tests/test_web_routers_sla.py \
		tests/test_web_routers_ci_alerts.py \
		tests/test_orchestration_schedule.py \
		tests/test_orchestration_sensor.py \
		tests/test_assets_coverage_gaps.py \
		-v

lint:
	black src/ tests/
	isort src/ tests/
	flake8 src/ tests/

test:
	pytest tests/ -v

ingest:
	$(PYTHON) src/ingestion/extract.py

run:
	streamlit run src/dashboard/app.py

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf data/*.parquet
	rm -rf data/*.duckdb

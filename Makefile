.PHONY: setup install test lint clean ingest run

# Variáveis do Projeto
PYTHON = python3
VENV = .venv

setup:
	$(PYTHON) -m venv $(VENV)
	@echo "Rode 'source $(VENV)/bin/activate' e depois 'make install'"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

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

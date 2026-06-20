# F1-006 - Execucao dos Planos 004 e 005

## Status
Em execucao.

## Objetivo
Registrar as mudancas efetivamente aplicadas para os planos `PL-002-parametrizacao-on-demand` e `PL-003-ia-mlops-observabilidade`.

## Implementado
- `src/ingestion/config.py`: parser reutilizavel para `FOCUS_DRIVERS`.
- `src/ingestion/extract.py`: suporte a `--focus-drivers`.
- `src/ingestion/process.py`: escrita atomica, Gold particionada por `session_key`, metadados de execucao mais ricos e suporte a `--focus-drivers`.
- `src/ingestion/assets.py`: mesmos principios de escrita segura e Gold particionada na camada Dagster.
- `src/web/database.py`: mapeamento DuckDB atualizado para Gold particionada.
- `src/web/routers/analytics.py`: endpoint de pipeline execution expondo novas metricas.
- `tests/test_data_integrity.py` e `tests/test_api.py`: cobertura atualizada para o layout particionado e para os novos campos de observabilidade.
- `.github/workflows/cd.yml`: corrigido o nome do service do Compose.

## Verificacao
- `python3 -m py_compile` nos arquivos alterados: aprovado.
- `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_api.py tests/test_data_integrity.py tests/test_cli_pipeline.py -q`: aprovado.

## Pendencias
- Integracao formal de `Dagster Run Configuration` ainda nao foi fechada.
- Integracao de `mlflow`, `chromadb` e `sentence-transformers` segue como proxima etapa se o objetivo for completar integralmente o plano 005.
- Observabilidade ainda pode evoluir com freshness/latency detalhados por fonte e por particao.

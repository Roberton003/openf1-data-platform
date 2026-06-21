# Templates de Código

## Uso

Copie o template desejado e renomeie para o nome da sua feature:

```bash
cp src/_templates/skeleton_asset.py src/ingestion/my_new_asset.py
```

## Regras Não-Negociáveis

| Template | Regra | Exceção |
|----------|-------|---------|
| `skeleton_asset.py` | Funções < 50 linhas | Dagster @asset decorator ok |
| `skeleton_asset.py` | `logging.exception()` ou `context.log.error()` em todo except | Test files |
| `skeleton_route.py` | `async def` para rotas I/O | CPU-bound com threadpool |
| `skeleton_route.py` | `response_model` declarado | Rotas DELETE |
| `skeleton_model.py` | `Field(description=...)` em todo campo | — |
| `skeleton_test.py` | `@pytest.fixture` + `@pytest.mark.parametrize` | Testes de integração |

## Base Teórica

- **Python Fluente (Ramalho)**: Cap. 9 — Objetos pythônicos (__repr__, properties)
- **FastAPI (Lubanovic)**: Cap. 4 — Async patterns, Cap. 5 — Pydantic v2
- **FastAPI Cookbook (De Luca)**: Cap. 11 — Middleware & production hardening

# ADR-010: Sistema Definitivo de Qualidade de Código

**Status:** Accepted
**Data:** 2026-06-20
**Agentes:** `domain/adversarial-reviewer`, `domain/data-engineer`, `core/harness-architect`
**Skills:** `expert-python-modern`, `code-quality`, `multi-agent-orchestration`, `adversarial-review`
**Livros base:** Python Fluente (Ramalho), FastAPI (Lubanovic), FastAPI Cookbook (De Luca)

## Contexto

Após auditoria de 81 arquivos Python (12.200+ linhas, nota C+), identificou-se:

- ~500 linhas duplicadas entre `assets.py` e `process.py`
- `process_medallion_pipeline`: 830 linhas (god function)
- `except Exception: pass` em 3 pontos de produção
- Rotas sync em FastAPI async
- ~37 `print()` em produção
- Nenhum gate automatizado impedia esses padrões

## Decisão

Adotar **sistema de qualidade em 4 camadas** com bypass responsável:

1. **Prevenção**: Templates scaffold + Ruff rules (C90, PL, T10, TRY, RET) + Pre-commit
2. **Detecção**: `scripts/quality_gates.py` no CI
3. **Bypass**: `QUALITY_GATE_OVERRIDE=incident-NNN` com log e issue obrigatória em 48h
4. **Remediação**: `auto_heal_cov.py` fecha gaps de cobertura automaticamente

## Consequências

**Positivas:**
- Código novo nasce dentro dos padrões (templates)
- Duplicação, god functions e bare except são detectados antes do merge
- Bypass com accountability — não incentiva silêncio
- Cobertura por módulo com thresholds justificados (ingestion 70%, web 80%, dashboard 50%)

**Negativas:**
- 4h/mês de manutenção dos gates (quality_gates.py, templates, pre-commit)
- Falsos positivos iniciais exigem tuning (documentados no dry-run inicial)
- Pre-commit pode ser desabilitado sob pressão (mitigado pelo CI gate obrigatório)

## Principais Referências

| Princípio | Fonte | Gate |
|-----------|-------|------|
| Complexidade ciclomática ≤ 10 | Python Fluente Cap. 7 | Ruff C901 |
| `except Exception:` com `.exception()` | FastAPI Lubanovic Cap. 10 | TRY002 |
| `print()` proibido em `src/` | FastAPI Lubanovic Cap. 10 | T10 |
| Funções < 200 linhas | Python Fluente Cap. 12 | quality_gates.py |
| Rotas async por padrão | FastAPI Lubanovic Cap. 4 | quality_gates.py |
| DRY: sem blocos ≥ 15 linhas duplicados | Python Fluente Cap. 8 | quality_gates.py |
| Bypass com issue 48h | FastAPI Cookbook Cap. 11 | quality_gates.py + CI |

## Arquivos Alterados

| Arquivo | Mudança |
|---------|---------|
| `ruff.toml` | expandido com PL, T10, TRY, C90, RET, FBT, PTH |
| `.pre-commit-config.yaml` | +7 hooks (trailing-whitespace, debug-statements, name-tests-test, quality-gates) |
| `.github/workflows/ci.yml` | novo job `quality-gates` |
| `scripts/quality_gates.py` | novo — 6 checks estruturais |
| `src/_templates/skeleton_*.py` | 4 templates + README |
| `scripts/auto_heal_cov.py` | existente — cobertura automática |

## Próxima Revisão

2027-01-20 — revisar thresholds e false positive rate.

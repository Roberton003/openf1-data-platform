# Plano F1-020/021/022: Cobertura 60%, Terraform State Backend, Dagster Daemon

## 1. Contexto

- 192 testes, 42% coverage (target: 60%)
- `infra/main.tf`: Cloud Run dashboard sem state backend GCS
- `src/orchestration/definitions.py`: Dagster assets sem schedules/sensors
- `docker-compose.yml`: API + dashboard legacy, sem Dagster daemon

## 2. F1-020 — Coverage 60%

### Decisão
Testes targetados nos módulos com maior gap de cobertura, priorizando
código testável sem dependências externas (DuckDB in-memory, mocks).

### Módulos-alvo

| # | Módulo | Linhas não cobertas | Estratégia | Ganho estimado |
|---|--------|-------------------|------------|----------------|
| 1 | `web/model_loader.py` | 54 (0%) | Mock joblib + MLflow, testar singleton/cache | +54 |
| 2 | `web/routers/analytics.py` | 200 (30%) | Testar SQL validation + endpoints com mock_db | +120 |
| 3 | `web/ci_monitor.py` | 160 (13%) | Mock GitHub API, testar check_and_heal_ci | +80 |
| 4 | `ingestion/storage.py` | 15 (56%) | Testar atomic_write + atomic_append | +15 |
| 5 | `ingestion/vector_store.py` | 39 (22%) | Mock ChromaDB, testar index/query | +25 |
| 6 | `ingestion/compress_bronze.py` | 33 (0%) | Testar compressão de arquivos parquet | +33 |
| 7 | `web/routers/race_intelligence.py` | 91 (62%) | Mock endpoints de race intelligence | +50 |
| 8 | `ingestion/assets.py` | 486 (0%) | Testar `_calc_freshness_minutes` + 2-3 assets mockados | +100 |

**Total estimado:** +477 linhas → ~60%

### Arquivos de teste a criar

| Arquivo | Módulo | Testes |
|---------|--------|--------|
| `tests/test_model_loader.py` | `web/model_loader.py` | 6 testes: singleton, cache TTL, joblib fallback, mlflow fallback |
| `tests/test_sql_validation.py` | `web/routers/analytics.py` | 10 testes: blocklist, allowlist, LIMIT injection, comments |
| `tests/test_ci_monitor.py` | `web/ci_monitor.py` | 5 testes: check, heal, report, mock GitHub |
| `tests/test_storage.py` | `ingestion/storage.py` | 4 testes: atomic_write, atomic_append, partitioned |
| `tests/test_compress_bronze.py` | `ingestion/compress_bronze.py` | 3 testes: compress, skip archive, no files |
| `tests/test_race_intelligence_endpoints.py` | `web/routers/race_intelligence.py` | 5 testes: session_summary, driver_options, strategy |
| `tests/test_assets_freshness.py` | `ingestion/assets.py` | 4 testes: _calc_freshness, None, empty, nested |

### Critérios de aceite
1. `pytest --cov=src --cov-fail-under=60` passa
2. Todos os testes existentes continuam passando
3. Nenhum teste novo depende de serviços externos

### Rollback
`git revert` do commit F1-020

## 3. F1-021 — Terraform State Backend (GCS)

### Decisão
Adicionar GCS bucket para state backend do Terraform, com versionamento
e locking via Cloud Storage.

### Alterações

| Arquivo | Mudança |
|---------|---------|
| `infra/main.tf` | Adicionar `terraform` block com GCS backend |
| `infra/backend.tf` | Novo — configuração do backend GCS |
| `infra/variables.tf` | Adicionar `state_bucket` variable |
| `infra/outputs.tf` | Novo — outputs do backend |

### Conteúdo

**infra/backend.tf:**
```hcl
terraform {
  backend "gcs" {
    bucket = "openf1-terraform-state"
    prefix = "terraform/state"
  }
}
```

**infra/main.tf (modificado):**
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "openf1-terraform-state"
    prefix = "terraform/state"
  }
}
```

**infra/variables.tf (modificado):**
```hcl
variable "state_bucket" {
  description = "GCS bucket for Terraform state"
  type        = string
  default     = "openf1-terraform-state"
}
```

### Pré-requisitos
- Bucket GCS `openf1-terraform-state` criado manualmente (ou via `gsutil mb`)
- Credenciais GCP configuradas (`GOOGLE_APPLICATION_CREDENTIALS`)

### Critérios de aceite
1. `terraform init` configura o backend GCS
2. `terraform plan` roda sem erros
3. State versionamento funciona

### Rollback
Remover `backend "gcs"` block e voltar ao state local

## 4. F1-022 — Orquestração Ativa (Dagster Daemon)

### Decisão
Configurar Dagster com schedules para ingestão automática e sensors
para monitoramento de freshness.

### Alterações

| Arquivo | Mudança |
|---------|---------|
| `src/orchestration/definitions.py` | Adicionar schedules e sensors |
| `src/orchestration/schedules.py` | Novo — schedule de ingestão diária |
| `src/orchestration/sensors.py` | Novo — sensor de freshness |
| `docker-compose.yml` | Adicionar serviços dagster-webserver e dagster-daemon |
| `dagster.yaml` | Novo — configuração do Dagster daemon |

### Conteúdo

**src/orchestration/schedules.py:**
```python
from dagster import schedule, RunRequest

@schedule(cron_schedule="0 6 * * *", job_name="daily_ingestion")
def daily_ingestion_schedule(context):
    return RunRequest(run_config={
        "ops": {"extract": {"config": {"year": 2025, "gp": "all"}}}
    })
```

**src/orchestration/sensors.py:**
```python
from dagster import sensor, SensorEvaluationContext

@sensor(job_name="freshness_check")
def freshness_sensor(context):
    # Verifica se Bronze tem dados frescos
    # Se não, dispara reprocessamento
    ...
```

**dagster.yaml:**
```yaml
run_coordinator:
  module: dagster.core.run_coordinator
  class: DefaultRunCoordinator

run_launcher:
  module: dagster.core.launcher
  class: DefaultRunLauncher

scheduler:
  module: dagster.core.scheduler
  class: DagsterDaemonScheduler

daemons:
  - module: dagster.daemon
    class: DagsterDaemon
```

**docker-compose.yml (adição):**
```yaml
dagster-webserver:
  image: dagster/dagster-webserver:latest
  ports:
    - "3000:3000"
  volumes:
    - ./dagster.yaml:/dagster.yaml
  command: ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "/dagster.yaml"]

dagster-daemon:
  image: dagster/dagster-daemon:latest
  volumes:
    - ./dagster.yaml:/dagster.yaml
  command: ["dagster-daemon", "run", "-w", "/dagster.yaml"]
```

### Critérios de aceite
1. `dagster dev` roda com schedules e sensors
2. `dagster-webserver` acessível em `localhost:3000`
3. Schedule diário dispara RunRequest
4. Sensor de freshness detecta Bronze stale

### Rollback
Remover services do docker-compose, reverter definitions.py

## 5. Ordem de Execução

1. **F1-020** (coverage) — sem dependências externas, executa primeiro
2. **F1-021** (Terraform) — requer bucket GCS, pode ser bloqueado
3. **F1-022** (Dagster) — requer F1-020 para testes de schedules/sensors

## 6. Processing Context

```yaml
effort: T3
orchestration:
  topology: SEQUENTIAL
  agents: [test-engineer, devops-release-engineer, data-engineer]
  skills: [write-implementation-plan, data-engineering, verification-workflow-designer]
  stages:
    - phase: 1
      capability: test-engineer
      agents: [test-engineer]
      scope: [tests/test_model_loader.py, tests/test_sql_validation.py, ...]
    - phase: 2
      capability: devops-release-engineer
      agents: [devops-release-engineer]
      scope: [infra/backend.tf, infra/main.tf, infra/variables.tf]
    - phase: 3
      capability: data-engineer
      agents: [data-engineer]
      scope: [src/orchestration/schedules.py, src/orchestration/sensors.py, dagster.yaml]
```

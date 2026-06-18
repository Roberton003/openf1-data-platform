# ADR-003: FastAPI Assíncrono com Delegamento de Threads OLAP

## Status
**Accepted**

## Data
2026-06-09

## Contexto
O DuckDB é uma biblioteca C++ embarcada que executa operações analíticas (OLAP) complexas de forma puramente síncrona em Python. 
Em um servidor web assíncrono como o **FastAPI**, que opera sob um único loop de eventos de rede (event loop do asyncio), executar uma query síncrona pesada do DuckDB (como um JOIN analítico de telemetria com milhões de linhas) causaria o seguinte problema:
* **Bloqueio do Event Loop:** Durante a execução da query SQL no DuckDB, a thread principal do FastAPI é travada pelo processo de computação de dados. Isso impede o servidor de responder a qualquer outra requisição HTTP ou conexão concorrente pendente, degradando a vazão do servidor e provocando timeouts para outros usuários.

## Decisão
Adotamos o **FastAPI** como servidor assíncrono de API, mas delegamos toda a computação síncrona do DuckDB para o pool de threads em segundo plano do Python através do método `asyncio.to_thread` (ou `loop.run_in_executor`).

Exemplo técnico:
```python
import asyncio
import duckdb

def execute_olap(sql: str, params: tuple):
    with duckdb.connect("openf1.duckdb", read_only=True) as conn:
        return conn.execute(sql, params).fetch_df()

@app.get("/api/telemetry")
async def get_telemetry(session_key: int, driver_number: int):
    # Executa em thread separada, liberando a thread principal do FastAPI
    df = await asyncio.to_thread(execute_olap, query_sql, (session_key, driver_number))
    return df.to_dict(orient="records")
```

## Consequências
### Ganhos (Prós):
* **Alta Concorrência no Servidor Web:** O FastAPI consegue receber centenas de conexões concorrentes simultaneamente na porta web, enquanto o processamento analítico das queries roda paralelamente nas threads de CPU destinadas ao DuckDB.
* **Experiência Web Fluida:** O dashboard no frontend pode disparar chamadas AJAX simultâneas sem sofrer com gargalos de enfileiramento de requisições no servidor FastAPI.
* **Segurança de Thread:** Como o DuckDB é aberto em modo `read_only=True` dentro do escopo de execução das threads, múltiplas conexões de leitura simultâneas podem operar de forma thread-safe sem corrupção.

### Perdas/Restrições (Contras):
* **Overhead de Troca de Contexto:** O uso de threads introduz um leve overhead de troca de contexto de CPU em Python (gerenciado pelo Global Interpreter Lock - GIL), porém insignificante perto do tempo de travamento que um bloqueio total causaria.
* **Gerenciamento de Pool de Conexões:** Exige a abertura e o fechamento correto de conexões leves do DuckDB ou a utilização de uma conexão compartilhada com controle estrito de locks.

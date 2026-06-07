# 🛠️ Resolução de Anomalias de Ingestão & Decisões de Engenharia

Este documento registra as anomalias técnicas encontradas na API da **OpenF1** durante a fase de desenvolvimento, bem como as respectivas resoluções de arquitetura de dados e engenharia defensiva adotadas na plataforma.

---

## 🛑 1. Resiliência a Respostas 404 em Recursos Ausentes

### O Problema:
Durante a ingestão de sessões analíticas da F1 (como a corrida de chave `9662`), o endpoint `/pit_stops` retornou um status **HTTP 404 Client Error: Not Found**. 
Muitas APIs modernas retornam status 404 (recurso não encontrado) quando não existem eventos gravados para aquela consulta específica, em vez de retornar um status 200 OK com uma lista vazia `[]`. Isso interrompe pipelines de extração padrão que esperam respostas estruturadas de sucesso.

### A Resolução de Engenharia:
Na função de ingestão resiliente `fetch_endpoint` em `extract.py`, implementamos uma captura defensiva de exceções da biblioteca `requests`:
```python
try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    # Captura 404 e trata como retorno vazio, evitando a quebra do pipeline
    if e.response.status_code == 404:
        print(f"Endpoint {endpoint} retornou 404. Tratando como vazio.")
        return None
    raise e
```
Com essa tratativa, os steths de re-tentativa exponencial da biblioteca `tenacity` só são acionados para erros de rede reais (5xx, timeouts), enquanto os retornos sem dados da API (404) passam de forma segura e o pipeline prossegue.

---

## 🛞 2. Incompatibilidade de Tipos Mistos no PyArrow (Escrita Parquet)

### O Problema:
O endpoint `/intervals` fornece os tempos de distância dos pilotos na pista. Na coluna `gap_to_leader` e `interval`, os dados contêm strings quando ocorrem voltas de atraso (ex: `"+1 LAP"`, `"+2 LAPS"`) e floats decimais quando os carros estão na mesma volta (ex: `"1.234"`).
Ao tentar salvar o DataFrame do Pandas em formato **Apache Parquet** (`to_parquet`), o motor de conversão **PyArrow** tenta inferir o tipo da coluna a partir dos primeiros registros. Ele infere que a coluna é float, mas falha catastroficamente ao encontrar uma string mais à frente:
> `pyarrow.lib.ArrowInvalid: ("Could not convert '+1 LAP' with type str: tried to convert to double")`

### A Resolução de Engenharia:
Antes de invocar o método `.to_parquet`, aplicamos um cast seletivo forçando o tipo de dados dessas colunas mistas para strings nativas (`str`) no Pandas, o que normaliza o esquema para a escrita e leitura no Parquet:
```python
if ep == "intervals":
    for col in ["gap_to_leader", "interval"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
```
Isso garante compatibilidade rigorosa de esquemas e impede falhas de tipos durante a ingestão do data lake.

---

## 📊 3. JOIN Analítico In-Memory via DuckDB no Streamlit

### Decisão de Arquitetura:
Telemetria de F1 de alta frequência gera milhões de registros. Em vez de subir e pagar por um banco de dados transacional pesado em produção para servir leituras analíticas simples no Dashboard, adotamos o **DuckDB** como motor OLAP local e em memória.

No front-end do Streamlit, realizamos consultas analíticas complexas com JOIN diretamente em cima dos arquivos Parquet locais gerados de forma desacoplada:

```sql
SELECT DISTINCT
    d.full_name as Piloto,
    d.team_name as Escuderia,
    d.name_acronym as Sigla,
    i.gap_to_leader as GapLeader,
    i.interval as Intervalo
FROM read_parquet('intervals.parquet') i
JOIN read_parquet('drivers.parquet') d 
  ON CAST(i.driver_number AS INTEGER) = CAST(d.driver_number AS INTEGER)
WHERE i.gap_to_leader IS NOT NULL 
LIMIT 15
```

### Vantagens:
1. **Velocidade**: Consultas em arquivos Parquet no DuckDB duram milissegundos.
2. **Custo-Zero**: Roda inteiramente local no navegador/servidor sem infraestrutura adicional.
3. **Escalabilidade**: Estrutura robusta simulando uma camada Silver de Data Lakehouse analítico corporativo.

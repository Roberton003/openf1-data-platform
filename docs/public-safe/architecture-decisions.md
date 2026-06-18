# Architecture Decisions Summary

This is a public-safe summary of the main engineering decisions in the OpenF1
Data Platform.

## Decision Themes

| Area | Public Summary | Reviewer Signal |
|---|---|---|
| Local OLAP | DuckDB is used for analytical serving over Parquet data. | Shows practical OLAP design without unnecessary cloud cost. |
| Medallion Data Flow | Raw, refined and analytical layers separate ingestion from serving. | Shows data lifecycle thinking and recoverability. |
| Concurrent Ingestion | Data extraction is segmented to reduce timeout risk and improve throughput. | Shows awareness of external API limits and reliability. |
| Data Contracts | Schema validation protects analytical layers from silent corruption. | Shows governance and quality controls. |
| API Serving | FastAPI exposes analytical endpoints backed by DuckDB views. | Shows product-facing data delivery. |
| Dashboard Serving | The Race Intelligence UI consumes FastAPI contracts instead of reading lakehouse files directly. | Shows separation between storage, serving and user experience. |
| On-Demand Scope | Ingestion can evolve from static batches to parameterized runs. | Shows self-service and operational flexibility. |
| AI Analytics | AI is treated as an assistive layer over governed analytical data. | Shows controlled use of AI instead of opaque automation. |
| Agentic Harness | Agentic capabilities are adopted selectively, with the existing project governance remaining the source of truth. | Shows constrained reuse instead of a parallel operating model. |

## Public Boundary

This summary keeps the professional rationale visible while omitting private
planning notes, detailed execution strategy and project operating methods that
are not needed for portfolio evaluation.

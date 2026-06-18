# Public-Safe Documentation

This folder contains the portfolio-safe documentation layer for the OpenF1 Data
Platform. It is intended for recruiters, tech leads and technical reviewers who
need to understand the project without exposing private operating strategy,
detailed planning heuristics or product reasoning.

## Documentation Layers

| Layer | Visibility | Purpose |
|---|---|---|
| `README.md` at repository root | Public | Project overview, setup and primary capabilities. |
| `docs/public-safe/` | Public-safe | Curated architecture, decisions and plan summaries for portfolio review. |
| `docs/public-safe/agentic-capabilities-summary.md` | Public-safe | Public-facing summary of the harness capability strategy. |
| `docs/adr/` | Internal detailed | Full architecture decision records, trade-offs and internal rationale. |
| `docs/plans/` | Internal detailed | Approved plans, execution notes, audits and implementation strategy. |
| Local operating notes | Internal local | Project workflow, review rules, risks and local context. |

## Publishing Rule

Public-safe documents should explain what was built, why the engineering choices
are reasonable, how the system is validated and what trade-offs exist. They
should not expose private review methods, internal planning notes, product
strategy or unresolved implementation shortcuts.

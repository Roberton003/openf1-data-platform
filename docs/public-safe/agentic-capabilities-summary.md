# Agentic Capabilities Summary

This is a public-safe summary of the agentic harness decisions used in the OpenF1
Data Platform.

## What Was Kept

| Category | Summary | Why it matters |
|---|---|---|
| Native harness base | Project bootstrap, formal planning, engineering decisions, and multi-agent orchestration remain the core operating model. | Keeps the system simple, reviewable and portable across projects. |
| Domain extensions | Data-oriented and long-running work patterns are kept as opt-in capabilities for cases that actually need them. | Avoids imposing data-heavy governance on every repository. |
| Explicit rejections | Full-package installation, global default rollout, duplicate governance layers and generic prompt libraries were rejected. | Prevents context bloat, maintenance drift and parallel rule systems. |

## Project-Level Gains

- less duplicated governance;
- clearer routing between planning, verification and execution;
- stronger traceability for decisions that matter;
- a smaller and more reusable operating surface for future work.

## Cross-Project Gains

- a reusable vocabulary for deciding when to absorb, extend or discard a capability;
- a safer pattern for bringing agentic behavior into other repositories;
- less risk of copying a heavy governance stack where it does not pay for itself.

## Boundary

This summary avoids private operating heuristics and implementation shortcuts. The
full rationale stays in the internal plan and session handoff.

#!/usr/bin/env python3
"""
Verify that governance files enforce mandatory agent/skill support.

Run: python scripts/verify_agent_support.py
Exit 0 = all checks pass, Exit 1 = failure.

Checks 1-22: Verify governance FILES contain required content
Checks 23-28: Verify PLANS and HANDOFFS have agents/skills documented
"""

import sys
from pathlib import Path

ERRORS: list[str] = []
WARNS: list[str] = []


def check(file: Path, label: str, expected: str) -> None:
    if not file.exists():
        ERRORS.append(f"[MISSING] {file} — {label}")
        return
    content = file.read_text()
    if expected not in content:
        ERRORS.append(f"[FAIL] {file} — {label}: '{expected}' not found")


def check_file_contains(file: Path, label: str, expected: str) -> None:
    """Check if file exists and contains expected string."""
    if not file.exists():
        return  # skip non-existent files
    content = file.read_text()
    if expected not in content:
        ERRORS.append(f"[FAIL] {file} — {label}: '{expected}' not found")


CORE = Path.home() / ".config" / "opencode" / "opencode-core.md"
SKILLS = Path.home() / ".config" / "opencode" / "skills"
PROJECT = Path("/media/Arquivos/Engenharia TI 2026/openf1-data-platform")

# === CAMADA 1: Governance Files ===

# 1. opencode-core.md §3 — Task Router table has Agents Mínimos column
check(CORE, "§3 Task Router Agents Mínimos", "Agents Mínimos")

# 2. opencode-core.md §3 — GOVERNANCE GATE rule
check(CORE, "§3 GOVERNANCE GATE", "GOVERNANCE GATE")

# 3. opencode-core.md §3 — mandatory support rule
check(CORE, "§3 mandatory rule", "Não executar")

# 4. opencode-core.md §3 — fallback rule
check(CORE, "§3 fallback rule", "Rejected/Blocked")

# 5. opencode-core.md §3 — PARAR instruction
check(CORE, "§3 PARAR instruction", "PARAR. Não executar")

# 6. opencode-core.md §4 — agents field in YAML
check(CORE, "§4 agents field", "agents: [lista de agentes acionados]")

# 7. opencode-core.md §4 — skills field in YAML
check(CORE, "§4 skills field", "skills: [lista de skills acionadas]")

# 8. opencode-core.md §4 — validation rule
check(CORE, "§4 validation rule", "bloquear execução até documentação completa")

# 9. task-router — agents in output YAML
check(SKILLS / "task-router" / "SKILL.md", "output agents field", "agents: [obrigatório para T1+]")

# 15. task-router — skills in output YAML
check(SKILLS / "task-router" / "SKILL.md", "output skills field", "skills: [obrigatório para T1+]")

# 16. task-router — mandatory support rule
check(SKILLS / "task-router" / "SKILL.md", "mandatory rule", "Sem suporte, não iniciar")

# 17. effort-budget-governor — agents in output
check(SKILLS / "effort-budget-governor" / "SKILL.md", "output agents field", "Agents: [obrigatório para T1+]")

# 18. effort-budget-governor — skills in output
check(SKILLS / "effort-budget-governor" / "SKILL.md", "output skills field", "Skills: [obrigatório para T1+]")

# 19. effort-budget-governor — hard rule mandatory support
check(
    SKILLS / "effort-budget-governor" / "SKILL.md",
    "hard rule mandatory",
    "Toda atividade T1+ requer agents e skills documentados",
)

# 20. effort-budget-governor — hard rule block
check(SKILLS / "effort-budget-governor" / "SKILL.md", "hard rule block", "Execução sem suporte documentado é bloqueada")

# 21. executing-plans — Step 0 GOVERNANCE GATE
check(SKILLS / "executing-plans" / "SKILL.md", "Step 0 GOVERNANCE GATE", "GOVERNANCE GATE")

# 22. executing-plans — Step 0 lists agents invocation
check(SKILLS / "executing-plans" / "SKILL.md", "Step 0 invoke agent", "Try invoking at least 1 domain agent")

# 23. executing-plans — Step 0 CANNOT be skipped
check(SKILLS / "executing-plans" / "SKILL.md", "Step 0 CANNOT", "CANNOT be skipped")

# === CAMADA 2: Plans and Handoffs ===

plans_dir = PROJECT / "docs" / "plans"
handoffs_dir = PROJECT / "docs" / "session-handoffs"

# 26. Recent plans should mention agents or Supporting Agents
if plans_dir.exists():
    recent_plans = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    for plan in recent_plans:
        content = plan.read_text()
        has_agents = "agents" in content.lower() or "supporting agents" in content.lower() or "agent" in content.lower()
        if not has_agents:
            WARNS.append(f"[WARN] {plan.name} — no mention of agents in recent plan")

# 27. Recent handoffs should mention agents (only handoffs after ADR-013, 2026-06-18)
if handoffs_dir.exists():
    recent_handoffs = sorted(handoffs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    adr013_date = 1781827200  # 2026-06-18 00:00:00 UTC
    for ho in recent_handoffs[:5]:
        if ho.name == "README.md":
            continue
        if ho.stat().st_mtime < adr013_date:
            continue  # skip handoffs before ADR-013
        content = ho.read_text()
        has_agents = "agents" in content.lower() or "supporting agents" in content.lower()
        if not has_agents:
            ERRORS.append(f"[FAIL] {ho.name} — no mention of agents in recent handoff")

# === CAMADA 3: Pre-commit hook ===
pre_commit = PROJECT / ".pre-commit-config.yaml"
if pre_commit.exists():
    content = pre_commit.read_text()
    if "verify-agent-support" not in content:
        ERRORS.append("[FAIL] .pre-commit-config.yaml — verify-agent-support hook not found")

# --- Report ---
print("=" * 60)
print("Agent/Skill Support Governance Verification")
print("=" * 60)
print("Checks run: 20")
print(f"Passed:     {20 - len(ERRORS)}")
print(f"Failed:     {len(ERRORS)}")
print(f"Warnings:   {len(WARNS)}")
print()

if WARNS:
    for w in WARNS:
        print(f"  ⚠ {w}")
    print()

if ERRORS:
    for e in ERRORS:
        print(f"  ✗ {e}")
    print()
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: ALL CHECKS PASSED")
    sys.exit(0)

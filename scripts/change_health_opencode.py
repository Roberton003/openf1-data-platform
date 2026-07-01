#!/usr/bin/env python3
"""Change health aggregator for OpenCode harness.

Classifies change risk and aggregates quality signals.

Usage:
    python scripts/change_health_opencode.py              # default: markdown
    python scripts/change_health_opencode.py --markdown   # markdown report
    python scripts/change_health_opencode.py --json       # json report
    python scripts/change_health_opencode.py --check      # exit code gate
    python scripts/change_health_opencode.py --baseline   # gen baseline

Exit codes (--check):
    0  — all good or manual review only (no gate violation)
    1  — gate violation (ruff fail, quality_gates fail, skill warning)
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass
class ChangeHealthReport:
    risk: str = "LOW"
    manual_review_required: bool = False
    changed_files: int = 0
    python_files: int = 0
    markdown_files: int = 0
    ruff: str = "NOT_RUN"
    quality_gates: str = "NOT_RUN"
    skill_validation: str = "NOT_RUN"
    complexity_delta: str = "no_new_violations"
    suggested_focus: str = ""


# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT = Path(
    os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent)
)
SCRIPTS = PROJECT / "scripts"
QUALITY_GATES = SCRIPTS / "quality_gates.py"
HARNESS_HOME = Path.home() / ".config" / "opencode"
SKILLS_DIR = HARNESS_HOME / "skills"

BASELINE_FILE = PROJECT / ".quality-baseline-opencode.json"

HARNESS_PATHS = {
    "opencode.jsonc": "CRITICAL",
    ".last-handoff.json": "HIGH",
    "handoff-writer": "HIGH",
    "session-start-hook": "HIGH",
    "agentic-quality-policy": "HIGH",
}


# ── Git helpers ──────────────────────────────────────────────────────────────

def _git(*args: str, cwd: Optional[Path] = None) -> str:
    try:
        r = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, check=False,
            cwd=cwd or PROJECT,
        )
        return r.stdout.strip()
    except FileNotFoundError:
        return ""


def _detect_base_branch() -> str:
    for candidate in ("origin/main", "origin/master", "main", "master"):
        r = _git("rev-parse", "--abbrev-ref", candidate)
        if r and r != "HEAD":
            return candidate.replace("origin/", "")
    return "main"


def _uncommitted_paths() -> list[str]:
    """Only uncommitted changes (working tree vs HEAD)."""
    out = _git("diff", "--name-only", "HEAD")
    if not out:
        out = _git("status", "--porcelain")
        return [p[3:] for p in out.split("\n") if p.strip() and p[0] != "!"]
    return [p for p in out.split("\n") if p.strip()]


def _branch_diff_paths() -> list[str]:
    """All changes in branch vs base (accumulated across sessions)."""
    base = _detect_base_branch()
    out = _git("diff", "--name-only", f"origin/{base}...")
    if not out:
        out = _git("diff", "--name-only", "HEAD")
    return [p for p in out.split("\n") if p.strip()]


def _uncommitted_numstat() -> tuple[int, int]:
    """Volume of only uncommitted changes (avoids multi-session accumulation)."""
    out = _git("diff", "--numstat", "HEAD")
    if not out:
        return 0, 0
    added = removed = 0
    for line in out.split("\n"):
        if line.strip():
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    added += int(parts[0]) if parts[0] != "-" else 0
                    removed += int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    pass
    return added, removed


# ── Classification ──────────────────────────────────────────────────────────

_LOW = "LOW"
_MEDIUM = "MEDIUM"
_HIGH = "HIGH"
_CRITICAL = "CRITICAL"


def _classify(
    changed: list[str], added: int, removed: int,
    uncommitted_count: int = 0,
) -> str:
    risk = _LOW

    # 5º sinal: segurança (sobrescreve qualquer classificação)
    for p in changed:
        lower = p.lower()
        if "secrets.baseline" in lower or "quality-baseline" in lower:
            continue  # arquivos de baseline não são exposição
        if any(x in lower for x in ("credential", "secret", "token", "password")):
            return _CRITICAL

    # 1º sinal: path patterns
    for p in changed:
        lower = p.lower()
        if any(x in lower for x in (
            "skill", "agent", "opencode.jsonc",
            "templates", "handoff", "agentic-quality-policy",
        )):
            risk = _MEDIUM
            break

    # 4º sinal: schema/protocolo
    for p in changed:
        lower = p.lower()
        if any(x in lower for x in (
            ".last-handoff.json", "handoff-writer", "session-start-hook",
            "opencode.jsonc",
        )):
            risk = _HIGH
            break

    # 2º sinal: diff volume (uncommitted only — avoids multi-session accumulation)
    if added > 50 or removed > 50:
        risk = _HIGH

    # 3º sinal: múltiplos módulos (uncommitted only)
    if uncommitted_count > 3:
        risk = _HIGH

    # CRITICAL re-check for config change
    for p in changed:
        name = Path(p).name
        if name == "opencode.jsonc":
            risk = _CRITICAL

    return risk


def _manual_review_required(risk: str, changed: list[str]) -> bool:
    if risk in (_CRITICAL, _HIGH):
        return True
    if risk == _MEDIUM:
        for p in changed:
            lower = p.lower()
            if any(x in lower for x in (
                ".last-handoff.json", "handoff-writer", "session-start-hook",
            )):
                return True
    return False


# ── Skill validation ────────────────────────────────────────────────────────

def _find_skills(changed: list[str]) -> list[Path]:
    skills: list[Path] = []
    for p in changed:
        path = Path(p)
        if path.name == "SKILL.md":
            if path.exists():
                skills.append(path)
            else:
                alt = SKILLS_DIR / p
                if alt.exists():
                    skills.append(alt)
        elif path.suffix == ".md" and "skill" in str(path).lower():
            if path.exists():
                skills.append(path)
    return skills


def _validate_skills(skills: list[Path]) -> tuple[bool, list[str]]:
    if not skills:
        return True, []
    all_ok = True
    warnings: list[str] = []
    for skill in skills:
        if not skill.exists():
            warnings.append(f"[SKILL MISSING] {skill}")
            all_ok = False
            continue
        content = skill.read_text()
        skill_warnings: list[str] = []
        if "# Skill:" not in content and "# Skill " not in content:
            skill_warnings.append(f"[SKILL FORMAT] {skill.name}: missing '# Skill:' title")
        if "## Procedimento" not in content and "## Workflow" not in content:
            skill_warnings.append(f"[SKILL FORMAT] {skill.name}: missing '## Procedimento' or '## Workflow'")
        if "Regras" not in content:
            skill_warnings.append(f"[SKILL FORMAT] {skill.name}: missing 'Regras' section")
        if "Anti-Pattern" not in content:
            skill_warnings.append(f"[SKILL FORMAT] {skill.name}: missing 'Anti-Patterns' section")
        if not content.strip():
            skill_warnings.append(f"[SKILL FORMAT] {skill.name}: empty file")
        if skill_warnings:
            all_ok = False
            warnings.extend(skill_warnings)
    return all_ok, warnings


# ── Quality gates integration ────────────────────────────────────────────────

def _run_ruff(changed: list[str]) -> str:
    python_files = [p for p in changed if p.endswith(".py")]
    if not python_files:
        return "NOT_RUN"
    try:
        r = subprocess.run(
            ["ruff", "check", *python_files],
            capture_output=True, text=True, check=False,
            cwd=PROJECT,
        )
        return "PASS" if r.returncode == 0 else "FAIL"
    except FileNotFoundError:
        return "NOT_RUN"


def _run_quality_gates(changed: list[str]) -> str:
    python_files = [p for p in changed if p.endswith(".py")]
    src_files = [p for p in python_files if p.startswith("src/")]
    if not src_files:
        return "NOT_APPLICABLE"
    if not QUALITY_GATES.exists():
        return "NOT_RUN"
    try:
        r = subprocess.run(
            [sys.executable, str(QUALITY_GATES), "--dry-run"],
            capture_output=True, text=True, check=False,
            cwd=PROJECT,
        )
        return "PASS" if "FAIL" not in r.stdout else "FAIL"
    except FileNotFoundError:
        return "NOT_RUN"


def _suggested_focus(risk: str, changed: list[str]) -> str:
    if risk == _CRITICAL:
        return "REVISÃO HUMANA OBRIGATÓRIA: credencial/segurança detectada"
    if risk == _HIGH:
        return "verificar schema, protocolo e plano de rollback"
    if risk == _MEDIUM:
        if any("skill" in p.lower() for p in changed):
            return "verificar estrutura da nova skill (seções obrigatórias)"
        if any("template" in p.lower() for p in changed):
            return "verificar consistência com schema de handoff"
        return "verificar consistência da mudança"
    return "mudança de baixo risco — revisão visual suficiente"


# ── Baseline ─────────────────────────────────────────────────────────────────

def _load_baseline() -> dict:
    if BASELINE_FILE.exists():
        try:
            return json.loads(BASELINE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_baseline(report: ChangeHealthReport) -> None:
    BASELINE_FILE.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def _build_report() -> ChangeHealthReport:
    branch_changed = _branch_diff_paths()
    uncommitted = _uncommitted_paths()
    added, removed = _uncommitted_numstat()

    risk = _classify(branch_changed, added, removed, uncommitted_count=len(uncommitted))
    changed_files = len(branch_changed)
    python_files = sum(1 for p in branch_changed if p.endswith(".py") and "conftest" not in p)
    markdown_files = sum(1 for p in branch_changed if p.endswith(".md"))

    skills = _find_skills(branch_changed)
    skill_ok, skill_warnings = _validate_skills(skills)
    skill_status = "OK" if skill_ok else "WARNINGS"

    ruff_status = _run_ruff(uncommitted)
    qg_status = _run_quality_gates(branch_changed)

    return ChangeHealthReport(
        risk=risk,
        manual_review_required=_manual_review_required(risk, branch_changed),
        changed_files=changed_files,
        python_files=python_files,
        markdown_files=markdown_files,
        ruff=ruff_status,
        quality_gates=qg_status,
        skill_validation=skill_status,
        complexity_delta="new_warnings" if skill_warnings else "no_new_violations",
        suggested_focus=_suggested_focus(risk, branch_changed),
    )


def _format_markdown(r: ChangeHealthReport) -> str:
    lines = [
        "# Change Health — OpenCode Harness",
        "",
        f"- Risk: {r.risk}",
        f"- Changed files: {r.changed_files}",
        f"- Python files: {r.python_files} | Markdown files: {r.markdown_files}",
        f"- Ruff: {r.ruff}",
        f"- Quality gates: {r.quality_gates}",
        f"- Skill validation: {r.skill_validation}",
        f"- Complexity delta: {r.complexity_delta}",
        f"- Manual review required: {'yes' if r.manual_review_required else 'no'}",
        f"- Suggested focus: {r.suggested_focus}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="OpenCode harness change health")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.add_argument("--markdown", action="store_true", help="output as Markdown")
    p.add_argument("--check", action="store_true", help="gate mode (exit code)")
    p.add_argument("--baseline", action="store_true", help="generate/update baseline file")
    args = p.parse_args()

    report = _build_report()

    if args.baseline:
        _save_baseline(report)
        print(f"Baseline saved to {BASELINE_FILE}")
        return

    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(_format_markdown(report))

    if args.check:
        if report.quality_gates == "FAIL":
            sys.exit(1)
        if report.ruff == "FAIL":
            sys.exit(1)
        if report.skill_validation == "WARNINGS":
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Quality gates — enforces structural code quality rules.

Usage:
    python scripts/quality_gates.py              # full check, exit code = violations
    python scripts/quality_gates.py --fail       # exit 1 if any violation
    python scripts/quality_gates.py --json       # machine-readable output
    python scripts/quality_gates.py --dry-run    # print violations, no exit
    python scripts/quality_gates.py --exclude X  # comma-sep paths to exclude

Checks:
    god_function      — function > 200 lines or cyclomatic complexity > 15
    duplicate_code    — blocks ≥15 identical non-comment lines in different files
    bare_except       — except Exception: without .exception() or .error() logging
    sync_in_async     — sync def in FastAPI router files
    print_in_prod     — print() calls outside tests/ and scripts/
    module_side_effect — top-level code (outside def/class) in src/
"""

import argparse
import ast
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SRC_DIR = Path("src")
EXCLUDE_DEFAULT = {"src/dashboard/", "src/dashboard"}
BASELINE_FILE = Path(".quality-baseline.json")
VIOLATION_EXIT = 1


def parse_args():
    p = argparse.ArgumentParser(description="Code quality gates")
    p.add_argument("--fail", action="store_true", help="exit 1 if violations found")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.add_argument("--dry-run", action="store_true", help="print violations, exit 0")
    p.add_argument("--exclude", help="extra paths to exclude (comma-sep)")
    p.add_argument(
        "--update-baseline",
        action="store_true",
        help="run full scan and save all violations as acceptable baseline",
    )
    p.add_argument(
        "--no-baseline",
        action="store_true",
        help="ignore baseline file, run full scan",
    )
    return p.parse_args()


def get_baseline_id(v: dict) -> str:
    return f"{v['check']}:{v['file']}:{v['line']}"


def load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    try:
        data = json.loads(BASELINE_FILE.read_text())
        return {get_baseline_id(v) for v in data.get("violations", [])}
    except (json.JSONDecodeError, KeyError):
        print(f"  ⚠  Corrupt baseline file {BASELINE_FILE}, ignoring")
        return set()


def save_baseline(violations: list[dict]):
    baseline = {
        "_meta": {
            "created": __import__("datetime").datetime.now().isoformat(),
            "count": len(violations),
            "note": "Pre-existing violations accepted as technical debt. Expires: auto-6mo-review.",
        },
        "violations": sorted(violations, key=lambda v: f"{v['file']}:{v['line']}"),
    }
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"  ✓ Baseline saved: {len(violations)} violations in {BASELINE_FILE}")


def get_exclude_set(extra):
    ex = set(EXCLUDE_DEFAULT)
    if extra:
        ex.update(p.strip() for p in extra.split(","))
    return ex


def get_python_files(exclude):
    for path in SRC_DIR.rglob("*.py"):
        rel = path.relative_to(".").as_posix()
        if any(rel.startswith(e) or rel == e for e in exclude):
            continue
        yield path


# ─── Check 1: God Function ─────────────────────────────────────────


def check_god_function(tree, filepath):
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            lines = node.end_lineno - node.lineno if node.end_lineno else 0
            cc = _cyclomatic_complexity(node)
            if lines > 200:
                violations.append(
                    {
                        "check": "god_function",
                        "file": str(filepath),
                        "line": node.lineno,
                        "name": name,
                        "detail": f"{lines} lines (max 200), CC={cc}",
                        "severity": "FAIL",
                    }
                )
            elif cc > 15:
                violations.append(
                    {
                        "check": "god_function",
                        "file": str(filepath),
                        "line": node.lineno,
                        "name": name,
                        "detail": f"CC={cc} (max 15), {lines} lines",
                        "severity": "FAIL",
                    }
                )
    return violations


def _cyclomatic_complexity(node):
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.Assert)):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += len(child.values) - 1
    return max(count, 1)


# ─── Check 2: Duplicate Code ────────────────────────────────────────


def check_duplicate_code(files, exclude):
    violations = []
    blocks = defaultdict(list)

    for fp in files:
        rel = fp.relative_to(".").as_posix()
        if any(rel.startswith(e) for e in exclude):
            continue
        try:
            text = fp.read_text()
        except Exception:
            continue
        lines = [l for l in text.split("\n") if l.strip() and not l.strip().startswith(("#", '"""', "'''"))]
        for i in range(len(lines) - 14):
            block = "\n".join(lines[i : i + 15])
            if len(block.strip()) < 30:
                continue
            key = hash(block)
            blocks[key].append((rel, i + 1))

    for key, locations in blocks.items():
        if len(locations) >= 2:
            unique_files = set(loc[0] for loc in locations)
            if len(unique_files) >= 2:
                violations.append(
                    {
                        "check": "duplicate_code",
                        "file": ", ".join(f"{f}:{l}" for f, l in locations[:4]),
                        "line": locations[0][1],
                        "name": locations[0][0],
                        "detail": f"15+ identical lines across {len(unique_files)} files",
                        "severity": "WARN",
                    }
                )
    return violations


# ─── Check 3: Bare Except ──────────────────────────────────────────


def check_bare_except(tree, filepath):
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                violations.append(
                    {
                        "check": "bare_except",
                        "file": str(filepath),
                        "line": node.lineno,
                        "name": ": except:",
                        "detail": "bare except with no exception type",
                        "severity": "FAIL",
                    }
                )
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                _has_log = _body_has_logging(node.body)
                if not _has_log:
                    violations.append(
                        {
                            "check": "bare_except",
                            "file": str(filepath),
                            "line": node.lineno,
                            "name": ": except Exception:",
                            "detail": "except Exception without logging (use logger.exception())",
                            "severity": "FAIL",
                        }
                    )
    return violations


def _body_has_logging(body):
    for n in body:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            func = n.value.func
            if isinstance(func, ast.Attribute) and func.attr in ("exception", "error", "critical", "warning"):
                return True
        elif isinstance(n, ast.Raise):
            return True
    return False


# ─── Check 4: Sync in Async ────────────────────────────────────────


def check_sync_in_async(tree, filepath):
    violations = []
    rel = str(filepath)
    if "routers" not in rel and "router" not in rel.lower():
        return violations

    any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            has_route_decorator = any(
                isinstance(d, ast.Call)
                and hasattr(d.func, "attr")
                and d.func.attr in ("get", "post", "put", "patch", "delete", "head", "options", "websocket")
                for d in node.decorator_list
            )
            if not has_route_decorator:
                continue
            violations.append(
                {
                    "check": "sync_in_async",
                    "file": rel,
                    "line": node.lineno,
                    "name": node.name,
                    "detail": "sync def in FastAPI router file — should be async def for I/O routes",
                    "severity": "WARN",
                }
            )
    return violations


# ─── Check 5: Print in Production ──────────────────────────────────


def check_print_in_prod(tree, filepath):
    violations = []
    rel = str(filepath)
    if rel.startswith("tests/") or rel.startswith("scripts/"):
        return violations
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            violations.append(
                {
                    "check": "print_in_prod",
                    "file": rel,
                    "line": node.lineno,
                    "name": "print()",
                    "detail": "print() in production code — use logging instead",
                    "severity": "FAIL",
                }
            )
    return violations


# ─── Check 6: Module Side Effect ───────────────────────────────────


def check_module_side_effect(tree, filepath):
    violations = []
    rel = str(filepath)
    if rel.startswith("tests/") or rel.startswith("scripts/"):
        return violations

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            left = node.test.left
            if isinstance(left, ast.Name) and left.id == "__name__":
                continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            names = []
            if isinstance(node, ast.Assign):
                names = [t for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target]
            if names and all(n.id.isupper() or n.id.startswith("_") for n in names):
                continue
            if names and names[0].id in ("router", "app", "client"):
                continue
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id in ("importlib",) and func.attr == "import_module":
                        continue
        violations.append(
            {
                "check": "module_side_effect",
                "file": rel,
                "line": node.lineno,
                "name": node.__class__.__name__,
                "detail": f"top-level code (outside def/class) in src/ line {node.lineno}",
                "severity": "WARN",
            }
        )
    return violations


# ─── Orchestrator ──────────────────────────────────────────────────


def run_checks(exclude):
    violations = []
    files = list(get_python_files(exclude))

    for fp in files:
        try:
            tree = ast.parse(fp.read_text(), filename=str(fp))
        except SyntaxError as e:
            violations.append(
                {
                    "check": "syntax_error",
                    "file": str(fp),
                    "line": e.lineno or 0,
                    "name": "SyntaxError",
                    "detail": str(e),
                    "severity": "FAIL",
                }
            )
            continue

        violations.extend(check_god_function(tree, fp))
        violations.extend(check_bare_except(tree, fp))
        violations.extend(check_sync_in_async(tree, fp))
        violations.extend(check_print_in_prod(tree, fp))
        violations.extend(check_module_side_effect(tree, fp))

    violations.extend(check_duplicate_code(files, exclude))
    return violations


OVERRIDE_LOG = Path("docs/session-handoffs/_quality-override-log.jsonl")


def check_override() -> str | None:
    """Check for QUALITY_GATE_OVERRIDE env var bypass.

    Returns:
        The override reason string if bypassed, None otherwise.
    """
    reason = os.environ.get("QUALITY_GATE_OVERRIDE", "").strip()
    if reason:
        log_entry = json.dumps(
            {
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "override": reason,
                "user": os.environ.get("USER", "unknown"),
            }
        )
        OVERRIDE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(OVERRIDE_LOG, "a") as f:
            f.write(log_entry + "\n")
        print(f"  ⚠  QUALITY GATE OVERRIDE: {reason}")
        print(f"  ⚠  Logged to {OVERRIDE_LOG}")
        print("  ⚠  Mandatory follow-up issue required within 48h")
    return reason


def main():
    args = parse_args()
    override = check_override()
    if override:
        print("  → Quality gates SKIPPED due to override")
        sys.exit(0)

    exclude = get_exclude_set(args.exclude)
    violations = run_checks(exclude)

    # --update-baseline: snapshot current violations as acceptable debt
    if args.update_baseline:
        save_baseline(violations)
        sys.exit(0)

    # --no-baseline: skip baseline filtering
    baseline_ids = set()
    if not args.no_baseline:
        baseline_ids = load_baseline()

    if baseline_ids:
        filtered = [v for v in violations if get_baseline_id(v) not in baseline_ids]
        skipped = len(violations) - len(filtered)
        violations = filtered
    else:
        skipped = 0

    if args.json:
        print(json.dumps(violations, indent=2))
    else:
        fails = [v for v in violations if v["severity"] == "FAIL"]
        warns = [v for v in violations if v["severity"] == "WARN"]

        print(f"\n{'=' * 60}")
        print("  QUALITY GATES REPORT")
        print(f"  {len(fails)} FAILURES, {len(warns)} WARNINGS", end="")
        if skipped:
            print(f"  ({skipped} pre-existing violations filtered via baseline)")
        else:
            print()
        print(f"{'=' * 60}")

        for v in fails:
            print(f"  FAIL  {v['check']:20s} {v['file']}:{v['line']}  {v['detail']}")
        for v in warns:
            print(f"  WARN  {v['check']:20s} {v['file']}:{v['line']}  {v['detail']}")

        if not fails and not warns:
            print("  ✓ All quality gates passed")

    exit_code = VIOLATION_EXIT if args.fail and any(v["severity"] == "FAIL" for v in violations) else 0

    if args.dry_run:
        sys.exit(0)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

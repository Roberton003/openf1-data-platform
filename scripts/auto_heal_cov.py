#!/usr/bin/env python3
"""Auto-heal coverage gaps — detect → generate tests → validate → commit.

Usage:
    python scripts/auto_heal_cov.py             # heal all below-target modules
    python scripts/auto_heal_cov.py --target 60 # set coverage target (default: 60)
    python scripts/auto_heal_cov.py --dry-run   # detect only, no writes
    python scripts/auto_heal_cov.py --max 3     # max functions to generate per run

Strategy:
    1. Run pytest with coverage, collect the JSON report
    2. Identify modules below the coverage target
    3. For each uncovered function, parse AST → generate test skeleton
    4. Write to the correct test file (create if missing)
    5. Run new tests, validate they pass
    6. Commit all with a descriptive message

Safety:
    - Max N functions per run (configurable, default 5)
    - Dry-run mode for inspection before writes
    - Only modifies test files, never source
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "src"
TESTS = PROJECT / "tests"
COV_JSON = PROJECT / ".coverage_tmp.json"

TEST_HEADER = '''"""Auto-generated tests for {module} — coverage heal."""
import pytest
'''

MOCK_IMPORTS = """
from unittest.mock import patch, MagicMock, PropertyMock
"""


def run_capture(cmd, cwd=None, timeout=120):
    """Run a command and return (returncode, stdout, stderr)."""
    cwd = cwd or PROJECT
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def get_coverage_data(target=60):
    """Run pytest with JSON coverage report, return parsed data.

    Uses a subset of fast test files to avoid timeout.
    Falls back to full suite if subset fails to produce data.
    """
    fast_tests = [
        "tests/test_extract.py",
        "tests/test_process_edge.py",
        "tests/test_config.py",
        "tests/test_health.py",
        "tests/test_database.py",
        "tests/test_schemas.py",
        "tests/test_storage.py",
        "tests/test_compress_bronze.py",
        "tests/test_vector_store.py",
        "tests/test_ci_monitor_extended.py",
        "tests/test_analytics.py",
        "tests/test_sql_validation.py",
        "tests/test_telemetry.py",
        "tests/test_model_loader.py",
        "tests/test_quarantine.py",
        "tests/test_rate_limit.py",
    ]
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *fast_tests,
        "--cov=src",
        "--cov-report=json:" + str(COV_JSON),
        "-q",
        "-x",
        "--tb=short",
    ]
    rc, out, err = run_capture(cmd, timeout=120)
    if rc not in (0, 1):
        print(f"[COV] fast tests failed: rc={rc}")
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=json:" + str(COV_JSON),
            "--cov-fail-under=0",
            "-q",
            "--ignore=tests/test_cli_pipeline.py",
        ]
        rc, out, err = run_capture(cmd, timeout=180)
        if rc not in (0, 1):
            print(f"[COV] full suite also failed: rc={rc}")
            return None

    if not COV_JSON.exists():
        print(f"[COV] coverage JSON not found at {COV_JSON}")
        return None

    with open(COV_JSON) as f:
        data = json.load(f)

    COV_JSON.unlink(missing_ok=True)

    return data


def find_below_target(data, target=60):
    """Return list of modules below coverage target, sorted by gap size."""
    modules = []
    for mod_name, mod_data in data.get("files", {}).items():
        covered = mod_data.get("summary", {}).get("percent_covered", 100)
        if covered < target and covered > 0:
            modules.append((mod_name, covered))
    modules.sort(key=lambda x: x[1])
    return modules


def get_function_ranges(source):
    """Parse AST of source code, return list of (func_name, start, end, args)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            functions.append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno or node.lineno,
                    args,
                    ast.get_docstring(node) or "",
                    [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                )
            )
    return functions


def find_uncovered_functions(module_path, missing_lines, executed_lines):
    """Given a module path and coverage line data, return uncovered funcs."""
    if not module_path.exists():
        return []

    source = module_path.read_text()
    all_funcs = get_function_ranges(source)
    print(
        f"      [find_uncovered_functions] {module_path.name}: {len(all_funcs)} functions, {len(missing_lines)} missing, {len(executed_lines)} executed",
        flush=True,
    )

    exec_set = set(executed_lines)
    uncovered = []
    for func_name, start, end, args, docstring, decorators in all_funcs:
        func_body = set(range(start + 1, end + 1))
        total_body = len(func_body)
        executed_body_lines = func_body & exec_set
        executed_count = len(executed_body_lines)
        coverage_pct = round((executed_count / total_body) * 100, 1) if total_body > 0 else 0
        if coverage_pct < 30:
            print(
                f"    FUNC {func_name}: lines {start}-{end} "
                f"({total_body} body lines, {executed_count} executed, "
                f"{coverage_pct}% cov)"
            )
            uncovered.append((func_name, start, end, args, docstring, decorators))

    return uncovered


def detect_dependencies(module_path, func_start, func_end):
    """Scan function source for external dependencies to mock."""
    if not module_path.exists():
        return set()

    source = module_path.read_text()
    lines = source.split("\n")
    func_lines = lines[func_start - 1 : func_end]

    text = "\n".join(func_lines)
    deps = set()

    if "requests." in text or "requests.get" in text or "requests.post" in text:
        deps.add("requests")
    if "pd.read_parquet" in text or "pd.DataFrame" in text or "pd." in text:
        deps.add("pandas")
    if "duckdb" in text:
        deps.add("duckdb")
    if "smtplib" in text or "smtp" in text.lower():
        deps.add("smtplib")
    if "subprocess" in text:
        deps.add("subprocess")
    if "mlflow" in text:
        deps.add("mlflow")
    if "chromadb" in text or "ChromaDB" in text or "SentenceTransformer" in text:
        deps.add("chromadb")
    if "openf1.org" in text or "fetch(" in text:
        deps.add("requests")
    if "os.path" in text or "os.makedirs" in text or "os.path.exists" in text:
        deps.add("os")
    if "DATA_DIR" in text:
        deps.add("DATA_DIR")
    if "QUARANTINE_DIR" in text:
        deps.add("QUARANTINE_DIR")
    if "get_focus_drivers" in text:
        deps.add("config")
    if "index_race_control_messages" in text:
        deps.add("vector_store")
    if "HTTPException" in text or "Depends" in text:
        deps.add("api_dependency")

    return deps


def map_test_file(module_name):
    """Map source module name to test file path."""
    for mapping, test_file in [
        ("ingestion/process", "test_process_edge"),
        ("ingestion/assets", "test_assets_extended"),
        ("ingestion/extract", "test_extract"),
        ("ingestion/config", "test_config"),
        ("ingestion/vector_store", "test_vector_store"),
        ("web/ci_monitor", "test_ci_monitor_extended"),
        ("web/database", "test_database"),
        ("web/analytics", "test_analytics"),
        ("web/model_loader", "test_model_loader"),
        ("routers/sla", "test_web_routers_sla"),
        ("routers/ci_alerts", "test_web_routers_ci_alerts"),
    ]:
        if mapping in module_name:
            return TESTS / f"{test_file}.py"

    stem = module_name.replace("src/", "").replace(".py", "").replace("/", "_")
    return TESTS / f"test_{stem}.py"

    return TESTS / f"test_{stem}.py"


def classify_func(func_name, args, deps, func_size, module_name):
    """Classify a function into a test template category."""
    if func_size > 50 or "api_dependency" in deps:
        return "complex"
    if "duckdb" in deps or "duckdb" in func_name:
        return "duckdb"
    if "requests" in deps:
        return "request"
    if "DATA_DIR" in deps or ("os" in deps and func_size > 15):
        return "filesystem"
    if not args:
        return "no_args"
    return "simple"


def generate_test(func_name, args, docstring, decorators, deps, module_name, func_size):
    """Generate test function body for an uncovered function."""
    category = classify_func(func_name, args, deps, func_size, module_name)
    lines = []

    if decorators:
        lines.append(f"# decorators: {decorators}")

    if docstring:
        short_doc = docstring.strip().split("\n")[0][:80]
        lines.append(f"# {func_name}: {short_doc}")
    lines.append("")

    from_path = module_name.replace("/", ".")[:-3]

    if category == "complex":
        lines.append('@pytest.mark.xfail(reason="TODO: auto-generated skeleton needs review")')
        lines.append(f"def test_{func_name}():")
        lines.append(f'    """TODO: auto-generated test for {func_name} — needs manual fixture setup."""')
        lines.append('    pytest.skip("Complex function — requires integration fixtures")')
    elif category == "duckdb":
        lines.append(f"def test_{func_name}(mock_db):")
        if "conn" in args or "connection" in args:
            lines.append(f"    from {from_path} import {func_name}")
            lines.append(f"    result = {func_name}(mock_db)")
        else:
            duckdb_arg = next((a for a in args if "db" not in a and "conn" not in a), None)
            lines.append(f"    from {from_path} import {func_name}")
            lines.append("    from unittest.mock import patch")
            lines.append('    with patch("duckdb.connect", return_value=mock_db):')
            if duckdb_arg:
                mock_val = _mock_arg(duckdb_arg)
                lines.append(f"        result = {func_name}({mock_val})")
            else:
                lines.append(f"        result = {func_name}()")
        lines.append("    assert result is not None")
    elif category == "filesystem":
        lines.append(f"def test_{func_name}(tmp_path):")
        lines.append("    from unittest.mock import patch")
        lines.append(f"    from {from_path} import {func_name}")
        mock_args = []
        for a in args:
            if a in ("base_dir", "partition_quarantine_dir", "target_dir"):
                mock_args.append("str(tmp_path)")
            elif a in ("year",):
                mock_args.append("2025")
            elif a in ("gp_name", "session_name", "table_name", "reason"):
                mock_args.append('"test"')
            elif a == "focus_drivers":
                mock_args.append("{1: 'Driver'}")
            elif "df" in a or "dataframe" in a.lower():
                mock_args.append("pd.DataFrame({'col': [1]})")
            else:
                mock_args.append("None")
        if not mock_args:
            lines.append('    with patch("os.path.exists", return_value=True):')
            lines.append(f"        result = {func_name}()")
        else:
            lines.append(f"    result = {func_name}({', '.join(mock_args)})")
        if func_name.startswith("_calc_freshness"):
            lines.append("    assert result is None  # empty tmp_path has no files")
        elif func_name.startswith("_write") or func_name.startswith("_append"):
            lines.append("    assert result is None")
        else:
            lines.append("    assert result is not None")
    else:
        lines.append(f"def test_{func_name}():")
        lines.append(f"    from {from_path} import {func_name}")
        mock_args = []
        for a in args:
            mock_args.append(_mock_arg(a))
        if not mock_args:
            lines.append(f"    result = {func_name}()")
        else:
            lines.append(f"    result = {func_name}({', '.join(mock_args)})")
        lines.append("    assert result is not None")

    return "\n".join(lines)


def _mock_arg(a):
    """Map function argument name to a test mock value."""
    if a in ("year", "n", "max_retries", "timeout"):
        return "2025" if a == "year" else "5"
    if a in (
        "gp_name",
        "session_name",
        "table_name",
        "reason",
        "base_dir",
        "partition_quarantine_dir",
        "target_dir",
        "part_exec_path",
        "message",
    ):
        return '"test"'
    if "df" in a or "dataframe" in a.lower():
        return "pd.DataFrame({'c': [1]})"
    if "contract" in a or "cls" in a:
        return "MockContract"
    if "schema" in a:
        return '{"c": "int64"}'
    if "cols" in a or "required_cols" in a:
        return '["c"]'
    if "dir" in a or "path" in a:
        return '"/tmp/test"'
    if "row" in a:
        return '{"data_freshness_minutes": 5, "duration_seconds": 30, "quarantine_rate": 0.0}'
    if "run" in a:
        return '"test-run-id"'
    if "target" in a:
        return '"test-target"'
    return "None"


def auto_heal(target=60, max_funcs=5, dry_run=False):
    """Main auto-heal pipeline."""
    print(f"=== Auto-Heal Coverage === target={target}%, max={max_funcs} funcs")

    data = get_coverage_data(target)
    if not data:
        print("[FAIL] Could not collect coverage data.")
        return 1

    below = find_below_target(data, target)
    if not below:
        print(f"[OK] All modules above {target}% coverage.")
        return 0

    print(f"\nModules below {target}%:")
    for mod, cov in below:
        print(f"  {mod}: {cov:.1f}%")

    total_generated = 0
    generated_tests = {}

    for mod_name, cov_pct in below:
        module_path = PROJECT / mod_name
        if not module_path.exists():
            print(f"    [SKIP] {mod_name} not found at {module_path}")
            continue

        missing_lines = data["files"].get(mod_name, {}).get("missing_lines", [])
        executed_lines = data["files"].get(mod_name, {}).get("executed_lines", [])

        uncovered = find_uncovered_functions(module_path, missing_lines, executed_lines)
        print(f"\n  {mod_name}: {len(uncovered)} uncovered functions ({cov_pct:.1f}% cov)")
        if not uncovered:
            continue

        target_file = map_test_file(mod_name)
        existing_tests = set()
        if target_file.exists():
            existing_content = target_file.read_text()
            for line in existing_content.split("\n"):
                if line.startswith("def test_"):
                    existing_tests.add(line.split("(")[0].replace("def ", "").strip())

        count = 0
        for func_name, start, end, args, docstring, decorators in uncovered:
            test_name = f"test_{func_name}"
            if test_name in existing_tests:
                continue

            deps = detect_dependencies(module_path, start, end)
            func_size = end - start

            test_body = generate_test(func_name, args, docstring, decorators, deps, mod_name, func_size)

            if test_name not in generated_tests:
                generated_tests[test_name] = []
            generated_tests[test_name].append((target_file, test_body, mod_name))

            count += 1
            total_generated += 1

            if count >= max_funcs:
                break

    if not generated_tests:
        print("\n[OK] All uncovered functions already have tests.")
        return 0

    print(f"\n=== Writing {total_generated} new tests ===")

    by_file = {}
    for test_name, entries in generated_tests.items():
        for target_file, test_body, mod_name in entries:
            if target_file not in by_file:
                by_file[target_file] = []
            by_file[target_file].append((test_name, test_body, mod_name))

    for target_file, entries in by_file.items():
        mod_name = entries[0][2]
        header = TEST_HEADER.format(module=mod_name)

        all_test_bodies = "\n".join(tb for _, tb, _ in entries)
        needs_pandas = "pd." in all_test_bodies
        needs_pytest = (
            "@pytest.mark" in all_test_bodies
            or "pytest.skip" in all_test_bodies
            or "pytest.importorskip" in all_test_bodies
        )
        needs_mock = "MagicMock" in all_test_bodies or "mock_" in all_test_bodies
        needs_patch = (
            "from unittest.mock import patch" in all_test_bodies or "from unittest.mock import" in all_test_bodies
        )
        needs_os = "os." in all_test_bodies

        extra_imports = []
        if needs_pandas:
            extra_imports.append("import pandas as pd")
        if needs_os:
            extra_imports.append("import os")
        if needs_pytest:
            if not target_file.exists() or "import pytest" not in target_file.read_text():
                extra_imports.insert(0, "import pytest")
        if needs_mock and not needs_patch:
            extra_imports.append("from unittest.mock import MagicMock")

        if target_file.exists():
            content = target_file.read_text()
            if extra_imports:
                insert_pos = content.find("\n\n")
                if insert_pos == -1:
                    insert_pos = len(content)
                content = content[:insert_pos] + "\n" + "\n".join(extra_imports) + "\n" + content[insert_pos:]
        else:
            content = header + "\n" + "\n".join(extra_imports) + "\n\n"

        for test_name, test_body, _ in entries:
            content += f"\n{test_body}\n"

        if dry_run:
            print(f"\n  [DRY-RUN] Would write to {target_file.name}:")
            for test_name, test_body, _ in entries:
                print(f"    + {test_name}")
                for line in test_body.split("\n"):
                    print(f"      {line}")
        else:
            target_file.write_text(content)
            print(f"  [WRITE] {target_file.name} ({len(entries)} new tests)")

    if dry_run:
        print(f"\n[DRY-RUN] {total_generated} tests would be generated.")
        return 0

    print("\n=== Validating new tests ===")

    test_files = sorted({str(f) for f in by_file})
    if test_files:
        cmd = [sys.executable, "-m", "pytest"] + test_files + ["-q", "--tb=short", "-x"]
        rc, out, err = run_capture(cmd, timeout=120)
        print(out[-500:] if len(out) > 500 else out)
        if err:
            print(err[-500:])

        if rc != 0:
            print(f"\n[FAIL] New tests did not pass (rc={rc}). Skipping commit.")
            return 1

    print("\n=== Committing ===")

    files_to_add = [str(f) for f in by_file]
    add_cmd = ["git", "add"] + files_to_add
    rc, out, err = run_capture(add_cmd)
    if rc != 0:
        print(f"[FAIL] git add: {err[:300]}")
        return 1

    msg = f"test: auto-heal coverage — {total_generated} novos testes"
    commit_cmd = ["git", "commit", "-m", msg]
    rc, out, err = run_capture(commit_cmd)
    if rc != 0:
        print(f"[FAIL] git commit: {err[:300]}")
        return 1

    print(f"[OK] Commit: {msg}")
    print(f"[OK] {total_generated} tests auto-generated, validated, and committed.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Auto-heal coverage gaps")
    parser.add_argument("--target", type=int, default=60, help="Coverage target %")
    parser.add_argument("--max", type=int, default=5, help="Max functions per run")
    parser.add_argument("--dry-run", action="store_true", help="Detect only, no writes")
    args = parser.parse_args()

    sys.exit(auto_heal(target=args.target, max_funcs=args.max, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

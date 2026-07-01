"""Tests for scripts/change_health_opencode.py."""

import json
import subprocess
import sys

from scripts.change_health_opencode import (
    ChangeHealthReport,
    _classify,
    _detect_base_branch,
    _format_markdown,
    _manual_review_required,
)

# ── Classification unit tests ────────────────────────────────────────────────


class TestClassify:
    def test_low_typo_in_readme(self):
        """Cenário 1: LOW — typo em README"""
        risk = _classify(["README.md"], added=1, removed=1)
        assert risk == "LOW"

    def test_medium_new_skill(self):
        """Cenário 2: MEDIUM — nova skill"""
        risk = _classify(["skills/data-quality/SKILL.md"], added=30, removed=0)
        assert risk == "MEDIUM"

    def test_medium_template_rename(self):
        """Cenário 3: MEDIUM — renomear campo em template"""
        risk = _classify(["docs/templates/handoff.md"], added=2, removed=2)
        assert risk == "MEDIUM"

    def test_high_schema_multiple_scripts(self):
        """Cenário 4: HIGH — schema + scripts + skill"""
        changed = [
            ".last-handoff.json",
            "scripts/codex/record_handoff.py",
            "skills/handoff-writer/SKILL.md",
        ]
        risk = _classify(changed, added=80, removed=20)
        assert risk == "HIGH"

    def test_critical_credential_exposed(self):
        """Cenário 5: CRITICAL — credencial exposta"""
        risk = _classify(["opencode.jsonc"], added=1, removed=0)
        assert risk == "CRITICAL"

    def test_critical_credential_in_path(self):
        """CRITICAL — token/password/credential no path"""
        risk = _classify(["config/credentials.json"], added=10, removed=0)
        assert risk == "CRITICAL"

    def test_not_critical_for_baseline_files(self):
        """CRITICAL não dispara para .secrets.baseline"""
        risk = _classify([".secrets.baseline"], added=5, removed=0)
        assert risk == "LOW"

    def test_medium_via_handoff_path(self):
        """MEDIUM — path contém handoff"""
        risk = _classify(["docs/session-handoffs/README.md"], added=10, removed=5)
        assert risk == "MEDIUM"

    def test_high_more_than_3_files(self):
        """HIGH — mais de 3 arquivos (uncommitted)"""
        risk = _classify(
            ["a.py", "b.py", "c.py", "d.py", "e.py"],
            added=10,
            removed=0,
            uncommitted_count=5,
        )
        assert risk == "HIGH"

    def test_high_large_diff(self):
        """HIGH — diff > 50 linhas"""
        risk = _classify(["a.py"], added=100, removed=0)
        assert risk == "HIGH"

    def test_low_single_small_change(self):
        """LOW — 1 arquivo, poucas linhas, sem path especial"""
        risk = _classify(["README.md"], added=3, removed=1)
        assert risk == "LOW"


# ── Manual review ────────────────────────────────────────────────────────────


class TestManualReview:
    def test_critical_requires_review(self):
        assert _manual_review_required("CRITICAL", ["opencode.jsonc"]) is True

    def test_high_requires_review(self):
        assert _manual_review_required("HIGH", [".last-handoff.json"]) is True

    def test_medium_on_schema_path_requires_review(self):
        assert _manual_review_required("MEDIUM", [".last-handoff.json"]) is True

    def test_medium_on_skill_path_no_review(self):
        assert _manual_review_required("MEDIUM", ["skills/foo/SKILL.md"]) is False

    def test_low_no_review(self):
        assert _manual_review_required("LOW", ["README.md"]) is False


# ── Baseline detection ───────────────────────────────────────────────────────


class TestDetectBaseBranch:
    def test_returns_valid_branch(self):
        branch = _detect_base_branch()
        assert branch in ("main", "master")
        assert isinstance(branch, str)
        assert len(branch) > 0


# ── Markdown formatting ──────────────────────────────────────────────────────


class TestFormatMarkdown:
    def test_low_report_format(self):
        r = ChangeHealthReport(
            risk="LOW",
            changed_files=1,
            python_files=0,
            markdown_files=1,
        )
        md = _format_markdown(r)
        assert "# Change Health" in md
        assert "Risk: LOW" in md
        assert "Changed files: 1" in md

    def test_critical_report_format(self):
        r = ChangeHealthReport(
            risk="CRITICAL",
            manual_review_required=True,
            changed_files=1,
            python_files=0,
            markdown_files=0,
            suggested_focus="REVISÃO HUMANA OBRIGATÓRIA",
        )
        md = _format_markdown(r)
        assert "Risk: CRITICAL" in md
        assert "Manual review required: yes" in md


# ── Integration: CLI flags ───────────────────────────────────────────────────


class TestCLI:
    def test_json_output_is_valid(self):
        r = subprocess.run(
            [sys.executable, "scripts/change_health_opencode.py", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "risk" in data
        assert data["risk"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_markdown_output_has_header(self):
        r = subprocess.run(
            [sys.executable, "scripts/change_health_opencode.py", "--markdown"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0
        assert "# Change Health" in r.stdout

    def test_help_output(self):
        r = subprocess.run(
            [sys.executable, "scripts/change_health_opencode.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0
        assert "--json" in r.stdout
        assert "--markdown" in r.stdout
        assert "--check" in r.stdout
        assert "--baseline" in r.stdout

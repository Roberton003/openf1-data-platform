#!/usr/bin/env python3
"""Build a dry-run corpus manifest for the OpenF1 local context index."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_INCLUDE = (
    "README.md",
    "requirements.txt",
    "Makefile",
    "docker-compose.yml",
    "workspace.yaml",
    ".github/workflows/*.yml",
    "infra/*.tf",
    "src/**/*.py",
    "src/web/static/race_intelligence/*.html",
    "src/web/static/race_intelligence/*.css",
    "src/web/static/race_intelligence/*.js",
    "tests/*.py",
    "tests/**/*.py",
    "docs/PROJECT_PROFILE.md",
    "docs/adr/*.md",
    "docs/plans/*.md",
    "docs/public-safe/*.md",
    "docs/medallion_architecture.md",
    "docs/data_consumption_guide.md",
    "docs/dashboard_data_exploration.md",
)

DEFAULT_EXCLUDE = (
    ".git/**",
    ".venv/**",
    "venv/**",
    "env/**",
    "**/__pycache__/**",
    ".pytest_cache/**",
    ".tox/**",
    ".coverage",
    "build/**",
    "dist/**",
    "data/**",
    "models/**",
    "Formula Insights/**",
    ".tmp_dagster_home*/**",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.parquet",
    "*.joblib",
    "*.pkl",
    "*.odt",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.log",
    "openf1_platform_analysis.html",
    "docs_api-endpoints.odt",
)

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".tf",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class CorpusFile:
    path: str
    bytes: int
    estimated_tokens: int
    category: str


def matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        "Makefile",
    }


def categorize(path: str) -> str:
    if path.startswith("src/"):
        return "code"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("docs/adr/"):
        return "adr"
    if path.startswith("docs/plans/"):
        return "plans"
    if path.startswith("docs/public-safe/"):
        return "public_docs"
    if path.startswith("docs/"):
        return "private_docs"
    if path.startswith(".github/") or path.startswith("infra/"):
        return "ops"
    return "root"


def build_manifest(root: Path) -> list[CorpusFile]:
    files: list[CorpusFile] = []
    for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = file_path.relative_to(root).as_posix()
        if matches_any(rel, DEFAULT_EXCLUDE):
            continue
        if not matches_any(rel, DEFAULT_INCLUDE):
            continue
        if not is_text_candidate(file_path):
            continue
        size = file_path.stat().st_size
        files.append(
            CorpusFile(
                path=rel,
                bytes=size,
                estimated_tokens=max(1, size // 4),
                category=categorize(rel),
            )
        )
    return files


def summarize(files: list[CorpusFile]) -> dict[str, object]:
    by_category: dict[str, dict[str, int]] = {}
    for item in files:
        bucket = by_category.setdefault(item.category, {"files": 0, "bytes": 0, "estimated_tokens": 0})
        bucket["files"] += 1
        bucket["bytes"] += item.bytes
        bucket["estimated_tokens"] += item.estimated_tokens
    return {
        "files": len(files),
        "bytes": sum(item.bytes for item in files),
        "estimated_tokens": sum(item.estimated_tokens for item in files),
        "by_category": by_category,
    }


def write_markdown(path: Path, files: list[CorpusFile]) -> None:
    summary = summarize(files)
    lines = [
        "# OpenF1 Context Corpus Dry Run",
        "",
        f"- Files: {summary['files']}",
        f"- Bytes: {summary['bytes']}",
        f"- Estimated tokens: {summary['estimated_tokens']}",
        "",
        "## Categories",
        "",
    ]
    for category, values in sorted(summary["by_category"].items()):
        lines.append(
            f"- {category}: {values['files']} files, {values['bytes']} bytes, ~{values['estimated_tokens']} tokens"
        )
    lines.extend(["", "## Files", ""])
    for item in files:
        lines.append(f"- `{item.path}` ({item.bytes} bytes, ~{item.estimated_tokens} tokens, {item.category})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--json", default="docs/token-budget/openf1_context_corpus.json")
    parser.add_argument("--markdown", default="docs/token-budget/openf1_context_corpus.md")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = build_manifest(root)
    payload = {
        "root": str(root),
        "summary": summarize(files),
        "files": [asdict(item) for item in files],
    }

    json_path = root / args.json
    md_path = root / args.markdown
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(md_path, files)
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

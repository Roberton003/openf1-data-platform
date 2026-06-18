#!/usr/bin/env python3
from __future__ import annotations

import re
from argparse import ArgumentParser
from datetime import date
from pathlib import Path


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:80] or "handoff"


def main() -> int:
    parser = ArgumentParser(description="Create a session handoff skeleton.")
    parser.add_argument("title", help="Title for the handoff")
    parser.add_argument("--project", default="", help="Project name")
    parser.add_argument(
        "--template",
        default="docs/templates/handoff.md",
        help="Template path relative to the repo root",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    template_path = (repo_root / args.template).resolve()
    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")

    outdir = repo_root / "docs/session-handoffs"
    outdir.mkdir(parents=True, exist_ok=True)

    path = outdir / f"{date.today().isoformat()}_{slugify(args.title)}.md"
    content = template_path.read_text(encoding="utf-8").format(
        title=args.title,
        date=date.today().isoformat(),
        project=args.project,
    )
    path.write_text(content, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

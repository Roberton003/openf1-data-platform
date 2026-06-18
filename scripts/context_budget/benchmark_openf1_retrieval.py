#!/usr/bin/env python3
"""Run a lightweight lexical retrieval baseline over the OpenF1 context corpus."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from pathlib import Path

from build_openf1_corpus import build_manifest

DEFAULT_QUERIES = [
    {
        "id": "race-intelligence-router",
        "query": "Race Intelligence FastAPI endpoints session summary driver duel pipeline health",
        "expected": ["src/web/routers/race_intelligence.py", "tests/test_api.py"],
    },
    {
        "id": "duckdb-schema-fallback",
        "query": "DuckDB database empty schema fallback table columns parquet missing data",
        "expected": ["src/web/database.py", "tests/test_api.py"],
    },
    {
        "id": "ingestion-config",
        "query": "ingestion configuration on demand sessions drivers stints weather telemetry",
        "expected": [
            "src/ingestion/config.py",
            "src/ingestion/extract.py",
            "src/ingestion/process.py",
        ],
    },
    {
        "id": "ci-pipeline",
        "query": "GitHub Actions pytest flake8 CI deployment workflow",
        "expected": [
            ".github/workflows/ci.yml",
            ".github/workflows/cd.yml",
            "Makefile",
        ],
    },
    {
        "id": "mlops-observability-plan",
        "query": "MLOps observability MLflow ChromaDB sentence transformers monitoring plan",
        "expected": [
            "docs/plans/005_ia_mlops_observabilidade.md",
            "docs/adr/adr-005-ia-hibrida-text-to-sql.md",
        ],
    },
]

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def score(
    query_tokens: list[str], doc_tokens: Counter[str], idf: dict[str, float]
) -> float:
    q_counts = Counter(query_tokens)
    total = sum(doc_tokens.values()) or 1
    value = 0.0
    for token, q_count in q_counts.items():
        tf = doc_tokens.get(token, 0) / total
        if tf:
            value += q_count * tf * idf.get(token, 0.0)
    return value


def recall_at_k(results: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 0.0
    top = set(results[:k])
    return len(top.intersection(expected)) / len(expected)


def reciprocal_rank(results: list[str], expected: list[str]) -> float:
    expected_set = set(expected)
    for idx, path in enumerate(results, start=1):
        if path in expected_set:
            return 1.0 / idx
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument(
        "--output", default="docs/token-budget/openf1_retrieval_baseline.json"
    )
    parser.add_argument("--k", type=int, nargs="+", default=[3, 5, 10])
    args = parser.parse_args()

    root = Path(args.root).resolve()
    corpus = build_manifest(root)
    docs: list[dict[str, object]] = []
    df: Counter[str] = Counter()
    started = time.perf_counter()

    for item in corpus:
        text = read_text(root / item.path)
        tokens = Counter(tokenize(item.path + "\n" + text))
        docs.append(
            {
                "path": item.path,
                "tokens": tokens,
                "estimated_tokens": item.estimated_tokens,
            }
        )
        df.update(tokens.keys())

    idf = {
        token: math.log((len(docs) + 1) / (count + 1)) + 1.0
        for token, count in df.items()
    }
    query_results = []

    for query in DEFAULT_QUERIES:
        query_tokens = tokenize(query["query"])
        ranked = sorted(
            (
                {
                    "path": doc["path"],
                    "score": score(query_tokens, doc["tokens"], idf),
                    "estimated_tokens": doc["estimated_tokens"],
                }
                for doc in docs
            ),
            key=lambda row: row["score"],
            reverse=True,
        )
        ranked = [row for row in ranked if row["score"] > 0]
        paths = [str(row["path"]) for row in ranked]
        max_k = max(args.k)
        query_results.append(
            {
                "id": query["id"],
                "query": query["query"],
                "expected": query["expected"],
                "top_results": ranked[:max_k],
                "metrics": {
                    f"recall_at_{k}": recall_at_k(paths, query["expected"], k)
                    for k in args.k
                }
                | {"mrr": reciprocal_rank(paths, query["expected"])},
            }
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    payload = {
        "method": "lexical_tf_idf_file_baseline",
        "corpus_files": len(corpus),
        "elapsed_ms": elapsed_ms,
        "queries": query_results,
    }

    out_path = root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"corpus_files": len(corpus), "elapsed_ms": elapsed_ms}, indent=2))


if __name__ == "__main__":
    main()

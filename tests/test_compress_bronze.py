"""Tests for ingestion/compress_bronze.py — cold storage compression."""

import json
import os

from src.ingestion.compress_bronze import compress_bronze_layer


def test_compress_bronze_creates_archive(tmp_path):
    bronze_dir = tmp_path / "bronze" / "year=2025" / "gp=Bahrain"
    bronze_dir.mkdir(parents=True)
    (bronze_dir / "data.json").write_text(json.dumps({"key": "value"}))

    compress_bronze_layer(str(tmp_path))

    archive = tmp_path / "bronze" / "archive" / "year=2025" / "gp=Bahrain" / "raw_data.tar.gz"
    assert archive.exists()


def test_compress_bronze_removes_originals(tmp_path):
    bronze_dir = tmp_path / "bronze" / "year=2025" / "gp=Bahrain"
    bronze_dir.mkdir(parents=True)
    (bronze_dir / "data.json").write_text(json.dumps({"key": "value"}))

    compress_bronze_layer(str(tmp_path))

    assert not (bronze_dir / "data.json").exists()


def test_compress_bronze_skips_nonexistent_dir(tmp_path):
    compress_bronze_layer(str(tmp_path / "nonexistent"))


def test_compress_bronze_ignores_archive_dir(tmp_path):
    bronze_dir = tmp_path / "bronze"
    archive_dir = bronze_dir / "archive" / "old"
    archive_dir.mkdir(parents=True)
    (archive_dir / "data.json").write_text("old data")

    compress_bronze_layer(str(tmp_path))

    assert (archive_dir / "data.json").exists()


def test_compress_bronze_skips_non_json_files(tmp_path):
    bronze_dir = tmp_path / "bronze" / "test"
    bronze_dir.mkdir(parents=True)
    (bronze_dir / "data.csv").write_text("a,b\n1,2")

    compress_bronze_layer(str(tmp_path))

    archive = tmp_path / "bronze" / "archive" / "test" / "raw_data.tar.gz"
    assert not archive.exists()

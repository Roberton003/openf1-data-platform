import os
import tarfile

from src.ingestion.compress_bronze import compress_bronze_layer


def test_compress_bronze_layer(tmp_path):
    bronze_dir = tmp_path / "bronze" / "test_partition"
    archive_dir = tmp_path / "bronze" / "archive" / "test_partition"
    os.makedirs(bronze_dir, exist_ok=True)

    mock_files = {
        "file1.json": '{"status": "green", "laps": 10}',
        "file2.json": '{"status": "yellow", "laps": 11}',
    }
    for name, content in mock_files.items():
        (bronze_dir / name).write_text(content, encoding="utf-8")

    compress_bronze_layer(data_base_dir=str(tmp_path))

    remaining = [f for f in os.listdir(bronze_dir) if f.endswith(".json")]
    assert len(remaining) == 0, "JSON files were not deleted after compression."

    archive_tar = archive_dir / "raw_data.tar.gz"
    assert archive_tar.exists(), "Archive tar.gz was not created."

    with tarfile.open(archive_tar, "r:gz") as tar:
        members = tar.getnames()
        assert "file1.json" in members
        assert "file2.json" in members

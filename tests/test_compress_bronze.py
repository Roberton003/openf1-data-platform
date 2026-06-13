# Test suite for Bronze layer compaction utility
import os
import shutil
import tarfile

from src.ingestion.compress_bronze import compress_bronze_layer


def test_compress_bronze_layer():
    # Setup test directories under data/bronze/test_partition
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
    test_bronze_dir = os.path.join(base_dir, "bronze/test_partition")
    test_archive_dir = os.path.join(base_dir, "bronze/archive/test_partition")

    # Clean up any residual test folders
    if os.path.exists(test_bronze_dir):
        shutil.rmtree(test_bronze_dir)
    if os.path.exists(test_archive_dir):
        shutil.rmtree(test_archive_dir)

    os.makedirs(test_bronze_dir, exist_ok=True)

    # 1. Create mock JSON files
    mock_files = {
        "file1.json": '{"status": "green", "laps": 10}',
        "file2.json": '{"status": "yellow", "laps": 11}',
    }

    for name, content in mock_files.items():
        with open(os.path.join(test_bronze_dir, name), "w", encoding="utf-8") as f:
            f.write(content)

    # 2. Run the compression script
    compress_bronze_layer()

    # 3. Asserts
    # The original directory should have no JSON files left
    remaining_files = [f for f in os.listdir(test_bronze_dir) if f.endswith(".json")]
    assert len(remaining_files) == 0, "JSON files were not deleted after compression."

    # The archive tar.gz must exist
    archive_tar = os.path.join(test_archive_dir, "raw_data.tar.gz")
    assert os.path.exists(archive_tar), "Archive tar.gz was not created."

    # Assert tar content integrity
    with tarfile.open(archive_tar, "r:gz") as tar:
        members = tar.getnames()
        assert "file1.json" in members
        assert "file2.json" in members

    # 4. Clean up after successful test
    shutil.rmtree(test_bronze_dir)
    shutil.rmtree(
        os.path.dirname(test_archive_dir)
    )  # Removes archive/test_partition folder

"""
Regression gate — confirms the test suite has not shrunk unexpectedly.
Uses pytest --collect-only for accurate parametrized test counting.
"""

import subprocess
import sys


def test_regression_gate():
    """Collect all tests and confirm the suite is stable."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    lines = result.stdout.strip().splitlines()
    collected_line = [line for line in lines if "collected" in line or "selected" in line]
    assert collected_line, f"Cannot parse collection count:\n{result.stdout[-500:]}"
    count = int(collected_line[-1].split()[0])
    print(f"Tests collected: {count}")
    assert count >= 110, f"Regression: expected >= 110 tests, found {count}"

import subprocess
import sys


def test_main_strict_gate_mode_fails_on_high_risk_change():
    process = subprocess.run(
        [sys.executable, "-m", "src.main", "--gate-mode", "strict"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    assert "Quality gate failed: high-risk change requires manual review." in process.stderr


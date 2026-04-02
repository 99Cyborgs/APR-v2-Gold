from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "apr_core.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_doctor_cli_smoke():
    result = _run("doctor")
    assert result.returncode == 0, result.stderr or result.stdout


def test_audit_render_goldset_and_packs_cli_smoke(tmp_path: Path):
    record_path = tmp_path / "record.json"
    report_path = tmp_path / "report.md"
    goldset_path = tmp_path / "goldset.json"

    audit = _run("audit", "fixtures/inputs/reviewable_sound_paper.json", "--output", str(record_path))
    assert audit.returncode == 0, audit.stderr or audit.stdout
    assert record_path.exists()

    render = _run("render", str(record_path), "--output", str(report_path))
    assert render.returncode == 0, render.stderr or render.stdout
    assert report_path.exists()

    goldset = _run("goldset", "--output", str(goldset_path))
    assert goldset.returncode == 0, goldset.stderr or goldset.stdout
    assert goldset_path.exists()

    packs = _run("packs", "--pack-path", "fixtures/external_packs/apr-pack-physics")
    assert packs.returncode == 0, packs.stderr or packs.stdout

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))
existing = sys.modules.get("apr_core")
if existing and not str(getattr(existing, "__file__", "")).startswith(str(SRC)):
    for name in list(sys.modules):
        if name == "apr_core" or name.startswith("apr_core."):
            sys.modules.pop(name, None)

from apr_core.goldset import run_goldset_manifest


def test_goldset_runner_passes_fixture_manifest():
    summary = run_goldset_manifest(ROOT / "benchmarks" / "goldset" / "manifest.yaml")
    assert summary["failed"] == 0
    assert summary["total_cases"] >= 8

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

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

from apr_core.policy import load_contract_manifest  # noqa: E402
import scripts.build_release as build_release  # noqa: E402


def test_release_contract_keeps_package_identity_and_bootstrap_entrypoint():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]

    assert pyproject["project"]["name"] == "apr-v2"
    assert scripts["apr"] == "apr_core_bootstrap:main"
    assert scripts["apr-doctor"] == "apr_core.cli:doctor_entry_main"
    assert scripts["apr-readiness"] == "apr_core.cli:readiness_entry_main"
    assert (ROOT / "src" / "apr_core_bootstrap.py").exists()


def test_release_contract_sources_version_from_active_manifest():
    manifest_version = load_contract_manifest()["contract"]["version"]
    setup_text = (ROOT / "setup.py").read_text(encoding="utf-8")

    assert "setup(version=manifest_version())" in setup_text
    assert re.search(r"manifest\.yaml", setup_text)
    assert manifest_version in (ROOT / "contracts" / "active" / "manifest.yaml").read_text(encoding="utf-8")


def test_release_contract_keeps_expected_bundle_exclusions():
    assert build_release.EXCLUDED_DIRS == {".git", ".pytest_cache", "__pycache__", "dist", "build", "output", "reports", ".apr"}

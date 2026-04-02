from __future__ import annotations

import re
from pathlib import Path

from setuptools import setup

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "contracts" / "active" / "manifest.yaml"


def manifest_version() -> str:
    match = re.search(r"(?m)^\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", MANIFEST.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Could not read contract version from contracts/active/manifest.yaml")
    return match.group(1)


setup(version=manifest_version())

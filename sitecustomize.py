from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

existing = sys.modules.get("apr_core")
if existing and not str(getattr(existing, "__file__", "")).startswith(str(SRC)):
    for name in list(sys.modules):
        if name == "apr_core" or name.startswith("apr_core."):
            sys.modules.pop(name, None)

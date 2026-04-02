from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    src_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(src_root))
    from apr_core.cli import main as cli_main

    return cli_main()

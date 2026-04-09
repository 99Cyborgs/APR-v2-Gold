from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stable_json_dumps(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, sort_keys=True)


def stable_json_sha256(payload: Any) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False)
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_text_bundle(bundle: dict[str | Path, str]) -> None:
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    try:
        for raw_target, text in bundle.items():
            target = Path(raw_target)
            target.parent.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False)
            temp_path = Path(handle.name)
            with handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            temps[target] = temp_path

        for target, temp_path in temps.items():
            if target.exists():
                backup_handle = tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False)
                backup_path = Path(backup_handle.name)
                backup_handle.close()
                if backup_path.exists():
                    backup_path.unlink()
                os.replace(target, backup_path)
                backups[target] = backup_path
            os.replace(temp_path, target)
            installed.append(target)
    except Exception:
        for target in reversed(installed):
            if target.exists():
                target.unlink()
            backup_path = backups.get(target)
            if backup_path and backup_path.exists():
                os.replace(backup_path, target)
        for target, backup_path in backups.items():
            if target in installed:
                continue
            if backup_path.exists():
                os.replace(backup_path, target)
        raise
    finally:
        for temp_path in temps.values():
            if temp_path.exists():
                temp_path.unlink()
        for backup_path in backups.values():
            if backup_path.exists():
                backup_path.unlink()


def write_json(path: str | Path, payload: Any) -> None:
    _atomic_write_text(path, stable_json_dumps(payload, indent=2) + "\n")


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    _atomic_write_text(path, text)


def append_jsonl_atomic(path: str | Path, payload: Any) -> None:
    target = Path(path)
    serialized = stable_json_dumps(payload) + "\n"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    _atomic_write_text(target, existing + serialized)


def read_yaml(path: str | Path) -> dict[str, Any]:
    loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return loaded or {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_by_path(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def git_output(args: list[str], cwd: str | Path | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip() or completed.stderr.strip()

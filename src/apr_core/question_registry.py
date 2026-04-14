from __future__ import annotations

from typing import Any

from jsonschema import validate

from apr_core.policy import load_question_registry, load_question_registry_schema
from apr_core.utils import repo_root, sha256_file


def question_registry_path() -> str:
    return str((repo_root() / "contracts" / "active" / "question_registry.yaml").resolve())


def question_registry_sha256() -> str:
    return sha256_file(question_registry_path())


def load_validated_question_registry() -> dict[str, Any]:
    registry = load_question_registry()
    validate(instance=registry, schema=load_question_registry_schema())
    return registry

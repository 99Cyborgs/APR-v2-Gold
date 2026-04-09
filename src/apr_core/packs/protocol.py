from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


PackRunner = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class PackSpec:
    pack_id: str
    version: str
    api_version: int
    display_name: str
    advisory_only: bool
    supported_domains: list[str]
    run: PackRunner
    repo_root: str | None = None
    resolved_repo_root: str | None = None
    manifest_path: str | None = None
    manifest_sha256: str | None = None
    python_module: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def manifest_view(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "display_name": self.display_name,
            "version": self.version,
            "api_version": self.api_version,
            "advisory_only": self.advisory_only,
            "supported_domains": list(self.supported_domains),
            "repo_root": self.repo_root,
            "resolved_repo_root": self.resolved_repo_root,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "python_module": self.python_module,
        }

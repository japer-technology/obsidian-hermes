"""Security-sensitive ports that require deployment-specific implementations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class DispatchEnvelope:
    run_id: str
    trace_id: str
    task_id: str
    task_generation: int
    fence_epoch: int
    expires_at: str
    context_paths: tuple[str, ...]
    permissions: Mapping[str, Any]
    staging_path: str
    signature: str


class Attestor(Protocol):
    def attest(self, payload: bytes, *, key_ref: str) -> str:
        """Sign an exact canonical payload without exposing key material."""
        ...

    def verify(self, payload: bytes, signature: str, *, key_id: str) -> bool:
        """Verify one approval, control, or dispatch attestation."""
        ...


class DispatchTransport(Protocol):
    def issue(self, envelope: DispatchEnvelope) -> None:
        """Reveal one already-claimed command to only its allocated worker."""
        ...

    def revoke(self, run_id: str) -> None:
        """Revoke a terminal or expired run capability."""
        ...

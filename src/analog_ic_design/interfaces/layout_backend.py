"""LayoutBackend interface (Stage 0 stub — no implementation).

All geometry/DRC/LVS/PEX access routes through here from Stage 8 on; no UI,
AI, or client module may touch KLayout/Magic/Netgen directly (Law 4).
Distances, if any cross later, are SI meters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationReport:
    """Minimal Stage 0 physical-verification handle (Stage 8 owns details)."""

    passed: bool
    report_artifact_id: str


class LayoutBackend(ABC):
    """Physical-design backend (KLayout primary, Magic/Netgen adapters).

    All quantities crossing this interface are SI base units (meters).
    """

    @abstractmethod
    def run_drc(self, *, cell_name: str) -> VerificationReport:
        """Run DRC on `cell_name`; details owned by Stage 8."""
        raise NotImplementedError

    @abstractmethod
    def backend_version(self) -> str:
        """Free-form build string feeding `execution_environment_hash`."""
        raise NotImplementedError

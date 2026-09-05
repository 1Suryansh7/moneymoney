"""Simulator interface (Stage 0 stub — no implementation).

Contract notes: netlists cross this boundary as deterministic `str`
(byte-identical comparisons live in Stage 1); every run carries a
`reproducibility_id` per final_build.md section 14.1. Stage 2 extends the
result shape additively (waveform parsing) without changing this signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulateResult:
    """Minimal Stage 0 run handle: identity + untouched raw simulator bytes."""

    reproducibility_id: str
    raw_output: bytes


class Simulator(ABC):
    """Electrical simulator backend (ngspice via libngspice from Stage 2).

    All quantities crossing this interface are SI base units.
    """

    @abstractmethod
    def simulate(self, *, netlist: str, seed: int) -> SimulateResult:
        """Run `netlist` deterministically under `seed`. SI units inside."""
        raise NotImplementedError

    @abstractmethod
    def simulator_version(self) -> str:
        """Free-form build string feeding `execution_environment_hash`."""
        raise NotImplementedError

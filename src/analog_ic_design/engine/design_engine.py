"""DesignEngine v0.1 API skeleton (Stage 0 — signatures only, no logic).

Versioning rule (final_build.md section 3 addendum): additive changes
(new methods, new OPTIONAL parameters) keep v0.1; any signature or behavior
change to an existing method bumps to v0.2 with a migration note in the same
commit. `ENGINE_API_VERSION` in `analog_ic_design/__init__.py` is the proof.

Conventions frozen here: all parameters keyword-only; all physical values SI
base units (Hz, F, Ohm, V, A, s, m); ids/handles are opaque `str`; every
method raises NotImplementedError until its owning stage lands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping


class DesignEngine(ABC):
    """Single canonical entry point (Law 4: no side doors past this surface)."""

    @abstractmethod
    def create_project(self, *, name: str) -> str:
        """Create a project; returns the project id. (Stage 1 owns storage.)"""
        raise NotImplementedError

    @abstractmethod
    def create_cell(self, *, project_id: str, cell_name: str) -> str:
        """Create a cell in a project; returns the cell id."""
        raise NotImplementedError

    @abstractmethod
    def instantiate(
        self, *, cell_id: str, template_id: str, parameters: Mapping[str, float]
    ) -> str:
        """Instantiate `template_id` in `cell_id`; SI values; returns instance id."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        """Pre-simulation gate (schema/connectivity/units/models); zero bypass."""
        raise NotImplementedError

    @abstractmethod
    def netlist(self, *, cell_id: str) -> str:
        """Compile cell to a deterministic, byte-comparable SPICE netlist."""
        raise NotImplementedError

    @abstractmethod
    def simulate(self, *, netlist: str, seed: int) -> str:
        """Run netlist via the Simulator backend; returns reproducibility id."""
        raise NotImplementedError

    @abstractmethod
    def check_constraints(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        """Evaluate hard constraints; returns (all_pass, violation_messages)."""
        raise NotImplementedError

    @abstractmethod
    def optimize(self, *, cell_id: str, spec_id: str) -> str:
        """Size cell against a spec; returns the optimization job id."""
        raise NotImplementedError

    @abstractmethod
    def run_drc(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """Physical verification via LayoutBackend; returns (clean, markers)."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, *, cell_name: str) -> str:
        """Post-layout extraction handle for the Stage 9 delta loop."""
        raise NotImplementedError

    @abstractmethod
    def compare(self, *, first_id: str, second_id: str, tolerance: float) -> bool:
        """Tolerance-based equivalence (never byte equality on simulator floats)."""
        raise NotImplementedError

"""PDKAdapter interface (Stage 0 stub — no implementation).

Sky130 first; second PDK (Stage 10) exercises whether this abstraction is
genuine. Per Law 2, no model-binding string is authored from memory — the
Stage 1G golden reference quotes the on-disk PDK files this adapter exposes.
All electrical/geometric values are SI base units.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PDKAdapter(ABC):
    """Process-design-kit adapter (model bindings, versions, minima).

    All physical quantities exposed through this adapter are SI base units.
    """

    @abstractmethod
    def pdk_id(self) -> str:
        """Canonical PDK identifier, e.g. "sky130A"."""
        raise NotImplementedError

    @abstractmethod
    def pdk_version(self) -> str:
        """Pinned commit/version string feeding `execution_environment_hash`."""
        raise NotImplementedError

    @abstractmethod
    def validate_model_binding(self, *, model_name: str) -> bool:
        """True iff `model_name` exists in the pinned PDK model cards."""
        raise NotImplementedError

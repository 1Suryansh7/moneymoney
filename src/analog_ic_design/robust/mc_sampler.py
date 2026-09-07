"""Seeded geometric Monte Carlo sampler (Stage 4.5 Commit 4.5B).

Spike verdict (empirical, pinned EDA image, ngspice-47 + sky130A — full
table in `tests/test_mc_spike.py`): setting `mc_mm_switch=1` DOES activate
real mismatch variation (6% run-to-run Id spread), but `setseed` does NOT
make it repeatable — same seed in separate worker processes gives
different draws. ngspice-native MC is therefore unusable under the
platform's reproducibility contract (same seed must give same result).

What ships instead: seeded per-instance geometric perturbation. For each
instance and each of its W/L parameters present, value' = value × (1+ε),
ε ~ N(0, σ) drawn from a per-(seed, sample) stream — order-independent and
bitwise repeatable across worker processes. Sigmas are DECLARED protocol
parameters (relative geometry spread), NOT foundry Pelgrom data: the PDK
supplies corner files + bin models (used for PVT), while this sampler
supplies the repeatable sampling mechanism. `StatisticalProtocol`
records the mechanism string verbatim so no finding is ever mistaken for
foundry mismatch statistics.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PerturbationConfig:
    """Relative geometric spread per W/L parameter (dimensionless sigma)."""

    sigma_w: float = 0.02
    sigma_l: float = 0.02

    def __post_init__(self) -> None:
        for label, value in (("sigma_w", self.sigma_w), ("sigma_l", self.sigma_l)):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 < float(value) < 1.0
            ):
                raise ValueError(
                    f"Schema: {label} must be a finite fraction in (0, 1), got {value!r}"
                )


class MonteCarloSampler:
    """Seeded per-instance W/L perturbation sampler."""

    def __init__(self, *, seed: int, config: PerturbationConfig | None = None) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"Schema: sampler seed must be an int, got {seed!r}")
        self._seed = seed
        self._config = config if config is not None else PerturbationConfig()

    @property
    def seed(self) -> int:
        """Master seed (each sample derives an independent stream)."""
        return self._seed

    @property
    def config(self) -> PerturbationConfig:
        """Declared spread (recorded in the statistical protocol)."""
        return self._config

    def perturb(
        self, params: Mapping[str, Mapping[str, float]], sample_index: int
    ) -> dict[str, dict[str, float]]:
        """Return W/L-perturbed geometry for one MC sample.

        `params` maps instance name to its {parameter: value} dict; only W/L
        keys (any case) are perturbed, everything else passes through
        untouched. Deterministic in (seed, sample_index).
        """
        if isinstance(sample_index, bool) or not isinstance(sample_index, int):
            raise ValueError(f"Schema: sample_index must be an int, got {sample_index!r}")
        if sample_index < 0:
            raise ValueError(f"Schema: sample_index must be >= 0, got {sample_index!r}")
        # One independent stream per (seed, index): an odd multiplier modulo
        # a power of two keeps distinct indices on distinct streams, and the
        # modulo keeps every stream seed non-negative for any integer seed.
        rng = random.Random((self._seed * 1_000_003 + sample_index) % 2**63)
        out: dict[str, dict[str, float]] = {}
        for inst, values in params.items():
            row: dict[str, float] = {}
            for key, value in values.items():
                upper = str(key).upper()
                if upper == "W":
                    row[key] = float(value) * (1.0 + rng.gauss(0.0, self._config.sigma_w))
                elif upper == "L":
                    row[key] = float(value) * (1.0 + rng.gauss(0.0, self._config.sigma_l))
                else:
                    row[key] = float(value)
            out[str(inst)] = row
        return out

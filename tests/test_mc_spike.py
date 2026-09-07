"""Stage 4.5 Commit 4.5B tests: MC spike record + seeded sampler.

Spike record (empirical, pinned EDA image, ngspice-47 + sky130A primitive
NMOS Id deck, `.param mc_mm_switch=1`, Vgs sweep 0.5–1.2 V):

| Run | Seed | Id @Vgs=1.2 (A) | Verdict |
|---|---|---|---|
| mc=0, twice | — | identical | control deterministic |
| mc=1, twice | none | -1.34264e-04 vs -1.25935e-04 | VARIATION ACTIVE (~6%) |
| mc=1, twice | 42, 42 | -1.26061e-04 vs -1.20901e-04 | setseed NOT repeatable |
| mc=1 | 43 vs 42 | differ | seed changes draws, doesn't fix them |

Conclusion: ngspice-native mismatch varies but is unseedable across worker
processes, violating the reproducibility contract. The shipped sampler below
is therefore seeded Python-side perturbation (deterministic by construction);
its tests assert exact repeatability, declared-spread statistics, and
non-geometry passthrough. Base image, zero skips.
"""

from __future__ import annotations

import pytest

from analog_ic_design.robust.mc_sampler import MonteCarloSampler, PerturbationConfig


def test_config_rejects_nonsense() -> None:
    with pytest.raises(ValueError, match="in \\(0, 1\\)"):
        PerturbationConfig(sigma_w=0.0)
    with pytest.raises(ValueError, match="in \\(0, 1\\)"):
        PerturbationConfig(sigma_l=2.0)
    with pytest.raises(ValueError, match="seed must be an int"):
        MonteCarloSampler(seed=True)
    with pytest.raises(ValueError, match="sample_index"):
        MonteCarloSampler(seed=1).perturb({"m1": {"W": 1e-06}}, -1)


def test_perturb_deterministic_per_sample() -> None:
    sampler = MonteCarloSampler(seed=5)
    params = {"m1": {"W": 1e-06, "L": 160e-09, "NFIN": 2.0}, "m2": {"W": 2e-06}}
    first = sampler.perturb(params, 3)
    assert sampler.perturb(params, 3) == first
    assert first["m1"]["NFIN"] == 2.0
    assert first["m1"]["W"] != 1e-06
    assert MonteCarloSampler(seed=5).perturb(params, 4) != first


def test_perturb_statistics_match_declared_spread() -> None:
    sampler = MonteCarloSampler(seed=9, config=PerturbationConfig(sigma_w=0.02, sigma_l=0.02))
    draws = [
        sampler.perturb({"m": {"W": 1e-06}}, index)["m"]["W"] / 1e-06 - 1.0
        for index in range(2000)
    ]
    mean = sum(draws) / len(draws)
    var = sum((d - mean) ** 2 for d in draws) / len(draws)
    assert abs(mean) < 0.005
    assert abs(var**0.5 - 0.02) < 0.005


def test_perturb_leaves_originals_untouched() -> None:
    sampler = MonteCarloSampler(seed=1)
    params = {"m1": {"W": 1e-06}}
    sampler.perturb(params, 0)
    assert params == {"m1": {"W": 1e-06}}

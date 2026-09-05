"""Stage 2 Commit 2E tests: reproducibility identity contract.

Pure functions, runnable everywhere: determinism, per-field sensitivity,
netlist normalization, and tolerance-as-policy (never identity).
"""

from __future__ import annotations

from typing import Any

from analog_ic_design.sim.reproduce import (
    COMPARISON_POLICY_ID,
    canonical_encode,
    design_identity_hash,
    execution_environment_hash,
    normalize_netlist,
    reproducibility_id,
    waveforms_close,
)

NETLIST = "* cell x\nMm1 a b c d TEST_Model W=2e-06\n.end\n"
CONFIG = {"analysis": "tran", "tstop": 30e-9}


def _env(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "simulator": "ngspice-47",
        "pdk_version": "fd_pr@abc",
        "model_hashes": {"sky130.lib.spice": "00"},
        "container": "img@sha256:11",
        "backends": {"klayout": "0.30.12"},
        "measurement_version": "m0",
    }
    base.update(over)
    return base


def test_design_identity_deterministic_and_sensitive() -> None:
    first = design_identity_hash(netlist=NETLIST, sim_config=CONFIG)
    assert first == design_identity_hash(netlist=NETLIST, sim_config=CONFIG)
    assert len(first) == 64
    assert design_identity_hash(netlist=NETLIST + "* c\n", sim_config=CONFIG) != first
    assert design_identity_hash(netlist=NETLIST, sim_config={}) != first


def test_normalization_ignores_whitespace_noise() -> None:
    noisy = "\n\n* cell x   \nMm1 a b c d TEST_Model W=2e-06  \n.end\n\n"
    assert normalize_netlist(noisy) == NETLIST
    assert design_identity_hash(netlist=noisy, sim_config=CONFIG) == design_identity_hash(
        netlist=NETLIST, sim_config=CONFIG
    )


def test_environment_hash_moves_with_any_component() -> None:
    first = execution_environment_hash(**_env())
    assert first == execution_environment_hash(**_env())
    assert execution_environment_hash(**_env(simulator="ngspice-48")) != first
    assert execution_environment_hash(**_env(container="img@sha256:22")) != first


def test_reproducibility_binds_all_four() -> None:
    design = design_identity_hash(netlist=NETLIST, sim_config=CONFIG)
    env = execution_environment_hash(**_env())
    first = reproducibility_id(design=design, environment=env, seed=7, analysis={"tstop": 1.0})
    again = reproducibility_id(design=design, environment=env, seed=7, analysis={"tstop": 1.0})
    other_seed = reproducibility_id(design=design, environment=env, seed=8, analysis={"tstop": 1.0})
    other_design = reproducibility_id(design="other", environment=env, seed=7, analysis={})
    assert first == again
    assert other_seed != first
    assert other_design != first


def test_tolerance_is_policy_not_identity() -> None:
    assert COMPARISON_POLICY_ID == "tolerance-v1"
    assert waveforms_close([1.0, 2.0], [1.0, 2.0])
    assert waveforms_close([1.0], [1.001])
    assert not waveforms_close([1.0], [1.1])
    assert not waveforms_close([1.0, 2.0], [1.0])
    assert waveforms_close([], [])


def test_canonical_encode_is_stable() -> None:
    assert canonical_encode({"b": 1, "a": [1, 2]}) == b'{"a":[1,2],"b":1}'

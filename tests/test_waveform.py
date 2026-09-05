"""Stage 2 Commit 2F tests: transient waveform parsing.

Pure-function tests over hand-built `RawSim` payloads — runnable everywhere,
zero skips by construction. A live end-to-end (lib → parse) assertion lands
in 2H with the inverter.
"""

from __future__ import annotations

import pytest

from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.sim.waveform import Trace, Waveform, parse_transient
from analog_ic_design.units.quantity import Ampere, Second, Volt


def _raw(**vectors: list[float]) -> RawSim:
    return RawSim(vectors=dict(vectors), log="")


def test_typed_waveform() -> None:
    wave = parse_transient(_raw(time=[0.0, 1e-9], out=[0.0, 1.8], **{"v1#branch": [0.0, 1e-3]}))
    assert isinstance(wave, Waveform)
    assert all(isinstance(t, Second) for t in wave.time)
    out = wave.trace("out")
    assert isinstance(out, Trace)
    assert all(isinstance(v, Volt) for v in out.values)
    assert all(isinstance(v, Ampere) for v in wave.trace("v1#branch").values)
    assert [float(v) for v in out.values] == [0.0, 1.8]


def test_missing_time_rejected() -> None:
    with pytest.raises(SimError, match="no 'time' vector"):
        parse_transient(_raw(out=[0.0]))


def test_empty_and_ragged_rejected() -> None:
    with pytest.raises(SimError):
        parse_transient(_raw(time=[]))
    with pytest.raises(SimError, match="ragged"):
        parse_transient(_raw(time=[0.0, 1.0], out=[0.0]))


def test_non_finite_samples_fail_closed() -> None:
    with pytest.raises(SimError, match="non-finite"):
        parse_transient(_raw(time=[0.0, 1.0], out=[0.0, float("inf")]))
    with pytest.raises(SimError, match="non-finite"):
        parse_transient(_raw(time=[0.0, float("nan")], out=[0.0, 1.0]))


def test_unknown_trace_raises_key_error() -> None:
    wave = parse_transient(_raw(time=[0.0], out=[0.0]))
    with pytest.raises(KeyError):
        wave.trace("nope")

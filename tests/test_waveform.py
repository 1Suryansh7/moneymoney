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


def test_transient_rejects_complex_data() -> None:
    raw = RawSim(
        vectors={"time": [0.0, 1.0], "out": [0.0, 1.0]},
        complex_vectors={"out": [0.0 + 0.0j, 1.0 + 0.0j]},
        log="",
    )
    with pytest.raises(SimError, match="complex data passed to parse_transient"):
        parse_transient(raw)


def test_typed_ac_waveform() -> None:
    from analog_ic_design.sim.waveform import ACTrace, ACWaveform, parse_ac
    from analog_ic_design.units.quantity import Hertz

    raw = RawSim(
        vectors={"frequency": [1.0, 10.0, 100.0]},
        complex_vectors={
            "out": [1.0 + 0.0j, 0.0 + 1.0j, 1.0 + 1.0j],
            "frequency": [1.0 + 0.0j, 10.0 + 0.0j, 100.0 + 0.0j],
        },
        log="",
    )
    ac = parse_ac(raw)
    assert isinstance(ac, ACWaveform)
    assert all(isinstance(f, Hertz) for f in ac.frequency)
    assert [float(f) for f in ac.frequency] == [1.0, 10.0, 100.0]

    tr = ac.trace("out")
    assert isinstance(tr, ACTrace)
    assert tr.name == "out"
    assert tr.real() == (1.0, 0.0, 1.0)
    assert tr.imag() == (0.0, 1.0, 1.0)

    # Magnitude
    mag = tr.magnitude()
    assert abs(mag[0] - 1.0) < 1e-9
    assert abs(mag[1] - 1.0) < 1e-9
    assert abs(mag[2] - 2.0**0.5) < 1e-9

    # Magnitude in dB
    db = tr.magnitude_db()
    assert abs(db[0] - 0.0) < 1e-6
    assert abs(db[1] - 0.0) < 1e-6
    assert abs(db[2] - 3.01029995) < 1e-5

    # Phase in degrees
    deg = tr.phase_deg()
    assert abs(deg[0] - 0.0) < 1e-6
    assert abs(deg[1] - 90.0) < 1e-6
    assert abs(deg[2] - 45.0) < 1e-6


def test_ac_missing_frequency_rejected() -> None:
    from analog_ic_design.sim.waveform import parse_ac

    raw = RawSim(complex_vectors={"out": [1.0 + 0j]})
    with pytest.raises(SimError, match="no 'frequency' vector"):
        parse_ac(raw)


def test_ac_empty_and_ragged_rejected() -> None:
    from analog_ic_design.sim.waveform import parse_ac

    with pytest.raises(SimError, match="empty frequency vector"):
        parse_ac(RawSim(vectors={"frequency": []}))
    with pytest.raises(SimError, match="ragged"):
        parse_ac(
            RawSim(
                vectors={"frequency": [1.0, 10.0]},
                complex_vectors={"out": [1.0 + 0j]},
            )
        )


def test_ac_non_finite_and_negative_frequency() -> None:
    from analog_ic_design.sim.waveform import parse_ac

    with pytest.raises(SimError, match="non-finite frequency"):
        parse_ac(RawSim(vectors={"frequency": [1.0, float("nan")]}))
    with pytest.raises(SimError, match="negative frequency"):
        parse_ac(RawSim(vectors={"frequency": [-1.0, 10.0]}))


def test_ac_non_finite_sample_fails_closed() -> None:
    from analog_ic_design.sim.waveform import parse_ac

    with pytest.raises(SimError, match="non-finite sample"):
        parse_ac(
            RawSim(
                vectors={"frequency": [1.0, 10.0]},
                complex_vectors={"out": [1.0 + 0j, float("nan") + 1j]},
            )
        )


def test_ac_unknown_trace_raises_key_error() -> None:
    from analog_ic_design.sim.waveform import parse_ac

    ac = parse_ac(RawSim(vectors={"frequency": [1.0]}, complex_vectors={"out": [1.0 + 0j]}))
    with pytest.raises(KeyError):
        ac.trace("nope")

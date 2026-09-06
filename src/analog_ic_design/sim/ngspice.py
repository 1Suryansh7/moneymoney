"""libngspice ctypes binding (Stage 2 Commit 2C).

Every signature below is grounded in `/usr/local/include/ngspice/sharedspice.h`
(pinned EDA image): ngSpice_Init (384), ngSpice_Command (403), ngGet_Vec_Info
(407), ngSpice_Circ (465), CurPlot/AllPlots/AllVecs (470/476/482); structs
vecvalues (185), vecvaluesall (193), vecinfo (200), vecinfoall (210);
callbacks SendChar (247), SendStat (254), ControlledExit (261), SendData
(270), SendInitData (279); NG_BOOL is C bool (171, hence c_bool).

Design: one `run_deck` call = Init-once-per-process + Circ + foreground
`run`, collecting vectors through the SendData callback (never by poking
ngspice's internal dvec layout). CDLL handles are cached per process and
never unloaded (matches the 2D worker model: one sim per process).
Complex data is fail-closed (AC support is Stage 3+ scope).

Hardening rule (ADR-021): ERROR-path C calls (rejected Circ, failed `run`)
corrupt libngspice process-global state and segfault LATER in-process runs
in the same process (observed 2026-09-06). Production and EDA-test
execution of failing decks therefore belongs in worker processes (2D),
never in a long-lived process; `run_deck` fail-closes in pure Python
wherever it can (empty/dead decks, no-analysis decks) before touching C.
"""

from __future__ import annotations

import ctypes
import re
from ctypes import (
    CFUNCTYPE,
    POINTER,
    c_bool,
    c_char_p,
    c_double,
    c_int,
    c_void_p,
)
from dataclasses import dataclass, field
from typing import Any


class SimError(ValueError):
    """Simulation cannot run or produced no data. Taxonomy: load/init and
    environment problems -> `schema`; deck problems -> `netlist`; run/data
    problems -> `spice_convergence`. The message always states the trigger.
    Run-phase errors additionally carry the ngspice log tail, so a failure
    never discards the only diagnostic the simulator produced."""


#: Cap on log text attached to an error (full log stays on `RawSim.log`).
_LOG_TAIL_CHARS = 2000

#: SPICE analysis cards. A deck without one makes `run` a no-op that leaves
#: libngspice's process-global state corrupt enough to segfault a LATER
#: in-process `run` (observed 2026-09-06: full-suite segfault in the test
#: after a no-analysis deck ran). Fail closed before touching the C API.
_ANALYSIS_RE = re.compile(r"\.(tran|dc|ac|op|pz|tf|noise|sens|disto|four|fft)\b", re.IGNORECASE)


def _has_analysis(lines: list[str]) -> bool:
    """True iff the deck defines at least one analysis card outside comments
    and `.control` blocks (whose dotless commands are not analyses)."""
    in_control = False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("*", "#", "$")):
            continue
        low = line.lower()
        if low == ".control":
            in_control = True
            continue
        if low == ".endc":
            in_control = False
            continue
        if not in_control and _ANALYSIS_RE.search(line):
            return True
    return False


def _fail(message: str, log: list[str]) -> SimError:
    """Build a run-phase `SimError` with the ngspice log tail attached."""
    tail = "".join(log)[-_LOG_TAIL_CHARS:]
    return SimError(f"{message}\n--- ngspice log (tail) ---\n{tail or '(empty log)'}")


class _VecValues(ctypes.Structure):
    _fields_ = [
        ("name", c_char_p),
        ("creal", c_double),
        ("cimag", c_double),
        ("is_scale", c_bool),
        ("is_complex", c_bool),
    ]


class _VecValuesAll(ctypes.Structure):
    _fields_ = [("veccount", c_int), ("vecindex", c_int), ("vecsa", POINTER(POINTER(_VecValues)))]


class _VecInfo(ctypes.Structure):
    _fields_ = [
        ("number", c_int),
        ("vecname", c_char_p),
        ("is_real", c_bool),
        ("pdvec", c_void_p),
        ("pdvecscale", c_void_p),
    ]


class _VecInfoAll(ctypes.Structure):
    _fields_ = [
        ("name", c_char_p),
        ("title", c_char_p),
        ("date", c_char_p),
        ("type", c_char_p),
        ("veccount", c_int),
        ("vecs", POINTER(POINTER(_VecInfo))),
    ]


_SendChar = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
_SendStat = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
_ControlledExit = CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
_SendData = CFUNCTYPE(c_int, POINTER(_VecValuesAll), c_int, c_int, c_void_p)
_SendInitData = CFUNCTYPE(c_int, POINTER(_VecInfoAll), c_int, c_void_p)

_DEFAULT_LIB = "libngspice.so"
_HANDLES: dict[str, ctypes.CDLL] = {}
_INITIALIZED: set[str] = set()


@dataclass
class RawSim:
    """Raw run outcome: vector name -> samples, plus the ngspice log."""

    vectors: dict[str, list[float]] = field(default_factory=dict)
    complex_vectors: dict[str, list[complex]] = field(default_factory=dict)
    log: str = ""


def libngspice_available(lib_path: str = _DEFAULT_LIB) -> bool:
    """True iff the shared library loads (False on `base`, which lacks it)."""
    try:
        ctypes.CDLL(lib_path)
    except OSError:
        return False
    return True


def _load(lib_path: str) -> ctypes.CDLL:
    if lib_path not in _HANDLES:
        try:
            _HANDLES[lib_path] = ctypes.CDLL(lib_path)
        except OSError as exc:
            raise SimError(f"Schema: cannot load {lib_path!r}: {exc}") from exc
    return _HANDLES[lib_path]


def run_deck(*, lib_path: str = _DEFAULT_LIB, lines: list[str]) -> RawSim:
    """Load `lines` into libngspice and run them synchronously."""
    lib = _load(lib_path)
    if not _has_analysis(lines):
        raise SimError(
            "Netlist: deck defines no analysis "
            "(.tran/.dc/.ac/.op/.pz/.tf/.noise/.sens/.disto/.four/.fft) "
            "— nothing for ngspice to run"
        )
    lib.ngSpice_Init.restype = c_int
    lib.ngSpice_Command.restype = c_int
    lib.ngSpice_Command.argtypes = [c_char_p]
    lib.ngSpice_Circ.restype = c_int

    state: dict[str, object] = {
        "log": [],
        "data": {},
        "complex_data": {},
        "complex": False,
        "aborted": "",
    }
    log: list[str] = state["log"]  # type: ignore[assignment]
    data: dict[str, list[float]] = state["data"]  # type: ignore[assignment]
    complex_data: dict[str, list[complex]] = state["complex_data"]  # type: ignore[assignment]

    def on_char(msg: bytes | None, _id: int, _ud: object) -> int:
        log.append((msg or b"").decode("utf-8", "replace"))
        return 0

    def on_stat(_msg: bytes | None, _id: int, _ud: object) -> int:
        return 0

    def on_exit(status: int, _unload: bool, quit: bool, _id: int, _ud: object) -> int:
        if status != 0 or quit:
            state["aborted"] = f"ngspice exited abnormally (status={status}, quit={quit})"
        return 0

    def on_init(_info: object, _n: int, _ud: object) -> int:
        return 0

    def on_data(allv: Any, _count: int, _id: int, _ud: object) -> int:
        vals = ctypes.cast(allv, POINTER(_VecValuesAll)).contents
        for i in range(vals.veccount):
            vec = vals.vecsa[i].contents
            name = (vec.name or b"").decode("utf-8", "replace")
            if vec.is_complex:
                state["complex"] = True
                complex_data.setdefault(name, []).append(
                    complex(float(vec.creal), float(vec.cimag))
                )
            data.setdefault(name, []).append(float(vec.creal))
        return 0

    cbs = (
        _SendChar(on_char),
        _SendStat(on_stat),
        _ControlledExit(on_exit),
        _SendData(on_data),
        _SendInitData(on_init),
    )
    if lib_path not in _INITIALIZED:
        code = int(lib.ngSpice_Init(cbs[0], cbs[1], cbs[2], cbs[3], cbs[4], None, None))
        if code != 0:
            raise SimError(f"Schema: ngSpice_Init failed with code {code}")
        _INITIALIZED.add(lib_path)
    int(lib.ngSpice_Command(b"removecirc"))  # best-effort reset; ignored if absent
    arr = (c_char_p * (len(lines) + 1))(*[ln.encode("utf-8") for ln in lines], None)
    if int(lib.ngSpice_Circ(arr)) != 0:
        raise _fail("Netlist: ngspice rejected the deck (ngSpice_Circ nonzero)", log)
    if int(lib.ngSpice_Command(b"run")) != 0:
        raise _fail("SPICE convergence: ngspice 'run' command failed", log)
    _ = cbs
    if state["aborted"]:
        raise _fail(f"SPICE convergence: {state['aborted']}", log)
    if not data and not complex_data:
        raise _fail("SPICE convergence: run produced no vectors", log)
    return RawSim(vectors=data, complex_vectors=complex_data, log="".join(log))

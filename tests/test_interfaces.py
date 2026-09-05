"""Stage 0 Commit 2 tests: backend interface contract.

Asserts the Law 4 architecture: backends are abstract (no direct
construction), every method is fully annotated, the SI unit system is
documented, and every method raises NotImplementedError.
Failure taxonomy: Schema.
"""

from __future__ import annotations

import inspect
from typing import Any, cast

import pytest

from analog_ic_design.interfaces.layout_backend import (
    LayoutBackend,
    VerificationReport,
)
from analog_ic_design.interfaces.pdk_adapter import PDKAdapter
from analog_ic_design.interfaces.simulator import SimulateResult, Simulator

_ABCS: tuple[type, ...] = (Simulator, LayoutBackend, PDKAdapter)


class _Sim(Simulator):
    def simulate(self, *, netlist: str, seed: int) -> SimulateResult:
        raise NotImplementedError

    def simulator_version(self) -> str:
        raise NotImplementedError


class _Lay(LayoutBackend):
    def run_drc(self, *, cell_name: str) -> VerificationReport:
        raise NotImplementedError

    def backend_version(self) -> str:
        raise NotImplementedError


class _Pdk(PDKAdapter):
    def pdk_id(self) -> str:
        raise NotImplementedError

    def pdk_version(self) -> str:
        raise NotImplementedError

    def validate_model_binding(self, *, model_name: str) -> bool:
        raise NotImplementedError


def test_backends_are_abstract() -> None:
    for cls in _ABCS:
        assert inspect.isabstract(cls), f"Schema: {cls.__name__} is not abstract"
        with pytest.raises(TypeError):
            cast(Any, cls)()


def test_backend_methods_raise_not_implemented() -> None:
    # Call the abstract stub bodies directly through the base classes, so the
    # test proves the STUBS raise — not just the test doubles.
    sim = _Sim()
    with pytest.raises(NotImplementedError):
        Simulator.simulate(sim, netlist="*", seed=0)
    with pytest.raises(NotImplementedError):
        Simulator.simulator_version(sim)
    lay = _Lay()
    with pytest.raises(NotImplementedError):
        LayoutBackend.run_drc(lay, cell_name="x")
    with pytest.raises(NotImplementedError):
        LayoutBackend.backend_version(lay)
    pdk = _Pdk()
    with pytest.raises(NotImplementedError):
        PDKAdapter.pdk_id(pdk)
    with pytest.raises(NotImplementedError):
        PDKAdapter.pdk_version(pdk)
    with pytest.raises(NotImplementedError):
        PDKAdapter.validate_model_binding(pdk, model_name="sky130_fd_pr__nfet_01v8")


def test_backend_methods_fully_annotated_with_si_documented() -> None:
    for cls in _ABCS:
        documented = "SI" in (cls.__doc__ or "")
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            sig = inspect.signature(member)
            for param in sig.parameters.values():
                if param.name == "self":
                    continue
                assert param.annotation is not inspect.Parameter.empty, (
                    f"Schema: {cls.__name__}.{name} param '{param.name}' untyped"
                )
            assert sig.return_annotation is not inspect.Signature.empty, (
                f"Schema: {cls.__name__}.{name} return untyped"
            )
            assert documented or "SI" in (member.__doc__ or ""), (
                f"Schema: {cls.__name__} documents no SI unit system"
            )

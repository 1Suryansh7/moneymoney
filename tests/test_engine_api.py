"""Stage 0 Commit 2 tests: DesignEngine v0.1 skeleton contract.

Freezes the 11 method names, keyword-only SI-typed signatures, the
NotImplementedError behavior, and ENGINE_API_VERSION == "0.1".
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping

import pytest

from analog_ic_design import ENGINE_API_VERSION
from analog_ic_design.engine.design_engine import DesignEngine

METHODS: tuple[str, ...] = (
    "create_project",
    "create_cell",
    "instantiate",
    "validate",
    "netlist",
    "simulate",
    "check_constraints",
    "optimize",
    "run_drc",
    "extract",
    "compare",
)


class _Concrete(DesignEngine):
    def create_project(self, *, name: str) -> str:
        raise NotImplementedError

    def create_cell(self, *, project_id: str, cell_name: str) -> str:
        raise NotImplementedError

    def instantiate(
        self, *, cell_id: str, template_id: str, parameters: Mapping[str, float]
    ) -> str:
        raise NotImplementedError

    def validate(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        raise NotImplementedError

    def netlist(self, *, cell_id: str) -> str:
        raise NotImplementedError

    def simulate(self, *, netlist: str, seed: int) -> str:
        raise NotImplementedError

    def check_constraints(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        raise NotImplementedError

    def optimize(self, *, cell_id: str, spec_id: str) -> str:
        raise NotImplementedError

    def run_drc(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        raise NotImplementedError

    def extract(self, *, cell_name: str) -> str:
        raise NotImplementedError

    def compare(self, *, first_id: str, second_id: str, tolerance: float) -> bool:
        raise NotImplementedError


def test_engine_api_version_is_v0_1() -> None:
    assert ENGINE_API_VERSION == "0.1"


def test_engine_exposes_exactly_the_eleven_contract_methods() -> None:
    names = {n for n, _ in inspect.getmembers(DesignEngine, predicate=inspect.isfunction)}
    assert names == set(METHODS), (
        "Schema: DesignEngine surface changed. If intentional, bump ENGINE_API_VERSION "
        f"with a migration note (diff={names ^ set(METHODS)})"
    )


def test_engine_methods_keyword_only_typed_and_not_implemented() -> None:
    engine = _Concrete()
    for name in METHODS:
        member = getattr(engine, name)
        sig = inspect.signature(member)
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            assert param.kind is inspect.Parameter.KEYWORD_ONLY, (
                f"Schema: DesignEngine.{name} param '{param.name}' not keyword-only"
            )
            assert param.annotation is not inspect.Parameter.empty, (
                f"Schema: DesignEngine.{name} param '{param.name}' untyped"
            )
        assert sig.return_annotation is not inspect.Signature.empty, (
            f"Schema: DesignEngine.{name} return untyped"
        )
        # Invoke the abstract stub body via the base class: proves the STUB
        # raises, not just the test double.
        stub = getattr(DesignEngine, name)
        with pytest.raises(NotImplementedError):
            stub(engine, **{p: _dummy(sig.parameters[p]) for p in sig.parameters if p != "self"})


def _dummy(param: inspect.Parameter) -> object:
    annotation = str(param.annotation)
    if "Mapping" in annotation:
        return {}
    if "bool" in annotation:
        return True
    if "int" in annotation:
        return 0
    if "float" in annotation:
        return 0.0
    return "id"

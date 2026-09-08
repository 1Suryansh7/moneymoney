"""Canonical Analog IC Topology Template Library (Stage 6 Commit 6A).

Defines the six foundational analog building blocks per master-build-plan §4:
1. current_mirror: Simple/cascode NMOS current mirror
2. diff_pair: Differential input pair with active PMOS mirror load and tail source
3. common_source: Common-source amplifier with active PMOS load
4. cascode: Telescopic cascode amplifier stage
5. folded_cascode: Folded cascode operational amplifier
6. two_stage_miller: Two-stage operational amplifier with Miller compensation

Strict physical units: all internal parameters must be SI base units (meters,
Farads, Ohms). Non-numeric, string, or negative parameters are rejected.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final

from analog_ic_design.store.schema import new_id

STAMP: Final = "2026-09-08T00:00:00+00:00"
NMOS_MODEL: Final = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL: Final = "sky130_fd_pr__pfet_01v8"
CAP_MODEL: Final = "cap_subckt"
RES_MODEL: Final = "res_subckt"
MOS_PIN_ORDER: Final = "d g s b"
PASSIVE_PIN_ORDER: Final = "p n"


@dataclass(frozen=True)
class TemplateTradeoffs:
    """Documented analog trade-offs for topology intelligence and AI context."""

    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    typical_voltage_gain_db: str
    bandwidth_capability: str
    output_swing: str


class TopologyTemplate(ABC):
    """Abstract base class for canonical analog circuit topology templates."""

    @property
    @abstractmethod
    def template_id(self) -> str:
        """Unique machine-readable identifier for the template."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable presentation name."""

    @property
    @abstractmethod
    def default_parameters(self) -> dict[str, float]:
        """Default sizing parameters strictly in SI base units."""

    @property
    @abstractmethod
    def ports(self) -> tuple[str, ...]:
        """Declared external pin names."""

    @property
    @abstractmethod
    def tradeoffs(self) -> TemplateTradeoffs:
        """Engineering trade-offs and capability profile."""

    def validate_parameters(self, params: dict[str, float]) -> dict[str, float]:
        """Validate and merge user parameters against defaults in SI units."""
        merged = dict(self.default_parameters)
        for key, val in params.items():
            if key not in merged:
                raise ValueError(
                    f"Schema: unknown parameter {key!r} for template {self.template_id}"
                )
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    f"Units: parameter {key!r} must be a numeric SI value, got {val!r}"
                )
            if val <= 0:
                raise ValueError(f"Units: parameter {key!r} must be positive, got {val!r}")
            merged[key] = float(val)
        return merged

    @abstractmethod
    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        """Instantiate template into SQLite relational IR; returns cell_id."""


def _setup_tech_and_bindings(conn: sqlite3.Connection, project_id: str) -> dict[str, str]:
    """Create technology and model bindings for NMOS, PMOS, and passives."""
    tech_id = new_id()
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)",
        (tech_id, project_id, "sky130A", "fd_pr@403964dc/open_pdks@1689ac3f", STAMP),
    )
    bindings = [
        ("nfet_01v8", NMOS_MODEL, MOS_PIN_ORDER, "subckt"),
        ("pfet_01v8", PMOS_MODEL, MOS_PIN_ORDER, "subckt"),
        ("cap_subckt", CAP_MODEL, PASSIVE_PIN_ORDER, "subckt"),
        ("res_subckt", RES_MODEL, PASSIVE_PIN_ORDER, "subckt"),
    ]
    for sym, model, pin_order, kind in bindings:
        conn.execute(
            "INSERT INTO model_binding"
            " (id, technology_id, device_symbol, model_name, pin_order, kind, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id(), tech_id, sym, model, pin_order, kind, STAMP),
        )
    return {"tech_id": tech_id}


def _setup_symbols(conn: sqlite3.Connection, lib_id: str) -> dict[str, str]:
    """Create symbol records in library; returns mapping from symbol name to symbol_id."""
    syms: dict[str, str] = {}
    for name in ("nfet_01v8", "pfet_01v8", "cap_subckt", "res_subckt"):
        cell_id = new_id()
        sym_id = new_id()
        conn.execute(
            "INSERT INTO cell VALUES (?, ?, ?, ?)", (cell_id, lib_id, f"{name}_cell", STAMP)
        )
        conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (sym_id, cell_id, name, STAMP))
        syms[name] = sym_id
    return syms


class CurrentMirrorTemplate(TopologyTemplate):
    """NMOS simple current mirror template."""

    @property
    def template_id(self) -> str:
        return "current_mirror"

    @property
    def display_name(self) -> str:
        return "NMOS Current Mirror"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {"w": 1.0e-06, "l": 0.5e-06, "m": 1.0}

    @property
    def ports(self) -> tuple[str, ...]:
        return ("in_ref", "out_mirror", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=("Simple layout", "Wide compliance range", "Low component count"),
            weaknesses=("Moderate output impedance", "Channel-length modulation mismatch"),
            typical_voltage_gain_db="N/A",
            bandwidth_capability="High",
            output_swing="Limited by Vds,sat",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        m1, m2 = new_id(), new_id()
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m1, cell, syms["nfet_01v8"], "m1", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m2, cell, syms["nfet_01v8"], "m2", STAMP),
        )

        nets = {name: new_id() for name in self.ports}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            (m1, "d", "in_ref"),
            (m1, "g", "in_ref"),
            (m1, "s", "vss"),
            (m1, "b", "vss"),
            (m2, "d", "out_mirror"),
            (m2, "g", "in_ref"),
            (m2, "s", "vss"),
            (m2, "b", "vss"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        for iid, mult in ((m1, 1.0), (m2, p["m"])):
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)",
                (new_id(), iid, "W", p["w"] * mult, STAMP),
            )
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "L", p["l"], STAMP)
            )
        return cell


class DiffPairTemplate(TopologyTemplate):
    """Differential pair with active current mirror PMOS load."""

    @property
    def template_id(self) -> str:
        return "diff_pair"

    @property
    def display_name(self) -> str:
        return "Differential Pair with Active Load"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {
            "w_in": 2.0e-06,
            "l_in": 0.5e-06,
            "w_load": 2.0e-06,
            "l_load": 0.5e-06,
            "w_tail": 2.0e-06,
            "l_tail": 0.5e-06,
        }

    @property
    def ports(self) -> tuple[str, ...]:
        return ("vip", "vin", "outp", "outn", "vbias", "vdd", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=("Common-mode rejection", "Differential input", "Low offset"),
            weaknesses=("Limited voltage gain per stage", "Tail voltage headroom required"),
            typical_voltage_gain_db="20-35 dB",
            bandwidth_capability="High (>100 MHz)",
            output_swing="Moderate",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        m1, m2, m3, m4, m5 = (new_id() for _ in range(5))
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m1, cell, syms["nfet_01v8"], "m1", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m2, cell, syms["nfet_01v8"], "m2", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m3, cell, syms["pfet_01v8"], "m3", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m4, cell, syms["pfet_01v8"], "m4", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m5, cell, syms["nfet_01v8"], "m5", STAMP),
        )

        net_names = list(self.ports) + ["tail"]
        nets = {name: new_id() for name in net_names}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            (m1, "d", "outp"),
            (m1, "g", "vip"),
            (m1, "s", "tail"),
            (m1, "b", "vss"),
            (m2, "d", "outn"),
            (m2, "g", "vin"),
            (m2, "s", "tail"),
            (m2, "b", "vss"),
            (m3, "d", "outp"),
            (m3, "g", "outp"),
            (m3, "s", "vdd"),
            (m3, "b", "vdd"),
            (m4, "d", "outn"),
            (m4, "g", "outp"),
            (m4, "s", "vdd"),
            (m4, "b", "vdd"),
            (m5, "d", "tail"),
            (m5, "g", "vbias"),
            (m5, "s", "vss"),
            (m5, "b", "vss"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        param_tuples = (
            (m1, p["w_in"], p["l_in"]),
            (m2, p["w_in"], p["l_in"]),
            (m3, p["w_load"], p["l_load"]),
            (m4, p["w_load"], p["l_load"]),
            (m5, p["w_tail"], p["l_tail"]),
        )
        for iid, w_val, l_val in param_tuples:
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "W", w_val, STAMP)
            )
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "L", l_val, STAMP)
            )
        return cell


class CommonSourceTemplate(TopologyTemplate):
    """Common-source amplifier with active PMOS current source load."""

    @property
    def template_id(self) -> str:
        return "common_source"

    @property
    def display_name(self) -> str:
        return "Common-Source Amplifier"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {"w_n": 1.0e-06, "l_n": 0.18e-06, "w_p": 2.0e-06, "l_p": 0.18e-06}

    @property
    def ports(self) -> tuple[str, ...]:
        return ("in", "out", "vbias", "vdd", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=("Wide output swing", "Simple structure", "Compact silicon area"),
            weaknesses=("Moderate gain (15-25 dB)", "Miller capacitance on input"),
            typical_voltage_gain_db="15-25 dB",
            bandwidth_capability="High (>50 MHz)",
            output_swing="Near rail-to-rail (Vdd - 2*Vds,sat)",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        mn, mp = new_id(), new_id()
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (mn, cell, syms["nfet_01v8"], "m1", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (mp, cell, syms["pfet_01v8"], "m2", STAMP),
        )

        nets = {name: new_id() for name in self.ports}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            (mn, "d", "out"),
            (mn, "g", "in"),
            (mn, "s", "vss"),
            (mn, "b", "vss"),
            (mp, "d", "out"),
            (mp, "g", "vbias"),
            (mp, "s", "vdd"),
            (mp, "b", "vdd"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), mn, "W", p["w_n"], STAMP)
        )
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), mn, "L", p["l_n"], STAMP)
        )
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), mp, "W", p["w_p"], STAMP)
        )
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), mp, "L", p["l_p"], STAMP)
        )
        return cell


class CascodeTemplate(TopologyTemplate):
    """Telescopic cascode amplifier stage with cascode PMOS load."""

    @property
    def template_id(self) -> str:
        return "cascode"

    @property
    def display_name(self) -> str:
        return "Telescopic Cascode Amplifier"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {
            "w_in": 2.0e-06,
            "l_in": 0.5e-06,
            "w_casc": 2.0e-06,
            "l_casc": 0.5e-06,
            "w_load": 4.0e-06,
            "l_load": 0.5e-06,
        }

    @property
    def ports(self) -> tuple[str, ...]:
        return ("in", "out", "vbias_n", "vbias_p1", "vbias_p2", "vdd", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=(
                "High intrinsic gain (>40-55 dB)",
                "High output impedance",
                "Low Miller feedback",
            ),
            weaknesses=("Severely reduced output voltage swing", "Multiple bias voltages needed"),
            typical_voltage_gain_db="40-55 dB",
            bandwidth_capability="Moderate",
            output_swing="Poor (Vdd - 4*Vds,sat)",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        m1, m2, m3, m4 = (new_id() for _ in range(4))
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m1, cell, syms["nfet_01v8"], "m1", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m2, cell, syms["nfet_01v8"], "m2", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m3, cell, syms["pfet_01v8"], "m3", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m4, cell, syms["pfet_01v8"], "m4", STAMP),
        )

        net_names = list(self.ports) + ["n_int_n", "n_int_p"]
        nets = {name: new_id() for name in net_names}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            (m1, "d", "n_int_n"),
            (m1, "g", "in"),
            (m1, "s", "vss"),
            (m1, "b", "vss"),
            (m2, "d", "out"),
            (m2, "g", "vbias_n"),
            (m2, "s", "n_int_n"),
            (m2, "b", "vss"),
            (m3, "d", "out"),
            (m3, "g", "vbias_p1"),
            (m3, "s", "n_int_p"),
            (m3, "b", "vdd"),
            (m4, "d", "n_int_p"),
            (m4, "g", "vbias_p2"),
            (m4, "s", "vdd"),
            (m4, "b", "vdd"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        for iid, w_val, l_val in (
            (m1, p["w_in"], p["l_in"]),
            (m2, p["w_casc"], p["l_casc"]),
            (m3, p["w_load"], p["l_load"]),
            (m4, p["w_load"], p["l_load"]),
        ):
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "W", w_val, STAMP)
            )
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "L", l_val, STAMP)
            )
        return cell


class FoldedCascodeTemplate(TopologyTemplate):
    """Folded cascode operational amplifier template."""

    @property
    def template_id(self) -> str:
        return "folded_cascode"

    @property
    def display_name(self) -> str:
        return "Folded Cascode Operational Amplifier"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {
            "w_in": 5.0e-06,
            "l_in": 0.5e-06,
            "w_tail": 5.0e-06,
            "l_tail": 0.5e-06,
            "w_casc_n": 3.0e-06,
            "l_casc_n": 0.5e-06,
            "w_load_p": 6.0e-06,
            "l_load_p": 0.5e-06,
        }

    @property
    def ports(self) -> tuple[str, ...]:
        return ("vip", "vin", "out", "vbias_tail", "vbias_n1", "vbias_n2", "vbias_p", "vdd", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=(
                "Wide input common-mode range (includes Vss)",
                "High gain",
                "Self-compensating with Cload",
            ),
            weaknesses=("Higher power dissipation", "More bias references"),
            typical_voltage_gain_db="50-65 dB",
            bandwidth_capability="High",
            output_swing="Moderate (Vdd - 4*Vds,sat)",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        # M1/M2 PMOS input pair, M0 PMOS tail, M3/M4 NMOS current sinks,
        # M5/M6 NMOS cascodes, M7/M8 PMOS cascode active load
        inst_ids = {
            name: new_id() for name in ("m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8")
        }
        for name in ("m0", "m1", "m2", "m7", "m8"):
            conn.execute(
                "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
                (inst_ids[name], cell, syms["pfet_01v8"], name, STAMP),
            )
        for name in ("m3", "m4", "m5", "m6"):
            conn.execute(
                "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
                (inst_ids[name], cell, syms["nfet_01v8"], name, STAMP),
            )

        internals = ["tail", "fold_p", "fold_n", "casc_mirror"]
        net_names = list(self.ports) + internals
        nets = {name: new_id() for name in net_names}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            (inst_ids["m0"], "d", "tail"),
            (inst_ids["m0"], "g", "vbias_tail"),
            (inst_ids["m0"], "s", "vdd"),
            (inst_ids["m0"], "b", "vdd"),
            (inst_ids["m1"], "d", "fold_p"),
            (inst_ids["m1"], "g", "vip"),
            (inst_ids["m1"], "s", "tail"),
            (inst_ids["m1"], "b", "vdd"),
            (inst_ids["m2"], "d", "fold_n"),
            (inst_ids["m2"], "g", "vin"),
            (inst_ids["m2"], "s", "tail"),
            (inst_ids["m2"], "b", "vdd"),
            (inst_ids["m3"], "d", "fold_p"),
            (inst_ids["m3"], "g", "vbias_n1"),
            (inst_ids["m3"], "s", "vss"),
            (inst_ids["m3"], "b", "vss"),
            (inst_ids["m4"], "d", "fold_n"),
            (inst_ids["m4"], "g", "vbias_n1"),
            (inst_ids["m4"], "s", "vss"),
            (inst_ids["m4"], "b", "vss"),
            (inst_ids["m5"], "d", "casc_mirror"),
            (inst_ids["m5"], "g", "vbias_n2"),
            (inst_ids["m5"], "s", "fold_p"),
            (inst_ids["m5"], "b", "vss"),
            (inst_ids["m6"], "d", "out"),
            (inst_ids["m6"], "g", "vbias_n2"),
            (inst_ids["m6"], "s", "fold_n"),
            (inst_ids["m6"], "b", "vss"),
            (inst_ids["m7"], "d", "casc_mirror"),
            (inst_ids["m7"], "g", "vbias_p"),
            (inst_ids["m7"], "s", "vdd"),
            (inst_ids["m7"], "b", "vdd"),
            (inst_ids["m8"], "d", "out"),
            (inst_ids["m8"], "g", "vbias_p"),
            (inst_ids["m8"], "s", "vdd"),
            (inst_ids["m8"], "b", "vdd"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        param_assignments = (
            (inst_ids["m0"], p["w_tail"], p["l_tail"]),
            (inst_ids["m1"], p["w_in"], p["l_in"]),
            (inst_ids["m2"], p["w_in"], p["l_in"]),
            (inst_ids["m3"], p["w_casc_n"], p["l_casc_n"]),
            (inst_ids["m4"], p["w_casc_n"], p["l_casc_n"]),
            (inst_ids["m5"], p["w_casc_n"], p["l_casc_n"]),
            (inst_ids["m6"], p["w_casc_n"], p["l_casc_n"]),
            (inst_ids["m7"], p["w_load_p"], p["l_load_p"]),
            (inst_ids["m8"], p["w_load_p"], p["l_load_p"]),
        )
        for iid, w_val, l_val in param_assignments:
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "W", w_val, STAMP)
            )
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "L", l_val, STAMP)
            )
        return cell


class TwoStageMillerTemplate(TopologyTemplate):
    """Two-stage operational amplifier with Miller compensation."""

    @property
    def template_id(self) -> str:
        return "two_stage_miller"

    @property
    def display_name(self) -> str:
        return "Two-Stage Miller Operational Amplifier"

    @property
    def default_parameters(self) -> dict[str, float]:
        return {
            "w_in": 5.0e-06,
            "l_in": 0.5e-06,
            "w_load": 5.0e-06,
            "l_load": 0.5e-06,
            "w_tail": 5.0e-06,
            "l_tail": 0.5e-06,
            "w_out": 20.0e-06,
            "l_out": 0.5e-06,
            "w_load2": 10.0e-06,
            "l_load2": 0.5e-06,
            "cc": 1.0e-12,
            "rz": 1000.0,
        }

    @property
    def ports(self) -> tuple[str, ...]:
        return ("vip", "vin", "out", "vbias1", "vbias2", "vdd", "vss")

    @property
    def tradeoffs(self) -> TemplateTradeoffs:
        return TemplateTradeoffs(
            strengths=(
                "Very high DC gain (>60 dB)",
                "Wide output voltage swing",
                "Independent stage optimization",
            ),
            weaknesses=(
                "Right-half-plane zero",
                "Requires frequency compensation capacitor (Cc, Rz)",
            ),
            typical_voltage_gain_db="60-80 dB",
            bandwidth_capability="High (20-100 MHz UGB)",
            output_swing="Large (Rail-to-rail minus 2*Vds,sat)",
        )

    def instantiate(
        self,
        conn: sqlite3.Connection,
        params: dict[str, float],
        cell_name: str,
        project_name: str = "topology_project",
    ) -> str:
        p = self.validate_parameters(params)
        pid, lib, cell = new_id(), new_id(), new_id()
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
        conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
        conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, cell_name, STAMP))
        _setup_tech_and_bindings(conn, pid)
        syms = _setup_symbols(conn, lib)

        # Stage 1: M1, M2 (NMOS input pair), M3, M4 (PMOS mirror load), M5 (NMOS tail)
        # Stage 2: M6 (PMOS driver), M7 (NMOS active load)
        # Compensation: Cc, Rz
        m1, m2, m3, m4, m5 = (new_id() for _ in range(5))
        m6, m7 = new_id(), new_id()
        cc_inst, rz_inst = new_id(), new_id()

        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m1, cell, syms["nfet_01v8"], "m1", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m2, cell, syms["nfet_01v8"], "m2", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m3, cell, syms["pfet_01v8"], "m3", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m4, cell, syms["pfet_01v8"], "m4", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m5, cell, syms["nfet_01v8"], "m5", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m6, cell, syms["pfet_01v8"], "m6", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (m7, cell, syms["nfet_01v8"], "m7", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (cc_inst, cell, syms["cap_subckt"], "cc", STAMP),
        )
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (rz_inst, cell, syms["res_subckt"], "rz", STAMP),
        )

        internals = ["tail", "n_d1", "out1", "n_comp"]
        net_names = list(self.ports) + internals
        nets = {name: new_id() for name in net_names}
        for name, nid in nets.items():
            conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

        hooks = (
            # Stage 1 diff pair
            (m1, "d", "n_d1"),
            (m1, "g", "vip"),
            (m1, "s", "tail"),
            (m1, "b", "vss"),
            (m2, "d", "out1"),
            (m2, "g", "vin"),
            (m2, "s", "tail"),
            (m2, "b", "vss"),
            (m3, "d", "n_d1"),
            (m3, "g", "n_d1"),
            (m3, "s", "vdd"),
            (m3, "b", "vdd"),
            (m4, "d", "out1"),
            (m4, "g", "n_d1"),
            (m4, "s", "vdd"),
            (m4, "b", "vdd"),
            (m5, "d", "tail"),
            (m5, "g", "vbias1"),
            (m5, "s", "vss"),
            (m5, "b", "vss"),
            # Stage 2 common-source driver
            (m6, "d", "out"),
            (m6, "g", "out1"),
            (m6, "s", "vdd"),
            (m6, "b", "vdd"),
            (m7, "d", "out"),
            (m7, "g", "vbias2"),
            (m7, "s", "vss"),
            (m7, "b", "vss"),
            # Miller compensation path: out1 -> Cc -> n_comp -> Rz -> out
            (cc_inst, "p", "out1"),
            (cc_inst, "n", "n_comp"),
            (rz_inst, "p", "n_comp"),
            (rz_inst, "n", "out"),
        )
        for iid, term, net in hooks:
            conn.execute(
                "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
                (new_id(), iid, nets[net], term, STAMP),
            )

        param_assignments = (
            (m1, "W", p["w_in"]),
            (m1, "L", p["l_in"]),
            (m2, "W", p["w_in"]),
            (m2, "L", p["l_in"]),
            (m3, "W", p["w_load"]),
            (m3, "L", p["l_load"]),
            (m4, "W", p["w_load"]),
            (m4, "L", p["l_load"]),
            (m5, "W", p["w_tail"]),
            (m5, "L", p["l_tail"]),
            (m6, "W", p["w_out"]),
            (m6, "L", p["l_out"]),
            (m7, "W", p["w_load2"]),
            (m7, "L", p["l_load2"]),
            (cc_inst, "c", p["cc"]),
            (rz_inst, "r", p["rz"]),
        )
        for iid, pname, pval in param_assignments:
            conn.execute(
                "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pval, STAMP)
            )
        return cell


REGISTERED_TEMPLATES: Final[dict[str, TopologyTemplate]] = {
    "current_mirror": CurrentMirrorTemplate(),
    "diff_pair": DiffPairTemplate(),
    "common_source": CommonSourceTemplate(),
    "cascode": CascodeTemplate(),
    "folded_cascode": FoldedCascodeTemplate(),
    "two_stage_miller": TwoStageMillerTemplate(),
}


def get_template(template_id: str) -> TopologyTemplate:
    """Retrieve registered TopologyTemplate by ID."""
    if template_id not in REGISTERED_TEMPLATES:
        raise ValueError(f"Schema: unknown template_id {template_id!r}")
    return REGISTERED_TEMPLATES[template_id]


def list_templates() -> list[str]:
    """Return sorted list of all available topology template IDs."""
    return sorted(REGISTERED_TEMPLATES.keys())


def instantiate_template(
    conn: sqlite3.Connection,
    template_id: str,
    params: dict[str, float] | None = None,
    cell_name: str | None = None,
    project_name: str = "topology_project",
) -> str:
    """Convenience helper to instantiate any registered template into SQLite."""
    template = get_template(template_id)
    cname = cell_name or f"{template_id}_cell"
    p = params or {}
    return template.instantiate(conn, p, cname, project_name=project_name)

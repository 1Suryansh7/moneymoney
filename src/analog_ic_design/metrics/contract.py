"""MetricContract definitions & canonical 7-metric matrix (Stage 3 Commit 3A).

Law: Every metric is governed by an explicit contract defining semantics,
required analysis, stimulus, formula, sign convention, and SI units BEFORE
any measurement function or optimizer uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class MetricContract:
    """Canonical specification of how a metric is legally defined and measured."""

    metric_id: str
    name: str
    definition: str
    required_analysis: str  # "dc", "ac", "tran", "op"
    required_testbench: str
    stimulus: str
    observed_nodes: tuple[str, ...]
    formula_description: str
    sign_convention: str
    units: str  # SI base unit or pure ratio symbol: "V/V", "Hz", "deg", "V/s", "W", "V", "s"
    reference_condition: str
    crossing_rule: str | None
    invalid_data_behavior: str
    comparison_policy: str
    golden_fixture_id: str


# Canonical 7-Metric Matrix per master plan §14.2 & final_prompt.md §Stage 3
DC_GAIN: Final = MetricContract(
    metric_id="dc_gain",
    name="DC Voltage Gain",
    definition="Small-signal transfer voltage slope at DC operating point: dV(out)/dV(in).",
    required_analysis="dc",
    required_testbench="dc_transfer",
    stimulus="DC voltage sweep across high-gain transition region",
    observed_nodes=("in", "out"),
    formula_description="Maximum absolute numerical derivative |dV(out)/dV(in)| in active region.",
    sign_convention="Magnitude (positive float V/V); transfer slope sign preserved in record.",
    units="V/V",
    reference_condition="At maximum slope / mid-rail bias Vout = VDD / 2",
    crossing_rule=None,
    invalid_data_behavior="fail closed with SimError if transition not found or non-monotonic",
    comparison_policy="rel_tol=0.05",
    golden_fixture_id="cs_amp_nmos",
)

AC_GAIN: Final = MetricContract(
    metric_id="ac_gain",
    name="Low-Frequency AC Gain",
    definition="Small-signal open-loop voltage gain at lowest frequency decade: |V(out)/V(in)|.",
    required_analysis="ac",
    required_testbench="ac_small_signal",
    stimulus="AC 1.0 V small-signal input with DC operating point bias",
    observed_nodes=("in", "out"),
    formula_description="|V(out)| / |V(in)| at minimum frequency decade (f = f_min).",
    sign_convention="Magnitude (positive float V/V)",
    units="V/V",
    reference_condition="f = f_min (low-frequency plateau before dominant pole roll-off)",
    crossing_rule=None,
    invalid_data_behavior="fail closed with SimError if AC vectors empty or non-finite",
    comparison_policy="rel_tol=0.05",
    golden_fixture_id="cs_amp_nmos",
)

BANDWIDTH: Final = MetricContract(
    metric_id="bandwidth",
    name="Unity-Gain Bandwidth",
    definition="Frequency where open-loop AC gain crosses 0 dB (unity gain |A| = 1.0 V/V).",
    required_analysis="ac",
    required_testbench="ac_frequency_sweep",
    stimulus="AC 1.0 V decade frequency sweep (1 Hz to 10 GHz)",
    observed_nodes=("in", "out"),
    formula_description="Frequency f_ugb where 20*log10(|V(out)/V(in)|) = 0 dB via interpolation.",
    sign_convention="Positive frequency in Hertz (Hz)",
    units="Hz",
    reference_condition="0 dB crossing of open-loop transfer function",
    crossing_rule="first downward crossing through 1.0 V/V (0 dB)",
    invalid_data_behavior="fail closed if gain never reaches unity or starts below 0 dB",
    comparison_policy="rel_tol=0.10",
    golden_fixture_id="cs_amp_nmos",
)

PHASE_MARGIN: Final = MetricContract(
    metric_id="phase_margin",
    name="Phase Margin",
    definition="180° minus unwrapped lag from the DC phasor to unity gain (signed).",
    required_analysis="ac",
    required_testbench="closed_loop_return_ratio",
    stimulus="Middlebrook / Tian loop injection AC source in feedback network",
    observed_nodes=("loop_inj_p", "loop_inj_n"),
    formula_description="PM = 180 - (unwrap[0] - unwrap[f_ugb]); unwrap-first, never across ±180°.",
    sign_convention="Signed deg: >=45 STABLE, 0-45 MARGINAL, <0 UNSTABLE (never clamped).",
    units="deg",
    reference_condition="At unity-gain frequency of loop return ratio T",
    crossing_rule="loop gain magnitude |T| = 1.0 downward crossing",
    invalid_data_behavior="fail closed if loop gain does not cross 0 dB or injection invalid",
    comparison_policy="abs_tol=5.0",
    golden_fixture_id="diff_amp_closed_loop",
)

SLEW_RATE: Final = MetricContract(
    metric_id="slew_rate",
    name="Slew Rate",
    definition="Maximum rate of change of output voltage under large-signal step excitation.",
    required_analysis="tran",
    required_testbench="large_signal_step",
    stimulus="Full-swing rail-to-rail voltage step with sub-10ps edge time",
    observed_nodes=("in", "out"),
    formula_description="(V(t2) - V(t1)) / (t2 - t1) between 20% and 80% of total step.",
    sign_convention="Positive float in Volts per second (V/s) for both rising and falling slews.",
    units="V/s",
    reference_condition="20% to 80% output transition window",
    crossing_rule="linear interpolation between threshold crossings",
    invalid_data_behavior="fail closed if output does not reach 80% threshold",
    comparison_policy="rel_tol=0.10",
    golden_fixture_id="inverter_step_response",
)

POWER: Final = MetricContract(
    metric_id="power",
    name="Average Static/Dynamic Power",
    definition="Time-averaged product of supply voltage and supply current: VDD * I_avg(VDD).",
    required_analysis="tran",
    required_testbench="periodic_transient",
    stimulus="Continuous periodic excitation or static DC bias",
    observed_nodes=("vdd",),
    formula_description="VDD * (1/T_window) * integral(I(VDD), t_start, t_end).",
    sign_convention="Positive power dissipated (current drawn from positive supply into circuit).",
    units="W",
    reference_condition="Full integer number of periods during steady-state window",
    crossing_rule=None,
    invalid_data_behavior="fail closed if window is zero or supply current non-finite",
    comparison_policy="rel_tol=0.05",
    golden_fixture_id="inverter_transient_power",
)

OFFSET: Final = MetricContract(
    metric_id="offset",
    name="Input-Referred Offset Voltage",
    definition="Differential input voltage required to force differential output to zero.",
    required_analysis="dc",
    required_testbench="differential_dc_sweep",
    stimulus="Differential input DC sweep around common-mode operating point",
    observed_nodes=("inp", "inn", "outp", "outn"),
    formula_description="V(inp) - V(inn) at the point where V(outp) - V(outn) = 0.",
    sign_convention="Signed differential voltage in Volts (V)",
    units="V",
    reference_condition="Nominal DC with declared common-mode input voltage",
    crossing_rule="zero crossing of differential output voltage",
    invalid_data_behavior="fail closed if output never crosses zero within sweep range",
    comparison_policy="abs_tol=1e-3",
    golden_fixture_id="diff_pair_nmos",
)

SETTLING_TIME: Final = MetricContract(
    metric_id="settling_time",
    name="Settling Time",
    definition="Time from step until output enters and permanently stays within error band.",
    required_analysis="tran",
    required_testbench="closed_loop_step",
    stimulus="Step voltage input at t=t0",
    observed_nodes=("in", "out"),
    formula_description=(
        "t_settle - t0, where t_settle is last time |V(out, t) - V_final| > band * |V_step|."
    ),
    sign_convention="Positive elapsed time in Seconds (s)",
    units="s",
    reference_condition="1% error band around steady-state final value V_final",
    crossing_rule="staying condition: output must not leave error band after t_settle",
    invalid_data_behavior="fail closed if output never settles or window ends outside band",
    comparison_policy="rel_tol=0.10",
    golden_fixture_id="closed_loop_amp_step",
)

CANONICAL_METRICS: Final[tuple[MetricContract, ...]] = (
    DC_GAIN,
    AC_GAIN,
    BANDWIDTH,
    PHASE_MARGIN,
    SLEW_RATE,
    POWER,
    OFFSET,
    SETTLING_TIME,
)

METRIC_BY_ID: Final[dict[str, MetricContract]] = {
    m.metric_id: m for m in CANONICAL_METRICS
}

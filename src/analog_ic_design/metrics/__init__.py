"""Measurement & Specification Engine: MetricContracts and extraction."""

from __future__ import annotations

from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.contract import (
    AC_GAIN,
    BANDWIDTH,
    CANONICAL_METRICS,
    DC_GAIN,
    METRIC_BY_ID,
    OFFSET,
    PHASE_MARGIN,
    POWER,
    SETTLING_TIME,
    SLEW_RATE,
    MetricContract,
)
from analog_ic_design.metrics.gain import (
    extract_ac_gain,
    extract_ac_gain_db,
    extract_dc_gain,
)
from analog_ic_design.metrics.offset import extract_offset
from analog_ic_design.metrics.phase_margin import extract_phase_margin
from analog_ic_design.metrics.power import extract_power
from analog_ic_design.metrics.settling_time import extract_settling_time
from analog_ic_design.metrics.slew_rate import (
    extract_falling_slew_rate,
    extract_rising_slew_rate,
    extract_slew_rate,
)

__all__ = [
    "AC_GAIN",
    "BANDWIDTH",
    "CANONICAL_METRICS",
    "DC_GAIN",
    "METRIC_BY_ID",
    "MetricContract",
    "OFFSET",
    "PHASE_MARGIN",
    "POWER",
    "SETTLING_TIME",
    "SLEW_RATE",
    "extract_ac_gain",
    "extract_ac_gain_db",
    "extract_bandwidth",
    "extract_dc_gain",
    "extract_falling_slew_rate",
    "extract_offset",
    "extract_phase_margin",
    "extract_power",
    "extract_rising_slew_rate",
    "extract_settling_time",
    "extract_slew_rate",
]


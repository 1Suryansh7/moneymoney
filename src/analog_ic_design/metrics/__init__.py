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
from analog_ic_design.metrics.phase_margin import extract_phase_margin

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
    "extract_phase_margin",
]

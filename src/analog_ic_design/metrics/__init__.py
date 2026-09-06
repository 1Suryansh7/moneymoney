"""Measurement & Specification Engine: MetricContracts and extraction."""

from __future__ import annotations

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
]

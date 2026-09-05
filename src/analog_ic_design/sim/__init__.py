"""Simulation kernel: libngspice binding (2C), runner (2D), identity (2E)."""

from analog_ic_design.sim.backend import NgspiceBackend
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available, run_deck

__all__ = ["NgspiceBackend", "RawSim", "SimError", "libngspice_available", "run_deck"]

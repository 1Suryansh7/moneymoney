"""Open-source AI-native analog IC design platform.

Stage 0: packaging + API contract skeleton only. No simulation, schema, or
measurement logic exists yet. All physical quantities in this package are SI
base units (F, Ohm, Hz, V, A, s, m, K) once Stage 1 lands; see
`analog_ic_design.units` (intentionally empty until Stage 1 Commit 1A).
"""

from typing import Final

__version__: Final = "0.0.0"
ENGINE_API_VERSION: Final = "0.1"

__all__ = ["ENGINE_API_VERSION", "__version__"]

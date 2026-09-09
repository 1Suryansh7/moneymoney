"""HTTP API service surface (Stage 7B).

Routes call `EngineV01` exclusively (Law 4 mirror); no simulator, store,
or schema imports in route code — enforced by the architecture boundary
test. Only engine-implemented methods get routes; deferred engine methods
get no endpoint until they stop raising.
"""

from analog_ic_design.api.server import create_app

__all__ = ["create_app"]

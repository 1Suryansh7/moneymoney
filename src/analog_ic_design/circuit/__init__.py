"""Circuit domain: connectivity (1C), canonicalization (1D), compiler (1E)."""

from analog_ic_design.circuit.canonical import (
    CanonicalCell,
    CanonicalDevice,
    CanonicalTerminal,
    canonical_encode,
    canonical_hash,
    canonicalize,
)
from analog_ic_design.circuit.compiler import CompilerError, compile_netlist
from analog_ic_design.circuit.graph import (
    ConnectivityGraph,
    GraphError,
    NetNode,
    PortRef,
    build_graph,
)
from analog_ic_design.circuit.validator import (
    ValidationError,
    ValidationReport,
    Violation,
    record_errors,
    validate,
)

__all__ = [
    "CanonicalCell",
    "CanonicalDevice",
    "CanonicalTerminal",
    "CompilerError",
    "ConnectivityGraph",
    "GraphError",
    "NetNode",
    "PortRef",
    "ValidationError",
    "ValidationReport",
    "Violation",
    "build_graph",
    "canonical_encode",
    "canonical_hash",
    "canonicalize",
    "compile_netlist",
    "record_errors",
    "validate",
]

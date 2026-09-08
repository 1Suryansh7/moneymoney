"""Topology Intelligence Package (Stage 6).

Provides canonical topology templates, design knowledge base linkages,
multi-criteria retrieval engine, and candidate circuit IR.
"""

from __future__ import annotations

from analog_ic_design.topology.templates import (
    REGISTERED_TEMPLATES,
    CascodeTemplate,
    CommonSourceTemplate,
    CurrentMirrorTemplate,
    DiffPairTemplate,
    FoldedCascodeTemplate,
    TemplateTradeoffs,
    TopologyTemplate,
    TwoStageMillerTemplate,
    get_template,
    instantiate_template,
    list_templates,
)

__all__ = [
    "REGISTERED_TEMPLATES",
    "CascodeTemplate",
    "CommonSourceTemplate",
    "CurrentMirrorTemplate",
    "DiffPairTemplate",
    "FoldedCascodeTemplate",
    "TemplateTradeoffs",
    "TopologyTemplate",
    "TwoStageMillerTemplate",
    "get_template",
    "instantiate_template",
    "list_templates",
]

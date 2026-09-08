"""Topology Intelligence Package (Stage 6).

Provides canonical topology templates, design knowledge base linkages,
multi-criteria retrieval engine, and candidate circuit IR.
"""

from __future__ import annotations

from analog_ic_design.topology.knowledge_base import (
    TemplateCapabilities,
    get_template_experiments,
    query_template_capabilities,
    record_template_experiment,
)
from analog_ic_design.topology.retriever import (
    ScoredCandidate,
    TargetSpec,
    retrieve_best_sizing,
    retrieve_candidate_topologies,
)
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
    "ScoredCandidate",
    "TargetSpec",
    "TemplateCapabilities",
    "TemplateTradeoffs",
    "TopologyTemplate",
    "TwoStageMillerTemplate",
    "get_template",
    "get_template_experiments",
    "instantiate_template",
    "list_templates",
    "query_template_capabilities",
    "record_template_experiment",
    "retrieve_best_sizing",
    "retrieve_candidate_topologies",
]

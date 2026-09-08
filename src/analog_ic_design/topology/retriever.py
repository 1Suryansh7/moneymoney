"""Multi-Criteria Topology Retrieval Engine (Stage 6 Commit 6B / AI-03).

Ranks topology candidates using composite scoring:
- Target specification similarity
- Topology structural compatibility
- Historical PVT yield and validated outcomes
- Hard penalty for failed trials (anti-patterns)

Retrieves both positive supporting experiments and known failure modes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from analog_ic_design.topology.knowledge_base import (
    get_template_experiments,
    query_template_capabilities,
)
from analog_ic_design.topology.templates import REGISTERED_TEMPLATES, get_template


@dataclass(frozen=True)
class TargetSpec:
    """Target analog design requirements in SI base units."""

    gain_v_v: float | None = None          # Voltage gain in V/V (e.g. 1000.0 for 60 dB)
    gain_db: float | None = None           # Optional convenience in dB
    bandwidth_hz: float | None = None      # Unity-gain bandwidth in Hz (e.g. 40e6)
    max_power_w: float | None = None       # Maximum quiescent power in Watts
    is_differential: bool = False          # Requires differential input pair
    is_mirror: bool = False                # Requires current mirroring


@dataclass(frozen=True)
class ScoredCandidate:
    """Evaluated topology candidate with composite score and evidence links."""

    template_id: str
    composite_score: float
    spec_similarity: float
    topology_compat: float
    robust_yield: float
    failure_penalty: float
    suggested_parameters: dict[str, float]
    evidence_ids: tuple[str, ...]
    failure_ids: tuple[str, ...]
    reasoning: str


def _eval_spec_similarity(
    template_id: str, target: TargetSpec, max_obs_gain: float | None
) -> float:
    """Calculate similarity between target specification and topology capability."""
    target_gain = target.gain_v_v
    if target_gain is None and target.gain_db is not None:
        target_gain = 10.0 ** (target.gain_db / 20.0)

    score = 0.5  # Neutral default

    # Gain capability matching
    if target_gain is not None:
        if target_gain > 500.0:  # >54 dB
            if template_id in ("two_stage_miller", "folded_cascode"):
                score = 0.95
            elif template_id == "cascode":
                score = 0.75
            elif template_id in ("diff_pair", "common_source"):
                score = 0.20
            else:
                score = 0.05
        elif target_gain > 50.0:  # 34-54 dB
            if template_id in ("diff_pair", "cascode"):
                score = 0.90
            elif template_id in ("two_stage_miller", "folded_cascode"):
                score = 0.80
            elif template_id == "common_source":
                score = 0.50
            else:
                score = 0.10
        else:  # Low gain (<34 dB)
            if template_id in ("common_source", "diff_pair"):
                score = 0.90
            else:
                score = 0.60

    # If historical data exists, adjust score by observed maximum capability
    if max_obs_gain is not None and target_gain is not None:
        if max_obs_gain >= target_gain * 0.9:
            score = min(1.0, score + 0.1)
        else:
            score = max(0.0, score - 0.2)

    return score


def _eval_topology_compat(template_id: str, target: TargetSpec) -> float:
    """Calculate structural architectural compatibility with the requirement."""
    t = get_template(template_id)
    has_diff_inputs = "vip" in t.ports and "vin" in t.ports

    if target.is_mirror:
        return 1.0 if template_id == "current_mirror" else 0.05

    if target.is_differential:
        if not has_diff_inputs:
            return 0.0  # Incompatible: cannot satisfy differential input
        return 1.0

    # Single-ended or general requirement
    if template_id == "current_mirror":
        return 0.1
    return 0.8


def retrieve_candidate_topologies(
    conn: sqlite3.Connection,
    target: TargetSpec,
    *,
    w_spec: float = 0.35,
    w_topo: float = 0.30,
    w_pvt: float = 0.20,
    w_fail: float = 0.15,
) -> list[ScoredCandidate]:
    """Retrieve and rank canonical topology templates using multi-criteria scoring.

    Adversarial guarantee: penalized heavily if historical trials failed.
    """
    candidates: list[ScoredCandidate] = []

    for tid in sorted(REGISTERED_TEMPLATES.keys()):
        template = get_template(tid)
        caps = query_template_capabilities(conn, tid)
        experiments = get_template_experiments(conn, tid)

        # Multi-criteria scoring components
        s_spec = _eval_spec_similarity(tid, target, caps.max_gain)
        s_topo = _eval_topology_compat(tid, target)
        s_pvt = caps.yield_rate if caps.total_trials > 0 else 0.5

        success_trials = [e for e in experiments if e["status"] == "succeeded"]
        failed_trials = [e for e in experiments if e["status"] == "failed"]

        # Failure penalty: fraction of failed trials plus penalty if last trial failed
        p_fail = 0.0
        if caps.total_trials > 0:
            p_fail = len(failed_trials) / float(caps.total_trials)
            if experiments and experiments[-1]["status"] == "failed":
                p_fail = min(1.0, p_fail + 0.3)

        composite = (w_spec * s_spec) + (w_topo * s_topo) + (w_pvt * s_pvt) - (w_fail * p_fail)

        # Suggested sizing parameters: prefer winning historical trial, else defaults
        suggested_params = dict(template.default_parameters)
        evidence_ids: list[str] = []
        if success_trials:
            best_trial = success_trials[-1]
            if isinstance(best_trial["parameters"], dict):
                suggested_params.update(best_trial["parameters"])
            evidence_ids.append(str(best_trial["id"]))

        failure_ids = tuple(str(f["id"]) for f in failed_trials[-3:])

        reasoning = (
            f"Composite score {composite:.3f} (Spec={s_spec:.2f}, Topo={s_topo:.2f}, "
            f"PVT_Yield={s_pvt:.2f}, Fail_Pen={p_fail:.2f}). "
            f"Typical gain: {template.tradeoffs.typical_voltage_gain_db}."
        )

        candidates.append(
            ScoredCandidate(
                template_id=tid,
                composite_score=composite,
                spec_similarity=s_spec,
                topology_compat=s_topo,
                robust_yield=s_pvt,
                failure_penalty=p_fail,
                suggested_parameters=suggested_params,
                evidence_ids=tuple(evidence_ids),
                failure_ids=failure_ids,
                reasoning=reasoning,
            )
        )

    candidates.sort(key=lambda c: c.composite_score, reverse=True)
    return candidates


def retrieve_best_sizing(
    conn: sqlite3.Connection,
    template_id: str,
    target_metric: dict[str, float] | None = None,
) -> tuple[dict[str, float], tuple[str, ...]]:
    """Retrieve optimal sizing parameters for a chosen template based on history.

    Adversarial protection: NEVER copies parameters from a failed experiment,
    even if that experiment's parameters had highest nominal target match.
    """
    template = get_template(template_id)
    experiments = get_template_experiments(conn, template_id)
    if not experiments:
        return dict(template.default_parameters), ()

    successes = [e for e in experiments if e["status"] == "succeeded"]
    if not successes:
        return dict(template.default_parameters), ()

    # Score each successful trial against target metric if provided
    best_exp = successes[0]
    best_dist = float("inf")
    for s in successes:
        metrics = s["metrics"]
        if not isinstance(metrics, dict) or target_metric is None:
            best_exp = s
            continue
        dist = 0.0
        for k, target_val in target_metric.items():
            if k in metrics and isinstance(metrics[k], (int, float)):
                dist += (float(metrics[k]) - float(target_val)) ** 2
        if dist < best_dist:
            best_dist = dist
            best_exp = s

    params = dict(template.default_parameters)
    if isinstance(best_exp["parameters"], dict):
        params.update(best_exp["parameters"])
    return params, (str(best_exp["id"]),)

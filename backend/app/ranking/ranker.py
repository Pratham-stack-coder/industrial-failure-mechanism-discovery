"""
Mechanism Ranking Module
========================
Ranks candidate mechanism hypotheses using a multi-factor transparent scoring function.

Scoring factors (configurable weights):
  1. temporal_consistency  — do precursor events occur in the right temporal order?
  2. evidence_strength     — average strength of supporting evidence items
  3. evidence_coverage     — fraction of expected evidence items actually found
  4. recurrence            — does this pattern appear in historical failures?
  5. mechanism_plausibility — physics/domain plausibility score
  6. contradiction_penalty  — deducts score for strong contradicting evidence

All scores are in [0, 1]. Overall score = weighted sum - contradiction penalty.

Baseline comparison:
  - CorrelationRankingBaseline: ranks mechanisms by simple parameter correlation strength
  - AnomalyScoreBaseline: ranks by anomaly count (no mechanism attribution)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from app.mechanisms.discovery import CandidateMechanismHypothesis, EvidenceItem
from app.core.config import settings


# ============================================================
# Mechanism plausibility priors
# ============================================================

# Physics/domain plausibility priors for mechanism types
# Based on typical industrial failure statistics (not data-driven for this parameter)
MECHANISM_PLAUSIBILITY = {
    "wear": 0.85,
    "thermal": 0.80,
    "contamination": 0.75,
    "process_drift": 0.80,
    "mechanical": 0.70,
    "chemical": 0.65,
    "electrical": 0.60,
    "material_defect": 0.70,
    "operator_error": 0.55,
    "environmental": 0.60,
    "composite": 0.50,
    "unknown": 0.30,
}


# ============================================================
# Scoring functions
# ============================================================

def score_temporal_consistency(
    hypothesis: CandidateMechanismHypothesis,
    expected_max_lag_hours: float = 72.0,
) -> float:
    """
    Score how well the temporal ordering of evidence matches expectations.

    Higher score if:
    - Precursor events have lag_hours > 0 (they occurred BEFORE failure)
    - Evidence items are ordered consistently (earlier causes precede later effects)
    - No evidence is post-failure (negative lags would be contradictory)

    Returns score in [0, 1].
    """
    supporting = hypothesis.supporting_evidence
    if not supporting:
        return 0.0

    lags = [ev.lag_hours for ev in supporting if ev.lag_hours is not None]
    if not lags:
        return 0.3  # evidence exists but no temporal info

    # All valid evidence should have lag >= 0 (occurred before failure)
    valid_lags = [l for l in lags if l >= 0]
    invalid_lags = [l for l in lags if l < 0]

    # Fraction with correct temporal direction
    direction_score = len(valid_lags) / len(lags)

    # Prefer evidence clustered within expected window
    if valid_lags:
        mean_lag = np.mean(valid_lags)
        window_score = max(0.0, 1.0 - mean_lag / (expected_max_lag_hours * 2.0))
    else:
        window_score = 0.0

    # Bonus: ordered temporal chain (multiple distinct lags in sequence)
    if len(set(round(l) for l in valid_lags)) >= 2:
        chain_bonus = 0.2
    else:
        chain_bonus = 0.0

    score = direction_score * 0.5 + window_score * 0.4 + chain_bonus * 0.1
    return min(1.0, float(score))


def score_evidence_strength(
    hypothesis: CandidateMechanismHypothesis,
) -> float:
    """
    Compute average strength of supporting evidence items.
    Penalized if very few items.

    Returns score in [0, 1].
    """
    supporting = hypothesis.supporting_evidence
    if not supporting:
        return 0.0

    strengths = [ev.strength for ev in supporting]
    mean_strength = float(np.mean(strengths))

    # Penalize if only one piece of evidence
    count_multiplier = min(1.0, len(supporting) / 3.0)

    return float(mean_strength * (0.6 + 0.4 * count_multiplier))


def score_evidence_coverage(
    hypothesis: CandidateMechanismHypothesis,
) -> float:
    """
    Score how many expected evidence items were actually found.

    Coverage = found_evidence / (found_evidence + missing_evidence)

    Returns score in [0, 1].
    """
    n_supporting = len(hypothesis.supporting_evidence)
    n_missing = len(hypothesis.missing_evidence)
    total = n_supporting + n_missing

    if total == 0:
        return 0.5  # neutral when we can't determine

    return float(n_supporting / total)


def score_recurrence(
    hypothesis: CandidateMechanismHypothesis,
    historical_mechanisms: Optional[List[str]] = None,
) -> float:
    """
    Score mechanism by how often similar patterns appeared historically.

    Args:
        hypothesis: the candidate hypothesis
        historical_mechanisms: list of mechanism type strings from past investigations

    Returns score in [0, 1].
    """
    if not historical_mechanisms:
        return 0.3  # baseline when no historical data

    matching = sum(
        1 for m in historical_mechanisms
        if m == hypothesis.mechanism_type
    )
    total = len(historical_mechanisms)
    recurrence_rate = matching / total

    # Prefer recurring but not universal (would be noise)
    if recurrence_rate > 0.7:
        score = 0.6  # too common
    elif recurrence_rate > 0.2:
        score = 0.8  # good match
    elif recurrence_rate > 0.05:
        score = 0.5
    else:
        score = 0.2  # rare

    return float(score)


def score_mechanism_plausibility(
    hypothesis: CandidateMechanismHypothesis,
) -> float:
    """Return domain plausibility prior for the mechanism type."""
    return MECHANISM_PLAUSIBILITY.get(hypothesis.mechanism_type, 0.4)


def compute_contradiction_penalty(
    hypothesis: CandidateMechanismHypothesis,
) -> float:
    """
    Compute penalty for contradicting evidence.

    Penalty formula: sum(strength * 0.3) for all contradicting items,
    capped at 0.5 (maximum penalty).

    Returns penalty in [0, 0.5].
    """
    contradicting = hypothesis.contradicting_evidence
    if not contradicting:
        return 0.0

    total_penalty = sum(ev.strength * 0.3 for ev in contradicting)
    return min(0.5, float(total_penalty))


# ============================================================
# Main ranking function
# ============================================================

def rank_mechanisms(
    hypotheses: List[CandidateMechanismHypothesis],
    weights: Optional[Dict[str, float]] = None,
    historical_mechanisms: Optional[List[str]] = None,
) -> List[CandidateMechanismHypothesis]:
    """
    Rank candidate mechanism hypotheses by overall score.

    Args:
        hypotheses:              list of CandidateMechanismHypothesis objects
        weights:                 optional dict of factor weights (overrides settings)
        historical_mechanisms:   list of mechanism types from past investigations

    Returns:
        Ranked list (highest score first), with scores populated.
    """
    if not hypotheses:
        return []

    # Use settings defaults or provided weights
    w = weights or {
        "temporal_consistency": settings.weight_temporal_consistency,
        "evidence_strength": settings.weight_evidence_strength,
        "evidence_coverage": settings.weight_evidence_coverage,
        "recurrence": settings.weight_recurrence,
        "mechanism_plausibility": settings.weight_mechanism_plausibility,
    }

    # Normalize weights
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    scored: List[Tuple[float, CandidateMechanismHypothesis]] = []

    for hyp in hypotheses:
        tc = score_temporal_consistency(hyp)
        es = score_evidence_strength(hyp)
        ec = score_evidence_coverage(hyp)
        rc = score_recurrence(hyp, historical_mechanisms)
        mp = score_mechanism_plausibility(hyp)
        penalty = compute_contradiction_penalty(hyp)

        overall = (
            tc * w.get("temporal_consistency", 0.25)
            + es * w.get("evidence_strength", 0.30)
            + ec * w.get("evidence_coverage", 0.20)
            + rc * w.get("recurrence", 0.10)
            + mp * w.get("mechanism_plausibility", 0.15)
            - penalty
        )
        overall = max(0.0, min(1.0, overall))

        # Estimate confidence from evidence count and strength
        n_supporting = len(hyp.supporting_evidence)
        n_contradicting = len(hyp.contradicting_evidence)
        confidence = overall * min(1.0, n_supporting / max(1, n_supporting + n_contradicting))

        # Populate scores on hypothesis
        hyp.temporal_consistency_score = round(tc, 4)
        hyp.evidence_strength_score = round(es, 4)
        hyp.evidence_coverage_score = round(ec, 4)
        hyp.recurrence_score = round(rc, 4)
        hyp.plausibility_score = round(mp, 4)
        hyp.contradiction_penalty = round(penalty, 4)
        hyp.overall_score = round(overall, 4)
        hyp.confidence = round(confidence, 4)
        hyp.supporting_evidence_count = len(hyp.supporting_evidence)
        hyp.contradicting_evidence_count = len(hyp.contradicting_evidence)
        hyp.missing_evidence_count = len(hyp.missing_evidence)

        scored.append((overall, hyp))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Assign ranks
    ranked = []
    for rank_idx, (score, hyp) in enumerate(scored, start=1):
        hyp.rank = rank_idx
        ranked.append(hyp)

    return ranked


# ============================================================
# Baseline ranking methods (for experimental comparison)
# ============================================================

class CorrelationRankingBaseline:
    """
    Baseline 4: Rank mechanisms purely by highest correlation-based evidence strength.
    No temporal reasoning, no graph, no contradiction penalty.
    """

    def rank(
        self, hypotheses: List[CandidateMechanismHypothesis]
    ) -> List[CandidateMechanismHypothesis]:
        """Rank by mean supporting evidence strength only."""
        def mean_strength(hyp):
            if not hyp.supporting_evidence:
                return 0.0
            return float(np.mean([ev.strength for ev in hyp.supporting_evidence]))

        ranked = sorted(hypotheses, key=mean_strength, reverse=True)
        for i, hyp in enumerate(ranked):
            hyp.rank = i + 1
            hyp.overall_score = round(mean_strength(hyp), 4)
        return ranked


class AnomalyScoreBaseline:
    """
    Baseline 1 & 2: Rank mechanisms by anomaly count (no mechanism attribution).
    Equivalent to simple anomaly detection without mechanism discovery.
    """

    def rank(
        self, hypotheses: List[CandidateMechanismHypothesis]
    ) -> List[CandidateMechanismHypothesis]:
        """Rank by count of anomalous evidence items."""
        def anomaly_count(hyp):
            return len([
                ev for ev in hyp.supporting_evidence
                if ev.evidence_type in ("changepoint", "statistical_anomaly")
            ])

        ranked = sorted(hypotheses, key=anomaly_count, reverse=True)
        for i, hyp in enumerate(ranked):
            hyp.rank = i + 1
            cnt = anomaly_count(hyp)
            hyp.overall_score = round(min(1.0, cnt / 5.0), 4)
        return ranked


class FeatureImportanceBaseline:
    """
    Baseline 3: Rank mechanisms by SHAP-style feature importance 
    of the most anomalous parameter. Uses statistical deviation as proxy.
    """

    def rank(
        self, hypotheses: List[CandidateMechanismHypothesis]
    ) -> List[CandidateMechanismHypothesis]:
        """Rank by maximum deviation magnitude across supporting evidence."""
        def max_deviation(hyp):
            devs = [
                abs(ev.deviation) if ev.deviation is not None else 0.0
                for ev in hyp.supporting_evidence
            ]
            return max(devs) if devs else 0.0

        ranked = sorted(hypotheses, key=max_deviation, reverse=True)
        for i, hyp in enumerate(ranked):
            hyp.rank = i + 1
            dev = max_deviation(hyp)
            hyp.overall_score = round(min(1.0, dev / 10.0), 4)
        return ranked


# ============================================================
# Scoring breakdown (for explainability display)
# ============================================================

def get_scoring_breakdown(
    hypothesis: CandidateMechanismHypothesis,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Return a transparent breakdown of the scoring for this hypothesis."""
    w = weights or {
        "temporal_consistency": settings.weight_temporal_consistency,
        "evidence_strength": settings.weight_evidence_strength,
        "evidence_coverage": settings.weight_evidence_coverage,
        "recurrence": settings.weight_recurrence,
        "mechanism_plausibility": settings.weight_mechanism_plausibility,
    }
    return {
        "factors": {
            "temporal_consistency": {
                "score": hypothesis.temporal_consistency_score,
                "weight": w.get("temporal_consistency", 0.25),
                "contribution": round(
                    hypothesis.temporal_consistency_score * w.get("temporal_consistency", 0.25), 4
                ),
                "explanation": "How well precursor events align with the expected temporal order",
            },
            "evidence_strength": {
                "score": hypothesis.evidence_strength_score,
                "weight": w.get("evidence_strength", 0.30),
                "contribution": round(
                    hypothesis.evidence_strength_score * w.get("evidence_strength", 0.30), 4
                ),
                "explanation": "Average strength of supporting evidence items",
            },
            "evidence_coverage": {
                "score": hypothesis.evidence_coverage_score,
                "weight": w.get("evidence_coverage", 0.20),
                "contribution": round(
                    hypothesis.evidence_coverage_score * w.get("evidence_coverage", 0.20), 4
                ),
                "explanation": "Fraction of expected evidence items that were found",
            },
            "recurrence": {
                "score": hypothesis.recurrence_score,
                "weight": w.get("recurrence", 0.10),
                "contribution": round(
                    hypothesis.recurrence_score * w.get("recurrence", 0.10), 4
                ),
                "explanation": "How often this mechanism type appeared historically",
            },
            "mechanism_plausibility": {
                "score": hypothesis.plausibility_score,
                "weight": w.get("mechanism_plausibility", 0.15),
                "contribution": round(
                    hypothesis.plausibility_score * w.get("mechanism_plausibility", 0.15), 4
                ),
                "explanation": "Domain plausibility prior for this mechanism type",
            },
        },
        "contradiction_penalty": hypothesis.contradiction_penalty,
        "overall_score": hypothesis.overall_score,
        "confidence": hypothesis.confidence,
        "evidence_summary": {
            "supporting": hypothesis.supporting_evidence_count,
            "contradicting": hypothesis.contradicting_evidence_count,
            "missing": hypothesis.missing_evidence_count,
        },
        "note": (
            "This is a candidate hypothesis ranked by algorithmic evidence scoring. "
            "Temporal precedence does not imply causation. Expert review required."
        ),
    }

"""
Research Evaluation Metrics Engine
==================================
Computes formal information retrieval and causal discovery metrics:
- NDCG@K (Normalized Discounted Cumulative Gain at K)
- MRR (Mean Reciprocal Rank)
- Precision@K (Top-K accuracy)
- Recall@K
- Contradiction Sensitivity Rate
"""

from typing import List, Dict, Any, Optional
import numpy as np


class ResearchBenchmarkEvaluator:
    """
    Evaluator for comparing ranked candidate failure mechanisms against ground-truth causality.
    """

    @staticmethod
    def dcg_at_k(relevances: List[float], k: int = 5) -> float:
        """Discounted Cumulative Gain at rank K."""
        relevances = np.asarray(relevances, dtype=float)[:k]
        if not relevances.size:
            return 0.0
        # Formula: sum_{i=1}^k rel_i / log2(i + 1)
        discounts = np.log2(np.arange(len(relevances)) + 2)
        return float(np.sum(relevances / discounts))

    @classmethod
    def ndcg_at_k(
        cls,
        ranked_mechanism_ids: List[str],
        ground_truth_relevance: Dict[str, float],
        k: int = 5,
    ) -> float:
        """
        Normalized Discounted Cumulative Gain at K.
        ground_truth_relevance: dict mapping mechanism_id / mechanism_type to graded relevance (e.g. 1.0, 0.5, 0.0)
        """
        relevances = [ground_truth_relevance.get(m_id, 0.0) for m_id in ranked_mechanism_ids[:k]]
        actual_dcg = cls.dcg_at_k(relevances, k)

        ideal_relevances = sorted(ground_truth_relevance.values(), reverse=True)[:k]
        ideal_dcg = cls.dcg_at_k(ideal_relevances, k)

        if ideal_dcg == 0.0:
            return 0.0
        return float(min(1.0, actual_dcg / ideal_dcg))

    @staticmethod
    def mean_reciprocal_rank(
        ranked_mechanism_ids: List[str],
        ground_truth_primary_id: str,
    ) -> float:
        """
        Reciprocal Rank of the primary true failure mechanism.
        Returns 1 / rank if found, else 0.0.
        """
        for i, m_id in enumerate(ranked_mechanism_ids):
            if m_id == ground_truth_primary_id:
                return float(1.0 / (i + 1))
        return 0.0

    @staticmethod
    def precision_at_k(
        ranked_mechanism_ids: List[str],
        ground_truth_relevant_ids: List[str],
        k: int = 1,
    ) -> float:
        """
        Fraction of top-K recommended mechanisms that are true causal mechanisms.
        """
        if k <= 0 or not ranked_mechanism_ids:
            return 0.0
        top_k = ranked_mechanism_ids[:k]
        hits = sum(1 for m_id in top_k if m_id in ground_truth_relevant_ids)
        return float(hits / k)

    @staticmethod
    def recall_at_k(
        ranked_mechanism_ids: List[str],
        ground_truth_relevant_ids: List[str],
        k: int = 5,
    ) -> float:
        """
        Fraction of all true causal mechanisms recovered within top-K.
        """
        if not ground_truth_relevant_ids:
            return 1.0
        top_k = set(ranked_mechanism_ids[:k])
        hits = sum(1 for m_id in ground_truth_relevant_ids if m_id in top_k)
        return float(hits / len(ground_truth_relevant_ids))

    @classmethod
    def evaluate_ranking(
        cls,
        ranked_ids: List[str],
        ground_truth_primary: str,
        ground_truth_all: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Execute comprehensive evaluation suite for a single investigation run.
        """
        if ground_truth_all is None:
            ground_truth_all = {ground_truth_primary: 1.0}

        relevant_keys = [k for k, v in ground_truth_all.items() if v > 0]

        return {
            "ndcg@3": cls.ndcg_at_k(ranked_ids, ground_truth_all, k=3),
            "ndcg@5": cls.ndcg_at_k(ranked_ids, ground_truth_all, k=5),
            "mrr": cls.mean_reciprocal_rank(ranked_ids, ground_truth_primary),
            "precision@1": cls.precision_at_k(ranked_ids, relevant_keys, k=1),
            "precision@3": cls.precision_at_k(ranked_ids, relevant_keys, k=3),
            "recall@5": cls.recall_at_k(ranked_ids, relevant_keys, k=5),
        }

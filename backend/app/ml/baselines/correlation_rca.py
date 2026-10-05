"""
Baseline 3: Correlation-Based Root Cause Analysis (Correlation RCA)
===================================================================
Standard industry baseline that ranks candidate causes purely by bivariate
Pearson and Spearman correlation against failure flags or defect rates.
Demonstrates severe vulnerability to non-causal confounding and lack of temporal precedence.
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from scipy import stats


class CorrelationRCABaseline:
    """
    Correlation-based root-cause baseline computing linear & rank associations.
    """

    def __init__(self, method: str = "spearman"):
        self.method = method  # "pearson" or "spearman"

    def rank_variables(
        self,
        X: pd.DataFrame,
        target_series: pd.Series,
    ) -> List[Dict[str, Any]]:
        """
        Rank candidate telemetry channels by absolute correlation with failure target.
        """
        correlations = {}
        p_values = {}

        y = target_series.fillna(0).values

        for col in X.columns:
            x_vals = X[col].fillna(X[col].median()).values
            if np.std(x_vals) < 1e-7 or np.std(y) < 1e-7:
                correlations[col] = 0.0
                p_values[col] = 1.0
                continue

            if self.method == "pearson":
                r, p = stats.pearsonr(x_vals, y)
            else:
                r, p = stats.spearmanr(x_vals, y)

            correlations[col] = float(np.nan_to_num(r))
            p_values[col] = float(np.nan_to_num(p))

        # Sort by absolute correlation magnitude
        sorted_cols = sorted(correlations.items(), key=lambda item: abs(item[1]), reverse=True)

        max_corr = abs(sorted_cols[0][1]) if sorted_cols and abs(sorted_cols[0][1]) > 0 else 1.0

        return [
            {
                "variable": col,
                "correlation": round(val, 4),
                "abs_correlation": round(abs(val), 4),
                "p_value": round(p_values[col], 6),
                "rank": rank + 1,
                "overall_score": round(abs(val) / max_corr, 3),
                "method": f"correlation_rca_{self.method}",
            }
            for rank, (col, val) in enumerate(sorted_cols)
        ]

"""
Feature Extraction for Heterogeneous Temporal Industrial Data
=============================================================
Computes statistical, temporal, and frequency-domain features from
time-series telemetry and event logs to serve discovery and baseline algorithms.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats


class FeatureExtractor:
    """
    Extracts multi-scale temporal and relational features from industrial time-series.
    """

    def __init__(self, window_sizes: Optional[List[int]] = None):
        # Default rolling window sizes (e.g. 5 min, 15 min, 60 min)
        self.window_sizes = window_sizes or [5, 15, 60]

    def extract_time_series_features(
        self,
        df: pd.DataFrame,
        value_columns: List[str],
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """
        Extract rolling statistics, gradients, and lag features for specified columns.
        """
        df = df.copy()
        if timestamp_col in df.columns:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            df = df.sort_values(timestamp_col)

        feature_dfs = [df]

        for col in value_columns:
            if col not in df.columns:
                continue

            series = df[col]
            extracted = {}

            # Rate of change / first difference
            extracted[f"{col}_diff"] = series.diff().fillna(0)
            extracted[f"{col}_pct_change"] = series.pct_change().replace([np.inf, -np.inf], 0).fillna(0)

            # Multi-scale rolling statistics
            for w in self.window_sizes:
                rolling = series.rolling(window=w, min_periods=1)
                extracted[f"{col}_mean_w{w}"] = rolling.mean()
                extracted[f"{col}_std_w{w}"] = rolling.std().fillna(0)
                extracted[f"{col}_min_w{w}"] = rolling.min()
                extracted[f"{col}_max_w{w}"] = rolling.max()
                extracted[f"{col}_skew_w{w}"] = rolling.apply(lambda x: float(stats.skew(x)) if len(x) > 2 and np.std(x) > 1e-6 else 0.0, raw=False).fillna(0)

            # Cumulative deviation from median
            median_val = series.median()
            extracted[f"{col}_dev_from_median"] = (series - median_val).abs()

            feature_dfs.append(pd.DataFrame(extracted, index=df.index))

        result = pd.concat(feature_dfs, axis=1)
        # Remove any duplicate columns if present
        result = result.loc[:, ~result.columns.duplicated()]
        return result

    def extract_window_aggregates(
        self,
        df: pd.DataFrame,
        value_columns: List[str],
    ) -> Dict[str, float]:
        """
        Extract fixed-size summary vector for an entire analysis window.
        """
        summary = {}
        for col in value_columns:
            if col not in df.columns:
                continue
            vals = df[col].dropna().values
            if len(vals) == 0:
                continue

            summary[f"{col}_mean"] = float(np.mean(vals))
            summary[f"{col}_std"] = float(np.std(vals))
            summary[f"{col}_min"] = float(np.min(vals))
            summary[f"{col}_max"] = float(np.max(vals))
            summary[f"{col}_range"] = float(np.ptp(vals))
            summary[f"{col}_skewness"] = float(stats.skew(vals)) if len(vals) > 2 else 0.0
            summary[f"{col}_kurtosis"] = float(stats.kurtosis(vals)) if len(vals) > 3 else 0.0
            summary[f"{col}_p95"] = float(np.percentile(vals, 95))
            summary[f"{col}_p05"] = float(np.percentile(vals, 5))

        return summary

"""
Baseline 1: Isolation Forest Anomaly Detection
=============================================
Conventional unsupervised anomaly detection baseline.
Detects point-wise and window-wise anomalies in multivariate telemetry,
demonstrating the limitation of purely statistical anomaly detection
without causal/temporal mechanism discovery.
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class IsolationForestBaseline:
    """
    Isolation Forest baseline model for industrial anomaly detection.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
        )
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame) -> "IsolationForestBaseline":
        """Fit isolation forest on sensor feature matrix."""
        self.feature_names = list(X.columns)
        X_clean = X.fillna(X.median()).values
        X_scaled = self.scaler.fit_transform(X_clean)
        self.model.fit(X_scaled)
        return self

    def predict_anomalies(self, X: pd.DataFrame) -> np.ndarray:
        """
        Returns boolean array: True for anomalies (-1 from model), False for normal.
        """
        X_clean = X[self.feature_names].fillna(X.median()).values
        X_scaled = self.scaler.transform(X_clean)
        preds = self.model.predict(X_scaled)
        return preds == -1

    def compute_anomaly_scores(self, X: pd.DataFrame) -> np.ndarray:
        """
        Returns normalized anomaly scores in [0, 1], where 1 is highest anomaly.
        """
        X_clean = X[self.feature_names].fillna(X.median()).values
        X_scaled = self.scaler.transform(X_clean)
        # decision_function gives negative values for anomalies
        raw_scores = -self.model.decision_function(X_scaled)
        # Min-max scale to [0, 1]
        min_s, max_s = np.min(raw_scores), np.max(raw_scores)
        if max_s > min_s:
            return (raw_scores - min_s) / (max_s - min_s)
        return np.zeros_like(raw_scores)

    def rank_anomalous_sensors(self, X: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Produce a crude ranking of sensors based on deviation from median in anomalous points.
        Illustrates the baseline's lack of causal ordering.
        """
        scores = self.compute_anomaly_scores(X)
        anom_mask = scores > 0.7

        if not np.any(anom_mask):
            anom_mask = scores > np.percentile(scores, 95)

        X_anom = X.loc[anom_mask, self.feature_names]
        X_norm = X.loc[~anom_mask, self.feature_names]

        deviations = {}
        for col in self.feature_names:
            norm_mean = X_norm[col].mean()
            norm_std = X_norm[col].std() + 1e-6
            anom_mean = X_anom[col].mean()
            z_score = abs(anom_mean - norm_mean) / norm_std
            deviations[col] = float(z_score)

        sorted_items = sorted(deviations.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "sensor": k,
                "z_deviation": round(v, 3),
                "rank": i + 1,
                "overall_score": round(min(1.0, v / 10.0), 3),
                "method": "isolation_forest_zscore",
            }
            for i, (k, v) in enumerate(sorted_items)
        ]

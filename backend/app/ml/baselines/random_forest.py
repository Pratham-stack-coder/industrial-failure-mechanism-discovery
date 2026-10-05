"""
Baseline 2: Supervised Random Forest Classifier
==============================================
Predictive-maintenance baseline that trains a supervised classifier to predict
failure occurrence from operational features.
Demonstrates that supervised predictive models often identify symptoms rather
than antecedent mechanisms due to feature correlation and absence of temporal causality.
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, f1_score


class RandomForestBaseline:
    """
    Supervised Random Forest baseline for failure prediction and feature importance ranking.
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 10, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight="balanced",
        )
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestBaseline":
        """Fit random forest on labeled failure instances."""
        self.feature_names = list(X.columns)
        X_clean = X.fillna(X.median()).values
        self.model.fit(X_clean, y.values)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict failure probability."""
        X_clean = X[self.feature_names].fillna(X.median()).values
        return self.model.predict_proba(X_clean)[:, 1]

    def rank_features(self) -> List[Dict[str, Any]]:
        """
        Rank variables by Gini feature importance.
        """
        importances = self.model.feature_importances_
        sorted_indices = np.argsort(importances)[::-1]

        return [
            {
                "feature": self.feature_names[i],
                "importance": float(round(importances[i], 4)),
                "rank": rank + 1,
                "overall_score": float(round(importances[i] / np.max(importances), 3)),
                "method": "random_forest_gini",
            }
            for rank, i in enumerate(sorted_indices)
        ]

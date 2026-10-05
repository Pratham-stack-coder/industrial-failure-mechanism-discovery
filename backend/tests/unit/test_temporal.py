"""
Unit tests for Temporal Analysis Module
"""

import pytest
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
from app.temporal.temporal_analysis import (
    detect_change_points,
    compute_lag_correlations,
    detect_parameter_trends,
)


def test_detect_change_points_with_step():
    now = datetime.now(timezone.utc)
    n = 60
    # Create time series with step change at index 30
    timestamps = [now + timedelta(minutes=i) for i in range(n)]
    values = np.concatenate([np.random.normal(10, 0.5, 30), np.random.normal(25, 0.5, 30)])

    s_series = pd.Series(values)
    t_series = pd.Series(timestamps)

    cps = detect_change_points(s_series, t_series, "spindle_temp", penalty=2.0, min_size=5)
    assert len(cps) >= 1
    first_cp = cps[0]
    assert 25 <= first_cp.change_index <= 35
    assert first_cp.direction == "increase"
    assert first_cp.magnitude > 10.0


def test_compute_lag_correlations():
    now = datetime.now(timezone.utc)
    n = 100
    timestamps = [now + timedelta(hours=i) for i in range(n)]

    # Signal A
    a_base = np.sin(np.linspace(0, 10, n))
    # Signal B lags A by 2 steps
    b_base = np.roll(a_base, 2)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "param_a": a_base,
        "param_b": b_base,
    })

    corrs = compute_lag_correlations(
        df=df,
        param_a="param_a",
        param_b="param_b",
        max_lag_hours=10.0,
        step_hours=1.0,
        min_samples=20,
    )

    assert len(corrs) > 0
    max_corr = max(corrs, key=lambda c: abs(c.correlation))
    assert abs(max_corr.correlation) > 0.5


def test_detect_parameter_trends():
    now = datetime.now(timezone.utc)
    n = 40
    timestamps = [now + timedelta(hours=i) for i in range(n)]
    # Upward linear trend
    values = np.linspace(10, 50, n) + np.random.normal(0, 0.5, n)

    s_series = pd.Series(values)
    t_series = pd.Series(timestamps)

    trend_info = detect_parameter_trends(s_series, t_series, min_samples=10)
    assert trend_info is not None
    assert trend_info["slope_per_hour"] > 0
    assert trend_info["trend"] == "increasing"

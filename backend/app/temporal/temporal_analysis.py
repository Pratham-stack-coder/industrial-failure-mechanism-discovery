"""
Temporal Analysis Module
========================
Performs time-series analysis on industrial parameter data:
  - Change-point detection (ruptures library)
  - Lag cross-correlation analysis
  - Trend detection
  - Event-sequence extraction
  - Temporal window feature computation

All functions operate on pandas DataFrames with a 'timestamp' column.
Results are structured dicts traceable to source records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import ruptures as rpt
from scipy import stats
from loguru import logger


# ============================================================
# Data structures
# ============================================================

@dataclass
class ChangePoint:
    """A detected change-point in a parameter time-series."""
    parameter_code: str
    timestamp: datetime
    change_index: int
    pre_mean: float
    post_mean: float
    magnitude: float          # post_mean - pre_mean
    relative_change: float    # magnitude / abs(pre_mean) if pre_mean != 0
    direction: str            # "increase" | "decrease"
    confidence: float         # 0..1 based on ruptures penalty


@dataclass
class TemporalCorrelation:
    """Cross-correlation between two parameters at a specific lag."""
    param_a: str
    param_b: str
    lag_hours: float          # positive = a precedes b
    correlation: float        # Pearson r
    p_value: float
    n_samples: int
    is_significant: bool      # p < 0.05


@dataclass
class TemporalWindow:
    """Feature summary for a time window around an event."""
    start_time: datetime
    end_time: datetime
    center_time: datetime
    parameter_stats: Dict[str, Dict[str, float]]
    # param_code → {mean, std, min, max, trend_slope, n_anomalous, pct_oos}
    event_counts: Dict[str, int]
    # event_type → count


@dataclass
class EventSequence:
    """An ordered sequence of industrial events preceding a failure."""
    failure_time: datetime
    events: List[Dict[str, Any]]
    # Each: {type, time, lag_hours, entity_id, description}
    total_duration_hours: float


# ============================================================
# Change-point detection
# ============================================================

def detect_change_points(
    series: pd.Series,
    timestamps: pd.Series,
    param_code: str,
    model: str = "rbf",
    penalty: float = 3.0,
    min_size: int = 5,
) -> List[ChangePoint]:
    """
    Detect change-points in a parameter time-series using the ruptures library.

    Args:
        series:     numeric values (NaN-cleaned before analysis)
        timestamps: corresponding timestamps
        param_code: parameter identifier for labeling results
        model:      ruptures cost function model ('rbf', 'l2', 'cosine')
        penalty:    BIC-style penalty; higher = fewer change-points
        min_size:   minimum segment size

    Returns:
        List of ChangePoint objects, ordered by time.
    """
    # Clean NaN
    mask = series.notna()
    clean_vals = series[mask].values.astype(float)
    clean_ts = timestamps[mask].values

    if len(clean_vals) < min_size * 2:
        return []

    try:
        signal = clean_vals.reshape(-1, 1)
        algo = rpt.Pelt(model=model, min_size=min_size).fit(signal)
        bkps = algo.predict(pen=penalty)
    except Exception as e:
        logger.debug(f"Change-point detection failed for {param_code}: {e}")
        return []

    change_points = []
    prev_idx = 0

    for bkp in bkps[:-1]:  # last bkp is len(signal)
        if bkp >= len(clean_vals):
            continue

        pre_seg = clean_vals[prev_idx:bkp]
        post_seg = clean_vals[bkp : min(bkp + min_size * 5, len(clean_vals))]

        if len(pre_seg) < 2 or len(post_seg) < 2:
            prev_idx = bkp
            continue

        pre_mean = float(np.mean(pre_seg))
        post_mean = float(np.mean(post_seg))
        magnitude = post_mean - pre_mean
        rel_change = magnitude / abs(pre_mean) if abs(pre_mean) > 1e-9 else 0.0

        # Simple confidence from t-test between segments
        try:
            _, p_val = stats.ttest_ind(pre_seg, post_seg)
            confidence = max(0.0, 1.0 - float(p_val))
        except Exception:
            confidence = 0.5

        # Convert index back to timestamp
        cp_ts = pd.Timestamp(clean_ts[bkp - 1]).to_pydatetime()
        if cp_ts.tzinfo is None:
            cp_ts = cp_ts.replace(tzinfo=timezone.utc)

        change_points.append(
            ChangePoint(
                parameter_code=param_code,
                timestamp=cp_ts,
                change_index=bkp,
                pre_mean=round(pre_mean, 4),
                post_mean=round(post_mean, 4),
                magnitude=round(magnitude, 4),
                relative_change=round(rel_change, 4),
                direction="increase" if magnitude > 0 else "decrease",
                confidence=round(confidence, 4),
            )
        )
        prev_idx = bkp

    return change_points


# ============================================================
# Lag cross-correlation analysis
# ============================================================

def compute_lag_correlations(
    df: pd.DataFrame,
    param_a: str,
    param_b: str,
    max_lag_hours: float = 48.0,
    step_hours: float = 1.0,
    min_samples: int = 30,
) -> List[TemporalCorrelation]:
    """
    Compute lagged cross-correlations between two parameters.

    A positive lag means param_a changes first, then param_b.
    Returns correlations at each tested lag, ordered by |correlation|.

    Args:
        df:             DataFrame with columns ['timestamp', param_a, param_b]
        param_a:        first parameter (potential cause)
        param_b:        second parameter (potential effect)
        max_lag_hours:  maximum lag to test
        step_hours:     lag step size
        min_samples:    minimum overlapping samples required

    Returns:
        List of TemporalCorrelation objects sorted by |correlation| descending.
    """
    if param_a not in df.columns or param_b not in df.columns:
        return []

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")

    # Resample to hourly to standardise lag computation
    df = df.set_index("timestamp")
    hourly = df[[param_a, param_b]].resample("1h").mean().interpolate(limit=3)
    hourly = hourly.reset_index()

    results = []
    lag_steps = np.arange(-max_lag_hours, max_lag_hours + step_hours, step_hours)

    for lag in lag_steps:
        lag_periods = int(lag)
        if lag_periods == 0:
            shifted_a = hourly[param_a]
            shifted_b = hourly[param_b]
        elif lag_periods > 0:
            # param_a leads param_b
            shifted_a = hourly[param_a].iloc[lag_periods:]
            shifted_b = hourly[param_b].iloc[:-lag_periods]
        else:
            # param_b leads param_a
            shifted_a = hourly[param_a].iloc[:lag_periods]
            shifted_b = hourly[param_b].iloc[-lag_periods:]

        valid_mask = shifted_a.notna() & shifted_b.notna()
        n = valid_mask.sum()
        if n < min_samples:
            continue

        a_vals = shifted_a[valid_mask].values
        b_vals = shifted_b[valid_mask].values

        try:
            r, p = stats.pearsonr(a_vals, b_vals)
        except Exception:
            continue

        results.append(
            TemporalCorrelation(
                param_a=param_a,
                param_b=param_b,
                lag_hours=float(lag),
                correlation=round(float(r), 4),
                p_value=round(float(p), 6),
                n_samples=int(n),
                is_significant=(float(p) < 0.05 and abs(float(r)) > 0.15),
            )
        )

    return sorted(results, key=lambda x: abs(x.correlation), reverse=True)


# ============================================================
# Temporal window feature extraction
# ============================================================

def extract_window_features(
    measurements_df: pd.DataFrame,
    events_df: pd.DataFrame,
    center_time: datetime,
    lookback_hours: float = 48.0,
    lookahead_hours: float = 0.0,
    parameter_codes: Optional[List[str]] = None,
) -> TemporalWindow:
    """
    Extract summary features for a time window around a center event.

    Args:
        measurements_df: parameter measurements with columns
                         [timestamp, parameter_code, value, is_out_of_spec, is_anomalous]
        events_df:       events (maintenance, process_changes) with columns
                         [timestamp, event_type]
        center_time:     the event of interest (usually failure time)
        lookback_hours:  how far back to look
        lookahead_hours: how far forward to look (usually 0 for failure analysis)
        parameter_codes: restrict to these parameter codes (None = all)

    Returns:
        TemporalWindow with statistical summaries.
    """
    start_time = center_time - timedelta(hours=lookback_hours)
    end_time = center_time + timedelta(hours=lookahead_hours)

    # Filter measurements
    m_df = measurements_df.copy()
    m_df["timestamp"] = pd.to_datetime(m_df["timestamp"], utc=True)
    if center_time.tzinfo is None:
        center_time = center_time.replace(tzinfo=timezone.utc)
        start_time = start_time.replace(tzinfo=timezone.utc)
        end_time = end_time.replace(tzinfo=timezone.utc)

    mask = (m_df["timestamp"] >= start_time) & (m_df["timestamp"] <= end_time)
    m_window = m_df[mask]

    if parameter_codes:
        m_window = m_window[m_window["parameter_code"].isin(parameter_codes)]

    # Compute per-parameter stats
    param_stats: Dict[str, Dict[str, float]] = {}
    for pcode, group in m_window.groupby("parameter_code"):
        vals = group["value"].dropna()
        if len(vals) < 2:
            continue

        # Trend slope (linear regression of value vs time)
        times_h = (group["timestamp"] - start_time).dt.total_seconds().values / 3600.0
        vals_arr = group["value"].values
        valid = ~np.isnan(vals_arr)
        if valid.sum() >= 3:
            slope, _, _, _, _ = stats.linregress(times_h[valid], vals_arr[valid])
        else:
            slope = 0.0

        param_stats[str(pcode)] = {
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std()), 4),
            "min": round(float(vals.min()), 4),
            "max": round(float(vals.max()), 4),
            "trend_slope_per_hour": round(float(slope), 6),
            "n_samples": int(len(vals)),
            "n_anomalous": int(group["is_anomalous"].sum()),
            "pct_out_of_spec": round(
                float(group["is_out_of_spec"].sum()) / max(1, len(group)), 4
            ),
        }

    # Count events in window
    event_counts: Dict[str, int] = {}
    if not events_df.empty:
        e_df = events_df.copy()
        e_df["timestamp"] = pd.to_datetime(e_df["timestamp"], utc=True)
        e_window = e_df[(e_df["timestamp"] >= start_time) & (e_df["timestamp"] <= end_time)]
        if "event_type" in e_window.columns:
            event_counts = e_window["event_type"].value_counts().to_dict()

    return TemporalWindow(
        start_time=start_time,
        end_time=end_time,
        center_time=center_time,
        parameter_stats=param_stats,
        event_counts={str(k): int(v) for k, v in event_counts.items()},
    )


# ============================================================
# Event sequence extraction
# ============================================================

def extract_event_sequence(
    failure_time: datetime,
    maintenance_df: pd.DataFrame,
    process_changes_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    change_points: List[ChangePoint],
    lookback_hours: float = 96.0,
) -> EventSequence:
    """
    Build a chronological sequence of all relevant events preceding a failure.

    Args:
        failure_time:       the failure timestamp
        maintenance_df:     maintenance events (with 'start_time' column)
        process_changes_df: process changes (with 'change_time' column)
        quality_df:         quality inspections (with 'inspection_time', 'result')
        change_points:      detected parameter change-points
        lookback_hours:     how far back to look

    Returns:
        EventSequence with chronologically ordered events.
    """
    if failure_time.tzinfo is None:
        failure_time = failure_time.replace(tzinfo=timezone.utc)
    cutoff = failure_time - timedelta(hours=lookback_hours)

    events: List[Dict[str, Any]] = []

    # Maintenance events
    if not maintenance_df.empty:
        m = maintenance_df.copy()
        time_col = "start_time" if "start_time" in m.columns else "timestamp"
        m[time_col] = pd.to_datetime(m[time_col], utc=True)
        m_window = m[(m[time_col] >= cutoff) & (m[time_col] <= failure_time)]
        for _, row in m_window.iterrows():
            t = row[time_col]
            lag = (failure_time - t).total_seconds() / 3600.0
            events.append({
                "type": "maintenance",
                "time": t,
                "lag_hours": round(lag, 2),
                "entity_id": str(row.get("machine_id", "")),
                "description": str(row.get("description", row.get("maintenance_type", ""))),
                "source_table": "maintenance_events",
                "source_id": str(row.get("id", "")),
            })

    # Process changes
    if not process_changes_df.empty:
        pc = process_changes_df.copy()
        time_col = "change_time" if "change_time" in pc.columns else "timestamp"
        pc[time_col] = pd.to_datetime(pc[time_col], utc=True)
        pc_window = pc[(pc[time_col] >= cutoff) & (pc[time_col] <= failure_time)]
        for _, row in pc_window.iterrows():
            t = row[time_col]
            lag = (failure_time - t).total_seconds() / 3600.0
            events.append({
                "type": "process_change",
                "time": t,
                "lag_hours": round(lag, 2),
                "entity_id": str(row.get("process_id", "")),
                "description": f"Process change: {row.get('change_type','')} on {row.get('parameter_name','')}",
                "source_table": "process_changes",
                "source_id": str(row.get("id", "")),
            })

    # Quality failures (previous failing inspections)
    if not quality_df.empty:
        q = quality_df.copy()
        time_col = "inspection_time" if "inspection_time" in q.columns else "timestamp"
        q[time_col] = pd.to_datetime(q[time_col], utc=True)
        q_window = q[
            (q[time_col] >= cutoff)
            & (q[time_col] <= failure_time)
            & (q.get("result", pd.Series(dtype=str)) == "fail")
        ]
        for _, row in q_window.iterrows():
            t = row[time_col]
            lag = (failure_time - t).total_seconds() / 3600.0
            events.append({
                "type": "quality_failure",
                "time": t,
                "lag_hours": round(lag, 2),
                "entity_id": str(row.get("batch_id", "")),
                "description": f"Quality inspection FAIL: defect_rate={row.get('defect_rate','')}",
                "source_table": "quality_inspections",
                "source_id": str(row.get("id", "")),
            })

    # Change-points (parameter-level events)
    for cp in change_points:
        if cutoff <= cp.timestamp <= failure_time:
            lag = (failure_time - cp.timestamp).total_seconds() / 3600.0
            events.append({
                "type": "changepoint",
                "time": cp.timestamp,
                "lag_hours": round(lag, 2),
                "entity_id": cp.parameter_code,
                "description": (
                    f"{cp.parameter_code} change-point: "
                    f"{cp.pre_mean:.3f}→{cp.post_mean:.3f} "
                    f"({cp.direction}, {cp.relative_change*100:.1f}%)"
                ),
                "source_table": "parameter_measurements",
                "source_id": None,
                "magnitude": cp.magnitude,
                "relative_change": cp.relative_change,
                "confidence": cp.confidence,
            })

    # Sort chronologically
    events.sort(key=lambda e: e["time"])

    # Convert timestamps to ISO strings for serialization
    for e in events:
        e["time"] = e["time"].isoformat()

    total_dur = lookback_hours if events else 0.0

    return EventSequence(
        failure_time=failure_time,
        events=events,
        total_duration_hours=total_dur,
    )


# ============================================================
# Trend analysis utilities
# ============================================================

def detect_parameter_trends(
    series: pd.Series,
    timestamps: pd.Series,
    window_hours: float = 24.0,
    min_samples: int = 10,
) -> Dict[str, Any]:
    """
    Detect trends (monotone increase/decrease) over a trailing window.
    Uses Mann-Kendall trend test.

    Returns dict with:
      trend: "increasing" | "decreasing" | "stable"
      slope_per_hour: linear regression slope
      mk_tau: Mann-Kendall tau statistic
      p_value: significance
    """
    mask = series.notna()
    vals = series[mask].values.astype(float)
    ts = pd.to_datetime(timestamps[mask])

    if len(vals) < min_samples:
        return {"trend": "insufficient_data", "slope_per_hour": 0.0, "mk_tau": 0.0, "p_value": 1.0}

    times_h = (ts - ts.iloc[0]).dt.total_seconds().values / 3600.0
    slope, intercept, r, p, se = stats.linregress(times_h, vals)

    # Mann-Kendall (simplified Scipy-compatible version)
    n = len(vals)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = vals[j] - vals[i]
            s += np.sign(diff)

    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    if var_s > 0:
        z = (s - np.sign(s)) / np.sqrt(var_s)
        mk_p = 2 * (1 - stats.norm.cdf(abs(z)))
        tau = s / (n * (n - 1) / 2.0)
    else:
        z, mk_p, tau = 0.0, 1.0, 0.0

    if mk_p < 0.05:
        trend = "increasing" if tau > 0 else "decreasing"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "slope_per_hour": round(float(slope), 6),
        "mk_tau": round(float(tau), 4),
        "p_value": round(float(mk_p), 6),
        "r_squared": round(float(r**2), 4),
    }


def compute_deviation_from_nominal(
    values: np.ndarray,
    nominal: float,
    upper_limit: Optional[float] = None,
    lower_limit: Optional[float] = None,
) -> Dict[str, float]:
    """Compute statistical deviation from nominal/expected value."""
    deviations = values - nominal
    pct_deviation = deviations / abs(nominal) * 100 if abs(nominal) > 1e-9 else deviations

    out_of_spec_count = 0
    if upper_limit is not None:
        out_of_spec_count += int(np.sum(values > upper_limit))
    if lower_limit is not None:
        out_of_spec_count += int(np.sum(values < lower_limit))

    return {
        "mean_deviation": round(float(np.nanmean(deviations)), 4),
        "max_deviation": round(float(np.nanmax(np.abs(deviations))), 4),
        "mean_pct_deviation": round(float(np.nanmean(pct_deviation)), 2),
        "out_of_spec_count": out_of_spec_count,
        "out_of_spec_pct": round(out_of_spec_count / max(1, len(values)), 4),
        "n_samples": len(values),
    }

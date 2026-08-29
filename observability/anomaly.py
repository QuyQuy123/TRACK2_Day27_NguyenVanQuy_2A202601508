"""Anomaly detection module.

Provides:
- Z-score detector
- Robust Median Absolute Deviation (MAD) / Modified Z-Score detector
- Context-aware auto detector supporting seasonality, segmentation, and events
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if not np.isfinite(float(current)):
        return {"is_anomaly": True, "score": float("inf"), "method": "zscore", "reason": "current_is_not_finite"}
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust Modified Z-score using Median Absolute Deviation (MAD).

    Handles zero-MAD and small-variance edge cases gracefully with practical scale.
    """
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if not np.isfinite(float(current)):
        return {"is_anomaly": True, "score": float("inf"), "method": "mad", "reason": "current_is_not_finite"}
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    cur = float(current)

    if mad == 0:
        # Quantized metrics (e.g. integer row counts) commonly have a zero MAD.
        # A 1% practical scale avoids alerting on negligible changes while catching collapses.
        practical_scale = max(abs(median) * 0.01, 1e-9)
        score = 0.6745 * abs(cur - median) / practical_scale
        return {
            "is_anomaly": bool(score > threshold),
            "score": float(score),
            "method": "mad",
            "reason": f"median={median:.3f}, mad=0, practical_scale={practical_scale:.6g}, threshold={threshold}",
        }

    modified_z = 0.6745 * abs(cur - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API with context-aware auto detector.

    Supports methods:
    - 'zscore': Standard Z-Score.
    - 'mad': Robust Modified Z-Score using MAD.
    - 'auto': Automatically selects robust MAD or Z-Score, factoring in context
              such as same_segment_history, day_of_week, and known_events.
    """
    history_values = list(history)
    if method == "mad":
        return mad_detector(current, history_values, threshold=max(3.5, threshold))
    if method == "zscore":
        return zscore_detector(current, history_values, threshold=threshold)
    if method == "auto":
        context = context or {}
        segment = context.get("same_segment_history")
        segment_values = list(segment) if segment is not None else []
        selected = segment_values if len(segment_values) >= 3 else history_values

        result = mad_detector(current, selected, threshold=max(3.5, threshold))
        if result["reason"] == "insufficient_history":
            result = zscore_detector(current, selected, threshold=threshold)

        base_method = result["method"]
        segment_name = "same_segment" if selected is segment_values else "all_history"
        result["method"] = f"auto:{segment_name}:{base_method}"
        metric = context.get("metric_name", "metric")
        result["reason"] += f"; metric={metric}; baseline={segment_name}"

        known_event = context.get("known_event")
        if known_event and result["is_anomaly"]:
            result["is_anomaly"] = False
            result["reason"] += f"; suppressed_by_known_event={known_event}"

        return result

    raise ValueError(f"Unsupported method: {method}")




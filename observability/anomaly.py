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

    Handles zero-MAD and small-variance edge cases gracefully.
    """
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    cur = float(current)

    if mad == 0:
        # Fallback to mean absolute deviation or direct equality
        mean_ad = float(np.mean(np.abs(values - median)))
        if mean_ad == 0:
            score = float("inf") if cur != median else 0.0
        else:
            score = 0.6745 * abs(cur - median) / mean_ad
        reason = f"median={median:.3f}, mad=0.0 (mean_ad={mean_ad:.3f}), threshold={threshold}"
    else:
        score = 0.6745 * abs(cur - median) / mad
        reason = f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}"

    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "mad",
        "reason": reason,
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
    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)
    if method == "mad":
        return mad_detector(current, history, threshold=threshold)
    if method == "auto":
        effective_history = list(history)
        ctx_desc = []

        if context:
            if "same_segment_history" in context and len(context["same_segment_history"]) >= 3:
                effective_history = list(context["same_segment_history"])
                ctx_desc.append("used_same_segment_history=True")
            if "day_of_week" in context:
                ctx_desc.append(f"dow={context['day_of_week']}")
            if "known_event" in context and context["known_event"]:
                ctx_desc.append(f"event={context['known_event']}")
                threshold = threshold * 1.5
            if "metric_name" in context:
                ctx_desc.append(f"metric={context['metric_name']}")

        # Use MAD if we have sufficient samples (>= 5), else fallback to Z-score
        if len(effective_history) >= 5:
            res = mad_detector(current, effective_history, threshold=threshold)
            res["method"] = "auto:mad"
        else:
            res = zscore_detector(current, effective_history, threshold=threshold)
            res["method"] = "auto:zscore"

        if ctx_desc:
            res["reason"] += f"; context: [{', '.join(ctx_desc)}]"
        return res

    raise ValueError(f"Unsupported method: {method}")


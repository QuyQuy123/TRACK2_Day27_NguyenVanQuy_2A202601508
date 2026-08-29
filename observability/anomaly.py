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
              such as day_of_week seasonality, same_segment_history, trend, and known_events.
    """
    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)
    if method == "mad":
        return mad_detector(current, history, threshold=threshold)
    if method == "auto":
        raw_values = np.asarray(list(history), dtype=float)
        values = raw_values[np.isfinite(raw_values)]
        if values.size < 3:
            return {"is_anomaly": False, "score": 0.0, "method": "auto:zscore", "reason": "insufficient_history"}

        context = context or {}
        cur = float(current)

        # 1. Direct segment history passed in context
        if "same_segment_history" in context and len(context["same_segment_history"]) >= 3:
            seg_values = np.asarray(list(context["same_segment_history"]), dtype=float)
            seg_values = seg_values[np.isfinite(seg_values)]
            if seg_values.size >= 3:
                res = mad_detector(cur, seg_values, threshold=threshold)
                res["method"] = "auto:same_segment_mad"
                res["reason"] += "; used_same_segment_history=True"
                return res

        # 2. Seasonality / Day-of-week context without pre-extracted segment
        if "day_of_week" in context and values.size >= 14:
            dow = context["day_of_week"]
            if isinstance(dow, str):
                dow_map = {
                    "mon": 0, "monday": 0, "tue": 1, "tuesday": 1,
                    "wed": 2, "wednesday": 2, "thu": 3, "thursday": 3,
                    "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
                    "sun": 6, "sunday": 6,
                }
                try:
                    dow = dow_map.get(dow.lower().strip(), int(dow))
                except (ValueError, AttributeError):
                    dow = 0
            else:
                dow = int(dow)

            phases = [values[p::7] for p in range(7)]
            medians = [float(np.median(p)) for p in phases if len(p) >= 2]

            if len(medians) == 7:
                sorted_phase_indices = np.argsort(medians)
                weekend_phases = sorted_phase_indices[:2]
                weekday_phases = sorted_phase_indices[2:]

                target_phase_indices = weekend_phases if dow in [5, 6] else weekday_phases
                target_phases = [phases[idx] for idx in target_phase_indices]

                best_m_score = None
                best_info = None
                for p_vals in target_phases:
                    med = float(np.median(p_vals))
                    mad = float(np.median(np.abs(p_vals - med)))
                    scale = mad if mad > 0 else (float(np.mean(np.abs(p_vals - med))) or 1.0)
                    m_score = 0.6745 * abs(cur - med) / scale
                    if best_m_score is None or m_score < best_m_score:
                        best_m_score = m_score
                        best_info = (med, scale)

                if best_m_score is not None:
                    med, scale = best_info
                    eff_thresh = threshold * (2.0 if context.get("known_event") else 1.0)
                    return {
                        "is_anomaly": bool(best_m_score > eff_thresh),
                        "score": float(best_m_score),
                        "method": "auto:seasonal_mad",
                        "reason": f"seasonal_dow={dow}, median={med:.3f}, mad={scale:.3f}, threshold={eff_thresh}",
                    }

        # 3. Trend handling in context or linear detrending
        if context.get("trend") or (values.size >= 7 and np.abs(np.corrcoef(np.arange(values.size), values)[0, 1]) > 0.85):
            x = np.arange(values.size)
            slope, intercept = np.polyfit(x, values, 1)
            expected = slope * values.size + intercept
            residuals = values - (slope * x + intercept)
            res_std = float(np.std(residuals))
            scale = max(res_std, float(np.mean(np.abs(values))) * 0.05, 1.0)
            trend_score = abs(cur - expected) / scale
            eff_thresh = threshold * (2.0 if context.get("known_event") else 1.0)
            return {
                "is_anomaly": bool(trend_score > eff_thresh),
                "score": float(trend_score),
                "method": "auto:trend",
                "reason": f"trend_expected={expected:.3f}, scale={scale:.3f}, threshold={eff_thresh}",
            }

        # 4. Standard robust MAD / Z-score default

        eff_thresh = threshold * (2.0 if context.get("known_event") else 1.0)
        if values.size >= 5:
            res = mad_detector(cur, values, threshold=eff_thresh)
            res["method"] = "auto:mad"
        else:
            res = zscore_detector(cur, values, threshold=eff_thresh)
            res["method"] = "auto:zscore"

        return res

    raise ValueError(f"Unsupported method: {method}")



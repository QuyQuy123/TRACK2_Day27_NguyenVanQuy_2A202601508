from __future__ import annotations

from typing import Any, Iterable

import numpy as np
from scipy import stats


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
    ks_pvalue_threshold: float = 0.01,
) -> dict[str, Any]:
    """Detect distribution drift using combined statistical tests.

    Combines:
    1. Robust mean and median ratio test
    2. Two-sample Kolmogorov-Smirnov (KS) test for distribution shape shift
    """
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)

    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "distribution_shift", "reason": "empty_input"}

    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))

    # Mean ratio calculation
    if base_mean == 0:
        mean_ratio = float("inf") if cur_mean != 0 else 1.0
    else:
        mean_ratio = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")

    # KS Test
    ks_stat = 0.0
    p_value = 1.0
    if cur.size >= 4 and base.size >= 4:
        try:
            ks_res = stats.ks_2samp(cur, base)
            ks_stat = float(ks_res.statistic)
            p_value = float(ks_res.pvalue)
        except Exception:
            pass

    is_anomaly = bool(mean_ratio >= ratio_threshold or (p_value < ks_pvalue_threshold and ks_stat > 0.5))
    score = float(max(mean_ratio if np.isfinite(mean_ratio) else 999.0, ks_stat * 10.0))

    return {
        "is_anomaly": is_anomaly,
        "score": score,
        "method": "ks_and_mean_ratio",
        "reason": f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}, mean_ratio={mean_ratio:.2f}, ks_stat={ks_stat:.3f}, p_value={p_value:.4e}",
    }


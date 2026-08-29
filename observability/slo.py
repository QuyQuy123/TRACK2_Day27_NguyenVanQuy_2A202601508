from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "multiwindow",
    critical_threshold: float = 14.4,
    warning_threshold: float = 6.0,
) -> dict[str, Any]:
    """Evaluate multi-window multi-burn-rate alerting policy based on Google SRE Workbook.

    Rules:
    - Sustained fast burn: BOTH short_window_burn >= critical_threshold AND long_window_burn >= critical_threshold -> page = True, severity = "critical".
    - Sustained moderate burn: BOTH short_window_burn >= warning_threshold AND long_window_burn >= warning_threshold -> page = True, severity = "warning".
    - Transient spike: short_window_burn is high but long_window_burn < warning_threshold -> page = False, severity = "info", reason = "transient_spike_suppressed".
    - Slow burn: long_window_burn is elevated but short window has recovered -> page = False, severity = "warning", reason = "slow_burn_ticket".
    - Normal: within allowed error budget -> page = False, severity = "info", reason = "healthy_error_budget".
    """
    short_b = float(short_window_burn)
    long_b = float(long_window_burn)

    if short_b >= critical_threshold and long_b >= critical_threshold:
        return {
            "page": True,
            "severity": "critical",
            "reason": f"sustained_critical_fast_burn (short={short_b:.1f}x, long={long_b:.1f}x >= {critical_threshold}x)",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
        }

    if short_b >= warning_threshold and long_b >= warning_threshold:
        return {
            "page": True,
            "severity": "warning",
            "reason": f"sustained_moderate_burn (short={short_b:.1f}x, long={long_b:.1f}x >= {warning_threshold}x)",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
        }

    if short_b >= warning_threshold and long_b < warning_threshold:
        return {
            "page": False,
            "severity": "info",
            "reason": f"transient_spike_suppressed (short={short_b:.1f}x high, but long={long_b:.1f}x low)",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
        }

    if long_b >= warning_threshold and short_b < warning_threshold:
        return {
            "page": False,
            "severity": "warning",
            "reason": f"slow_burn_non_paging (long={long_b:.1f}x elevated, short={short_b:.1f}x normal)",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
        }

    return {
        "page": False,
        "severity": "info",
        "reason": f"healthy_error_budget (short={short_b:.1f}x, long={long_b:.1f}x)",
        "short_window_burn": short_b,
        "long_window_burn": long_b,
    }


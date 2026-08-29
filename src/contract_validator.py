"""Comprehensive contract validator.

Supports:
- column/field presence and not-null checks
- uniqueness checks
- accepted values checks
- numeric range checks (min, max)
- string length checks (min_length, max_length)
- strict type validation (integer, number/float, string, datetime, boolean)
- dataset-level freshness checks with configurable severity
- severity-aware filtering and action recommendations (block, quarantine, warn, pass)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_type(series: pd.Series, expected_type: str) -> tuple[bool, int]:
    """Validate data types without silent coercion."""
    non_null = series.dropna()
    if non_null.empty:
        return True, 0

    expected = expected_type.lower().strip()
    invalid_count = 0

    if expected in {"integer", "int", "bigint", "int64", "int32"}:
        for val in non_null:
            if isinstance(val, (bool, np.bool_)):
                invalid_count += 1
            elif isinstance(val, (int, np.integer)):
                continue
            elif isinstance(val, (float, np.floating)):
                if not np.isfinite(val) or val != int(val):
                    invalid_count += 1
            elif isinstance(val, str):
                try:
                    f = float(val)
                    if f != int(f):
                        invalid_count += 1
                except ValueError:
                    invalid_count += 1
            else:
                invalid_count += 1

    elif expected in {"number", "float", "double", "numeric", "float64"}:
        for val in non_null:
            if isinstance(val, (bool, np.bool_)):
                invalid_count += 1
            elif isinstance(val, (int, float, np.number)):
                if isinstance(val, float) and not np.isfinite(val):
                    invalid_count += 1
            elif isinstance(val, str):
                try:
                    float(val)
                except ValueError:
                    invalid_count += 1
            else:
                invalid_count += 1

    elif expected in {"string", "str", "varchar", "text"}:
        for val in non_null:
            if not isinstance(val, str):
                invalid_count += 1

    elif expected in {"datetime", "timestamp", "date"}:
        converted = pd.to_datetime(non_null, errors="coerce", utc=True)
        invalid_count = int(converted.isna().sum())

    elif expected in {"boolean", "bool"}:
        for val in non_null:
            if isinstance(val, (bool, np.bool_)):
                continue
            if isinstance(val, str) and val.lower() in {"true", "false", "1", "0"}:
                continue
            if isinstance(val, (int, float)) and val in {0, 1}:
                continue
            invalid_count += 1

    return (invalid_count == 0), invalid_count


def validate_dataframe(
    df: pd.DataFrame,
    contract: dict[str, Any],
    *,
    reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    columns = contract.get("columns") or contract.get("fields") or {}

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
            continue

        series = df[column]

        if required:
            null_count = int(series.isna().sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )

        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )

        expected_type = rules.get("type")
        if expected_type:
            type_passed, type_invalid = _validate_type(series, expected_type)
            issues.append(
                _issue(
                    "type",
                    column=column,
                    severity=severity,
                    passed=type_passed,
                    details=f"expected_type={expected_type}; invalid_count={type_invalid}",
                )
            )

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )

        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = pd.Series(False, index=series.index)
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

        if "min_length" in rules or "max_length" in rules:
            non_null = series.dropna().astype(str)
            lengths = non_null.str.len()
            invalid_len = pd.Series(False, index=non_null.index)
            if "min_length" in rules:
                invalid_len |= lengths < rules["min_length"]
            if "max_length" in rules:
                invalid_len |= lengths > rules["max_length"]
            invalid_count = int(invalid_len.sum())
            issues.append(
                _issue(
                    "length",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

    # Freshness check
    freshness = contract.get("freshness")
    if freshness and isinstance(freshness, dict):
        col = freshness.get("column")
        max_delay = freshness.get("max_delay_minutes", 60)
        sev = freshness.get("severity", "warning")

        if not col or col not in df.columns:
            issues.append(
                _issue(
                    "freshness",
                    column=col,
                    severity=sev,
                    passed=False,
                    details=f"Freshness column '{col}' missing",
                )
            )
        else:
            timestamps = pd.to_datetime(df[col], utc=True, errors="coerce")
            valid_ts = timestamps.dropna()
            if valid_ts.empty:
                issues.append(
                    _issue(
                        "freshness",
                        column=col,
                        severity=sev,
                        passed=False,
                        details="No valid timestamps in freshness column",
                    )
                )
            else:
                latest = valid_ts.max()
                now = pd.Timestamp(reference_time or datetime.now(timezone.utc))
                delay_minutes = (now - latest).total_seconds() / 60.0
                passed = bool(0 <= delay_minutes <= max_delay)
                issues.append(
                    _issue(
                        "freshness",
                        column=col,
                        severity=sev,
                        passed=passed,
                        details=f"delay_minutes={delay_minutes:.1f}; max_delay_minutes={max_delay}",
                    )
                )

    return issues


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order.get(min_severity, 1)
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]


def determine_action(issues: list[dict[str, Any]]) -> str:
    """Determine operational action from validation issues: block, quarantine, warn, or pass."""
    failed = [i for i in issues if not i.get("passed", False)]
    if not failed:
        return "pass"

    has_critical = any(i.get("severity") == "critical" for i in failed)
    critical_checks = {i.get("check") for i in failed if i.get("severity") == "critical"}

    if has_critical:
        if "unique" in critical_checks or "not_null" in critical_checks or "type" in critical_checks:
            return "quarantine"
        return "block"

    has_warning = any(i.get("severity") == "warning" for i in failed)
    if has_warning:
        return "warn"

    return "info"


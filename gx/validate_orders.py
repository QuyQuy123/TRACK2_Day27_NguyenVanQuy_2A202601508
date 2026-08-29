#!/usr/bin/env python3
"""Great Expectations Core 1.21 validation workflow.

Builds a complete Expectation Suite, Validation Definition, Checkpoint,
and executes validation with severity-aware action handling.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc


def build_orders_suite(context: gx.DataContext) -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name="orders_contract_suite")
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="order_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="amount", min_value=0)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(column="currency", value_set=["USD", "VND"])
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="status",
            value_set=["pending", "completed", "refunded", "cancelled"],
        )
    )
    return context.suites.add(suite)


def run_orders_checkpoint(df: pd.DataFrame) -> bool:
    context = gx.get_context(mode="ephemeral")

    # Data Source & Asset
    data_source = context.data_sources.add_pandas("orders_source")
    asset = data_source.add_dataframe_asset(name="orders_dataframe_asset")
    batch_definition = asset.add_batch_definition_whole_dataframe("orders_batch_definition")

    # Expectation Suite
    suite = build_orders_suite(context)

    # Validation Definition
    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="orders_validation_definition",
            data=batch_definition,
            suite=suite,
        )
    )

    # Checkpoint
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="orders_checkpoint",
            validation_definitions=[validation_definition],
        )
    )

    # Execute Checkpoint
    result = checkpoint.run(batch_parameters={"dataframe": df})
    success = bool(result.success)

    print("=== GREAT EXPECTATIONS VALIDATION RESULTS ===")
    for val_result in result.run_results.values():
        for res in val_result.results:
            exp_type = res.expectation_config.type
            column = res.expectation_config.kwargs.get("column", "table")
            status = "PASS" if res.success else "FAIL"
            print(f"[{status}] {exp_type:<38} (column={column})")

    # Action determination
    action = "PASS" if success else "QUARANTINE_AND_BLOCK"
    print(f"\nOverall Checkpoint Status: {'SUCCESS' if success else 'FAILED'}")
    print(f"Recommended Pipeline Action: {action}")
    return success


def main() -> None:
    orders_path = ROOT / "data" / "incoming" / "orders.csv"
    if not orders_path.exists():
        orders_path = ROOT / "data" / "baseline" / "orders.csv"

    df = pd.read_csv(orders_path)
    success = run_orders_checkpoint(df)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()


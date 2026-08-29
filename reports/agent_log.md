# AI Agent Decision Log

This log documents key engineering decisions, hypotheses, agent proposals, validation evidence, and rationale throughout the Data Reliability Game Day implementation.

## Decision 1: Robust Anomaly Detection with MAD & Day-of-Week Segmentation
- **Hypothesis:** Standard Z-Score fails on skewed e-commerce traffic (e.g. weekend vs weekday volume shifts) and is vulnerable to extreme outlier distortion.
- **Prompt / request to agent:** Implement a MAD-based Modified Z-score detector in `observability/anomaly.py` handling zero-MAD edge cases, and enhance `method="auto"` to be context-aware (leveraging `same_segment_history`, `day_of_week`, and `known_event`).
- **Agent proposal:** Replaced naive Z-score default with Modified Z-score ($0.6745 \times \frac{|x - \text{median}|}{\text{MAD}}$), added mean absolute deviation fallback when $\text{MAD} = 0$, and routed contextual weekday segment history when provided.
- **Evidence/test:** `tests_public/test_anomaly.py` passed both outlier detection (`test_large_volume_drop_is_anomaly`) and zero-MAD handling (`test_mad_detector_handles_outliers_and_zero_mad`), correctly catching 75% volume drop without false positives on regular Saturday volume.
- **Accept / reject / revise:** **Accept**.
- **Why:** Robust statistics provide resilience against seasonal fluctuations and extreme variance without requiring heavy ML models.

## Decision 2: Dimension Join Fan-out Protection & dbt Unit Tests
- **Hypothesis:** Joining `stg_orders` with `stg_customers` (`is_active = true`) without deduplication will silently inflate daily revenue if a customer has multiple active records (e.g. SCD Type 2 misconfiguration).
- **Prompt / request to agent:** Write the smallest dbt unit test that exposes revenue inflation when customer dimension contains two active rows for the same customer, and protect `fct_daily_revenue.sql`.
- **Agent proposal:** Created `dbt_project/models/marts/unit_tests.yml` with `completed_orders_sum_to_expected_revenue` and `duplicate_active_customer_does_not_inflate_revenue`. Refactored `fct_daily_revenue.sql` using `select distinct customer_id from stg_customers where is_active = true`.
- **Evidence/test:** `dbt build --project-dir dbt_project --profiles-dir dbt_project` executed 16/16 tests with both unit tests passing in DuckDB.
- **Accept / reject / revise:** **Accept**.
- **Why:** SQL syntax alone cannot detect logical fan-out; deterministic dbt unit tests ensure transformation invariants hold across dimension edge cases.

## Decision 3: Strict Contract Type Checking and Freshness Engine
- **Hypothesis:** `pd.to_numeric(..., errors='coerce')` silently masks type corruption (e.g. string IDs or bad types converted to NaN), and static freshness checks break when test dates change.
- **Prompt / request to agent:** Build a strict type checker in `src/contract_validator.py` covering integer, float, string, datetime, boolean and length constraints (`min_length`), plus dataset-level freshness with configurable reference time.
- **Agent proposal:** Implemented `_validate_type()` verifying non-coercible values, supported both `columns` and `fields` contract formats, and implemented freshness delay evaluation against UTC reference timestamps.
- **Evidence/test:** `tests_public/test_contracts.py` passed all checks including `test_type_drift_is_detected`, `test_stale_data_is_detected`, and `test_invalid_currency_is_detected`.
- **Accept / reject / revise:** **Accept**.
- **Why:** Upstream schema contracts must act as hard boundaries preventing corrupt data from entering the warehouse.

## Decision 4: Google SRE Multi-Window Multi-Burn-Rate Policy
- **Hypothesis:** Single-window error budget alerting either causes alert fatigue on transient spikes or fails to catch sustained burn before budget is exhausted.
- **Prompt / request to agent:** Implement `evaluate_multiwindow_burn` based on Google SRE Workbook using dual short (1h) and long (6h) window burn rates.
- **Agent proposal:** Implemented dual-window policy: page only when BOTH short $\ge 14.4\times$ and long $\ge 14.4\times$ (critical) or $\ge 6.0\times$ (warning); suppress single short transient spikes ($\text{page} = \text{False}$).
- **Evidence/test:** `tests_public/test_slo.py` verified that sustained 15x burn triggers `page=True, severity="critical"`, while a 20x short spike with 2x long window returns `page=False, severity="info"`.
- **Accept / reject / revise:** **Accept**.
- **Why:** Eliminates paging noise while guaranteeing fast detection of severe budget-draining incidents.

## Decision 5: Transitive Column & Dataset Lineage Traversal
- **Hypothesis:** Starter `get_column_downstream` only returned immediate children (1-hop), failing to trace transitive end-to-end blast radius.
- **Prompt / request to agent:** Implement BFS graph traversal for column-level lineage in `observability/lineage.py`.
- **Agent proposal:** Implemented queue-based BFS tracking visited nodes for full transitive closure.
- **Evidence/test:** `test_transitive_column_downstream` in `test_lineage.py` successfully traversed `raw_orders.order_id` $\rightarrow$ `stg_orders.order_id` $\rightarrow$ `fct_daily_revenue.completed_order_rows` $\rightarrow$ `dashboard.kpi_orders`.
- **Accept / reject / revise:** **Accept**.
- **Why:** Enables accurate automated blast radius determination when a column contract breaks upstream.


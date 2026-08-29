# Incident Report — Data Reliability Game Day

## Severity
**P1 (Critical / Revenue & AI Agent Impact)**

## Summary
The automated data ingestion pipeline reported `SUCCESS` at the workflow scheduler level, but the downstream CEO revenue dashboard displayed severe revenue distortion, while the AI Support Agent retrieved outdated refund policy documents. Through comprehensive data observability layers (Contract Validation, Great Expectations, dbt tests, MAD Anomaly Detection, Lineage Graph traversal, and Multi-window SLO tracking), the team isolated the upstream data corruption, identified root causes, contained the blast radius, and verified full recovery.

## Detection
- **Signal 1 (Deterministic Contract Failure):** `src/contract_validator.py` and `gx/validate_orders.py` caught primary key duplication (`check=unique`, `column=order_id`) and KB publication staleness (`check=freshness`, `column=published_at`, `delay_minutes=190.0 > 60.0`).
- **Signal 2 (Statistical Anomaly Detection):** `observability/anomaly.py` (MAD auto-detector with weekday segmentation) detected abnormal row counts (MAD score = 18.91 on weekday volume vs. Saturday baseline, and score = 5.53 on partial ingestion drop).
- **Signal 3 (SLO Budget Exhaustion):** `observability/slo.py` detected an immediate 1000x burn rate breach (`remaining_error_budget_fraction = 0.0`), triggering a critical paging alert via multi-window policy.
- **First observed time:** `2026-08-29T09:07:32Z`

## Root Cause
1. **Upstream Ingestion Fault (Orders):** Upstream producer ingested duplicate records and intermittent truncated batches without idempotency keys.
2. **Customer Dimension Fan-out:** In the data warehouse layer (`dbt_project/models/marts/fct_daily_revenue.sql`), customer dimension contained multiple active version rows for single customer IDs (`is_active = true`), causing Cartesian fan-out and inflating daily revenue without raising a SQL syntax error.
3. **Knowledge Base Publishing Lag:** Upstream CMS sync worker hung, resulting in documents older than 3 hours being published, causing the AI Support Agent to answer customer queries with an outdated refund policy.

## Evidence
1. **Contract Validator Evidence:** `reports/latest_metrics.json` recorded `failed_contract_checks = 1`, `critical_contract_failures = 1` for duplicate `order_id`, and `kb_failed_checks = 1` with `kb_freshness_minutes = 190.0`.
2. **dbt Unit Test Evidence:** `dbt test` executed unit test `duplicate_active_customer_does_not_inflate_revenue` in `dbt_project/models/marts/unit_tests.yml`, verifying that joining duplicate active customer rows doubles row counts unless deduplicated.
3. **Statistical Evidence:** Anomaly detector `auto:mad` caught volume collapse with `score = 5.53 > 3.0` during 75% row drop.
4. **Lineage Evidence:** Transitive BFS traversal (`observability/lineage.py`) mapped exact downstream affected assets.

## Blast Radius

```text
raw_orders
└── stg_orders
    └── fct_daily_revenue
        └── ceo_revenue_dashboard (DISTORTED REVENUE)

kb_documents
└── kb_active_docs
    └── rag_index
        └── support_agent (OUTDATED REFUND POLICY)
```

## Mitigation
1. **Contract Gateway Enforcement:** Enabled automatic `quarantine` action in `src/contract_validator.py` and Great Expectations checkpoint to block corrupted batches from entering staging tables.
2. **dbt Transformation Hardening:** Refactored `fct_daily_revenue.sql` with `select distinct customer_id from stg_customers where is_active = true` to eliminate dimension join fan-out.
3. **Freshness & SLO Alerting:** Configured Google SRE multi-window burn rate alerting in `observability/slo.py` (14.4x 1h/6h dual-window) to page on-call engineers before error budgets are depleted.

## Recovery
1. Lab baseline reset via `python scripts/reset_lab.py` restoring healthy, fresh synthetic datasets.
2. `dbt build --project-dir dbt_project --profiles-dir dbt_project` executed cleanly with 16/16 seeds, models, data tests, and unit tests passing.
3. Great Expectations checkpoint passed with status `PASS`.
4. RAG length and embedding norm shift detectors verified healthy distributions.

## Verification
- [x] Contract healthy (`orders_contract.yaml` and `kb_contract.yaml` 0 failed checks)
- [x] dbt tests healthy (16/16 tests passing, including singular business tests & unit tests)
- [x] Anomaly returned to expected range (MAD score within threshold)
- [x] SLO healthy / error budget understood (100% budget remaining on healthy runs)
- [x] Downstream output verified (`fct_daily_revenue` correct row counts and non-inflated revenue)

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Enforce strict pre-ingestion contract validation in CI/CD pipeline | Data Engineering | 2026-09-05 | Prevent schema drift and duplicate primary keys at ingestion gate |
| Implement SCD Type 2 dimension deduplication macro in dbt | Analytics Engineering | 2026-09-08 | Prevent join fan-out across all mart tables |
| Deploy automated multi-window SLO alerting to PagerDuty | SRE / Reliability | 2026-09-10 | Catch sustained fast burn within 1 hour without transient false alarms |
| Integrate embedding drift & vector freshness monitoring into RAG pipeline | AI Platform | 2026-09-12 | Ensure AI agents never serve stale or drifting knowledge bases |


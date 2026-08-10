# Issue: Enhancement of Shareholder Analysis (Time-Series)

## Overview
We now have multi-month shareholder data (MAR2026, DEC3383, etc.). The current dashboard only shows static "Top Holder" snapshots. We need to leverage this time-series data to provide actionable intelligence regarding accumulation and distribution patterns.

## Tasks

### 1. Backend: Accumulation/Distribution Detection
- [ ] Create a new service function `get_shareholder_trends(stock_code)` that calculates the month-over-month (MoM) change in percentage for top shareholders.
- [ ] Implement a logic to flag stocks with "Accumulation" (MoM increase > 3%) vs "Distribution" (MoM decrease > 3%).
- [ ] Store these flags in a new temporary table or cache to prevent slow real-time recalculation.

### 2. Backend: Whale Movement Tracker
- [ ] Identify recurring `shareholder_name` entries across multiple stocks.
- [ ] Flag "Smart Money" investors (those appearing in >3 top-holder lists).
- [ ] Create an endpoint `/api/shareholders/smart-money` to list these entities and their combined portfolio.

### 3. Dashboard UI: Trend Visualization
- [ ] Update the `Shareholders` dashboard table to include a `TREND` column.
- [ ] Use icons: ▲ (Green) for Accumulation, ▼ (Red) for Distribution, ▬ (Grey) for Stable.
- [ ] Add a "Top Accumulation" section in the dashboard to highlight stocks currently being bought by major holders.

### 4. Database Optimization
- [ ] Add indexing on `(stock_code, data_period)` to speed up trend calculation queries.
- [ ] Ensure the `bulk_import` logic correctly handles data overwrites if a specific period is re-uploaded.

## Deliverables
- API endpoint returning MoM percentage changes.
- UI components (icons/badges) showing trend status.
- A "Smart Money" tracking view.

## Priority: Medium
## Notes
- Be careful with `Every derived table must have its own alias` MySQL error when writing these complex aggregate queries.
- Refer to `shareholder_service.py` for existing data access patterns.

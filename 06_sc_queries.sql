-- ============================================================
-- Middleton Finance Suite — Supply Chain SQL Queries
-- ============================================================
-- Databases:
--   demand_planning.db  → sku_forecast, actuals, forecast_accuracy
--   inventory.db        → inventory_positions, holding_costs, slow_movers
--   cogs_margin.db      → cost_breakdown, standard_vs_actual, margin_waterfall
--
-- Run via:  python 07_run_sc_queries.py
-- ============================================================


-- ────────────────────────────────────────────
-- SECTION 5: DEMAND PLANNING & FORECAST ACCURACY
-- Database: demand_planning.db
-- ────────────────────────────────────────────

-- 5A. Forecast accuracy (MAPE) by product category
SELECT
    category,
    COUNT(*)                                        AS observations,
    ROUND(AVG(mape)*100, 2)                        AS avg_mape_pct,
    ROUND(AVG(bias_pct)*100, 2)                    AS avg_bias_pct,
    SUM(under_forecast)                             AS under_forecast_count,
    SUM(over_forecast)                              AS over_forecast_count,
    ROUND(SUM(CASE WHEN mape < 0.10 THEN 1 END)*100.0/COUNT(*), 1)
                                                    AS pct_within_10pct
FROM forecast_accuracy
GROUP BY category
ORDER BY avg_mape_pct DESC;


-- 5B. Monthly forecast vs. actual by category
SELECT
    a.month,
    a.category,
    SUM(f.forecast_units)                           AS total_forecast,
    SUM(a.actual_units)                             AS total_actual,
    SUM(a.actual_units) - SUM(f.forecast_units)    AS unit_variance,
    ROUND((SUM(a.actual_units) - SUM(f.forecast_units))*100.0
          / NULLIF(SUM(f.forecast_units), 0), 1)   AS variance_pct,
    ROUND(SUM(a.actual_revenue)/1e6, 2)            AS actual_rev_mm,
    ROUND(SUM(a.gross_profit)/1e6, 2)              AS gross_profit_mm
FROM actuals a
JOIN sku_forecast f ON a.sku_id = f.sku_id AND a.month = f.month
GROUP BY a.month, a.category
ORDER BY a.month, a.category;


-- 5C. Worst-performing SKUs by MAPE
SELECT
    sku_id,
    sku_name,
    category,
    ROUND(AVG(mape)*100, 2)                        AS avg_mape_pct,
    ROUND(AVG(bias_pct)*100, 2)                    AS avg_bias_pct,
    ROUND(MAX(ABS(error_units)), 0)                AS worst_single_miss_units,
    COUNT(CASE WHEN mape > 0.20 THEN 1 END)        AS months_over_20pct_error
FROM forecast_accuracy
GROUP BY sku_id, sku_name, category
ORDER BY avg_mape_pct DESC
LIMIT 10;


-- 5D. Forecast bias analysis — systematic over/under by category
SELECT
    category,
    ROUND(AVG(bias_pct)*100, 2)                    AS avg_bias_pct,
    ROUND(MIN(bias_pct)*100, 2)                    AS worst_neg_bias_pct,
    ROUND(MAX(bias_pct)*100, 2)                    AS worst_pos_bias_pct,
    CASE
        WHEN AVG(bias_pct) > 0.05  THEN 'Under-Forecasting — Demand Surprise Risk'
        WHEN AVG(bias_pct) < -0.05 THEN 'Over-Forecasting — Excess Inventory Risk'
        ELSE 'Balanced'
    END                                             AS bias_assessment
FROM forecast_accuracy
GROUP BY category
ORDER BY ABS(AVG(bias_pct)) DESC;


-- 5E. Quarterly revenue variance — forecast vs. actual
SELECT
    a.quarter,
    ROUND(SUM(f.forecast_value)/1e6, 2)            AS forecast_rev_mm,
    ROUND(SUM(a.actual_revenue)/1e6, 2)            AS actual_rev_mm,
    ROUND((SUM(a.actual_revenue)-SUM(f.forecast_value))/1e6, 2)
                                                    AS variance_mm,
    ROUND(AVG(fa.mape)*100, 2)                     AS avg_mape_pct
FROM actuals a
JOIN sku_forecast f    ON a.sku_id = f.sku_id AND a.month = f.month
JOIN forecast_accuracy fa ON a.sku_id = fa.sku_id AND a.month = fa.month
GROUP BY a.quarter
ORDER BY a.quarter;


-- ────────────────────────────────────────────
-- SECTION 6: INVENTORY HEALTH & HOLDING COST
-- Database: inventory.db
-- ────────────────────────────────────────────

-- 6A. Days Inventory Outstanding (DIO) vs. target by category
SELECT
    category,
    ROUND(AVG(days_inventory_outstanding), 1)      AS avg_dio,
    ROUND(AVG(target_dio), 1)                      AS target_dio,
    ROUND(AVG(dio_variance), 1)                    AS avg_variance_days,
    ROUND(SUM(inventory_value)/1e6, 2)             AS total_inv_value_mm,
    ROUND(AVG(inventory_turns), 2)                 AS avg_inv_turns
FROM inventory_positions
GROUP BY category
ORDER BY avg_variance_days DESC;


-- 6B. Total holding cost by category and component
SELECT
    category,
    ROUND(SUM(total_holding_cost)/1e6, 3)          AS total_holding_cost_mm,
    ROUND(SUM(cost_of_capital)/1e6, 3)             AS cost_of_capital_mm,
    ROUND(SUM(storage_cost)/1e6, 3)                AS storage_cost_mm,
    ROUND(SUM(insurance_cost)/1e6, 3)              AS insurance_cost_mm,
    ROUND(SUM(obsolescence_risk)/1e6, 3)           AS obsolescence_risk_mm,
    ROUND(SUM(total_holding_cost)*100.0/SUM(inventory_value), 2)
                                                    AS effective_holding_rate_pct
FROM holding_costs
GROUP BY category
ORDER BY total_holding_cost_mm DESC;


-- 6C. Monthly holding cost trend
SELECT
    month,
    ROUND(SUM(total_holding_cost)/1e6, 3)          AS monthly_holding_cost_mm,
    ROUND(SUM(inventory_value)/1e6, 2)             AS inventory_value_mm,
    ROUND(SUM(cost_of_capital)/1e6, 3)             AS cap_cost_mm,
    ROUND(SUM(storage_cost)/1e6, 3)                AS storage_mm,
    ROUND(SUM(obsolescence_risk)/1e6, 3)           AS obs_risk_mm
FROM holding_costs
GROUP BY month
ORDER BY month;


-- 6D. Slow movers and excess inventory by category
SELECT
    category,
    SUM(slow_mover_flag)                           AS slow_mover_skus,
    ROUND(AVG(months_no_movement), 1)              AS avg_months_no_movement,
    ROUND(SUM(excess_units), 0)                    AS total_excess_units,
    ROUND(SUM(excess_value)/1e3, 1)                AS excess_value_k,
    ROUND(SUM(write_off_risk)/1e3, 1)              AS write_off_risk_k
FROM slow_movers
WHERE slow_mover_flag = 1
GROUP BY category
ORDER BY write_off_risk_k DESC;


-- 6E. Inventory position by warehouse
SELECT
    warehouse,
    ROUND(AVG(days_inventory_outstanding), 1)      AS avg_dio,
    ROUND(SUM(inventory_value)/1e6, 2)             AS inv_value_mm,
    ROUND(SUM(on_hand_units), 0)                   AS total_on_hand,
    ROUND(SUM(on_order_units), 0)                  AS total_on_order,
    ROUND(AVG(inventory_turns), 2)                 AS avg_turns
FROM inventory_positions
GROUP BY warehouse
ORDER BY avg_dio DESC;


-- ────────────────────────────────────────────
-- SECTION 7: COGS & GROSS MARGIN ANALYSIS
-- Database: cogs_margin.db
-- ────────────────────────────────────────────

-- 7A. Gross margin waterfall by category
SELECT
    category,
    ROUND(SUM(list_revenue)/1e6, 2)                AS list_rev_mm,
    ROUND(SUM(discount_amount)/1e6, 2)             AS discount_mm,
    ROUND(SUM(net_revenue)/1e6, 2)                 AS net_rev_mm,
    ROUND(SUM(cogs_total)/1e6, 2)                  AS cogs_mm,
    ROUND(SUM(gross_profit)/1e6, 2)                AS gross_profit_mm,
    ROUND(AVG(gross_margin_pct)*100, 2)            AS avg_gm_pct,
    ROUND(AVG(discount_pct)*100, 2)                AS avg_disc_pct
FROM margin_waterfall
GROUP BY category
ORDER BY gross_profit_mm DESC;


-- 7B. COGS component breakdown by category
SELECT
    category,
    ROUND(SUM(materials_cogs)/SUM(cogs_total)*100, 1)  AS materials_pct,
    ROUND(SUM(labor_cogs)/SUM(cogs_total)*100, 1)      AS labor_pct,
    ROUND(SUM(overhead_cogs)/SUM(cogs_total)*100, 1)   AS overhead_pct,
    ROUND(SUM(logistics_cogs)/SUM(cogs_total)*100, 1)  AS logistics_pct,
    ROUND(SUM(yield_loss_cogs)/SUM(cogs_total)*100, 1) AS yield_loss_pct,
    ROUND(SUM(cogs_total)/1e6, 2)                      AS total_cogs_mm
FROM margin_waterfall
GROUP BY category
ORDER BY total_cogs_mm DESC;


-- 7C. Standard vs. actual cost variance by category
SELECT
    category,
    ROUND(AVG(standard_unit_cost), 2)              AS std_unit_cost,
    ROUND(AVG(actual_unit_cost), 2)                AS act_unit_cost,
    ROUND(AVG(total_cost_variance), 2)             AS avg_unit_variance,
    ROUND(AVG(materials_variance), 2)              AS avg_materials_var,
    ROUND(AVG(labor_variance), 2)                  AS avg_labor_var,
    ROUND(AVG(overhead_variance), 2)               AS avg_overhead_var,
    ROUND(AVG(logistics_variance), 2)              AS avg_logistics_var,
    ROUND(AVG(yield_variance), 2)                  AS avg_yield_var,
    COUNT(CASE WHEN favorable = 1 THEN 1 END)      AS favorable_months,
    COUNT(CASE WHEN favorable = 0 THEN 1 END)      AS unfavorable_months
FROM standard_vs_actual
GROUP BY category
ORDER BY avg_unit_variance DESC;


-- 7D. Monthly COGS and margin trend
SELECT
    month,
    ROUND(SUM(net_revenue)/1e6, 2)                 AS net_rev_mm,
    ROUND(SUM(cogs_total)/1e6, 2)                  AS cogs_mm,
    ROUND(SUM(gross_profit)/1e6, 2)                AS gp_mm,
    ROUND(AVG(gross_margin_pct)*100, 2)            AS avg_gm_pct,
    ROUND(AVG(discount_pct)*100, 2)                AS avg_disc_pct
FROM margin_waterfall
GROUP BY month
ORDER BY month;


-- 7E. Supplier cost variance — which suppliers drive overruns
SELECT
    supplier,
    COUNT(DISTINCT sku_id)                         AS sku_count,
    ROUND(AVG(total_cost_variance), 2)             AS avg_unit_variance,
    ROUND(AVG(total_cost_variance)/AVG(standard_unit_cost)*100, 2)
                                                    AS variance_pct_of_std,
    COUNT(CASE WHEN favorable = 1 THEN 1 END)      AS favorable_months,
    COUNT(CASE WHEN favorable = 0 THEN 1 END)      AS unfavorable_months,
    ROUND(SUM(units_produced), 0)                  AS total_units
FROM standard_vs_actual
GROUP BY supplier
ORDER BY avg_unit_variance DESC;


-- ────────────────────────────────────────────
-- SECTION 8: CROSS-DATABASE SNAPSHOTS
-- ────────────────────────────────────────────

-- 8A. Supply chain health (demand_planning.db)
SELECT 'Avg Forecast MAPE (FY2024)'        AS metric,
       ROUND(AVG(mape)*100, 2) || '%'      AS value
FROM forecast_accuracy
UNION ALL
SELECT 'Total Actual Revenue ($M)',
       ROUND(SUM(actual_revenue)/1e6, 1)
FROM actuals
UNION ALL
SELECT 'Avg Forecast Bias %',
       ROUND(AVG(bias_pct)*100, 2) || '%'
FROM forecast_accuracy;


-- 8B. Inventory health (inventory.db)
SELECT 'Total Inventory Value ($M)'        AS metric,
       ROUND(SUM(inventory_value)/1e6, 1)  AS value
FROM inventory_positions
UNION ALL
SELECT 'Avg DIO (All Categories)',
       ROUND(AVG(days_inventory_outstanding), 1)
FROM inventory_positions
UNION ALL
SELECT 'Slow Mover SKUs Flagged',
       SUM(slow_mover_flag)
FROM slow_movers;


-- 8C. COGS health (cogs_margin.db)
SELECT 'Total Net Revenue ($M)'            AS metric,
       ROUND(SUM(net_revenue)/1e6, 1)      AS value
FROM margin_waterfall
UNION ALL
SELECT 'Avg Gross Margin %',
       ROUND(AVG(gross_margin_pct)*100, 2) || '%'
FROM margin_waterfall
UNION ALL
SELECT 'Favorable Cost Variance Months',
       COUNT(CASE WHEN favorable = 1 THEN 1 END)
FROM standard_vs_actual;

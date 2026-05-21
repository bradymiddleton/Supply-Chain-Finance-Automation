"""
Middleton Finance Suite — Supply Chain Edition
Script 05: Generate Supply Chain Data & Load into SQLite Databases

Datasets modeled after:
  - Product Demand Forecasting (Kaggle: felixzhao/productdemandforecasting)
  - Demand Forecast for Inventory (Kaggle: oscarm524/demand-forecast-for-optimized-inventory-planning)
    → demand_planning.db

  - Supply Chain Dataset (Kaggle: amirmotefaker/supply-chain-dataset)
  - Retail Store Inventory (Kaggle: anirudhchauhan/retail-store-inventory-forecasting-dataset)
    → inventory.db

  - Logistics and Supply Chain (Kaggle: datasetengineer/logistics-and-supply-chain-dataset)
    → cogs_margin.db

Usage:
    python 05_generate_sc_data.py

Outputs:
    sc_databases/demand_planning.db
    sc_databases/inventory.db
    sc_databases/cogs_margin.db
    sc_exports/*.csv
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(99)
random.seed(99)

DB_DIR     = "sc_databases"
EXPORT_DIR = "sc_exports"
os.makedirs(DB_DIR,     exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ── Shared Reference Data ────────────────────────────────────

PRODUCT_CATEGORIES = ["GPUs", "CPUs", "Embedded", "Semi-Custom", "Adaptive Computing"]

SKUS = {
    "GPUs": [
        ("GPU-MI300X", "Instinct MI300X", 38500, 0.62),
        ("GPU-MI250",  "Instinct MI250",  24200, 0.63),
        ("GPU-RX7900", "Radeon RX 7900",   9800, 0.60),
        ("GPU-RX7800", "Radeon RX 7800",   5400, 0.59),
        ("GPU-W7900",  "Radeon PRO W7900",12800, 0.64),
    ],
    "CPUs": [
        ("CPU-EP9654",  "EPYC Genoa 9654",    10200, 0.57),
        ("CPU-EP9754",  "EPYC Bergamo 9754",   8800, 0.58),
        ("CPU-R97950X", "Ryzen 9 7950X",       1850, 0.52),
        ("CPU-TRP",     "Threadripper PRO",    5600, 0.56),
    ],
    "Embedded": [
        ("EMB-VAIC",  "Versal AI Core",  3200, 0.54),
        ("EMB-VPREM", "Versal Premium",  4800, 0.55),
        ("EMB-K26",   "Kria K26 SOM",    1100, 0.50),
    ],
    "Semi-Custom": [
        ("SC-XBOX",  "Xbox Custom APU",      2800, 0.68),
        ("SC-PS",    "PlayStation Custom APU", 3100, 0.69),
        ("SC-STEAM", "Steam Deck APU",        1400, 0.66),
    ],
    "Adaptive Computing": [
        ("AC-U55C", "Alveo U55C", 6800, 0.59),
        ("AC-U250", "Alveo U250", 9200, 0.61),
        ("AC-V80",  "Alveo V80",  14500, 0.63),
    ],
}

# Flatten SKU list
ALL_SKUS = []
for cat, skus in SKUS.items():
    for sku_id, name, unit_cost, cogs_pct in skus:
        ALL_SKUS.append({
            "sku_id": sku_id,
            "sku_name": name,
            "category": cat,
            "standard_unit_cost": unit_cost,
            "cogs_pct": cogs_pct,
        })

REGIONS     = ["West", "East", "Central", "South", "EMEA", "APAC"]
WAREHOUSES  = ["Dallas TX", "Portland OR", "Columbus OH", "Atlanta GA",
                "Amsterdam NL", "Singapore SG"]
SUPPLIERS   = ["TSMC (Primary)", "Samsung Foundry", "UMC", "GlobalFoundries",
                "ASE Group", "Amkor Technology"]

MONTHS_2024 = pd.date_range("2024-01-01", "2024-12-01", freq="MS")
QUARTERS_2024 = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]

def qtr(dt):
    return f"Q{((dt.month-1)//3)+1} {dt.year}"


# ════════════════════════════════════════════════════════════
# DATABASE 1: demand_planning.db
# Tables: sku_forecast, actuals, forecast_accuracy
# ════════════════════════════════════════════════════════════

def build_demand_planning_db():
    print("Building demand_planning.db ...")

    forecast_rows = []
    actual_rows   = []
    accuracy_rows = []

    for sku in ALL_SKUS:
        # Base monthly demand varies by category
        base_demand = {
            "GPUs": 420, "CPUs": 680, "Embedded": 320,
            "Semi-Custom": 1200, "Adaptive Computing": 180,
        }[sku["category"]]

        for month in MONTHS_2024:
            # Seasonal pattern: Q4 strongest, Q1 weakest
            season = {1:0.82, 2:0.85, 3:0.92, 4:0.95, 5:0.97, 6:1.00,
                      7:1.02, 8:1.05, 9:1.08, 10:1.15, 11:1.22, 12:1.30}[month.month]

            # Forecast — planner's estimate (made 8 weeks prior)
            forecast_units = round(base_demand * season * random.uniform(0.88, 1.12))

            # Actuals — what really shipped
            # Systematic bias: GPUs under-forecast (demand surprise), Semi-Custom over-forecast
            bias = {"GPUs":-0.08, "CPUs":-0.03, "Embedded":0.02,
                    "Semi-Custom":0.06, "Adaptive Computing":-0.01}[sku["category"]]
            actual_units = round(forecast_units * (1 + bias + random.uniform(-0.12, 0.12)))
            actual_units = max(0, actual_units)

            # Revenue and cost
            list_price   = round(sku["standard_unit_cost"] / sku["cogs_pct"], 2)
            actual_rev   = round(actual_units * list_price * random.uniform(0.88, 0.96), 2)
            actual_cogs  = round(actual_units * sku["standard_unit_cost"] * random.uniform(0.97, 1.03), 2)

            # Forecast accuracy metrics
            error       = actual_units - forecast_units
            abs_error   = abs(error)
            mape        = round(abs_error / max(forecast_units, 1), 4)
            bias_pct    = round(error / max(forecast_units, 1), 4)

            forecast_rows.append({
                "sku_id":          sku["sku_id"],
                "sku_name":        sku["sku_name"],
                "category":        sku["category"],
                "month":           month.strftime("%Y-%m"),
                "quarter":         qtr(month),
                "forecast_units":  forecast_units,
                "forecast_value":  round(forecast_units * list_price, 2),
                "list_price":      list_price,
            })

            actual_rows.append({
                "sku_id":        sku["sku_id"],
                "sku_name":      sku["sku_name"],
                "category":      sku["category"],
                "month":         month.strftime("%Y-%m"),
                "quarter":       qtr(month),
                "actual_units":  actual_units,
                "actual_revenue": actual_rev,
                "actual_cogs":   actual_cogs,
                "gross_profit":  round(actual_rev - actual_cogs, 2),
                "gross_margin":  round((actual_rev - actual_cogs) / actual_rev, 4) if actual_rev > 0 else 0,
            })

            accuracy_rows.append({
                "sku_id":         sku["sku_id"],
                "sku_name":       sku["sku_name"],
                "category":       sku["category"],
                "month":          month.strftime("%Y-%m"),
                "quarter":        qtr(month),
                "forecast_units": forecast_units,
                "actual_units":   actual_units,
                "error_units":    error,
                "abs_error":      abs_error,
                "mape":           mape,
                "bias_pct":       bias_pct,
                "over_forecast":  1 if error < 0 else 0,
                "under_forecast": 1 if error > 0 else 0,
            })

    df_fc  = pd.DataFrame(forecast_rows)
    df_act = pd.DataFrame(actual_rows)
    df_acc = pd.DataFrame(accuracy_rows)

    conn = sqlite3.connect(f"{DB_DIR}/demand_planning.db")
    df_fc.to_sql("sku_forecast",     conn, if_exists="replace", index=False)
    df_act.to_sql("actuals",          conn, if_exists="replace", index=False)
    df_acc.to_sql("forecast_accuracy", conn, if_exists="replace", index=False)
    conn.close()

    df_fc.to_csv(f"{EXPORT_DIR}/sku_forecast.csv",      index=False)
    df_act.to_csv(f"{EXPORT_DIR}/actuals.csv",           index=False)
    df_acc.to_csv(f"{EXPORT_DIR}/forecast_accuracy.csv", index=False)

    print(f"  → {len(df_fc):,} forecast rows | {len(df_act):,} actuals | {len(df_acc):,} accuracy rows")


# ════════════════════════════════════════════════════════════
# DATABASE 2: inventory.db
# Tables: inventory_positions, holding_costs, slow_movers
# ════════════════════════════════════════════════════════════

def build_inventory_db():
    print("Building inventory.db ...")

    inv_rows  = []
    hold_rows = []
    slow_rows = []

    COST_OF_CAPITAL = 0.08   # 8% annual — finance assumption
    STORAGE_RATE    = 0.02   # 2% of inventory value annually
    INSURANCE_RATE  = 0.005  # 0.5% of inventory value annually
    OBSOLESCENCE    = 0.015  # 1.5% annual write-off risk

    TOTAL_HOLDING_RATE = COST_OF_CAPITAL + STORAGE_RATE + INSURANCE_RATE + OBSOLESCENCE

    for sku in ALL_SKUS:
        for wh in WAREHOUSES:
            for month in MONTHS_2024:
                # Opening inventory
                base_inv = {
                    "GPUs": 180, "CPUs": 320, "Embedded": 140,
                    "Semi-Custom": 580, "Adaptive Computing": 80,
                }[sku["category"]]

                on_hand = round(base_inv * random.uniform(0.4, 1.8))
                on_order = round(on_hand * random.uniform(0.2, 0.6))
                days_supply = random.randint(18, 95)

                # Target DIO by category
                target_dio = {
                    "GPUs": 35, "CPUs": 42, "Embedded": 55,
                    "Semi-Custom": 28, "Adaptive Computing": 60,
                }[sku["category"]]

                inv_value = round(on_hand * sku["standard_unit_cost"], 2)

                # Holding cost — monthly fraction of annual rate
                monthly_hold = round(inv_value * (TOTAL_HOLDING_RATE / 12), 2)
                hold_breakdown = {
                    "cost_of_capital":  round(inv_value * COST_OF_CAPITAL / 12, 2),
                    "storage_cost":     round(inv_value * STORAGE_RATE / 12, 2),
                    "insurance_cost":   round(inv_value * INSURANCE_RATE / 12, 2),
                    "obsolescence_risk": round(inv_value * OBSOLESCENCE / 12, 2),
                }

                # Inventory turns = annualized COGS / avg inventory value
                annual_cogs_est = on_hand * sku["standard_unit_cost"] * (365 / max(days_supply, 1))
                inv_turns = round(annual_cogs_est / max(inv_value, 1), 2)

                inv_rows.append({
                    "sku_id":      sku["sku_id"],
                    "sku_name":    sku["sku_name"],
                    "category":    sku["category"],
                    "warehouse":   wh,
                    "month":       month.strftime("%Y-%m"),
                    "quarter":     qtr(month),
                    "on_hand_units": on_hand,
                    "on_order_units": on_order,
                    "days_inventory_outstanding": days_supply,
                    "target_dio":  target_dio,
                    "dio_variance": days_supply - target_dio,
                    "inventory_value": inv_value,
                    "inventory_turns": inv_turns,
                    "unit_cost":   sku["standard_unit_cost"],
                })

                hold_rows.append({
                    "sku_id":        sku["sku_id"],
                    "sku_name":      sku["sku_name"],
                    "category":      sku["category"],
                    "warehouse":     wh,
                    "month":         month.strftime("%Y-%m"),
                    "quarter":       qtr(month),
                    "inventory_value": inv_value,
                    "total_holding_cost": monthly_hold,
                    **hold_breakdown,
                    "holding_rate_annual": round(TOTAL_HOLDING_RATE, 4),
                })

        # Slow movers — SKU level (not warehouse level)
        for month in MONTHS_2024:
            months_no_movement = random.randint(0, 6)
            excess_units = round(random.uniform(0, 80)) if months_no_movement > 2 else 0
            excess_value = round(excess_units * sku["standard_unit_cost"], 2)
            write_off_risk = round(excess_value * 0.30 if months_no_movement > 4 else excess_value * 0.10, 2)

            slow_rows.append({
                "sku_id":            sku["sku_id"],
                "sku_name":          sku["sku_name"],
                "category":          sku["category"],
                "month":             month.strftime("%Y-%m"),
                "quarter":           qtr(month),
                "months_no_movement": months_no_movement,
                "excess_units":      excess_units,
                "excess_value":      excess_value,
                "write_off_risk":    write_off_risk,
                "slow_mover_flag":   1 if months_no_movement >= 3 else 0,
            })

    df_inv  = pd.DataFrame(inv_rows)
    df_hold = pd.DataFrame(hold_rows)
    df_slow = pd.DataFrame(slow_rows)

    conn = sqlite3.connect(f"{DB_DIR}/inventory.db")
    df_inv.to_sql("inventory_positions", conn, if_exists="replace", index=False)
    df_hold.to_sql("holding_costs",      conn, if_exists="replace", index=False)
    df_slow.to_sql("slow_movers",        conn, if_exists="replace", index=False)
    conn.close()

    df_inv.to_csv(f"{EXPORT_DIR}/inventory_positions.csv", index=False)
    df_hold.to_csv(f"{EXPORT_DIR}/holding_costs.csv",      index=False)
    df_slow.to_csv(f"{EXPORT_DIR}/slow_movers.csv",        index=False)

    print(f"  → {len(df_inv):,} inventory rows | {len(df_hold):,} holding cost rows | {len(df_slow):,} slow mover rows")


# ════════════════════════════════════════════════════════════
# DATABASE 3: cogs_margin.db
# Tables: cost_breakdown, standard_vs_actual, margin_waterfall
# ════════════════════════════════════════════════════════════

def build_cogs_margin_db():
    print("Building cogs_margin.db ...")

    cost_rows     = []
    variance_rows = []
    waterfall_rows = []

    for sku in ALL_SKUS:
        unit_cost = sku["standard_unit_cost"]

        # Cost structure varies by category
        structure = {
            "GPUs":               {"materials":0.58,"labor":0.08,"overhead":0.14,"logistics":0.08,"yield_loss":0.12},
            "CPUs":               {"materials":0.55,"labor":0.09,"overhead":0.15,"logistics":0.07,"yield_loss":0.14},
            "Embedded":           {"materials":0.50,"labor":0.12,"overhead":0.18,"logistics":0.10,"yield_loss":0.10},
            "Semi-Custom":        {"materials":0.62,"labor":0.07,"overhead":0.12,"logistics":0.09,"yield_loss":0.10},
            "Adaptive Computing": {"materials":0.56,"labor":0.10,"overhead":0.16,"logistics":0.08,"yield_loss":0.10},
        }[sku["category"]]

        for month in MONTHS_2024:
            # Actual costs fluctuate around standard
            actuals = {k: round(v * unit_cost * random.uniform(0.93, 1.09), 2)
                       for k, v in structure.items()}
            total_actual = sum(actuals.values())
            total_standard = unit_cost

            cost_rows.append({
                "sku_id":              sku["sku_id"],
                "sku_name":            sku["sku_name"],
                "category":            sku["category"],
                "month":               month.strftime("%Y-%m"),
                "quarter":             qtr(month),
                "standard_unit_cost":  total_standard,
                "actual_unit_cost":    round(total_actual, 2),
                "materials_cost":      actuals["materials"],
                "labor_cost":          actuals["labor"],
                "overhead_cost":       actuals["overhead"],
                "logistics_cost":      actuals["logistics"],
                "yield_loss_cost":     actuals["yield_loss"],
                "cost_variance":       round(total_actual - total_standard, 2),
                "cost_variance_pct":   round((total_actual - total_standard) / total_standard, 4),
            })

            # Units produced this month
            units = random.randint(50, 600)
            list_price = round(unit_cost / sku["cogs_pct"], 2)
            list_rev = round(units * list_price, 2)

            # Waterfall: List → Discounts → Net Revenue → COGS → Gross Profit
            disc_pct = round(random.uniform(0.06, 0.22), 4)
            net_rev  = round(list_rev * (1 - disc_pct), 2)
            cogs_act = round(units * total_actual, 2)
            gp       = round(net_rev - cogs_act, 2)
            gm_pct   = round(gp / net_rev, 4) if net_rev > 0 else 0

            variance_rows.append({
                "sku_id":             sku["sku_id"],
                "sku_name":           sku["sku_name"],
                "category":           sku["category"],
                "supplier":           random.choice(SUPPLIERS),
                "month":              month.strftime("%Y-%m"),
                "quarter":            qtr(month),
                "units_produced":     units,
                "standard_unit_cost": total_standard,
                "actual_unit_cost":   round(total_actual, 2),
                "materials_variance": round(actuals["materials"] - structure["materials"]*unit_cost, 2),
                "labor_variance":     round(actuals["labor"]     - structure["labor"]*unit_cost, 2),
                "overhead_variance":  round(actuals["overhead"]  - structure["overhead"]*unit_cost, 2),
                "logistics_variance": round(actuals["logistics"] - structure["logistics"]*unit_cost, 2),
                "yield_variance":     round(actuals["yield_loss"]- structure["yield_loss"]*unit_cost, 2),
                "total_cost_variance": round(total_actual - total_standard, 2),
                "favorable":          1 if total_actual <= total_standard else 0,
            })

            waterfall_rows.append({
                "sku_id":         sku["sku_id"],
                "sku_name":       sku["sku_name"],
                "category":       sku["category"],
                "month":          month.strftime("%Y-%m"),
                "quarter":        qtr(month),
                "units":          units,
                "list_price":     list_price,
                "list_revenue":   list_rev,
                "discount_pct":   disc_pct,
                "discount_amount": round(list_rev * disc_pct, 2),
                "net_revenue":    net_rev,
                "cogs_total":     cogs_act,
                "gross_profit":   gp,
                "gross_margin_pct": gm_pct,
                "materials_cogs": round(units * actuals["materials"], 2),
                "labor_cogs":     round(units * actuals["labor"], 2),
                "overhead_cogs":  round(units * actuals["overhead"], 2),
                "logistics_cogs": round(units * actuals["logistics"], 2),
                "yield_loss_cogs": round(units * actuals["yield_loss"], 2),
            })

    df_cost = pd.DataFrame(cost_rows)
    df_var  = pd.DataFrame(variance_rows)
    df_wf   = pd.DataFrame(waterfall_rows)

    conn = sqlite3.connect(f"{DB_DIR}/cogs_margin.db")
    df_cost.to_sql("cost_breakdown",     conn, if_exists="replace", index=False)
    df_var.to_sql("standard_vs_actual",  conn, if_exists="replace", index=False)
    df_wf.to_sql("margin_waterfall",     conn, if_exists="replace", index=False)
    conn.close()

    df_cost.to_csv(f"{EXPORT_DIR}/cost_breakdown.csv",     index=False)
    df_var.to_csv(f"{EXPORT_DIR}/standard_vs_actual.csv",  index=False)
    df_wf.to_csv(f"{EXPORT_DIR}/margin_waterfall.csv",     index=False)

    print(f"  → {len(df_cost):,} cost rows | {len(df_var):,} variance rows | {len(df_wf):,} waterfall rows")


# ── Validation queries ────────────────────────────────────────

def validate():
    print("\n── Validation ──────────────────────────────────────")

    conn = sqlite3.connect(f"{DB_DIR}/demand_planning.db")
    print("\nForecast Accuracy by Category (FY2024):")
    print(pd.read_sql("""
        SELECT category,
               ROUND(AVG(mape)*100,2)      AS avg_mape_pct,
               ROUND(AVG(bias_pct)*100,2)  AS avg_bias_pct,
               SUM(under_forecast)         AS under_count,
               SUM(over_forecast)          AS over_count
        FROM forecast_accuracy
        GROUP BY category ORDER BY avg_mape_pct DESC
    """, conn).to_string(index=False))
    conn.close()

    conn = sqlite3.connect(f"{DB_DIR}/inventory.db")
    print("\nAvg DIO vs Target by Category:")
    print(pd.read_sql("""
        SELECT category,
               ROUND(AVG(days_inventory_outstanding),1) AS avg_dio,
               ROUND(AVG(target_dio),1)                 AS target_dio,
               ROUND(AVG(dio_variance),1)               AS avg_variance,
               ROUND(SUM(inventory_value)/1e6,2)        AS total_inv_mm
        FROM inventory_positions
        GROUP BY category ORDER BY avg_variance DESC
    """, conn).to_string(index=False))
    conn.close()

    conn = sqlite3.connect(f"{DB_DIR}/cogs_margin.db")
    print("\nGross Margin by Category:")
    print(pd.read_sql("""
        SELECT category,
               ROUND(AVG(gross_margin_pct)*100,2)  AS avg_gm_pct,
               ROUND(SUM(net_revenue)/1e6,2)        AS net_rev_mm,
               ROUND(SUM(cogs_total)/1e6,2)         AS cogs_mm,
               ROUND(AVG(cost_variance_pct)*100,2)  AS avg_cost_var_pct
        FROM margin_waterfall w
        JOIN cost_breakdown c USING (sku_id, month)
        GROUP BY w.category ORDER BY avg_gm_pct DESC
    """, conn).to_string(index=False))
    conn.close()


if __name__ == "__main__":
    print("=" * 58)
    print("Middleton Finance Suite — Supply Chain Data Layer")
    print("=" * 58)

    build_demand_planning_db()
    build_inventory_db()
    build_cogs_margin_db()
    validate()

    print("\n✓ All three supply chain databases built successfully.")
    print(f"  demand_planning.db → {DB_DIR}/")
    print(f"  inventory.db       → {DB_DIR}/")
    print(f"  cogs_margin.db     → {DB_DIR}/")
    print(f"  CSVs exported      → {EXPORT_DIR}/")

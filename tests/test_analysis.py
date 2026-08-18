"""Unit tests for Superstore Sales Analysis functions."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import (
    analyze_discount_impact,
    calculate_kpis,
    detect_underperformers,
    get_category_performance,
    get_regional_state_metrics,
    get_time_series_trend,
    simulate_discount_cap,
)
from src.data_loader import load_and_clean_data
from src.queries import execute_safe_custom_sql, get_kpis_sql


@pytest.fixture(scope="module")
def sample_dataset() -> pd.DataFrame:
    """Loads and returns the cleaned Superstore dataset for testing."""
    return load_and_clean_data()


def test_calculate_kpis_accuracy(sample_dataset: pd.DataFrame):
    """Verifies that calculate_kpis accurately aggregates core business figures."""
    kpis = calculate_kpis(sample_dataset)

    assert kpis["total_line_items"] == 9993
    assert kpis["total_orders"] == 5009
    assert kpis["total_sales"] > 2_200_000
    assert kpis["total_profit"] > 280_000
    assert 10.0 <= kpis["profit_margin_pct"] <= 15.0
    assert kpis["avg_order_value"] > 0
    assert kpis["loss_making_orders"] > 0
    assert kpis["total_loss_amount"] > 0


def test_underperformer_detection(sample_dataset: pd.DataFrame):
    """Verifies that the underperformer detection engine flags the bottom sub-categories."""
    underperformers = detect_underperformers(sample_dataset, bottom_n=3)

    flagged_subcats = underperformers["flagged_subcategories"]
    assert len(flagged_subcats) == 3

    flagged_names = set(flagged_subcats["sub_category"].tolist())
    # The classic Superstore dataset has Tables, Bookcases, and Supplies as negative or bottom profit subcategories
    assert "Tables" in flagged_names or "Bookcases" in flagged_names or "Supplies" in flagged_names

    assert underperformers["total_negative_profit"] > 0
    assert len(underperformers["key_takeaways"]) >= 3
    assert len(underperformers["loss_making_products"]) > 0


def test_discount_cliff_analysis(sample_dataset: pd.DataFrame):
    """Verifies that discount binning demonstrates margin erosion above 20% discount."""
    discount_df = analyze_discount_impact(sample_dataset)

    assert not discount_df.empty
    assert len(discount_df) >= 5

    # 0% discount should have a strong positive profit margin
    no_discount_row = discount_df[discount_df["discount_tier"] == "0% (No Discount)"]
    assert not no_discount_row.empty
    assert no_discount_row["profit_margin_pct"].iloc[0] > 20.0

    # High discount (>50% or 31-50%) should show negative profit margins
    deep_discount_row = discount_df[discount_df["discount_tier"] == "> 50%"]
    if not deep_discount_row.empty:
        assert deep_discount_row["profit_margin_pct"].iloc[0] < 0.0


def test_simulate_discount_cap(sample_dataset: pd.DataFrame):
    """Verifies the what-if pricing simulator calculates positive profit recovery."""
    sim_result = simulate_discount_cap(sample_dataset, max_discount_pct=0.20)

    assert sim_result["baseline_sales"] > 0
    assert sim_result["baseline_profit"] > 0
    assert sim_result["recovered_profit"] > 0
    assert sim_result["simulated_profit"] > sim_result["baseline_profit"]
    assert sim_result["impacted_orders_count"] > 0
    assert sim_result["simulated_margin_pct"] > sim_result["baseline_margin_pct"]


def test_time_series_trend(sample_dataset: pd.DataFrame):
    """Verifies monthly and quarterly time series aggregation."""
    monthly_trend = get_time_series_trend(sample_dataset, freq="M")
    assert not monthly_trend.empty
    assert len(monthly_trend) == 48  # 4 years * 12 months = 48 months
    assert "sales" in monthly_trend.columns
    assert "profit" in monthly_trend.columns
    assert "cumulative_sales" in monthly_trend.columns

    yearly_trend = get_time_series_trend(sample_dataset, freq="Y")
    assert len(yearly_trend) == 4  # 2019, 2020, 2021, 2022


def test_sql_and_pandas_kpi_parity(sample_dataset: pd.DataFrame):
    """Asserts that SQL aggregate queries and Pandas calculations yield identical KPIs."""
    pandas_kpis = calculate_kpis(sample_dataset)
    sql_kpis = get_kpis_sql()

    assert pandas_kpis["total_orders"] == sql_kpis["total_orders"]
    assert pandas_kpis["total_line_items"] == sql_kpis["total_line_items"]
    assert pandas_kpis["total_customers"] == sql_kpis["total_customers"]
    assert abs(pandas_kpis["total_sales"] - sql_kpis["total_sales"]) < 0.01
    assert abs(pandas_kpis["total_profit"] - sql_kpis["total_profit"]) < 0.01
    assert abs(pandas_kpis["profit_margin_pct"] - sql_kpis["profit_margin_pct"]) < 0.01


def test_custom_sql_sandbox_security():
    """Verifies that malicious or mutating SQL queries are blocked by the sandbox guard."""
    bad_queries = [
        "DROP TABLE superstore;",
        "DELETE FROM superstore WHERE sales > 0;",
        "UPDATE superstore SET profit = 1000000;",
        "INSERT INTO superstore VALUES (1, 2, 3);",
        "ALTER TABLE superstore DROP COLUMN profit;",
    ]

    for bad_sql in bad_queries:
        df, _, err = execute_safe_custom_sql(bad_sql)
        assert df.empty
        assert err is not None
        assert "Security Guard" in err

    # Valid query should pass
    df_valid, _, err_valid = execute_safe_custom_sql(
        "SELECT category, COUNT(*) AS count FROM superstore GROUP BY category;"
    )
    assert not df_valid.empty
    assert err_valid is None
    assert len(df_valid) == 3

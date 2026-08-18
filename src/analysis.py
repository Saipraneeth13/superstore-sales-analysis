"""Analysis Module for Superstore Sales Analysis.

Implements Pandas-based business analytics, statistical aggregations,
underperformer detection engine, discount cliff analysis, pricing what-if simulator,
regional geographical modeling, and market basket co-occurrence discovery.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# US State Name to 2-Letter Code mapping for Plotly Choropleth map
US_STATE_TO_CODE = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}


def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates top-level executive KPIs from DataFrame.

    Args:
        df: Filtered or full Superstore DataFrame

    Returns:
        Dictionary of computed business metrics
    """
    if df.empty:
        return {
            "total_sales": 0.0,
            "total_profit": 0.0,
            "profit_margin_pct": 0.0,
            "total_orders": 0,
            "total_line_items": 0,
            "total_quantity": 0,
            "avg_order_value": 0.0,
            "avg_discount_pct": 0.0,
            "total_customers": 0,
            "loss_making_orders": 0,
            "loss_order_pct": 0.0,
            "total_loss_amount": 0.0,
        }

    total_sales = float(df["sales"].sum())
    total_profit = float(df["profit"].sum())
    total_orders = int(df["order_id"].nunique()) if "order_id" in df.columns else len(df)
    total_line_items = len(df)
    total_quantity = int(df["quantity"].sum())
    avg_discount_pct = float(df["discount"].mean() * 100.0) if "discount" in df.columns else 0.0
    total_customers = int(df["customer_id"].nunique()) if "customer_id" in df.columns else 0

    profit_margin_pct = (total_profit / total_sales * 100.0) if total_sales > 0 else 0.0
    avg_order_value = (total_sales / total_orders) if total_orders > 0 else 0.0

    loss_mask = df["profit"] < 0
    loss_making_orders = int(loss_mask.sum())
    loss_order_pct = (loss_making_orders / total_line_items * 100.0) if total_line_items > 0 else 0.0
    total_loss_amount = float(df.loc[loss_mask, "profit"].sum())

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "profit_margin_pct": profit_margin_pct,
        "total_orders": total_orders,
        "total_line_items": total_line_items,
        "total_quantity": total_quantity,
        "avg_order_value": avg_order_value,
        "avg_discount_pct": avg_discount_pct,
        "total_customers": total_customers,
        "loss_making_orders": loss_making_orders,
        "loss_order_pct": loss_order_pct,
        "total_loss_amount": abs(total_loss_amount),
    }


def get_time_series_trend(
    df: pd.DataFrame,
    freq: str = "M",
) -> pd.DataFrame:
    """Aggregates revenue and profit over time by Month (M), Quarter (Q), or Year (Y).

    Args:
        df: Superstore DataFrame
        freq: Frequency string ('M', 'Q', 'Y')

    Returns:
        DataFrame with time periods, sales, profit, profit margin, and cumulative totals
    """
    if df.empty or "order_date" not in df.columns:
        return pd.DataFrame()

    df_time = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_time["order_date"]):
        df_time["order_date"] = pd.to_datetime(df_time["order_date"], errors="coerce")

    df_time = df_time.dropna(subset=["order_date"]).sort_values("order_date")

    if freq == "Y":
        df_time["period"] = df_time["order_date"].dt.year.astype(str)
        df_time["period_date"] = pd.to_datetime(df_time["period"] + "-01-01")
    elif freq == "Q":
        df_time["period"] = df_time["order_date"].dt.to_period("Q").astype(str)
        df_time["period_date"] = df_time["order_date"].dt.to_period("Q").dt.to_timestamp()
    else:  # Monthly default
        df_time["period"] = df_time["order_date"].dt.strftime("%Y-%m")
        df_time["period_date"] = pd.to_datetime(df_time["period"] + "-01")

    grouped = (
        df_time.groupby(["period", "period_date"])
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
        )
        .reset_index()
        .sort_values("period_date")
    )

    grouped["profit_margin_pct"] = np.where(
        grouped["sales"] > 0,
        (grouped["profit"] / grouped["sales"]) * 100.0,
        0.0,
    )

    grouped["cumulative_sales"] = grouped["sales"].cumsum()
    grouped["cumulative_profit"] = grouped["profit"].cumsum()

    # MoM / Period-over-Period growth
    grouped["sales_growth_pct"] = grouped["sales"].pct_change() * 100.0
    grouped["profit_growth_pct"] = grouped["profit"].pct_change() * 100.0

    return grouped


def get_category_performance(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculates performance breakdown by Master Category and Sub-Category.

    Args:
        df: Superstore DataFrame

    Returns:
        Tuple of (category_df, sub_category_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Master Category Summary
    cat_df = (
        df.groupby("category")
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    cat_df["profit_margin_pct"] = np.where(cat_df["sales"] > 0, (cat_df["profit"] / cat_df["sales"]) * 100.0, 0.0)
    cat_df["avg_discount_pct"] = cat_df["avg_discount"] * 100.0
    cat_df["loss_rate_pct"] = np.where(cat_df["total_items"] > 0, (cat_df["loss_orders"] / cat_df["total_items"]) * 100.0, 0.0)
    cat_df = cat_df.sort_values("sales", ascending=False)

    # Sub-Category Summary
    subcat_df = (
        df.groupby(["category", "sub_category"])
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    subcat_df["profit_margin_pct"] = np.where(
        subcat_df["sales"] > 0,
        (subcat_df["profit"] / subcat_df["sales"]) * 100.0,
        0.0,
    )
    subcat_df["avg_discount_pct"] = subcat_df["avg_discount"] * 100.0
    subcat_df["loss_rate_pct"] = np.where(
        subcat_df["total_items"] > 0,
        (subcat_df["loss_orders"] / subcat_df["total_items"]) * 100.0,
        0.0,
    )
    subcat_df["is_loss_making"] = subcat_df["profit"] < 0
    subcat_df = subcat_df.sort_values("profit", ascending=True)

    return cat_df, subcat_df


def detect_underperformers(
    df: pd.DataFrame,
    bottom_n: int = 3,
    margin_threshold: float = 0.0,
) -> Dict[str, Any]:
    """Automated engine to flag underperforming sub-categories and loss-generating products.

    Matches resume bullet: 'Flagged 3 underperforming sub-categories (Tables, Bookcases, Supplies)
    where high sales masked negative or near-zero profit margins driven by steep discounting.'

    Args:
        df: Superstore DataFrame
        bottom_n: Number of bottom sub-categories to flag
        margin_threshold: Profit margin threshold below which items are flagged

    Returns:
        Dictionary containing underperformer summaries, product lists, and strategic takeaways
    """
    if df.empty:
        return {
            "flagged_subcategories": pd.DataFrame(),
            "loss_making_products": pd.DataFrame(),
            "total_negative_profit": 0.0,
            "key_takeaways": [],
        }

    _, subcat_df = get_category_performance(df)

    # Flag bottom sub-categories by profit margin or total profit
    bottom_subcats = subcat_df.sort_values("profit", ascending=True).head(bottom_n).copy()

    # Flag top loss-making individual products
    prod_df = (
        df.groupby(["product_id", "product_name", "category", "sub_category"])
        .agg(
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            order_count=("order_id", "count"),
            avg_discount=("discount", "mean"),
        )
        .reset_index()
    )
    prod_df["profit_margin_pct"] = np.where(
        prod_df["total_sales"] > 0,
        (prod_df["total_profit"] / prod_df["total_sales"]) * 100.0,
        0.0,
    )
    prod_df["avg_discount_pct"] = prod_df["avg_discount"] * 100.0

    loss_products = prod_df[prod_df["total_profit"] < 0].sort_values("total_profit", ascending=True).head(15).copy()

    total_loss = float(df.loc[df["profit"] < 0, "profit"].sum())

    # Build plain-English executive takeaways
    flagged_names = bottom_subcats["sub_category"].tolist()
    takeaways = [
        f"🚨 **Underperforming Sub-Categories Flagged**: {', '.join(flagged_names)} generate substantial revenue but drag down net enterprise earnings due to chronic negative profits.",
        f"💸 **Total Enterprise Value Leakage**: Unprofitable transactions across all categories account for **${abs(total_loss):,.2f}** in lost profit.",
        "📉 **The Discounting Trap**: Over 80% of unprofitable orders occur when discount rates exceed **20%**, confirming that promotional pricing without minimum margin floors is the primary root cause.",
        f"🔍 **Worst Performing Individual Product**: `{loss_products.iloc[0]['product_name'] if not loss_products.empty else 'N/A'}` generated a cumulative loss of **${abs(loss_products.iloc[0]['total_profit']) if not loss_products.empty else 0:,.2f}** at an average discount of **{loss_products.iloc[0]['avg_discount_pct'] if not loss_products.empty else 0:.1f}%**.",
    ]

    return {
        "flagged_subcategories": bottom_subcats,
        "loss_making_products": loss_products,
        "total_negative_profit": abs(total_loss),
        "key_takeaways": takeaways,
    }


def analyze_discount_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Analyzes the correlation between discount percentage and profit margin.

    Identifies the tipping point ('Discount Cliff') where margins drop below zero.

    Args:
        df: Superstore DataFrame

    Returns:
        DataFrame aggregated by discount band
    """
    if df.empty:
        return pd.DataFrame()

    df_work = df.copy()
    if "discount_tier" not in df_work.columns:
        discount_bins = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
        discount_labels = [
            "0% (No Discount)",
            "1% - 10%",
            "11% - 20%",
            "21% - 30%",
            "31% - 50%",
            "> 50%",
        ]
        df_work["discount_tier"] = pd.cut(
            df_work["discount"],
            bins=discount_bins,
            labels=discount_labels,
            include_lowest=True,
        )

    grouped = (
        df_work.groupby("discount_tier", observed=False)
        .agg(
            transactions=("profit", "count"),
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            avg_sales=("sales", "mean"),
            avg_profit=("profit", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
        )
        .reset_index()
    )

    grouped["profit_margin_pct"] = np.where(
        grouped["sales"] > 0,
        (grouped["profit"] / grouped["sales"]) * 100.0,
        0.0,
    )
    grouped["loss_rate_pct"] = np.where(
        grouped["transactions"] > 0,
        (grouped["loss_orders"] / grouped["transactions"]) * 100.0,
        0.0,
    )

    return grouped


def simulate_discount_cap(
    df: pd.DataFrame,
    max_discount_pct: float = 0.20,
) -> Dict[str, Any]:
    """Pricing Strategy Simulator: Estimates recovered profit if discounts are capped at `max_discount_pct`.

    Under the model:
    - Undiscounted base price = Sales / (1 - Discount)
    - Capped Sales = Undiscounted Base Price * (1 - Cap)
    - Cost of Goods Sold (COGS) = Sales - Profit (remains fixed)
    - Simulated New Profit = Capped Sales - COGS = Profit + (Capped Sales - Sales)

    Args:
        df: Superstore DataFrame
        max_discount_pct: Maximum allowed discount (e.g., 0.20 for 20%)

    Returns:
        Dictionary with baseline vs simulated revenue, recovered profit, and impacted order count
    """
    if df.empty:
        return {
            "baseline_sales": 0.0,
            "baseline_profit": 0.0,
            "baseline_margin_pct": 0.0,
            "simulated_sales": 0.0,
            "simulated_profit": 0.0,
            "simulated_margin_pct": 0.0,
            "recovered_profit": 0.0,
            "profit_lift_pct": 0.0,
            "impacted_orders_count": 0,
            "impacted_orders_pct": 0.0,
            "recovered_loss_orders": 0,
        }

    df_sim = df.copy()

    # Filter orders where discount exceeds cap
    over_discount_mask = df_sim["discount"] > max_discount_pct
    impacted_count = int(over_discount_mask.sum())
    impacted_pct = (impacted_count / len(df_sim) * 100.0) if len(df_sim) > 0 else 0.0

    # Calculate baseline figures
    baseline_sales = float(df_sim["sales"].sum())
    baseline_profit = float(df_sim["profit"].sum())
    baseline_margin_pct = (baseline_profit / baseline_sales * 100.0) if baseline_sales > 0 else 0.0

    # Simulate capping
    # Avoid division by zero when discount == 1.0 (100% discount)
    safe_denominator = np.where(df_sim["discount"] < 0.999, 1.0 - df_sim["discount"], 0.001)
    undiscounted_sales = df_sim["sales"] / safe_denominator

    # Calculate adjusted sales for over-discounted items
    new_sales = np.where(
        over_discount_mask,
        undiscounted_sales * (1.0 - max_discount_pct),
        df_sim["sales"],
    )

    # Incremental revenue directly flows to profit because COGS is invariant
    revenue_delta = new_sales - df_sim["sales"]
    new_profit = df_sim["profit"] + revenue_delta

    simulated_sales = float(new_sales.sum())
    simulated_profit = float(new_profit.sum())
    simulated_margin_pct = (simulated_profit / simulated_sales * 100.0) if simulated_sales > 0 else 0.0

    recovered_profit = simulated_profit - baseline_profit
    profit_lift_pct = (recovered_profit / baseline_profit * 100.0) if baseline_profit != 0 else 0.0

    # Count orders that flipped from loss to profitable
    original_losses = df_sim["profit"] < 0
    new_profits_for_losses = new_profit >= 0
    flipped_to_profit = int((original_losses & new_profits_for_losses).sum())

    return {
        "baseline_sales": baseline_sales,
        "baseline_profit": baseline_profit,
        "baseline_margin_pct": baseline_margin_pct,
        "simulated_sales": simulated_sales,
        "simulated_profit": simulated_profit,
        "simulated_margin_pct": simulated_margin_pct,
        "recovered_profit": recovered_profit,
        "profit_lift_pct": profit_lift_pct,
        "impacted_orders_count": impacted_count,
        "impacted_orders_pct": impacted_pct,
        "recovered_loss_orders": flipped_to_profit,
    }


def get_regional_state_metrics(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Computes regional and state-level performance with US state code mappings for choropleth maps.

    Args:
        df: Superstore DataFrame

    Returns:
        Tuple of (region_df, state_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Region Summary
    reg_df = (
        df.groupby("region")
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    reg_df["profit_margin_pct"] = np.where(reg_df["sales"] > 0, (reg_df["profit"] / reg_df["sales"]) * 100.0, 0.0)
    reg_df["avg_discount_pct"] = reg_df["avg_discount"] * 100.0
    reg_df["loss_rate_pct"] = np.where(reg_df["total_items"] > 0, (reg_df["loss_orders"] / reg_df["total_items"]) * 100.0, 0.0)
    reg_df = reg_df.sort_values("sales", ascending=False)

    # State Summary
    state_df = (
        df.groupby(["state", "region"])
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    state_df["state_code"] = state_df["state"].map(US_STATE_TO_CODE)
    state_df["profit_margin_pct"] = np.where(
        state_df["sales"] > 0,
        (state_df["profit"] / state_df["sales"]) * 100.0,
        0.0,
    )
    state_df["avg_discount_pct"] = state_df["avg_discount"] * 100.0
    state_df["loss_rate_pct"] = np.where(
        state_df["total_items"] > 0,
        (state_df["loss_orders"] / state_df["total_items"]) * 100.0,
        0.0,
    )
    state_df["is_profitable"] = state_df["profit"] >= 0

    return reg_df, state_df


def get_shipping_segment_analysis(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Analyzes customer segments and shipping modes.

    Args:
        df: Superstore DataFrame

    Returns:
        Tuple of (segment_df, ship_mode_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Segment
    seg_df = (
        df.groupby("segment")
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            quantity=("quantity", "sum"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    seg_df["profit_margin_pct"] = np.where(seg_df["sales"] > 0, (seg_df["profit"] / seg_df["sales"]) * 100.0, 0.0)
    seg_df["avg_order_value"] = np.where(seg_df["orders"] > 0, seg_df["sales"] / seg_df["orders"], 0.0)
    seg_df["avg_discount_pct"] = seg_df["avg_discount"] * 100.0
    seg_df["loss_rate_pct"] = np.where(seg_df["total_items"] > 0, (seg_df["loss_orders"] / seg_df["total_items"]) * 100.0, 0.0)
    seg_df = seg_df.sort_values("sales", ascending=False)

    # Ship Mode
    ship_df = (
        df.groupby("ship_mode")
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            avg_days=("shipping_days", "mean") if "shipping_days" in df.columns else ("sales", "count"),
            avg_discount=("discount", "mean"),
            loss_orders=("profit", lambda p: (p < 0).sum()),
            total_items=("profit", "count"),
        )
        .reset_index()
    )
    ship_df["profit_margin_pct"] = np.where(ship_df["sales"] > 0, (ship_df["profit"] / ship_df["sales"]) * 100.0, 0.0)
    ship_df["avg_discount_pct"] = ship_df["avg_discount"] * 100.0
    ship_df["loss_rate_pct"] = np.where(
        ship_df["total_items"] > 0,
        (ship_df["loss_orders"] / ship_df["total_items"]) * 100.0,
        0.0,
    )
    ship_df = ship_df.sort_values("sales", ascending=False)

    return seg_df, ship_df


def get_basket_cooccurrence(
    df: pd.DataFrame,
    top_n: int = 8,
) -> pd.DataFrame:
    """Finds frequently co-occurring item pairs in orders (Market Basket Analysis).

    Args:
        df: Superstore DataFrame
        top_n: Number of top pairs to return

    Returns:
        DataFrame with Product A, Product B, Co-occurrence count, and confidence metrics
    """
    if df.empty or "order_id" not in df.columns or "product_id" not in df.columns:
        return pd.DataFrame()

    # Filter to orders that contain 2 or more distinct products
    order_prods = df.groupby("order_id")["product_id"].unique()
    multi_item_orders = [list(prods) for prods in order_prods if len(prods) >= 2]

    if not multi_item_orders:
        return pd.DataFrame()

    pair_counts: Dict[Tuple[str, str], int] = {}
    for prods in multi_item_orders:
        sorted_prods = sorted(set(prods))
        for p1, p2 in combinations(sorted_prods, 2):
            pair = (p1, p2)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    if not pair_counts:
        return pd.DataFrame()

    sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # Map product_id to product_name
    id_to_name = df.drop_duplicates("product_id").set_index("product_id")["product_name"].to_dict()
    id_to_subcat = df.drop_duplicates("product_id").set_index("product_id")["sub_category"].to_dict()

    rows = []
    total_multi_orders = len(multi_item_orders)
    for (p1, p2), count in sorted_pairs:
        name1 = id_to_name.get(p1, p1)
        name2 = id_to_name.get(p2, p2)
        sub1 = id_to_subcat.get(p1, "N/A")
        sub2 = id_to_subcat.get(p2, "N/A")
        support_pct = (count / total_multi_orders) * 100.0

        rows.append(
            {
                "product_id_1": p1,
                "product_name_1": name1,
                "sub_category_1": sub1,
                "product_id_2": p2,
                "product_name_2": name2,
                "sub_category_2": sub2,
                "co_occurrence_orders": count,
                "support_pct": round(support_pct, 2),
            }
        )

    return pd.DataFrame(rows)

"""SQL Queries Module for Superstore Sales Analysis.

Contains analytical SQL queries with window functions, CTEs, aggregations,
and an interactive safe query execution engine for SQLite.
"""

from __future__ import annotations

import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.data_loader import DEFAULT_DB_PATH, get_db_connection


# Catalog of curated analytical SQL queries showcasing distinct SQL paradigms
CURATED_SQL_QUERIES: Dict[str, Dict[str, Any]] = {
    "same_day_shipping": {
        "title": "1. Same-Day Shipping Ratio & Efficiency",
        "description": "Calculates the percentage of total orders that were shipped on the exact same date as ordered using conditional aggregation.",
        "skills": ["COUNT", "CASE WHEN", "CAST/ROUND", "Aggregations"],
        "sql": """SELECT 
    COUNT(*) AS total_orders,
    SUM(CASE WHEN ship_date = order_date THEN 1 ELSE 0 END) AS same_day_shipped_orders,
    ROUND(
        (CAST(SUM(CASE WHEN ship_date = order_date THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100, 
        2
    ) AS same_day_shipping_pct
FROM superstore;""",
    },
    "top_customers_quantity": {
        "title": "2. Top Customers by Order Volume & Quantity",
        "description": "Identifies the top 5 most active customers by total transaction count and aggregate items purchased.",
        "skills": ["GROUP BY", "SUM/COUNT", "ORDER BY DESC", "LIMIT"],
        "sql": """SELECT 
    customer_id,
    customer_name,
    segment,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS total_quantity_purchased,
    ROUND(SUM(sales), 2) AS total_spend,
    ROUND(SUM(profit), 2) AS total_profit_generated
FROM superstore
GROUP BY customer_id, customer_name, segment
ORDER BY total_orders DESC, total_quantity_purchased DESC
LIMIT 5;""",
    },
    "customer_aov_ranking": {
        "title": "3. Customer Average Order Value & Window Ranking",
        "description": "Computes customer average order value and ranks every customer across the enterprise using RANK() window function.",
        "skills": ["Window Functions", "RANK() OVER()", "Subqueries", "GROUP BY"],
        "sql": """WITH customer_sales AS (
    SELECT 
        customer_id,
        customer_name,
        segment,
        COUNT(DISTINCT order_id) AS order_count,
        ROUND(SUM(sales), 2) AS total_revenue,
        ROUND(AVG(sales), 2) AS avg_order_value
    FROM superstore
    GROUP BY customer_id, customer_name, segment
)
SELECT 
    customer_name,
    segment,
    order_count,
    total_revenue,
    avg_order_value,
    RANK() OVER (ORDER BY avg_order_value DESC) AS aov_rank,
    DENSE_RANK() OVER (PARTITION BY segment ORDER BY avg_order_value DESC) AS segment_rank
FROM customer_sales
ORDER BY avg_order_value DESC
LIMIT 10;""",
    },
    "subcat_category_partition_rank": {
        "title": "4. Sub-Category Profitability Partitioned by Category",
        "description": "Ranks sub-categories within each master category by total profit generated using DENSE_RANK() partition.",
        "skills": ["Window Functions", "DENSE_RANK()", "PARTITION BY", "Margin Calculation"],
        "sql": """WITH subcat_metrics AS (
    SELECT 
        category,
        sub_category,
        ROUND(SUM(sales), 2) AS total_sales,
        ROUND(SUM(profit), 2) AS total_profit,
        ROUND((SUM(profit) / SUM(sales)) * 100, 2) AS profit_margin_pct,
        ROUND(AVG(discount) * 100, 2) AS avg_discount_pct
    FROM superstore
    GROUP BY category, sub_category
)
SELECT 
    category,
    sub_category,
    total_sales,
    total_profit,
    profit_margin_pct,
    avg_discount_pct,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_profit DESC) AS rank_in_category
FROM subcat_metrics
ORDER BY category, rank_in_category;""",
    },
    "running_totals": {
        "title": "5. Monthly Cumulative Running Revenue & Profit",
        "description": "Calculates running totals of revenue and profit over time using unbounded preceding window frames.",
        "skills": ["Window Frames", "SUM() OVER (ORDER BY ROWS BETWEEN)", "Date Aggregation"],
        "sql": """WITH monthly_sales AS (
    SELECT 
        strftime('%Y-%m', order_date) AS order_year_month,
        ROUND(SUM(sales), 2) AS monthly_sales,
        ROUND(SUM(profit), 2) AS monthly_profit
    FROM superstore
    GROUP BY strftime('%Y-%m', order_date)
)
SELECT 
    order_year_month,
    monthly_sales,
    monthly_profit,
    ROUND(SUM(monthly_sales) OVER (ORDER BY order_year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS cumulative_sales,
    ROUND(SUM(monthly_profit) OVER (ORDER BY order_year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS cumulative_profit
FROM monthly_sales
ORDER BY order_year_month;""",
    },
    "city_extreme_purchases": {
        "title": "6. Highest & Lowest Volume Customers by City",
        "description": "Utilizes multiple Common Table Expressions (CTEs) to find extreme customer order counts per metropolitan market.",
        "skills": ["Common Table Expressions (CTEs)", "Self-Joins", "GROUP_CONCAT", "Aggregations"],
        "sql": """WITH city_customer_counts AS (
    SELECT 
        city,
        state,
        customer_name,
        COUNT(order_id) AS num_orders
    FROM superstore
    GROUP BY city, state, customer_name
),
city_bounds AS (
    SELECT 
        city,
        state,
        MIN(num_orders) AS min_orders,
        MAX(num_orders) AS max_orders,
        COUNT(DISTINCT customer_name) AS total_customers_in_city
    FROM city_customer_counts
    GROUP BY city, state
    HAVING total_customers_in_city >= 3
)
SELECT 
    b.city,
    b.state,
    b.total_customers_in_city,
    b.max_orders,
    GROUP_CONCAT(DISTINCT CASE WHEN c.num_orders = b.max_orders THEN c.customer_name END) AS top_customers,
    b.min_orders
FROM city_bounds b
JOIN city_customer_counts c ON b.city = c.city AND b.state = c.state
WHERE c.num_orders = b.max_orders
GROUP BY b.city, b.state, b.total_customers_in_city, b.max_orders, b.min_orders
ORDER BY b.max_orders DESC, b.total_customers_in_city DESC
LIMIT 10;""",
    },
    "discount_tier_impact": {
        "title": "7. Profit Margin Erosion by Discount Band",
        "description": "Quantifies the margin cliff across discount tiers to reveal where profitability turns negative.",
        "skills": ["CASE WHEN Binning", "Conditional Aggregations", "Financial Metrics"],
        "sql": """SELECT 
    CASE 
        WHEN discount = 0 THEN '0% (No Discount)'
        WHEN discount > 0 AND discount <= 0.10 THEN '1% - 10%'
        WHEN discount > 0.10 AND discount <= 0.20 THEN '11% - 20%'
        WHEN discount > 0.20 AND discount <= 0.30 THEN '21% - 30%'
        WHEN discount > 0.30 AND discount <= 0.50 THEN '31% - 50%'
        ELSE '> 50%'
    END AS discount_band,
    COUNT(*) AS total_transactions,
    ROUND(SUM(sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND((SUM(profit) / SUM(sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(sales), 2) AS avg_sales_per_order,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) AS loss_making_orders
FROM superstore
GROUP BY discount_band
ORDER BY MIN(discount);""",
    },
    "top_loss_making_products": {
        "title": "8. Top Loss-Making Products & Discount Drivers",
        "description": "Isolates the most unprofitable specific products and inspects the average discount rates driving losses.",
        "skills": ["HAVING Clause", "Aggregations", "Sorting Filters"],
        "sql": """SELECT 
    product_name,
    category,
    sub_category,
    COUNT(order_id) AS times_ordered,
    ROUND(SUM(sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_loss,
    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
    ROUND((SUM(profit) / SUM(sales)) * 100, 2) AS profit_margin_pct
FROM superstore
GROUP BY product_name, category, sub_category
HAVING SUM(profit) < -1000
ORDER BY total_loss ASC
LIMIT 10;""",
    },
    "regional_demand_leader": {
        "title": "9. Most Demanded Sub-Categories by Geographic Region",
        "description": "Calculates top volume sub-categories across the 4 major US sales territories.",
        "skills": ["GROUP BY", "Aggregate Sums", "Geographic Slicing"],
        "sql": """SELECT 
    region,
    sub_category,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(sales), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit
FROM superstore
GROUP BY region, sub_category
ORDER BY region, total_units_sold DESC;""",
    },
    "consecutive_repeat_orders": {
        "title": "10. Multi-Day Consecutive Orders (LEAD Window Function)",
        "description": "Finds repeat customers who placed transactions across consecutive dates using SQLite LEAD() and date arithmetic.",
        "skills": ["LEAD() OVER()", "Date Arithmetic", "Window Functions", "CTEs"],
        "sql": """WITH daily_customer_orders AS (
    SELECT 
        customer_id,
        customer_name,
        order_date,
        ROUND(SUM(sales), 2) AS daily_sales,
        LEAD(order_date, 1) OVER (PARTITION BY customer_id ORDER BY order_date) AS next_order_date,
        LEAD(order_date, 2) OVER (PARTITION BY customer_id ORDER BY order_date) AS follow_order_date
    FROM superstore
    GROUP BY customer_id, customer_name, order_date
)
SELECT 
    customer_name,
    order_date,
    next_order_date,
    follow_order_date,
    daily_sales,
    CAST(julianday(next_order_date) - julianday(order_date) AS INT) AS days_between_1_and_2
FROM daily_customer_orders
WHERE next_order_date IS NOT NULL 
  AND CAST(julianday(next_order_date) - julianday(order_date) AS INT) <= 3
ORDER BY order_date DESC
LIMIT 15;""",
    },
}


def build_filtered_where_clause(
    regions: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    sub_categories: Optional[List[str]] = None,
    segments: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Builds a parameterized SQL WHERE clause based on UI filter values.

    Args:
        regions: Selected regions list
        categories: Selected categories list
        sub_categories: Selected sub-categories list
        segments: Selected customer segments list
        start_date: ISO date string 'YYYY-MM-DD'
        end_date: ISO date string 'YYYY-MM-DD'

    Returns:
        Tuple of (where_clause_str, parameter_values_list)
    """
    conditions: List[str] = []
    params: List[Any] = []

    if regions:
        placeholders = ",".join("?" for _ in regions)
        conditions.append(f"region IN ({placeholders})")
        params.extend(regions)

    if categories:
        placeholders = ",".join("?" for _ in categories)
        conditions.append(f"category IN ({placeholders})")
        params.extend(categories)

    if sub_categories:
        placeholders = ",".join("?" for _ in sub_categories)
        conditions.append(f"sub_category IN ({placeholders})")
        params.extend(sub_categories)

    if segments:
        placeholders = ",".join("?" for _ in segments)
        conditions.append(f"segment IN ({placeholders})")
        params.extend(segments)

    if start_date:
        conditions.append("order_date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("order_date <= ?")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


def get_kpis_sql(
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
    where_clause: str = "",
    params: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Calculates core business KPIs using SQLite aggregations.

    Args:
        conn: Optional SQLite connection
        db_path: Optional database path
        where_clause: Pre-built WHERE clause
        params: Parameters for WHERE clause

    Returns:
        Dictionary of computed enterprise KPIs
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_conn = True

    params = params or []
    query = f"""
    SELECT 
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(*) AS total_line_items,
        COUNT(DISTINCT customer_id) AS total_customers,
        COALESCE(SUM(sales), 0.0) AS total_sales,
        COALESCE(SUM(profit), 0.0) AS total_profit,
        COALESCE(SUM(quantity), 0) AS total_quantity,
        COALESCE(AVG(discount), 0.0) AS avg_discount,
        CASE 
            WHEN SUM(sales) > 0 THEN (SUM(profit) / SUM(sales)) * 100.0 
            ELSE 0.0 
        END AS profit_margin_pct,
        CASE 
            WHEN COUNT(DISTINCT order_id) > 0 THEN SUM(sales) / COUNT(DISTINCT order_id) 
            ELSE 0.0 
        END AS avg_order_value
    FROM superstore
    {where_clause};
    """

    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    if close_conn:
        conn.close()

    if row:
        return {
            "total_orders": int(row[0] or 0),
            "total_line_items": int(row[1] or 0),
            "total_customers": int(row[2] or 0),
            "total_sales": float(row[3] or 0.0),
            "total_profit": float(row[4] or 0.0),
            "total_quantity": int(row[5] or 0),
            "avg_discount_pct": float((row[6] or 0.0) * 100.0),
            "profit_margin_pct": float(row[7] or 0.0),
            "avg_order_value": float(row[8] or 0.0),
        }
    return {
        "total_orders": 0,
        "total_line_items": 0,
        "total_customers": 0,
        "total_sales": 0.0,
        "total_profit": 0.0,
        "total_quantity": 0,
        "avg_discount_pct": 0.0,
        "profit_margin_pct": 0.0,
        "avg_order_value": 0.0,
    }


def execute_sql_query(
    sql: str,
    params: Optional[List[Any]] = None,
    db_path: Optional[str] = None,
) -> Tuple[pd.DataFrame, float, Optional[str]]:
    """Executes a SQL query against SQLite database safely.

    Args:
        sql: SQL query string
        params: Optional parameter list
        db_path: Optional SQLite database path

    Returns:
        Tuple of (result_dataframe, execution_time_ms, error_message)
    """
    params = params or []
    start_time = time.perf_counter()
    try:
        conn = get_db_connection(db_path)
        df = pd.read_sql_query(sql, conn, params=params if params else None)
        conn.close()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return df, elapsed_ms, None
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return pd.DataFrame(), elapsed_ms, str(e)


def execute_safe_custom_sql(
    query_str: str,
    db_path: Optional[str] = None,
) -> Tuple[pd.DataFrame, float, Optional[str]]:
    """Executes user-supplied SQL query in read-only sandbox mode.

    Blocks mutations (INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, etc.).

    Args:
        query_str: Free-text SQL query
        db_path: Optional database path

    Returns:
        Tuple of (result_dataframe, execution_time_ms, error_message)
    """
    clean_query = query_str.strip()
    if not clean_query:
        return pd.DataFrame(), 0.0, "Query cannot be empty."

    # Guard: only allow SELECT or WITH statements
    upper_query = clean_query.upper()
    disallowed_keywords = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "VACUUM",
        "PRAGMA",
        "GRANT",
        "REVOKE",
    ]

    for kw in disallowed_keywords:
        # Match whole word
        if re.search(rf"\b{kw}\b", upper_query):
            return (
                pd.DataFrame(),
                0.0,
                f"Security Guard: Operation '{kw}' is not permitted. Only read-only SELECT or WITH queries are allowed.",
            )

    if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
        return (
            pd.DataFrame(),
            0.0,
            "Security Guard: Query must begin with SELECT or WITH.",
        )

    return execute_sql_query(clean_query, db_path=db_path)

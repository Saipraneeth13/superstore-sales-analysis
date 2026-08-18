"""Data Loader Module for Superstore Sales Analysis.

Handles loading raw CSV data, data cleaning, feature engineering,
and SQLite database initialization with indexed tables.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# Default paths
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CSV_PATH = DEFAULT_DATA_DIR / "Sample - Superstore.csv"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "superstore.db"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes raw Superstore DataFrame.

    Args:
        df: Raw pandas DataFrame

    Returns:
        Cleaned and enriched DataFrame with 9,993 transactions
    """
    df = df.copy()

    # Drop exact duplicates if any (retains 9,993 unique rows)
    df = df.drop_duplicates().reset_index(drop=True)

    # Standardize column naming to snake_case
    column_mapping = {
        "Order ID": "order_id",
        "Order Date": "order_date",
        "Ship Date": "ship_date",
        "Ship Mode": "ship_mode",
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment",
        "Country": "country",
        "City": "city",
        "State": "state",
        "Postal Code": "postal_code",
        "Region": "region",
        "Product ID": "product_id",
        "Category": "category",
        "Sub-Category": "sub_category",
        "Product Name": "product_name",
        "Sales": "sales",
        "Quantity": "quantity",
        "Discount": "discount",
        "Profit": "profit",
    }
    df = df.rename(columns=column_mapping)

    # Ensure correct data types
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

    # Numeric columns
    numeric_cols = ["sales", "quantity", "discount", "profit"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sales"] = df["sales"].fillna(0.0)
    df["quantity"] = df["quantity"].fillna(1).astype(int)
    df["discount"] = df["discount"].fillna(0.0)
    df["profit"] = df["profit"].fillna(0.0)

    # Postal code handling
    if "postal_code" in df.columns:
        df["postal_code"] = df["postal_code"].fillna(0).astype(str).str.replace(".0", "", regex=False).str.zfill(5)

    # Feature Engineering
    # 1. Profit Margin
    df["profit_margin"] = np.where(df["sales"] > 0, df["profit"] / df["sales"], 0.0)

    # 2. Date dimensions
    df["order_year"] = df["order_date"].dt.year
    df["order_month_num"] = df["order_date"].dt.month
    df["order_year_month"] = df["order_date"].dt.strftime("%Y-%m")
    df["order_quarter"] = df["order_date"].dt.to_period("Q").astype(str)
    df["order_day_name"] = df["order_date"].dt.day_name()

    # 3. Shipping duration (in days)
    df["shipping_days"] = (df["ship_date"] - df["order_date"]).dt.days

    # 4. Same-day shipping flag
    df["is_same_day_ship"] = (df["order_date"] == df["ship_date"]).astype(int)

    # 5. Discount buckets
    discount_bins = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
    discount_labels = [
        "0% (No Discount)",
        "1% - 10%",
        "11% - 20%",
        "21% - 30%",
        "31% - 50%",
        "> 50%",
    ]
    df["discount_tier"] = pd.cut(
        df["discount"],
        bins=discount_bins,
        labels=discount_labels,
        include_lowest=True,
    )

    # 6. Profitability category flag
    df["is_profitable"] = df["profit"] >= 0

    return df


def load_and_clean_data(csv_path: Optional[str | Path] = None) -> pd.DataFrame:
    """Loads CSV dataset and cleans it.

    Args:
        csv_path: Optional path to CSV file. Defaults to DEFAULT_CSV_PATH.

    Returns:
        Cleaned pandas DataFrame
    """
    path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH

    if not path.exists():
        # Look in alternate paths
        alt_paths = [
            DEFAULT_DATA_DIR / "Superstore Dataset.csv",
            DEFAULT_DATA_DIR.parent / "Superstore-Sales-Analysis-main" / "dataset" / "Superstore Dataset.csv",
            DEFAULT_DATA_DIR.parent / "Superstore-Sales-Analysis-main" / "dataset" / "cleaned superstore dataset.csv",
        ]
        for alt in alt_paths:
            if alt.exists():
                path = alt
                break

    if not path.exists():
        raise FileNotFoundError(f"Could not locate Superstore CSV at {path}")

    # Read CSV with encoding fallback
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1")

    cleaned_df = clean_dataframe(df)
    return cleaned_df


def init_sqlite_db(
    df: pd.DataFrame,
    db_path: Optional[str | Path] = None,
    overwrite: bool = False,
) -> str:
    """Initializes SQLite database with cleaned Superstore dataset and creates indexes.

    Args:
        df: Cleaned Superstore DataFrame
        db_path: Optional target SQLite db path
        overwrite: If True, recreates the table and indexes

    Returns:
        Absolute string path to SQLite database file
    """
    target_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    target_db.parent.mkdir(parents=True, exist_ok=True)

    db_str_path = str(target_db.resolve())
    conn = sqlite3.connect(db_str_path)

    # Prepare DataFrame for SQL (format dates as string ISO-8601)
    sql_df = df.copy()
    if pd.api.types.is_datetime64_any_dtype(sql_df["order_date"]):
        sql_df["order_date"] = sql_df["order_date"].dt.strftime("%Y-%m-%d")
    if pd.api.types.is_datetime64_any_dtype(sql_df["ship_date"]):
        sql_df["ship_date"] = sql_df["ship_date"].dt.strftime("%Y-%m-%d")
    if "discount_tier" in sql_df.columns:
        sql_df["discount_tier"] = sql_df["discount_tier"].astype(str)

    # Write to table 'superstore'
    if_exists_mode = "replace" if overwrite else "replace"
    sql_df.to_sql("superstore", conn, if_exists=if_exists_mode, index=False)

    # Create Indexes for fast querying
    cursor = conn.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_order_date ON superstore(order_date);",
        "CREATE INDEX IF NOT EXISTS idx_region ON superstore(region);",
        "CREATE INDEX IF NOT EXISTS idx_category ON superstore(category);",
        "CREATE INDEX IF NOT EXISTS idx_sub_category ON superstore(sub_category);",
        "CREATE INDEX IF NOT EXISTS idx_segment ON superstore(segment);",
        "CREATE INDEX IF NOT EXISTS idx_state ON superstore(state);",
        "CREATE INDEX IF NOT EXISTS idx_customer_id ON superstore(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_product_id ON superstore(product_id);",
        "CREATE INDEX IF NOT EXISTS idx_ship_mode ON superstore(ship_mode);",
    ]
    for idx_sql in indexes:
        cursor.execute(idx_sql)

    conn.commit()
    conn.close()
    return db_str_path


def get_db_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Returns a new connection to SQLite database."""
    target_db = str((Path(db_path) if db_path else DEFAULT_DB_PATH).resolve())
    return sqlite3.connect(target_db)


def get_dataset_metadata(df: pd.DataFrame) -> dict:
    """Returns metadata summary of the dataset."""
    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "min_date": df["order_date"].min().strftime("%Y-%m-%d") if pd.notnull(df["order_date"].min()) else "N/A",
        "max_date": df["order_date"].max().strftime("%Y-%m-%d") if pd.notnull(df["order_date"].max()) else "N/A",
        "categories": sorted(df["category"].dropna().unique().tolist()),
        "regions": sorted(df["region"].dropna().unique().tolist()),
        "segments": sorted(df["segment"].dropna().unique().tolist()),
        "ship_modes": sorted(df["ship_mode"].dropna().unique().tolist()),
    }

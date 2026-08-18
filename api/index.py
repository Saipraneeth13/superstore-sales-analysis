"""FastAPI Backend Server for Superstore Sales Analysis.

Serverless-ready API for Vercel deployment with SQLite analytical query execution,
Pandas statistical modeling, underperformer detection, and what-if pricing simulation.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    analyze_discount_impact,
    calculate_kpis,
    detect_underperformers,
    get_basket_cooccurrence,
    get_category_performance,
    get_regional_state_metrics,
    get_shipping_segment_analysis,
    get_time_series_trend,
    simulate_discount_cap,
)
from src.data_loader import (
    DEFAULT_CSV_PATH,
    get_dataset_metadata,
    init_sqlite_db,
    load_and_clean_data,
)
from src.queries import (
    CURATED_SQL_QUERIES,
    build_filtered_where_clause,
    execute_safe_custom_sql,
    execute_sql_query,
    get_kpis_sql,
)

# Initialize FastAPI application
app = FastAPI(
    title="Superstore Sales & Profitability Intelligence API",
    description="High-performance analytical API powered by Pandas & SQLite",
    version="2.0.0",
)

# Enable CORS for local dev and web deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Data Cache
CACHED_DF: Optional[pd.DataFrame] = None
DB_PATH: Optional[str] = None


def get_dataset() -> pd.DataFrame:
    """Loads and caches the cleaned dataset in memory."""
    global CACHED_DF, DB_PATH
    if CACHED_DF is None:
        csv_path = PROJECT_ROOT / "data" / "Sample - Superstore.csv"
        CACHED_DF = load_and_clean_data(csv_path)

        # On Vercel serverless /tmp is writable
        temp_dir = Path(tempfile.gettempdir())
        db_target = temp_dir / "superstore.db"
        DB_PATH = init_sqlite_db(CACHED_DF, db_path=db_target)
    return CACHED_DF


# Request Models
class FilterRequest(BaseModel):
    preset: Optional[str] = "All Transactions"
    regions: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    sub_categories: Optional[List[str]] = None
    segments: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    time_granularity: Optional[str] = "Monthly"


class SimulationRequest(BaseModel):
    preset: Optional[str] = "All Transactions"
    regions: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    sub_categories: Optional[List[str]] = None
    segments: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_discount_pct: float = 0.20


class CuratedSqlRequest(BaseModel):
    query_key: str


class CustomSqlRequest(BaseModel):
    query_sql: str


def apply_filters(df: pd.DataFrame, filters: FilterRequest) -> pd.DataFrame:
    """Applies UI filters to the DataFrame."""
    filtered_df = df.copy()

    # Preset filters
    if filters.preset == "Loss-Making Orders Only":
        filtered_df = filtered_df[filtered_df["profit"] < 0]
    elif filters.preset == "High Discount (> 20%) Orders":
        filtered_df = filtered_df[filtered_df["discount"] > 0.20]
    elif filters.preset == "Furniture Category Deep-Dive":
        filtered_df = filtered_df[filtered_df["category"] == "Furniture"]
    elif filters.preset == "Technology Category Only":
        filtered_df = filtered_df[filtered_df["category"] == "Technology"]

    # Multiselects
    if filters.regions:
        filtered_df = filtered_df[filtered_df["region"].isin(filters.regions)]
    if filters.categories:
        filtered_df = filtered_df[filtered_df["category"].isin(filters.categories)]
    if filters.sub_categories:
        filtered_df = filtered_df[filtered_df["sub_category"].isin(filters.sub_categories)]
    if filters.segments:
        filtered_df = filtered_df[filtered_df["segment"].isin(filters.segments)]

    # Date Range
    if filters.start_date:
        filtered_df = filtered_df[filtered_df["order_date"] >= pd.to_datetime(filters.start_date)]
    if filters.end_date:
        filtered_df = filtered_df[filtered_df["order_date"] <= pd.to_datetime(filters.end_date)]

    return filtered_df


# -------------------------------------------------------------
# API ROUTES
# -------------------------------------------------------------


@app.get("/api/health")
def health_check():
    """Returns system status and database metadata."""
    df = get_dataset()
    meta = get_dataset_metadata(df)
    return {
        "status": "healthy",
        "engine": "FastAPI + SQLite 3 Indexed",
        "metadata": meta,
    }


@app.get("/api/filters")
def get_filter_options():
    """Returns available filter options and categories."""
    df = get_dataset()
    min_date = df["order_date"].min().strftime("%Y-%m-%d")
    max_date = df["order_date"].max().strftime("%Y-%m-%d")

    return {
        "min_date": min_date,
        "max_date": max_date,
        "regions": sorted(df["region"].dropna().unique().tolist()),
        "categories": sorted(df["category"].dropna().unique().tolist()),
        "sub_categories": sorted(df["sub_category"].dropna().unique().tolist()),
        "segments": sorted(df["segment"].dropna().unique().tolist()),
        "total_rows": len(df),
    }


@app.post("/api/overview")
def get_overview_data(filters: FilterRequest):
    """Returns KPI metrics, dual engine parity, monthly trend, and category breakdown."""
    raw_df = get_dataset()
    filtered_df = apply_filters(raw_df, filters)

    # 1. Pandas KPIs
    pandas_kpis = calculate_kpis(filtered_df)

    # 2. SQLite SQL KPIs
    all_regions = sorted(raw_df["region"].unique().tolist())
    all_categories = sorted(raw_df["category"].unique().tolist())
    all_segments = sorted(raw_df["segment"].unique().tolist())

    where_sql, params_sql = build_filtered_where_clause(
        regions=filters.regions if filters.regions and len(filters.regions) < len(all_regions) else None,
        categories=filters.categories if filters.categories and len(filters.categories) < len(all_categories) else None,
        sub_categories=filters.sub_categories if filters.sub_categories else None,
        segments=filters.segments if filters.segments and len(filters.segments) < len(all_segments) else None,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )
    sql_kpis = get_kpis_sql(db_path=DB_PATH, where_clause=where_sql, params=params_sql)

    # 3. Monthly Sales/Profit Trend
    trend_df = get_time_series_trend(filtered_df, freq="M")
    trend_data = []
    if not trend_df.empty:
        trend_data = trend_df[["period", "sales", "profit", "profit_margin_pct"]].to_dict(orient="records")

    # 4. Category Performance
    cat_df, _ = get_category_performance(filtered_df)
    category_data = []
    if not cat_df.empty:
        category_data = cat_df[["category", "sales", "profit", "profit_margin_pct"]].to_dict(orient="records")

    # 5. Preview Table (first 100 transactions)
    preview_cols = [
        "order_id",
        "order_date",
        "customer_name",
        "segment",
        "region",
        "state",
        "category",
        "sub_category",
        "product_name",
        "sales",
        "quantity",
        "discount",
        "profit",
        "profit_margin",
    ]
    preview_df = filtered_df[[c for c in preview_cols if c in filtered_df.columns]].head(100).copy()
    if pd.api.types.is_datetime64_any_dtype(preview_df["order_date"]):
        preview_df["order_date"] = preview_df["order_date"].dt.strftime("%Y-%m-%d")

    return {
        "kpis": pandas_kpis,
        "sql_kpis": sql_kpis,
        "where_sql": where_sql,
        "monthly_trend": trend_data,
        "category_performance": category_data,
        "filtered_count": len(filtered_df),
        "preview_data": preview_df.to_dict(orient="records"),
    }


@app.post("/api/revenue-profit")
def get_revenue_profit_data(filters: FilterRequest):
    """Returns detailed revenue vs profit time series, sub-categories, and discount cliff scatter."""
    raw_df = get_dataset()
    filtered_df = apply_filters(raw_df, filters)

    freq_map = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}
    freq_code = freq_map.get(filters.time_granularity or "Monthly", "M")
    time_trend_df = get_time_series_trend(filtered_df, freq=freq_code)

    trend_records = []
    if not time_trend_df.empty:
        trend_records = time_trend_df[
            ["period", "sales", "profit", "profit_margin_pct", "cumulative_sales", "cumulative_profit"]
        ].to_dict(orient="records")

    _, subcat_df = get_category_performance(filtered_df)
    subcat_records = []
    if not subcat_df.empty:
        subcat_records = subcat_df[
            ["category", "sub_category", "sales", "profit", "profit_margin_pct", "avg_discount_pct"]
        ].to_dict(orient="records")

    # Sample scatter data points (up to 1500 points for smooth charting)
    scatter_df = (
        filtered_df.sample(min(1500, len(filtered_df)), random_state=42) if len(filtered_df) > 1500 else filtered_df
    )
    scatter_records = scatter_df[
        ["sub_category", "category", "sales", "profit", "discount", "profit_margin", "state"]
    ].to_dict(orient="records")

    return {
        "trend": trend_records,
        "subcategories": subcat_records,
        "scatter": scatter_records,
    }


@app.post("/api/regional")
def get_regional_data(filters: FilterRequest):
    """Returns US state metrics for choropleth maps, top/bottom states, segment, and shipping modes."""
    raw_df = get_dataset()
    filtered_df = apply_filters(raw_df, filters)

    reg_df, state_df = get_regional_state_metrics(filtered_df)
    seg_df, ship_df = get_shipping_segment_analysis(filtered_df)

    states_records = (
        state_df[["state", "state_code", "region", "sales", "profit", "profit_margin_pct", "loss_rate_pct", "orders"]]
        .dropna(subset=["state_code"])
        .to_dict(orient="records")
        if not state_df.empty
        else []
    )

    top_10 = (
        state_df.sort_values("profit", ascending=False)
        .head(10)[["state", "region", "sales", "profit", "profit_margin_pct", "avg_discount_pct"]]
        .to_dict(orient="records")
        if not state_df.empty
        else []
    )

    bottom_10 = (
        state_df.sort_values("profit", ascending=True)
        .head(10)[["state", "region", "sales", "profit", "profit_margin_pct", "avg_discount_pct"]]
        .to_dict(orient="records")
        if not state_df.empty
        else []
    )

    segments_records = (
        seg_df[["segment", "sales", "profit", "profit_margin_pct", "orders", "avg_order_value"]].to_dict(
            orient="records"
        )
        if not seg_df.empty
        else []
    )

    shipping_records = (
        ship_df[["ship_mode", "sales", "profit", "profit_margin_pct", "orders", "avg_days"]].to_dict(orient="records")
        if not ship_df.empty
        else []
    )

    return {
        "states": states_records,
        "top_states": top_10,
        "bottom_states": bottom_10,
        "segments": segments_records,
        "shipping": shipping_records,
    }


@app.post("/api/underperformers")
def get_underperformers_data(filters: FilterRequest):
    """Returns bottom sub-categories, loss-making SKUs, discount band erosion, and basket analysis."""
    raw_df = get_dataset()
    filtered_df = apply_filters(raw_df, filters)

    underperformers = detect_underperformers(filtered_df, bottom_n=3)
    discount_impact_df = analyze_discount_impact(filtered_df)
    basket_df = get_basket_cooccurrence(filtered_df, top_n=6)

    bottom_subcats = (
        underperformers["flagged_subcategories"][
            ["sub_category", "category", "sales", "profit", "profit_margin_pct", "avg_discount_pct"]
        ].to_dict(orient="records")
        if not underperformers["flagged_subcategories"].empty
        else []
    )

    loss_products = (
        underperformers["loss_making_products"]
        .head(10)[
            [
                "product_name",
                "category",
                "sub_category",
                "total_sales",
                "total_profit",
                "avg_discount_pct",
                "profit_margin_pct",
            ]
        ]
        .to_dict(orient="records")
        if not underperformers["loss_making_products"].empty
        else []
    )

    discount_bands = (
        discount_impact_df[
            ["discount_tier", "transactions", "sales", "profit", "profit_margin_pct", "loss_rate_pct"]
        ].to_dict(orient="records")
        if not discount_impact_df.empty
        else []
    )

    basket_records = (
        basket_df[
            [
                "product_name_1",
                "sub_category_1",
                "product_name_2",
                "sub_category_2",
                "co_occurrence_orders",
                "support_pct",
            ]
        ].to_dict(orient="records")
        if not basket_df.empty
        else []
    )

    return {
        "flagged_subcategories": bottom_subcats,
        "takeaways": underperformers["key_takeaways"],
        "loss_products": loss_products,
        "discount_bands": discount_bands,
        "basket_affinities": basket_records,
    }


@app.post("/api/simulate")
def run_pricing_simulation(sim_req: SimulationRequest):
    """Runs What-If Pricing Simulator with dynamic discount ceiling."""
    raw_df = get_dataset()
    filter_obj = FilterRequest(
        preset=sim_req.preset,
        regions=sim_req.regions,
        categories=sim_req.categories,
        sub_categories=sim_req.sub_categories,
        segments=sim_req.segments,
        start_date=sim_req.start_date,
        end_date=sim_req.end_date,
    )
    filtered_df = apply_filters(raw_df, filter_obj)
    sim_result = simulate_discount_cap(filtered_df, max_discount_pct=sim_req.max_discount_pct)
    return sim_result


@app.get("/api/sql/curated")
def get_curated_queries():
    """Returns curated SQL queries catalog."""
    queries_list = []
    for key, data in CURATED_SQL_QUERIES.items():
        queries_list.append(
            {
                "key": key,
                "title": data["title"],
                "description": data["description"],
                "skills": data["skills"],
                "sql": data["sql"],
            }
        )
    return queries_list


@app.post("/api/sql/execute-curated")
def execute_curated_query(req: CuratedSqlRequest):
    """Executes a curated SQL query against SQLite."""
    if req.query_key not in CURATED_SQL_QUERIES:
        raise HTTPException(status_code=404, detail="Query key not found")

    sql_str = CURATED_SQL_QUERIES[req.query_key]["sql"]
    df, elapsed_ms, err = execute_sql_query(sql_str, db_path=DB_PATH)

    if err:
        return {"success": False, "error": err, "elapsed_ms": elapsed_ms, "rows": [], "columns": []}

    return {
        "success": True,
        "error": None,
        "elapsed_ms": round(elapsed_ms, 2),
        "columns": df.columns.tolist(),
        "rows": df.to_dict(orient="records"),
        "row_count": len(df),
    }


@app.post("/api/sql/execute-custom")
def execute_custom_query(req: CustomSqlRequest):
    """Executes custom user SELECT/WITH SQL safely in sandbox."""
    df, elapsed_ms, err = execute_safe_custom_sql(req.query_sql, db_path=DB_PATH)

    if err:
        return {"success": False, "error": err, "elapsed_ms": elapsed_ms, "rows": [], "columns": []}

    return {
        "success": True,
        "error": None,
        "elapsed_ms": round(elapsed_ms, 2),
        "columns": df.columns.tolist(),
        "rows": df.to_dict(orient="records"),
        "row_count": len(df),
    }


@app.post("/api/export")
def export_filtered_csv(filters: FilterRequest):
    """Exports filtered dataset as downloadable CSV."""
    raw_df = get_dataset()
    filtered_df = apply_filters(raw_df, filters)

    stream = io.StringIO()
    filtered_df.to_csv(stream, index=False)
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=superstore_filtered_data.csv"},
    )
    return response


# Mount static assets for frontend SPA
PUBLIC_DIR = PROJECT_ROOT / "public"
if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serves the main single page web application."""
    index_file = PUBLIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Superstore Sales Intelligence API</h1><p>Visit /docs for API documentation.</p>")


if __name__ == "__main__":
    import uvicorn

    get_dataset()
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Superstore Sales Intelligence Server on http://localhost:{port}")
    uvicorn.run("api.index:app", host="0.0.0.0", port=port, reload=True)

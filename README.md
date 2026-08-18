# 📈 Superstore Sales & Profitability Intelligence Platform

[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3.0+-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Plotly.js](https://img.shields.io/badge/Plotly.js-2.32+-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/javascript/)
[![Pytest](https://img.shields.io/badge/Pytest-8.0+-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)

An interactive enterprise data analytics web application evaluating **9,993 sales transactions** across US retail markets from the classic Sample Superstore dataset. Built as a **production-ready full-stack web application (FastAPI + Vanilla JS/HTML5/CSS3 + Plotly.js + SQLite)** specifically optimized for **instant zero-config deployment to Vercel**.

---

## 🌟 Executive Summary & Findings

Superstore generated **$2,296,919.49 in revenue** across 5,009 unique customer orders, but only retained **$286,409.08 in net profit** (an aggregate **12.5% profit margin**). The average transaction discount stood at **15.6%**, concealing substantial margin erosion in key product categories and regional territories.

### 🔑 Key Analytical Takeaways

1. **🚨 The Underperformer Trap (Tables, Bookcases, Supplies)**:
   - **Tables** generated **$206.96K in sales** but suffered an aggregate net loss of **-$17,725.48** (-8.6% margin).
   - **Bookcases** generated **$114.88K in sales** with a net loss of **-$3,472.56** (-3.0% margin).
   - **Supplies** generated **$46.67K in sales** with a net loss of **-$1,189.10** (-2.5% margin).
   - *Root Cause*: Over 35% of Table orders carried discounts exceeding 40%, dropping transaction margins past the break-even floor.

2. **📉 The Discount Cliff (>20% Discount Threshold)**:
   - Orders with **0% discount** averaged a healthy **+30.1% profit margin**.
   - Orders with **1%–20% discount** remained profitable with an average **+12.8% profit margin**.
   - Orders exceeding **20% discount** experienced a catastrophic margin collapse, averaging **-42.5% to -85.2% profit margins**.

3. **🗺️ Regional Disparities & Drain States**:
   - **Top Profitable States**: California (**+$76,403**), New York (**+$74,039**), and Washington (**+$33,403**).
   - **Worst Loss States**: Texas (**-$25,729**), Ohio (**-$17,007**), Pennsylvania (**-$15,560**), and Illinois (**-$12,608**), driven by regional promotional discounts averaging over 30%.

4. **💡 Margin Recovery Simulation**:
   - Instituting an enterprise-wide **20% discount ceiling** is estimated to recover **+$40,000+ in net profit** (+14.0% profit lift) while salvaging over 850 previously loss-making transactions.

---

## 🏗️ Architecture & Project Structure

```
Superstore-Sales-Analysis/
├── api/
│   └── index.py                      # FastAPI serverless entry point & analytical REST endpoints
├── public/
│   ├── index.html                    # Single Page Application dashboard UI (Blue & White)
│   ├── styles.css                    # Modern responsive enterprise CSS theme
│   └── app.js                        # Reactive state, Plotly.js charts & AJAX client
├── data/
│   ├── Sample - Superstore.csv       # Standardized dataset (9,993 verified transactions)
│   └── superstore.db                 # SQLite database with B-Tree indexes
├── src/
│   ├── __init__.py
│   ├── data_loader.py                 # Data cleaning, date parsing, and SQLite indexer
│   ├── queries.py                     # 10 Curated SQL analytical queries + safe query sandbox
│   ├── analysis.py                    # Pandas analysis engine, underperformer detection, simulator
│   └── utils.py                       # Formatting helpers and color tokens
├── tests/
│   ├── __init__.py
│   └── test_analysis.py               # Automated pytest suite verifying calculations & SQL parity
├── vercel.json                        # Vercel serverless deployment configuration
├── package.json                       # Project descriptor & scripts
├── requirements.txt                   # FastAPI, Pandas, NumPy, Pydantic, Pytest
└── README.md                          # Full project documentation
```

---

## ⚡ Core Application Features

### 1. 📊 Executive Overview Tab
- **Scorecard Metrics**: Dynamic KPI cards for Total Revenue, Total Profit, Profit Margin %, Total Orders, and Average Order Value (AOV).
- **Dual-Engine Execution**: Side-by-side verification demonstrating that KPIs are computed simultaneously via **Pandas vectorization** and **SQLite SQL aggregations** with 100% precision parity.
- **Monthly Trajectory & Category Breakdown**: Integrated time-series line charts and grouped bar charts.
- **Transaction Explorer**: Filterable raw data table with live CSV export.

### 2. 💰 Revenue & Profitability Tab
- **Granular Time-Series**: Toggle between Monthly, Quarterly, and Yearly trends with dual Y-axis margin tracking.
- **Sub-Category Margin Disparity**: Side-by-side bar chart contrasting top-line sales against actual profit.
- **Interactive Discount Cliff Scatter Plot**: Visualizing 9,993 transactions plotted by Discount % vs. Profit ($) with zero-profit threshold lines.

### 3. 🗺️ Regional & Segment Dynamics Tab
- **Interactive US Choropleth Map**: Plotly US state map with metric switching (Sales, Profit, Profit Margin %, Loss Rate %).
- **State Leaderboards**: Top 10 most profitable states vs. Top 10 loss-making states.
- **Segment & Logistics Analysis**: Consumer vs. Corporate vs. Home Office performance and shipping duration vs. margin impact.

### 4. ⚠️ Underperformer Engine & Pricing Simulator
- **Automated Underperformer Detection**: Automatically isolates and flags bottom sub-categories and worst-performing SKUs.
- **Interactive "What-If" Discount Cap Simulator**: Dynamic slider allowing executives to test discount caps (5% to 40%) and instantly compute estimated recovered profit, new margin %, and salvaged orders.
- **Market Basket Affinity Discovery**: Identifies high-frequency co-occurring product pairs (e.g. `FUR-FU-10003464` and `TEC-PH-10002496`).

### 5. 🔍 SQL Query Explorer (Database Showcase)
- **10 Curated Analytical SQL Queries** showcasing advanced SQL paradigms:
  1. *Same-Day Shipping Ratio* (`COUNT`, `CASE WHEN`, `CAST/ROUND`)
  2. *Top Customers by Volume & Spend* (`GROUP BY`, `SUM/COUNT`, `LIMIT`)
  3. *Customer Average Order Value Ranking* (`RANK() OVER (ORDER BY avg_sales DESC)`)
  4. *Sub-Category Profitability Partitioning* (`DENSE_RANK() OVER (PARTITION BY category)`)
  5. *Monthly Cumulative Running Totals* (`SUM(sales) OVER (ROWS BETWEEN UNBOUNDED PRECEDING)`)
  6. *City Purchasing Extremes* (Multiple CTEs, `GROUP_CONCAT`, `Self-Joins`)
  7. *Discount Tier Margin Erosion Matrix* (`CASE WHEN` binning)
  8. *Top Loss-Making Products* (`HAVING SUM(profit) < -1000`)
  9. *Regional Demand Leaders* (`GROUP BY region, sub_category`)
  10. *Multi-Day Consecutive Repeat Buyers* (`LEAD() OVER()`, `julianday()` date arithmetic)
- **🛡️ Read-Only SQL Playground**: Safe query editor allowing users to execute custom `SELECT` / `WITH` statements against SQLite with built-in execution latency benchmarks (ms).

### 6. 📋 Strategic Recommendations Tab
- 4-Pillar Executive Action Plan (Discount Governance, Regional Realignment, Corporate B2B Agreements, Product Portfolio Rationalization).

---

## 🚀 How to Deploy to Vercel (1 Click)

### Option 1: Deploy via GitHub (Recommended)
1. Push this repository to your GitHub account (`git push origin main`).
2. Go to **[Vercel Dashboard](https://vercel.com/new)** $\rightarrow$ **Import Git Repository**.
3. Select your repository.
4. Click **Deploy**. Vercel will automatically detect `vercel.json` and deploy the FastAPI backend and static frontend!

### Option 2: Deploy via Vercel CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy directly from terminal
vercel
```

---

## 💻 Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run local FastAPI server
uvicorn api.index:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🧪 Running Automated Tests

```bash
pytest tests/test_analysis.py -v
```

---

## 👤 Author

- **Author**: Sai Sri Praneeth Bandi
- **Email**: [saipraneethbandi20@gmail.com](mailto:saipraneethbandi20@gmail.com)
- **GitHub**: [@Saipraneeth13](https://github.com/Saipraneeth13)

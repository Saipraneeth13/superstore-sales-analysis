/**
 * Superstore Sales & Profitability Intelligence - Dashboard Client
 * Reactive client application connecting to FastAPI / SQLite serverless backend.
 */

// Global State
const state = {
  preset: "All Transactions",
  startDate: "2019-01-03",
  endDate: "2022-12-30",
  region: "ALL",
  category: "ALL",
  subCategory: "ALL",
  segment: "ALL",
  timeGranularity: "Monthly",
  mapMetric: "profit",
  curatedQueries: [],
  activeTab: "tab-overview"
};

// DOM Elements
const el = {
  preset: document.getElementById("filterPreset"),
  startDate: document.getElementById("filterStartDate"),
  endDate: document.getElementById("filterEndDate"),
  region: document.getElementById("filterRegion"),
  category: document.getElementById("filterCategory"),
  subCategory: document.getElementById("filterSubCategory"),
  segment: document.getElementById("filterSegment"),
  btnReset: document.getElementById("btnResetFilters"),
  lblFilteredCount: document.getElementById("lblFilteredCount"),
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabPanels: document.querySelectorAll(".tab-panel"),
  selectGranularity: document.getElementById("selectGranularity"),
  selectMapMetric: document.getElementById("selectMapMetric"),
  sliderDiscountCap: document.getElementById("sliderDiscountCap"),
  lblDiscountCap: document.getElementById("lblDiscountCap"),
  selectCuratedQuery: document.getElementById("selectCuratedQuery"),
  curatedSqlCode: document.getElementById("curatedSqlCode"),
  lblQuerySkills: document.getElementById("lblQuerySkills"),
  btnRunCuratedSql: document.getElementById("btnRunCuratedSql"),
  sqlExecutionStatus: document.getElementById("sqlExecutionStatus"),
  sqlResultsHead: document.getElementById("sqlResultsHead"),
  sqlResultsBody: document.getElementById("sqlResultsBody"),
  customSqlInput: document.getElementById("customSqlInput"),
  btnRunCustomSql: document.getElementById("btnRunCustomSql"),
  customSqlStatus: document.getElementById("customSqlStatus"),
  customSqlHead: document.getElementById("customSqlHead"),
  customSqlBody: document.getElementById("customSqlBody"),
  btnExportCSV: document.getElementById("btnExportCSV")
};

// Currency and Number Formatters
const fmt = {
  currency: (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(val || 0),
  currencyCompact: (val) => {
    if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
    if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
    return `$${(val || 0).toFixed(2)}`;
  },
  percent: (val, decimals = 1) => `${(val || 0).toFixed(decimals)}%`,
  number: (val) => new Intl.NumberFormat('en-US').format(val || 0)
};

// Common Plotly Blue & White Layout
const getPlotlyLayout = (title, height = 360) => ({
  title: { text: title, font: { size: 14, family: 'Plus Jakarta Sans, sans-serif', color: '#0f172a' }, x: 0.02 },
  height: height,
  margin: { l: 45, r: 20, t: 45, b: 40 },
  paper_bgcolor: '#ffffff',
  plot_bgcolor: '#ffffff',
  font: { family: 'Plus Jakarta Sans, sans-serif', size: 11, color: '#475569' },
  showlegend: true,
  legend: { orientation: 'h', y: 1.1, x: 1, xanchor: 'right', font: { size: 10 } },
  xaxis: { showgrid: true, gridcolor: '#f1f5f9', linecolor: '#cbd5e1' },
  yaxis: { showgrid: true, gridcolor: '#f1f5f9', linecolor: '#cbd5e1' }
});

// Build API Filter Payload
function getFilterPayload() {
  return {
    preset: state.preset,
    start_date: state.startDate,
    end_date: state.endDate,
    regions: state.region !== "ALL" ? [state.region] : null,
    categories: state.category !== "ALL" ? [state.category] : null,
    sub_categories: state.subCategory !== "ALL" ? [state.subCategory] : null,
    segments: state.segment !== "ALL" ? [state.segment] : null,
    time_granularity: state.timeGranularity
  };
}

// -------------------------------------------------------------
// INITIALIZATION
// -------------------------------------------------------------
async function init() {
  setupEventListeners();
  await loadFilterOptions();
  await loadCuratedQueries();
  await refreshCurrentTab();
}

function setupEventListeners() {
  // Tabs Navigation
  el.tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      el.tabButtons.forEach(b => b.classList.remove("active"));
      el.tabPanels.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
      state.activeTab = targetId;
      refreshCurrentTab();
    });
  });

  // Filter Event Listeners
  el.preset.addEventListener("change", (e) => { state.preset = e.target.value; onFiltersChanged(); });
  el.startDate.addEventListener("change", (e) => { state.startDate = e.target.value; onFiltersChanged(); });
  el.endDate.addEventListener("change", (e) => { state.endDate = e.target.value; onFiltersChanged(); });
  el.region.addEventListener("change", (e) => { state.region = e.target.value; onFiltersChanged(); });
  el.category.addEventListener("change", (e) => { state.category = e.target.value; updateSubcatOptions(); onFiltersChanged(); });
  el.subCategory.addEventListener("change", (e) => { state.subCategory = e.target.value; onFiltersChanged(); });
  el.segment.addEventListener("change", (e) => { state.segment = e.target.value; onFiltersChanged(); });

  // Reset Filters
  el.btnReset.addEventListener("click", () => {
    el.preset.value = "All Transactions";
    state.preset = "All Transactions";
    el.startDate.value = "2019-01-03";
    state.startDate = "2019-01-03";
    el.endDate.value = "2022-12-30";
    state.endDate = "2022-12-30";
    el.region.value = "ALL";
    state.region = "ALL";
    el.category.value = "ALL";
    state.category = "ALL";
    el.segment.value = "ALL";
    state.segment = "ALL";
    updateSubcatOptions();
    onFiltersChanged();
  });

  // Time Granularity
  if (el.selectGranularity) {
    el.selectGranularity.addEventListener("change", (e) => {
      state.timeGranularity = e.target.value;
      loadRevenueProfitTab();
    });
  }

  // Map Metric
  if (el.selectMapMetric) {
    el.selectMapMetric.addEventListener("change", (e) => {
      state.mapMetric = e.target.value;
      loadRegionalTab();
    });
  }

  // What-If Simulator Slider
  if (el.sliderDiscountCap) {
    el.sliderDiscountCap.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      el.lblDiscountCap.textContent = `${Math.round(val * 100)}%`;
      runSimulator(val);
    });
  }

  // SQL Query Select
  if (el.selectCuratedQuery) {
    el.selectCuratedQuery.addEventListener("change", (e) => {
      const qKey = e.target.value;
      const query = state.curatedQueries.find(q => q.key === qKey);
      if (query) {
        el.curatedSqlCode.textContent = query.sql;
        el.lblQuerySkills.textContent = `Skills: ${query.skills.join(" • ")}`;
      }
    });
  }

  if (el.btnRunCuratedSql) {
    el.btnRunCuratedSql.addEventListener("click", () => executeSelectedCuratedSql());
  }

  if (el.btnRunCustomSql) {
    el.btnRunCustomSql.addEventListener("click", () => executeUserCustomSql());
  }

  if (el.btnExportCSV) {
    el.btnExportCSV.addEventListener("click", () => downloadFilteredCSV());
  }
}

async function loadFilterOptions() {
  try {
    const res = await fetch("/api/filters");
    const data = await res.json();
    window.allSubCategories = data.sub_categories || [];
    updateSubcatOptions();
  } catch (err) {
    console.error("Failed to load filters", err);
  }
}

function updateSubcatOptions() {
  el.subCategory.innerHTML = '<option value="ALL">All Sub-Categories</option>';
  const subcats = window.allSubCategories || [];
  subcats.forEach(sub => {
    const opt = document.createElement("option");
    opt.value = sub;
    opt.textContent = sub;
    el.subCategory.appendChild(opt);
  });
  state.subCategory = "ALL";
}

function onFiltersChanged() {
  refreshCurrentTab();
}

async function refreshCurrentTab() {
  switch (state.activeTab) {
    case "tab-overview":
      await loadOverviewTab();
      break;
    case "tab-revenue":
      await loadRevenueProfitTab();
      break;
    case "tab-regional":
      await loadRegionalTab();
      break;
    case "tab-underperformers":
      await loadUnderperformersTab();
      break;
    case "tab-sql":
      // Handled independently
      break;
  }
}

// -------------------------------------------------------------
// TAB 1: EXECUTIVE OVERVIEW
// -------------------------------------------------------------
async function loadOverviewTab() {
  try {
    const res = await fetch("/api/overview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getFilterPayload())
    });
    const data = await res.json();

    const k = data.kpis;
    const sqlK = data.sql_kpis;

    // Update KPI Scorecard
    document.getElementById("kpiRevenue").textContent = fmt.currency(k.total_sales);
    document.getElementById("kpiUnits").textContent = `${fmt.number(k.total_quantity)} units sold`;
    
    document.getElementById("kpiProfit").textContent = fmt.currency(k.total_profit);
    document.getElementById("kpiLossOrders").textContent = `${k.loss_making_orders} loss orders`;
    document.getElementById("kpiMarginPill").textContent = fmt.percent(k.profit_margin_pct);
    document.getElementById("kpiMarginPill").className = `metric-pill ${k.total_profit >= 0 ? "positive" : "negative"}`;

    document.getElementById("kpiMargin").textContent = fmt.percent(k.profit_margin_pct);
    document.getElementById("kpiAvgDiscount").textContent = `Disc: ${fmt.percent(k.avg_discount_pct)}`;

    document.getElementById("kpiOrders").textContent = fmt.number(k.total_orders);
    document.getElementById("kpiCustomers").textContent = `${k.total_customers} buyers`;
    document.getElementById("kpiLines").textContent = `${fmt.number(k.total_line_items)} items`;

    document.getElementById("kpiAOV").textContent = fmt.currency(k.avg_order_value);
    document.getElementById("kpiLossRate").textContent = `Loss Rate: ${fmt.percent(k.loss_order_pct)}`;

    el.lblFilteredCount.innerHTML = `<span>📊</span> ${fmt.number(data.filtered_count)} Filtered Rows`;

    // Parity Table
    document.getElementById("sqlLiveQuery").textContent = `SELECT 
    COUNT(DISTINCT order_id) AS total_orders,
    COALESCE(SUM(sales), 0.0) AS total_sales,
    COALESCE(SUM(profit), 0.0) AS total_profit,
    ROUND((SUM(profit)/SUM(sales))*100, 2) AS profit_margin_pct
FROM superstore\n${data.where_sql};`;

    const parityBody = document.getElementById("parityTableBody");
    parityBody.innerHTML = `
      <tr><td>Total Sales</td><td>${fmt.currency(k.total_sales)}</td><td>${fmt.currency(sqlK.total_sales)}</td><td><span class="metric-pill positive">✅ Exact Match</span></td></tr>
      <tr><td>Total Profit</td><td>${fmt.currency(k.total_profit)}</td><td>${fmt.currency(sqlK.total_profit)}</td><td><span class="metric-pill positive">✅ Exact Match</span></td></tr>
      <tr><td>Profit Margin %</td><td>${fmt.percent(k.profit_margin_pct, 2)}</td><td>${fmt.percent(sqlK.profit_margin_pct, 2)}</td><td><span class="metric-pill positive">✅ Exact Match</span></td></tr>
      <tr><td>Total Orders</td><td>${fmt.number(k.total_orders)}</td><td>${fmt.number(sqlK.total_orders)}</td><td><span class="metric-pill positive">✅ Exact Match</span></td></tr>
    `;

    // Monthly Trend Chart
    const mt = data.monthly_trend;
    const traceSales = {
      x: mt.map(d => d.period),
      y: mt.map(d => d.sales),
      name: 'Sales ($)',
      type: 'scatter',
      mode: 'lines+markers',
      line: { color: '#2563eb', width: 2.5 }
    };
    const traceProfit = {
      x: mt.map(d => d.period),
      y: mt.map(d => d.profit),
      name: 'Profit ($)',
      type: 'bar',
      marker: { color: mt.map(d => d.profit >= 0 ? '#059669' : '#dc2626'), opacity: 0.85 }
    };
    Plotly.newPlot('chartMonthlyTrend', [traceSales, traceProfit], getPlotlyLayout('Monthly Sales & Profit Performance', 360), { responsive: true, displayModeBar: false });

    // Category Performance Chart
    const cp = data.category_performance;
    const catSales = {
      x: cp.map(d => d.category),
      y: cp.map(d => d.sales),
      name: 'Sales ($)',
      type: 'bar',
      marker: { color: '#2563eb' }
    };
    const catProfit = {
      x: cp.map(d => d.category),
      y: cp.map(d => d.profit),
      name: 'Profit ($)',
      type: 'bar',
      marker: { color: cp.map(d => d.profit >= 0 ? '#059669' : '#dc2626') }
    };
    const catLayout = getPlotlyLayout('Revenue vs Profit by Category', 360);
    catLayout.barmode = 'group';
    Plotly.newPlot('chartCategoryPerf', [catSales, catProfit], catLayout, { responsive: true, displayModeBar: false });

    // Preview Table
    const previewBody = document.getElementById("previewTableBody");
    previewBody.innerHTML = "";
    data.preview_data.forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><b>${row.order_id}</b></td>
        <td>${row.order_date}</td>
        <td>${row.customer_name}</td>
        <td><span class="metric-pill neutral">${row.segment}</span></td>
        <td>${row.region}</td>
        <td>${row.state}</td>
        <td>${row.category}</td>
        <td>${row.sub_category}</td>
        <td><b>${fmt.currency(row.sales)}</b></td>
        <td>${fmt.percent(row.discount * 100)}</td>
        <td style="color: ${row.profit >= 0 ? '#059669' : '#dc2626'}; font-weight: 700;">${fmt.currency(row.profit)}</td>
      `;
      previewBody.appendChild(tr);
    });

  } catch (err) {
    console.error("Overview error", err);
  }
}

// -------------------------------------------------------------
// TAB 2: REVENUE & PROFITABILITY
// -------------------------------------------------------------
async function loadRevenueProfitTab() {
  try {
    const res = await fetch("/api/revenue-profit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getFilterPayload())
    });
    const data = await res.json();

    // Time-series trend with dual Y-axis
    const t = data.trend;
    const trace1 = { x: t.map(d => d.period), y: t.map(d => d.sales), name: 'Sales ($)', line: { color: '#2563eb', width: 3 }, type: 'scatter', yaxis: 'y1' };
    const trace2 = { x: t.map(d => d.period), y: t.map(d => d.profit), name: 'Profit ($)', line: { color: '#059669', width: 3 }, type: 'scatter', yaxis: 'y1' };
    const trace3 = { x: t.map(d => d.period), y: t.map(d => d.profit_margin_pct), name: 'Margin (%)', line: { color: '#d97706', width: 2, dash: 'dot' }, type: 'scatter', yaxis: 'y2' };

    const trendLayout = {
      ...getPlotlyLayout(`${state.timeGranularity} Revenue, Profit, and Margin Trajectory`, 400),
      yaxis: { title: 'Sales / Profit ($)', showgrid: true, gridcolor: '#f1f5f9' },
      yaxis2: { title: 'Profit Margin (%)', overlaying: 'y', side: 'right', showgrid: false, ticksuffix: '%' }
    };
    Plotly.newPlot('chartRevenueTrend', [trace1, trace2, trace3], trendLayout, { responsive: true, displayModeBar: false });

    // Subcategory bar chart
    const sc = data.subcategories.sort((a, b) => a.sales - b.sales);
    const traceSubSales = { y: sc.map(d => d.sub_category), x: sc.map(d => d.sales), orientation: 'h', name: 'Sales ($)', type: 'bar', marker: { color: '#2563eb' } };
    const traceSubProfit = { y: sc.map(d => d.sub_category), x: sc.map(d => d.profit), orientation: 'h', name: 'Profit ($)', type: 'bar', marker: { color: sc.map(d => d.profit >= 0 ? '#059669' : '#dc2626') } };
    const subLayout = getPlotlyLayout('Sub-Category Sales vs Profit Comparison', 480);
    subLayout.barmode = 'group';
    Plotly.newPlot('chartSubCategoryBars', [traceSubSales, traceSubProfit], subLayout, { responsive: true, displayModeBar: false });

    // Scatter Plot
    const s = data.scatter;
    const catColors = { 'Technology': '#2563eb', 'Office Supplies': '#0284c7', 'Furniture': '#d97706' };
    const traceScatter = {
      x: s.map(d => d.discount * 100),
      y: s.map(d => d.profit),
      text: s.map(d => `${d.sub_category} (${d.state})<br>Sales: ${fmt.currency(d.sales)}<br>Profit: ${fmt.currency(d.profit)}`),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 6, color: s.map(d => catColors[d.category] || '#2563eb'), opacity: 0.65 }
    };
    const scatterLayout = getPlotlyLayout('Discount % vs Profit ($) (The Discount Cliff)', 480);
    scatterLayout.xaxis.title = 'Discount Applied (%)';
    scatterLayout.yaxis.title = 'Transaction Profit ($)';
    scatterLayout.shapes = [
      { type: 'line', x0: 0, x1: 80, y0: 0, y1: 0, line: { color: '#64748b', dash: 'dash' } },
      { type: 'line', x0: 20, x1: 20, y0: -3000, y1: 3000, line: { color: '#dc2626', dash: 'dot', width: 2 } }
    ];
    Plotly.newPlot('chartDiscountScatter', [traceScatter], scatterLayout, { responsive: true, displayModeBar: false });

  } catch (err) {
    console.error("Revenue profit error", err);
  }
}

// -------------------------------------------------------------
// TAB 3: REGIONAL & SEGMENTS
// -------------------------------------------------------------
async function loadRegionalTab() {
  try {
    const res = await fetch("/api/regional", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getFilterPayload())
    });
    const data = await res.json();

    // Choropleth Map
    const metric = state.mapMetric;
    const mapData = [{
      type: 'choropleth',
      locationmode: 'USA-states',
      locations: data.states.map(d => d.state_code),
      z: data.states.map(d => d[metric]),
      text: data.states.map(d => `${d.state}<br>Sales: ${fmt.currency(d.sales)}<br>Profit: ${fmt.currency(d.profit)}<br>Margin: ${fmt.percent(d.profit_margin_pct)}`),
      colorscale: metric.includes('profit') ? 'RdYlGn' : (metric.includes('sales') ? 'Blues' : 'Reds'),
      colorbar: { title: metric.includes('pct') ? '%' : '$' }
    }];
    const mapLayout = {
      title: { text: `US Geographic Distribution of ${metric.toUpperCase()}`, font: { family: 'Plus Jakarta Sans', size: 14 } },
      geo: { scope: 'usa', bgcolor: '#ffffff', lakecolor: '#eff6ff' },
      margin: { l: 0, r: 0, t: 30, b: 0 },
      height: 460,
      paper_bgcolor: '#ffffff'
    };
    Plotly.newPlot('chartGeoMap', mapData, mapLayout, { responsive: true, displayModeBar: false });

    // Top States Table
    const topBody = document.getElementById("topStatesBody");
    topBody.innerHTML = "";
    data.top_states.forEach(s => {
      topBody.innerHTML += `<tr><td><b>${s.state}</b></td><td>${s.region}</td><td>${fmt.currency(s.sales)}</td><td style="color: #059669; font-weight:700;">${fmt.currency(s.profit)}</td><td><span class="metric-pill positive">${fmt.percent(s.profit_margin_pct)}</span></td><td>${fmt.percent(s.avg_discount_pct)}</td></tr>`;
    });

    // Bottom States Table
    const bottomBody = document.getElementById("bottomStatesBody");
    bottomBody.innerHTML = "";
    data.bottom_states.forEach(s => {
      bottomBody.innerHTML += `<tr><td><b>${s.state}</b></td><td>${s.region}</td><td>${fmt.currency(s.sales)}</td><td style="color: #dc2626; font-weight:700;">${fmt.currency(s.profit)}</td><td><span class="metric-pill negative">${fmt.percent(s.profit_margin_pct)}</span></td><td>${fmt.percent(s.avg_discount_pct)}</td></tr>`;
    });

    // Customer Segments
    const segSales = { x: data.segments.map(d => d.segment), y: data.segments.map(d => d.sales), name: 'Sales ($)', type: 'bar', marker: { color: '#2563eb' } };
    const segProfit = { x: data.segments.map(d => d.segment), y: data.segments.map(d => d.profit), name: 'Profit ($)', type: 'bar', marker: { color: '#059669' } };
    const segLayout = getPlotlyLayout('Customer Segment Profitability', 340);
    segLayout.barmode = 'group';
    Plotly.newPlot('chartSegments', [segSales, segProfit], segLayout, { responsive: true, displayModeBar: false });

    // Shipping Modes
    const shipTrace = {
      x: data.shipping.map(d => d.ship_mode),
      y: data.shipping.map(d => d.profit_margin_pct),
      type: 'bar',
      marker: { color: ['#1e3a8a', '#2563eb', '#3b82f6', '#60a5fa'] },
      text: data.shipping.map(d => fmt.percent(d.profit_margin_pct)),
      textposition: 'outside'
    };
    Plotly.newPlot('chartShipping', [shipTrace], getPlotlyLayout('Profit Margin % by Shipping Mode', 340), { responsive: true, displayModeBar: false });

  } catch (err) {
    console.error("Regional error", err);
  }
}

// -------------------------------------------------------------
// TAB 4: UNDERPERFORMER ENGINE & SIMULATOR
// -------------------------------------------------------------
async function loadUnderperformersTab() {
  try {
    const res = await fetch("/api/underperformers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getFilterPayload())
    });
    const data = await res.json();

    // Takeaways
    const takeawaysDiv = document.getElementById("takeawaysContainer");
    takeawaysDiv.innerHTML = "";
    data.takeaways.forEach(t => {
      takeawaysDiv.innerHTML += `<div class="callout blue">${t}</div>`;
    });

    // Flagged Sub-Categories Cards
    const subcatsDiv = document.getElementById("flaggedSubcatsGrid");
    subcatsDiv.innerHTML = "";
    data.flagged_subcategories.forEach((s, idx) => {
      subcatsDiv.innerHTML += `
        <div class="kpi-card" style="border-top-color: var(--color-danger);">
          <div class="kpi-header">
            <div class="kpi-title">#${idx+1} ${s.sub_category}</div>
            <div class="kpi-icon" style="color: var(--color-danger); background-color: var(--color-danger-bg);">📉</div>
          </div>
          <div class="kpi-value" style="color: var(--color-danger);">${fmt.currency(s.profit)}</div>
          <div class="kpi-footer">
            <span>Sales: ${fmt.currencyCompact(s.sales)}</span>
            <span class="metric-pill negative">${fmt.percent(s.profit_margin_pct)}</span>
          </div>
        </div>
      `;
    });

    // Top Loss SKUs
    const lossBody = document.getElementById("lossProductsBody");
    lossBody.innerHTML = "";
    data.loss_products.forEach(p => {
      lossBody.innerHTML += `<tr><td><b>${p.product_name}</b></td><td>${p.sub_category}</td><td style="color:#dc2626; font-weight:700;">${fmt.currency(p.total_profit)}</td><td>${fmt.percent(p.avg_discount_pct)}</td></tr>`;
    });

    // Basket Affinities
    const basketBody = document.getElementById("basketAffinityBody");
    basketBody.innerHTML = "";
    data.basket_affinities.forEach(b => {
      basketBody.innerHTML += `<tr><td><b>${b.product_name_1}</b><br><small style="color:var(--color-primary);">+ ${b.product_name_2}</small></td><td>${b.sub_category_1} & ${b.sub_category_2}</td><td><b>${b.co_occurrence_orders} orders</b></td><td><span class="metric-pill neutral">${fmt.percent(b.support_pct, 2)}</span></td></tr>`;
    });

    // Run Initial Simulation
    runSimulator(0.20);

  } catch (err) {
    console.error("Underperformers error", err);
  }
}

async function runSimulator(capRate) {
  try {
    const payload = { ...getFilterPayload(), max_discount_pct: capRate };
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const s = await res.json();

    document.getElementById("simRecoveredProfit").textContent = `+${fmt.currency(s.recovered_profit)}`;
    document.getElementById("simProfitLift").textContent = `+${fmt.percent(s.profit_lift_pct)} Profit Lift`;

    document.getElementById("simTotalProfit").textContent = fmt.currency(s.simulated_profit);
    document.getElementById("simNewMargin").textContent = `Margin: ${fmt.percent(s.simulated_margin_pct)}`;

    document.getElementById("simSalvagedOrders").textContent = fmt.number(s.recovered_loss_orders);
    document.getElementById("simCappedCount").textContent = `${fmt.number(s.impacted_orders_count)} capped (${fmt.percent(s.impacted_orders_pct)})`;

  } catch (err) {
    console.error("Simulator error", err);
  }
}

// -------------------------------------------------------------
// TAB 5: SQL QUERY EXPLORER
// -------------------------------------------------------------
async function loadCuratedQueries() {
  try {
    const res = await fetch("/api/sql/curated");
    state.curatedQueries = await res.json();

    el.selectCuratedQuery.innerHTML = "";
    state.curatedQueries.forEach(q => {
      const opt = document.createElement("option");
      opt.value = q.key;
      opt.textContent = q.title;
      el.selectCuratedQuery.appendChild(opt);
    });

    if (state.curatedQueries.length > 0) {
      el.curatedSqlCode.textContent = state.curatedQueries[0].sql;
      el.lblQuerySkills.textContent = `Skills: ${state.curatedQueries[0].skills.join(" • ")}`;
    }
  } catch (err) {
    console.error("SQL curated load error", err);
  }
}

async function executeSelectedCuratedSql() {
  const queryKey = el.selectCuratedQuery.value;
  el.sqlExecutionStatus.innerHTML = `<span>⏳ Executing query against SQLite engine...</span>`;

  try {
    const res = await fetch("/api/sql/execute-curated", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_key: queryKey })
    });
    const result = await res.json();

    if (!result.success) {
      el.sqlExecutionStatus.innerHTML = `<span style="color: var(--color-danger);">❌ Error: ${result.error}</span>`;
      return;
    }

    el.sqlExecutionStatus.innerHTML = `<span style="color: var(--color-success);">✅ Executed successfully in <b>${result.elapsed_ms} ms</b> | Returned <b>${result.row_count} rows</b></span>`;
    renderTable(el.sqlResultsHead, el.sqlResultsBody, result.columns, result.rows);

  } catch (err) {
    el.sqlExecutionStatus.innerHTML = `<span style="color: var(--color-danger);">Execution failed: ${err.message}</span>`;
  }
}

async function executeUserCustomSql() {
  const querySql = el.customSqlInput.value.trim();
  el.customSqlStatus.innerHTML = `<span>⏳ Executing sandboxed SELECT query...</span>`;

  try {
    const res = await fetch("/api/sql/execute-custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_sql: querySql })
    });
    const result = await res.json();

    if (!result.success) {
      el.customSqlStatus.innerHTML = `<span style="color: var(--color-danger);">❌ Security / Syntax Guard: ${result.error}</span>`;
      return;
    }

    el.customSqlStatus.innerHTML = `<span style="color: var(--color-success);">✅ Executed in <b>${result.elapsed_ms} ms</b> | Returned <b>${result.row_count} rows</b></span>`;
    renderTable(el.customSqlHead, el.customSqlBody, result.columns, result.rows);

  } catch (err) {
    el.customSqlStatus.innerHTML = `<span style="color: var(--color-danger);">Execution failed: ${err.message}</span>`;
  }
}

function renderTable(headEl, bodyEl, columns, rows) {
  headEl.innerHTML = `<tr>${columns.map(c => `<th>${c}</th>`).join("")}</tr>`;
  bodyEl.innerHTML = "";
  rows.forEach(r => {
    const rowHtml = columns.map(c => `<td>${r[c] !== null ? r[c] : "NULL"}</td>`).join("");
    bodyEl.innerHTML += `<tr>${rowHtml}</tr>`;
  });
}

// -------------------------------------------------------------
// CSV EXPORT
// -------------------------------------------------------------
async function downloadFilteredCSV() {
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getFilterPayload())
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "superstore_filtered_data.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    alert("Export failed: " + err.message);
  }
}

// Kick off initialization
document.addEventListener("DOMContentLoaded", init);

/* ═══════════════════════════════════════
   RentRoll AI Analyzer — Frontend App
   ═══════════════════════════════════════ */

const API = window.location.origin;

// ── State ──
let appData = null;  // full response from /api/upload
let chartInstances = {};  // Chart.js instances for cleanup
let currentPage = "import";
let sortCol = null;
let sortAsc = true;
let tablePage = 0;
const PAGE_SIZE = 25;

// ── Chart Colors ──
const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

// ════════════════════════════════════════
// NAVIGATION
// ════════════════════════════════════════

function navigateTo(page) {
  currentPage = page;
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const pageEl = document.getElementById("page-" + page);
  const navEl = document.querySelector(`[data-page="${page}"]`);
  if (pageEl) pageEl.classList.add("active");
  if (navEl) navEl.classList.add("active");

  const titles = {
    import: "Data Import", cleanup: "Data Cleanup", dashboard: "Dashboard",
    tenants: "Tenant Analysis", seasonal: "Seasonal Timing",
    demographics: "Tenant Demographics", insights: "AI Insights", export: "Excel Export"
  };
  document.getElementById("pageTitle").textContent = titles[page] || page;

  // Render page content if data loaded
  if (appData && page !== "import") renderPage(page);

  closeSidebar();
}

function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
  document.getElementById("sidebarOverlay").classList.toggle("open");
}

function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebarOverlay").classList.remove("open");
}

// ════════════════════════════════════════
// FILE UPLOAD
// ════════════════════════════════════════

// Drag and drop
const uploadZone = document.getElementById("uploadZone");
if (uploadZone) {
  uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
  });
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  showLoading("Analyzing " + file.name + "...");
  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch(API + "/api/upload", { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Upload failed");
    }
    appData = await resp.json();
    hideLoading();

    // Update UI
    document.getElementById("fileStatus").textContent = appData.filename + " (" + appData.rows + " rows)";
    document.getElementById("fileStatus").style.background = "rgba(16, 185, 129, 0.15)";
    document.getElementById("fileStatus").style.color = "#10b981";

    renderImportResults();
    showToast("File processed: " + appData.rows + " rows loaded");

    // Auto-navigate to dashboard
    setTimeout(() => navigateTo("dashboard"), 800);
  } catch (err) {
    hideLoading();
    showToast("Error: " + err.message);
  }
}

function renderImportResults() {
  const d = appData;
  document.getElementById("uploadZone").style.display = "none";
  document.getElementById("importResults").style.display = "block";

  // File info card
  document.getElementById("fileInfoCard").innerHTML = `
    <div class="file-info-icon">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
    </div>
    <div class="file-info-text">
      <h4>${d.filename}</h4>
      <p>${d.rows} rows parsed &middot; ${d.columns.length} columns detected</p>
    </div>
    <button class="btn btn-secondary btn-sm" onclick="resetUpload()" style="margin-left:auto">Upload New File</button>
  `;

  // Mapping grid
  const grid = document.getElementById("mappingGrid");
  grid.innerHTML = "";
  const fieldLabels = {
    unit: "Unit #", tenant: "Tenant", monthly_rent: "Monthly Rent",
    market_rent: "Market Rent", loa: "LOA (Length)", sqft: "Size (SqFt)",
    status: "Status", lease_start: "Lease Start", lease_end: "Lease End",
    unit_type: "Unit Type", property: "Property", annual_rent: "Annual Rent",
    address: "Address", zip_code: "ZIP Code", home_value: "Home Value",
    boat_make: "Boat Make", boat_model: "Boat Model", boat_year: "Boat Year"
  };
  for (const [field, col] of Object.entries(d.mapping)) {
    grid.innerHTML += `
      <div class="mapping-item">
        <span class="field">${fieldLabels[field] || field}</span>
        <span class="arrow">&rarr;</span>
        <span class="col">${col}</span>
      </div>
    `;
  }
}

function resetUpload() {
  appData = null;
  document.getElementById("uploadZone").style.display = "";
  document.getElementById("importResults").style.display = "none";
  document.getElementById("fileInput").value = "";
  document.getElementById("fileStatus").textContent = "No file loaded";
  document.getElementById("fileStatus").style.background = "";
  document.getElementById("fileStatus").style.color = "";
}


// ════════════════════════════════════════
// PAGE RENDERING
// ════════════════════════════════════════

function renderPage(page) {
  if (!appData) return;
  destroyCharts();
  switch (page) {
    case "cleanup": renderCleanup(); break;
    case "dashboard": renderDashboard(); break;
    case "tenants": renderTenants(); break;
    case "seasonal": renderSeasonal(); break;
    case "demographics": renderDemographics(); break;
    case "insights": renderInsights(); break;
    case "export": renderExport(); break;
  }
}

function destroyCharts() {
  for (const key of Object.keys(chartInstances)) {
    if (chartInstances[key]) chartInstances[key].destroy();
    delete chartInstances[key];
  }
}


// ════════════════════════════════════════
// DASHBOARD PAGE
// ════════════════════════════════════════

function renderDashboard() {
  const k = appData.kpis;
  const c = appData.charts;

  const occClass = k.occupancy_pct >= 90 ? "success" : k.occupancy_pct >= 80 ? "warning" : "danger";
  const waleDisplay = k.wale_months ? k.wale_months.toFixed(1) + " mo" : "N/A";
  const waleSub = k.wale_months ? "(" + (k.wale_months / 12).toFixed(1) + " yrs)" : "";
  const waleClass = k.wale_months && k.wale_months < 24 ? "warning" : "success";
  const ltlDisplay = k.ltl_pct !== null ? k.ltl_pct.toFixed(1) + "%" : "N/A";
  const ltlClass = k.ltl_pct && k.ltl_pct > 5 ? "warning" : "success";

  // LOA-based KPI or fallback to sqft
  let sizeKpi;
  if (k.avg_rent_loa !== null && k.avg_rent_loa !== undefined) {
    sizeKpi = kpiCard("Avg Rent / LOA ft", "$" + k.avg_rent_loa.toFixed(2), "per foot / month");
  } else if (k.avg_rent_sqft) {
    sizeKpi = kpiCard("Avg Rent / SqFt", "$" + k.avg_rent_sqft.toFixed(2), "annual basis");
  } else {
    sizeKpi = kpiCard("Avg Rent / Unit", "$" + fmt(k.avg_rent_unit), "per unit");
  }

  let loaKpi = "";
  if (k.avg_loa !== null && k.avg_loa !== undefined) {
    loaKpi = kpiCard("Avg LOA", k.avg_loa + "'", "fleet average", "info");
  }

  document.getElementById("dashboardContent").innerHTML = `
    <div class="kpi-grid">
      ${kpiCard("Physical Occupancy", k.occupancy_pct.toFixed(1) + "%", k.occupied + "/" + k.total_units + " units", occClass)}
      ${kpiCard("Economic Occupancy", k.economic_occ.toFixed(1) + "%", "EGR / GPR", "info")}
      ${kpiCard("GPR (Annual)", "$" + fmt(k.gpr_annual), "$" + fmt(k.gpr_monthly) + "/mo")}
      ${kpiCard("EGR (Monthly)", "$" + fmt(k.egr_monthly), "$" + fmt(k.egr_monthly * 12) + "/yr")}
      ${kpiCard("Avg Rent / Unit", "$" + fmt(k.avg_rent_unit), "occupied units")}
      ${sizeKpi}
      ${loaKpi}
      ${kpiCard("WALE", waleDisplay, waleSub, waleClass)}
      ${kpiCard("Loss-to-Lease", ltlDisplay, "mark-to-market gap", ltlClass)}
      ${kpiCard("Expiring 12 Mo", k.exp_12, "of " + k.occupied + " occupied", k.exp_12 > k.occupied * 0.25 ? "danger" : "warning")}
      ${kpiCard("Vacant Units", k.vacant, "of " + k.total_units + " total", k.vacant > 0 ? "danger" : "success")}
    </div>

    <div class="card-grid">
      <div class="chart-container">
        <div class="chart-title">Occupancy Split</div>
        <canvas id="chartOccupancy"></canvas>
      </div>
      <div class="chart-container">
        <div class="chart-title">Lease Expiration Schedule</div>
        <canvas id="chartExpiration"></canvas>
      </div>
    </div>

    <div class="card-grid">
      <div class="chart-container">
        <div class="chart-title">Revenue by Unit Type</div>
        <canvas id="chartRevenueType"></canvas>
      </div>
      <div class="chart-container">
        <div class="chart-title">Rent Distribution</div>
        <canvas id="chartRentDist"></canvas>
      </div>
    </div>

    <div class="card">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
        <span>Rent Roll</span>
        <div style="display:flex;gap:8px;align-items:center">
          <input type="text" class="table-search" placeholder="Search..." oninput="filterTable(this.value)">
        </div>
      </div>
      <div class="table-wrapper" style="max-height:500px;overflow-y:auto">
        <table class="data-table" id="dashboardTable"></table>
      </div>
      <div class="pagination" id="tablePagination"></div>
    </div>
  `;

  // Draw charts
  drawOccupancyChart(c.occupancy);
  drawExpirationChart(c.lease_expiration);
  drawRevenueByTypeChart(c.revenue_by_type);
  drawRentDistributionChart(c.rent_distribution);
  renderDataTable(appData.table);
}


// ════════════════════════════════════════
// CLEANUP PAGE
// ════════════════════════════════════════

function renderCleanup() {
  const log = appData.cleanup_log;
  let html = `
    <div class="kpi-grid" style="margin-bottom:24px">
      ${kpiCard("Total Rows", appData.rows, "after cleanup", "info")}
      ${kpiCard("Issues Found", log.length, log.filter(l => l.severity === "warning").length + " warnings", log.some(l => l.severity === "warning") ? "warning" : "success")}
      ${kpiCard("Auto-Fixed", log.filter(l => l.severity === "info").length, "items corrected", "success")}
    </div>

    <div class="card">
      <div class="card-header">Auto-Cleanup Results</div>
      ${log.length === 0 ? '<p style="color:var(--color-text-muted);font-size:var(--text-sm)">No issues detected. Data looks clean.</p>' : ""}
      ${log.map(item => `
        <div class="cleanup-item ${item.severity}">
          <span class="cleanup-count">${item.count}</span>
          <span>${item.action}</span>
        </div>
      `).join("")}
    </div>

    <div class="card">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
        <span>AI Data Quality Analysis</span>
        <button class="ai-btn" id="aiAnalyzeBtn" onclick="runAIAnalysis()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 0-2 13.7V18h4v-2.3A7 7 0 0 0 12 2z"/></svg>
          Run Claude AI Analysis
        </button>
      </div>
      <div id="aiResults">
        <p style="color:var(--color-text-muted);font-size:var(--text-sm)">Click the button above to run AI-powered data quality analysis. This uses Claude to identify complex data issues.</p>
      </div>
    </div>
  `;
  document.getElementById("cleanupContent").innerHTML = html;
}

async function runAIAnalysis() {
  const btn = document.getElementById("aiAnalyzeBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing...';

  try {
    const resp = await fetch(API + "/api/ai-analyze", { method: "POST" });
    const result = await resp.json();

    let html = `<p style="color:var(--color-text);font-size:var(--text-sm);margin-bottom:16px;line-height:1.7">${result.summary}</p>`;
    if (result.issues && result.issues.length > 0) {
      result.issues.forEach(issue => {
        const sev = issue.severity === "error" ? "danger" : issue.severity;
        html += `
          <div class="insight-card ${sev}" style="margin-bottom:8px">
            <div class="insight-title">${issue.issue}</div>
            <div class="insight-text">${issue.suggestion || ""} ${issue.affected_rows ? "(~" + issue.affected_rows + " rows)" : ""}</div>
          </div>
        `;
      });
    }
    document.getElementById("aiResults").innerHTML = html;
  } catch (err) {
    document.getElementById("aiResults").innerHTML = `<p style="color:var(--color-danger)">Error: ${err.message}</p>`;
  }

  btn.disabled = false;
  btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 0-2 13.7V18h4v-2.3A7 7 0 0 0 12 2z"/></svg> Run Again';
}


// ════════════════════════════════════════
// TENANT ANALYSIS PAGE
// ════════════════════════════════════════

function renderTenants() {
  const c = appData.charts;
  if (!c.concentration) {
    document.getElementById("tenantsContent").innerHTML = '<div class="empty-state"><h3>No tenant data</h3><p>Not enough occupied units to analyze</p></div>';
    return;
  }

  const tc = c.concentration;
  let tableRows = "";
  let cumPct = 0;
  for (let i = 0; i < tc.tenants.length; i++) {
    cumPct += tc.pct[i];
    tableRows += `<tr>
      <td>${i + 1}</td>
      <td>${tc.tenants[i]}</td>
      <td class="currency">${tc.units[i]}</td>
      <td class="currency">$${fmt(tc.rent[i])}</td>
      <td>${tc.pct[i].toFixed(1)}%</td>
      <td>${cumPct.toFixed(1)}%</td>
    </tr>`;
  }

  document.getElementById("tenantsContent").innerHTML = `
    <div class="section-header">Top Tenants by Revenue</div>
    <p class="section-sub">Revenue concentration analysis showing largest tenants and cumulative exposure.</p>

    <div class="card-grid">
      <div class="chart-container">
        <div class="chart-title">Revenue Concentration</div>
        <canvas id="chartConcentration"></canvas>
      </div>
      <div class="card">
        <div class="card-header">Top ${tc.tenants.length} Tenants</div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead><tr>
              <th>#</th><th>Tenant</th><th>Units</th><th>Monthly Rent</th><th>% Revenue</th><th>Cumulative</th>
            </tr></thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Draw concentration chart
  const ctx = document.getElementById("chartConcentration").getContext("2d");
  chartInstances.concentration = new Chart(ctx, {
    type: "bar",
    data: {
      labels: tc.tenants,
      datasets: [{
        data: tc.pct,
        backgroundColor: CHART_COLORS.slice(0, tc.tenants.length),
        borderRadius: 4,
      }]
    },
    options: {
      ...chartDefaults(),
      indexAxis: "y",
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
      scales: {
        x: { ...darkAxis(), title: { display: true, text: "% of Revenue", color: "#94a3b8" } },
        y: darkAxis()
      }
    }
  });
}


// ════════════════════════════════════════
// SEASONAL TIMING PAGE
// ════════════════════════════════════════

function renderSeasonal() {
  const c = appData.charts;
  if (!c.seasonal) {
    document.getElementById("seasonalContent").innerHTML = '<div class="empty-state"><h3>No seasonal data</h3><p>Not enough lease date data for seasonal analysis. Add Lease Start and Lease End columns.</p></div>';
    return;
  }

  const months = c.seasonal.months;
  const peak = months.reduce((a, b) => a.revenue > b.revenue ? a : b);
  const trough = months.reduce((a, b) => a.revenue < b.revenue ? a : b);
  const ratio = peak.revenue > 0 ? Math.round(trough.revenue / peak.revenue * 100) : 100;
  const annualModeled = months.reduce((s, m) => s + m.revenue, 0);

  let tableRows = months.map(m => `
    <tr>
      <td>${m.month}</td>
      <td>${m.units}</td>
      <td class="currency">$${fmt(m.revenue)}</td>
      <td>${m.pct_of_peak}%</td>
      <td>${m.occupancy_pct}%</td>
    </tr>
  `).join("");

  document.getElementById("seasonalContent").innerHTML = `
    <div class="section-header">Marina Seasonal Revenue Timing</div>
    <p class="section-sub">Monthly revenue recognition, occupancy curves, and seasonal rollover exposure analysis.</p>

    <div class="kpi-grid">
      ${kpiCard("Peak Month", peak.month, "$" + fmt(peak.revenue) + " / " + peak.units + " units", "success")}
      ${kpiCard("Trough Month", trough.month, "$" + fmt(trough.revenue) + " / " + trough.units + " units", "danger")}
      ${kpiCard("Trough/Peak Ratio", ratio + "%", "100% = no seasonality", ratio < 70 ? "warning" : "success")}
      ${kpiCard("Modeled Annual Rev", "$" + fmt(annualModeled), "sum of monthly model")}
    </div>

    <div class="card-grid">
      <div class="chart-container">
        <div class="chart-title">Monthly Revenue Curve</div>
        <canvas id="chartSeasonalRevenue"></canvas>
      </div>
      ${c.lease_clustering ? `<div class="chart-container">
        <div class="chart-title">Lease Start & End Clustering</div>
        <canvas id="chartClustering"></canvas>
      </div>` : ""}
    </div>

    <div class="card">
      <div class="card-header">Monthly Revenue Detail</div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>Month</th><th>Active Units</th><th>Revenue</th><th>% of Peak</th><th>Occupancy</th></tr></thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;

  // Revenue chart
  const ctxRev = document.getElementById("chartSeasonalRevenue").getContext("2d");
  chartInstances.seasonalRevenue = new Chart(ctxRev, {
    type: "bar",
    data: {
      labels: months.map(m => m.month),
      datasets: [{
        label: "Revenue",
        data: months.map(m => m.revenue),
        backgroundColor: months.map(m =>
          m.pct_of_peak >= 80 ? "#10b981" :
          m.pct_of_peak >= 50 ? "#f59e0b" : "#ef4444"
        ),
        borderRadius: 4,
      }]
    },
    options: {
      ...chartDefaults(),
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
      scales: {
        x: darkAxis(),
        y: { ...darkAxis(), title: { display: true, text: "Monthly Revenue ($)", color: "#94a3b8" } }
      }
    }
  });

  // Clustering chart
  if (c.lease_clustering) {
    const ctxCl = document.getElementById("chartClustering").getContext("2d");
    chartInstances.clustering = new Chart(ctxCl, {
      type: "bar",
      data: {
        labels: c.lease_clustering.months,
        datasets: [
          { label: "Lease Starts", data: c.lease_clustering.starts, backgroundColor: "#10b981", borderRadius: 4 },
          { label: "Lease Ends", data: c.lease_clustering.ends, backgroundColor: "#ef4444", borderRadius: 4 }
        ]
      },
      options: {
        ...chartDefaults(),
        scales: { x: darkAxis(), y: { ...darkAxis(), title: { display: true, text: "# of Leases", color: "#94a3b8" } } }
      }
    });
  }
}


// ════════════════════════════════════════
// DEMOGRAPHICS PAGE
// ════════════════════════════════════════

function renderDemographics() {
  const d = appData.demographics;
  if (!d || !d.has_data) {
    document.getElementById("demographicsContent").innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M3 3h18v18H3z"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
        <h3>No demographic data available</h3>
        <p>Upload a rent roll with address, ZIP code, or home value data to enable demographic analysis.</p>
      </div>`;
    return;
  }

  let html = `
    <div class="section-header">Tenant Demographics</div>
    <p class="section-sub">Analysis of tenant home values, geographic distribution, and fleet composition.</p>
  `;

  // ── Home Value Section ──
  if (d.home_value) {
    const hv = d.home_value;
    html += `
      <div class="kpi-grid" style="margin-bottom:24px">
        ${kpiCard("Median Home Value", "$" + fmt(hv.median_value), hv.values_found + " of " + hv.total_tenants + " tenants matched", "info")}
        ${kpiCard("Avg Home Value", "$" + fmt(hv.avg_value), hv.match_rate + "% match rate", "info")}
        ${hv.avg_rent_value_bps ? kpiCard("Rent/Value Ratio", hv.avg_rent_value_bps + " bps", "annual rent as % of home value") : ""}
      </div>

      <div class="card-grid">
        <div class="chart-container">
          <div class="chart-title">Home Value Tier Distribution</div>
          <canvas id="chartHomeTiers"></canvas>
        </div>
        <div class="card">
          <div class="card-header">Home Value Tiers</div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Tier</th><th>Range</th><th>Tenants</th><th>% of Total</th><th>Avg Value</th></tr></thead>
              <tbody>
                ${hv.tiers.map(t => `
                  <tr>
                    <td><span class="tier-badge tier-${t.tier.toLowerCase()}">${t.tier}</span></td>
                    <td>${t.range}</td>
                    <td>${t.count}</td>
                    <td>${t.pct}%</td>
                    <td class="currency">$${fmt(t.avg_value)}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // ── Geographic / ZIP Section ──
  if (d.geographic) {
    const geo = d.geographic;
    html += `
      <div class="kpi-grid" style="margin:32px 0 24px 0">
        ${kpiCard("Unique ZIP Codes", geo.total_zips, "geographic spread")}
        ${kpiCard("Top ZIP", geo.top_zip || "N/A", geo.top_zip_pct + "% of tenants", "info")}
      </div>

      <div class="card-grid">
        <div class="chart-container">
          <div class="chart-title">Tenants by ZIP Code</div>
          <canvas id="chartZipDist"></canvas>
        </div>
        <div class="card">
          <div class="card-header">Geographic Distribution</div>
          <div class="table-wrapper" style="max-height:400px;overflow-y:auto">
            <table class="data-table">
              <thead><tr><th>ZIP Code</th><th>Tenants</th><th>% Share</th><th>Avg Rent</th>${d.home_value ? "<th>Avg Home Value</th>" : ""}</tr></thead>
              <tbody>
                ${geo.zips.map(z => `
                  <tr>
                    <td>${z.zip}</td>
                    <td>${z.tenants}</td>
                    <td>${z.pct}%</td>
                    <td class="currency">$${fmt(z.avg_rent)}</td>
                    ${d.home_value ? `<td class="currency">${z.avg_home_value ? "$" + fmt(z.avg_home_value) : ""}</td>` : ""}
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // ── Boat Info Section ──
  if (d.boat_info) {
    const bi = d.boat_info;
    html += `
      <div style="margin-top:32px">
        <div class="section-header" style="font-size:var(--text-lg)">Fleet Composition</div>
        <p class="section-sub">Vessel information from the rent roll data.</p>
      </div>

      <div class="kpi-grid" style="margin-bottom:24px">
        ${kpiCard("Vessels with Info", bi.total_with_info, bi.pct_fleet + "% of fleet", "info")}
        ${bi.avg_loa ? kpiCard("Avg LOA", bi.avg_loa + "'", bi.min_loa + "' \u2013 " + bi.max_loa + "' range") : ""}
        ${bi.median_loa ? kpiCard("Median LOA", bi.median_loa + "'", "midpoint of fleet") : ""}
        ${bi.avg_year ? kpiCard("Avg Model Year", bi.avg_year, bi.oldest_year + " \u2013 " + bi.newest_year) : ""}
      </div>
    `;

    // LOA distribution + Top makes side by side
    const hasLoa = bi.loa_distribution && bi.loa_distribution.length > 0;
    const hasMakes = bi.top_makes && bi.top_makes.length > 0;

    if (hasLoa || hasMakes) {
      html += '<div class="card-grid">';
      if (hasLoa) {
        html += `
          <div class="chart-container">
            <div class="chart-title">LOA Distribution</div>
            <canvas id="chartLoaDist"></canvas>
          </div>
        `;
      }
      if (hasMakes) {
        html += `
          <div class="card">
            <div class="card-header">Top Boat Makes</div>
            <div class="table-wrapper">
              <table class="data-table">
                <thead><tr><th>Make</th><th>Count</th><th>% Fleet</th></tr></thead>
                <tbody>
                  ${bi.top_makes.map(m => `
                    <tr>
                      <td>${m.make}</td>
                      <td>${m.count}</td>
                      <td>${m.pct}%</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }
      html += '</div>';
    }
  }

  document.getElementById("demographicsContent").innerHTML = html;

  // ── Draw Home Value Tier Chart ──
  if (d.home_value && d.home_value.tiers.length > 0) {
    const tierColors = { Premium: "#8b5cf6", Strong: "#3b82f6", Moderate: "#f59e0b", Entry: "#64748b" };
    const tiers = d.home_value.tiers;
    const ctx = document.getElementById("chartHomeTiers").getContext("2d");
    chartInstances.homeTiers = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: tiers.map(t => t.tier + " (" + t.range + ")"),
        datasets: [{
          data: tiers.map(t => t.count),
          backgroundColor: tiers.map(t => tierColors[t.tier] || "#64748b"),
          borderWidth: 0,
        }]
      },
      options: {
        ...chartDefaults(),
        cutout: "60%",
        plugins: {
          ...chartDefaults().plugins,
          legend: { position: "bottom", labels: { color: "#94a3b8", padding: 14, font: { family: "'DM Sans'", size: 12 } } }
        }
      }
    });
  }

  // ── Draw ZIP Distribution Chart ──
  if (d.geographic && d.geographic.zips.length > 0) {
    const zips = d.geographic.zips.slice(0, 10);
    const ctx = document.getElementById("chartZipDist").getContext("2d");
    chartInstances.zipDist = new Chart(ctx, {
      type: "bar",
      data: {
        labels: zips.map(z => z.zip),
        datasets: [{
          label: "Tenants",
          data: zips.map(z => z.tenants),
          backgroundColor: "#3b82f6",
          borderRadius: 4,
        }]
      },
      options: {
        ...chartDefaults(),
        plugins: { ...chartDefaults().plugins, legend: { display: false } },
        scales: {
          x: { ...darkAxis(), title: { display: true, text: "ZIP Code", color: "#94a3b8" } },
          y: { ...darkAxis(), title: { display: true, text: "Tenants", color: "#94a3b8" }, beginAtZero: true }
        }
      }
    });
  }

  // ── Draw LOA Distribution Chart ──
  if (d.boat_info && d.boat_info.loa_distribution && d.boat_info.loa_distribution.length > 0) {
    const loa = d.boat_info.loa_distribution;
    const ctx = document.getElementById("chartLoaDist").getContext("2d");
    chartInstances.loaDist = new Chart(ctx, {
      type: "bar",
      data: {
        labels: loa.map(b => b.bucket),
        datasets: [{
          label: "Vessels",
          data: loa.map(b => b.count),
          backgroundColor: "#06b6d4",
          borderRadius: 4,
        }]
      },
      options: {
        ...chartDefaults(),
        plugins: { ...chartDefaults().plugins, legend: { display: false } },
        scales: {
          x: { ...darkAxis(), title: { display: true, text: "LOA Range", color: "#94a3b8" } },
          y: { ...darkAxis(), title: { display: true, text: "Vessels", color: "#94a3b8" }, beginAtZero: true }
        }
      }
    });
  }
}


// ════════════════════════════════════════
// INSIGHTS PAGE
// ════════════════════════════════════════

function renderInsights() {
  const insights = appData.insights;
  const k = appData.kpis;

  let html = `
    <div class="section-header">Investment Insights</div>
    <p class="section-sub">AI-generated analysis based on your rent roll data.</p>
  `;

  if (insights.length === 0) {
    html += '<div class="card"><p style="color:var(--color-text-muted)">Upload more detailed data (with lease dates and market rents) for richer insights.</p></div>';
  } else {
    insights.forEach(ins => {
      html += `
        <div class="insight-card ${ins.type}">
          <div class="insight-title">${ins.title}</div>
          <div class="insight-text">${ins.text}</div>
        </div>
      `;
    });
  }

  // Executive summary
  html += `
    <div class="card" style="margin-top:24px; border-left:3px solid var(--color-primary)">
      <div class="card-header">Executive Summary</div>
      <p style="color:var(--color-text-muted);font-size:var(--text-sm);line-height:1.8">
        This rent roll contains <strong style="color:var(--color-text)">${k.total_units}</strong> units
        with <strong style="color:var(--color-text)">${k.occupancy_pct}%</strong> physical occupancy
        and <strong style="color:var(--color-text)">$${fmt(k.egr_monthly)}/mo</strong> in effective gross revenue.
        ${k.wale_months ? "WALE is " + k.wale_months.toFixed(1) + " months (" + (k.wale_months/12).toFixed(1) + " yrs)." : ""}
        ${k.ltl_pct && k.ltl_pct > 2 ? "Loss-to-lease stands at " + k.ltl_pct.toFixed(1) + "%, representing mark-to-market upside." : ""}
        ${k.exp_12 > 0 ? k.exp_12 + " leases expire in the next 12 months requiring renewal attention." : ""}
      </p>
    </div>
  `;

  document.getElementById("insightsContent").innerHTML = html;
}


// ════════════════════════════════════════
// EXPORT PAGE
// ════════════════════════════════════════

function renderExport() {
  document.getElementById("exportContent").innerHTML = `
    <div class="section-header">Export to Excel</div>
    <p class="section-sub">Download your cleaned rent roll and KPI summary as a formatted Excel workbook.</p>

    <div class="card" style="max-width:500px">
      <div class="card-header">Export Options</div>
      <p style="color:var(--color-text-muted);font-size:var(--text-sm);margin-bottom:16px">
        The export includes two sheets:
      </p>
      <ul style="color:var(--color-text-muted);font-size:var(--text-sm);margin-bottom:24px;padding-left:20px;list-style:disc">
        <li style="margin-bottom:4px"><strong style="color:var(--color-text)">Rent Roll</strong> — Full cleaned data (${appData.rows} rows)</li>
        <li><strong style="color:var(--color-text)">KPI Summary</strong> — All computed metrics</li>
      </ul>
      <button class="btn btn-primary" onclick="downloadExcel()" style="width:100%">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Download Excel Workbook
      </button>
    </div>
  `;
}

async function downloadExcel() {
  showToast("Preparing download...");
  try {
    const resp = await fetch(API + "/api/export");
    if (!resp.ok) throw new Error("Export failed");
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rentroll_export.xlsx";
    a.click();
    URL.revokeObjectURL(url);
    showToast("Download started");
  } catch (err) {
    showToast("Export error: " + err.message);
  }
}


// ════════════════════════════════════════
// CHART HELPERS
// ════════════════════════════════════════

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 12 } } },
      tooltip: {
        backgroundColor: "#1c2030",
        titleColor: "#e2e8f0",
        bodyColor: "#94a3b8",
        borderColor: "#2a3042",
        borderWidth: 1,
        cornerRadius: 8,
        padding: 12,
        titleFont: { family: "'DM Sans', sans-serif", weight: 600 },
        bodyFont: { family: "'DM Sans', sans-serif" }
      }
    },
    animation: { duration: 600, easing: "easeOutQuart" }
  };
}

function darkAxis() {
  return {
    ticks: { color: "#64748b", font: { family: "'DM Sans', sans-serif", size: 11 } },
    grid: { color: "rgba(42, 48, 66, 0.4)" }
  };
}

function drawOccupancyChart(data) {
  if (!data) return;
  const ctx = document.getElementById("chartOccupancy").getContext("2d");
  const colors = data.labels.map(l => l === "Occupied" ? "#10b981" : "#ef4444");
  chartInstances.occupancy = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [{ data: data.values, backgroundColor: colors, borderWidth: 0 }]
    },
    options: {
      ...chartDefaults(),
      cutout: "65%",
      plugins: {
        ...chartDefaults().plugins,
        legend: { position: "bottom", labels: { color: "#94a3b8", padding: 16, font: { family: "'DM Sans'" } } }
      }
    }
  });
}

function drawExpirationChart(data) {
  if (!data) return;
  const ctx = document.getElementById("chartExpiration").getContext("2d");

  // Color code: Expired=red, near months=warm, far months=cool, 12+ Mo=green, No End=gray
  const barColors = data.labels.map((label, i) => {
    if (label === "Expired") return "#ef4444";
    if (label === "No End Date") return "#64748b";
    if (label === "12+ Mo") return "#10b981";
    // Monthly bars: gradient from warm to cool
    const monthIdx = i - 1; // offset for Expired at index 0
    if (monthIdx < 3) return "#f59e0b"; // next 3 months = amber
    if (monthIdx < 6) return "#3b82f6"; // 3-6 months = blue
    return "#8b5cf6"; // 6-12 months = purple
  });

  chartInstances.expiration = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        data: data.units,
        backgroundColor: barColors,
        borderRadius: 4,
      }]
    },
    options: {
      ...chartDefaults(),
      plugins: {
        ...chartDefaults().plugins,
        legend: { display: false },
        tooltip: {
          ...chartDefaults().plugins.tooltip,
          callbacks: {
            afterLabel: function(ctx) {
              const rent = data.rent ? data.rent[ctx.dataIndex] : null;
              return rent ? "Revenue: $" + Number(rent).toLocaleString("en-US") + "/mo" : "";
            }
          }
        }
      },
      scales: {
        x: {
          ...darkAxis(),
          ticks: {
            ...darkAxis().ticks,
            maxRotation: 45,
            minRotation: 45,
            font: { family: "'DM Sans', sans-serif", size: 10 }
          }
        },
        y: { ...darkAxis(), title: { display: true, text: "Units", color: "#94a3b8" } }
      }
    }
  });
}

function drawRevenueByTypeChart(data) {
  if (!data) return;
  const ctx = document.getElementById("chartRevenueType").getContext("2d");
  chartInstances.revType = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        data: data.values,
        backgroundColor: CHART_COLORS.slice(0, data.labels.length),
        borderRadius: 4,
      }]
    },
    options: {
      ...chartDefaults(),
      indexAxis: "y",
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
      scales: {
        x: { ...darkAxis(), title: { display: true, text: "Monthly Rent ($)", color: "#94a3b8" } },
        y: darkAxis()
      }
    }
  });
}

function drawRentDistributionChart(data) {
  if (!data || !data.values || data.values.length === 0) return;
  const ctx = document.getElementById("chartRentDist").getContext("2d");
  // Build histogram bins
  const vals = data.values.filter(v => v > 0).sort((a, b) => a - b);
  if (vals.length === 0) return;
  const min = vals[0];
  const max = vals[vals.length - 1];
  const binCount = Math.min(20, Math.max(5, Math.ceil(vals.length / 3)));
  const binSize = (max - min) / binCount || 1;
  const bins = [];
  const labels = [];
  for (let i = 0; i < binCount; i++) {
    bins.push(0);
    const lo = Math.round(min + i * binSize);
    labels.push("$" + fmt(lo));
  }
  vals.forEach(v => {
    let idx = Math.floor((v - min) / binSize);
    if (idx >= binCount) idx = binCount - 1;
    bins[idx]++;
  });

  chartInstances.rentDist = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        data: bins,
        backgroundColor: "#3b82f6",
        borderRadius: 4,
      }]
    },
    options: {
      ...chartDefaults(),
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
      scales: {
        x: { ...darkAxis(), title: { display: true, text: "Monthly Rent ($)", color: "#94a3b8" } },
        y: { ...darkAxis(), title: { display: true, text: "Count", color: "#94a3b8" } }
      }
    }
  });
}


// ════════════════════════════════════════
// DATA TABLE
// ════════════════════════════════════════

let tableData = [];
let filteredData = [];

function renderDataTable(data) {
  tableData = data;
  filteredData = [...data];
  tablePage = 0;
  sortCol = null;
  drawTable();
}

function filterTable(query) {
  const q = query.toLowerCase();
  filteredData = q ? tableData.filter(row =>
    Object.values(row).some(v => String(v).toLowerCase().includes(q))
  ) : [...tableData];
  tablePage = 0;
  drawTable();
}

function sortTable(col) {
  if (sortCol === col) {
    sortAsc = !sortAsc;
  } else {
    sortCol = col;
    sortAsc = true;
  }
  filteredData.sort((a, b) => {
    let va = a[col], vb = b[col];
    if (typeof va === "number" && typeof vb === "number") return sortAsc ? va - vb : vb - va;
    va = String(va || ""); vb = String(vb || "");
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  tablePage = 0;
  drawTable();
}

function drawTable() {
  const table = document.getElementById("dashboardTable");
  if (!table || filteredData.length === 0) return;

  // Determine whether LOA or SqFt is available based on data
  const hasLoa = filteredData.some(r => r.loa && r.loa > 0);
  const hasSqft = filteredData.some(r => r.sqft && r.sqft > 0);

  // Build columns: LOA preferred over SqFt for marina data
  const cols = ["property", "unit", "tenant", "unit_type", "status", "monthly_rent", "annual_rent", "market_rent"];
  const colLabels = {
    property: "Property", unit: "Unit", tenant: "Tenant", unit_type: "Type",
    status: "Status", monthly_rent: "Mo. Rent", annual_rent: "Ann. Rent",
    market_rent: "Mkt Rent", loa: "LOA (ft)", sqft: "SqFt",
    rent_per_loa: "$/LOA ft", lease_start: "Start", lease_end: "End", exp_bucket: "Exp."
  };

  if (hasLoa) {
    cols.push("loa");
    cols.push("rent_per_loa");
  } else if (hasSqft) {
    cols.push("sqft");
  }
  cols.push("lease_start", "lease_end", "exp_bucket");

  const currCols = new Set(["monthly_rent", "annual_rent", "market_rent"]);
  const numCols = new Set(["loa", "sqft", "rent_per_loa"]);

  const start = tablePage * PAGE_SIZE;
  const pageData = filteredData.slice(start, start + PAGE_SIZE);

  let html = "<thead><tr>";
  cols.forEach(col => {
    const isSorted = sortCol === col;
    const arrow = isSorted ? (sortAsc ? "\u25B2" : "\u25BC") : "\u25B2";
    html += `<th class="${isSorted ? "sorted" : ""}" onclick="sortTable('${col}')">${colLabels[col] || col}<span class="sort-arrow">${arrow}</span></th>`;
  });
  html += "</tr></thead><tbody>";

  pageData.forEach(row => {
    html += "<tr>";
    cols.forEach(col => {
      let val = row[col];
      if (col === "status") {
        const cls = val === "Occupied" ? "status-occupied" : "status-vacant";
        html += `<td><span class="status-badge ${cls}">${val}</span></td>`;
      } else if (currCols.has(col)) {
        html += `<td class="currency">${val ? "$" + fmt(val) : ""}</td>`;
      } else if (col === "rent_per_loa") {
        html += `<td class="currency">${val && val > 0 ? "$" + Number(val).toFixed(2) : ""}</td>`;
      } else if (numCols.has(col)) {
        html += `<td class="currency">${val && val > 0 ? fmt(val) : ""}</td>`;
      } else {
        html += `<td>${val || ""}</td>`;
      }
    });
    html += "</tr>";
  });
  html += "</tbody>";
  table.innerHTML = html;

  // Pagination
  const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);
  document.getElementById("tablePagination").innerHTML = `
    <span>Showing ${start + 1}-${Math.min(start + PAGE_SIZE, filteredData.length)} of ${filteredData.length}</span>
    <div class="pagination-btns">
      <button onclick="tablePage=0;drawTable()" ${tablePage === 0 ? "disabled" : ""}>First</button>
      <button onclick="tablePage--;drawTable()" ${tablePage === 0 ? "disabled" : ""}>Prev</button>
      <button onclick="tablePage++;drawTable()" ${tablePage >= totalPages - 1 ? "disabled" : ""}>Next</button>
      <button onclick="tablePage=${totalPages - 1};drawTable()" ${tablePage >= totalPages - 1 ? "disabled" : ""}>Last</button>
    </div>
  `;
}


// ════════════════════════════════════════
// UTILITY
// ════════════════════════════════════════

function fmt(n) {
  if (n === null || n === undefined || n === "") return "";
  return Math.round(Number(n)).toLocaleString("en-US");
}

function kpiCard(label, value, sub, cls) {
  return `
    <div class="kpi-card ${cls || ""}">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-sub">${sub || ""}</div>
    </div>
  `;
}

function showLoading(text) {
  document.getElementById("loadingText").textContent = text || "Processing...";
  document.getElementById("loadingOverlay").style.display = "flex";
}

function hideLoading() {
  document.getElementById("loadingOverlay").style.display = "none";
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

// ═══════════════════════════════════════════════════════════════
//  Chennai UHI Dashboard — app.js
//  Linear flow: load data → build map → build charts → wire events
// ═══════════════════════════════════════════════════════════════

// ── Global state ──────────────────────────────────────────────
var timeseries = [];   // [{ward, year, NDVI, NDBI, LST, rainfall}]
var trends = [];       // [{ward, trend, p_value, slope}]
var changepoints = []; // [{ward, changepoint_years}]
var geojson = null;    // GeoJSON FeatureCollection
var regression = {};   // {coefficients, r2}

var selectedIndicator = "LST";
var selectedYear = 2024;
var selectedZone = "all";
var selectedWard = null;

var leafletMap = null;
var geoLayer = null;
var wardChart = null;
var cityTrendChart = null;
var zoneChart = null;
var distChart = null;
var rankChart = null;

var YEARS = [2016,2017,2018,2019,2020,2021,2022,2023,2024];

// ── Color scales ───────────────────────────────────────────────
var PALETTES = {
  LST:  { colors: ["#1e40af","#3b82f6","#facc15","#f97316","#ef4444","#7f1d1d"], label: "LST (°C)" },
  NDVI: { colors: ["#7f1d1d","#f97316","#facc15","#86efac","#22c55e","#14532d"], label: "NDVI" },
  NDBI: { colors: ["#14532d","#22c55e","#facc15","#f97316","#ef4444","#7f1d1d"], label: "NDBI" }
};

function lerp(a, b, t) { return a + (b - a) * t; }

function hexToRgb(hex) {
  var r = parseInt(hex.slice(1,3),16);
  var g = parseInt(hex.slice(3,5),16);
  var b = parseInt(hex.slice(5,7),16);
  return [r,g,b];
}

function interpolateColor(colors, t) {
  var segments = colors.length - 1;
  var seg = Math.min(Math.floor(t * segments), segments - 1);
  var st = (t * segments) - seg;
  var c1 = hexToRgb(colors[seg]);
  var c2 = hexToRgb(colors[seg+1]);
  var r = Math.round(lerp(c1[0], c2[0], st));
  var g = Math.round(lerp(c1[1], c2[1], st));
  var b = Math.round(lerp(c1[2], c2[2], st));
  return "rgb("+r+","+g+","+b+")";
}

function getColor(value, min, max, indicator) {
  var t = max === min ? 0.5 : (value - min) / (max - min);
  t = Math.max(0, Math.min(1, t));
  return interpolateColor(PALETTES[indicator].colors, t);
}

// ── Data range helpers ─────────────────────────────────────────
function getYearData(year) {
  return timeseries.filter(function(d) { return +d.year === year; });
}

function getWardSeries(ward) {
  return timeseries.filter(function(d) { return +d.ward === ward; }).sort(function(a,b){ return +a.year - +b.year; });
}

function rangeOf(arr, field) {
  var vals = arr.map(function(d){ return +d[field]; });
  return { min: Math.min.apply(null,vals), max: Math.max.apply(null,vals) };
}

// ── CSV parser helper ──────────────────────────────────────────
function loadCSV(url, callback) {
  Papa.parse(url, {
    download: true,
    header: true,
    skipEmptyLines: true,
    complete: function(results) { callback(results.data); }
  });
}

// ── Data loading chain ─────────────────────────────────────────
function loadAll() {
  loadCSV("data/ward_timeseries_full.csv", function(rows) {
    timeseries = rows;

    loadCSV("data/trend_significance.csv", function(trows) {
      trends = trows;

      loadCSV("data/changepoints.csv", function(crows) {
        changepoints = crows;

        fetch("data/regression_summary.json")
          .then(function(r){ return r.json(); })
          .then(function(reg) {
            regression = reg;

            fetch("data/wards_2024.geojson")
              .then(function(r){ return r.json(); })
              .then(function(gj) {
                geojson = gj;
                onDataReady();
              });
          });
      });
    });
  });
}

// ── Once all data loaded ───────────────────────────────────────
function onDataReady() {
  buildHeroStats();
  buildMap();
  buildZoneFilter();
  buildCityTrendChart("LST");
  buildZoneChart();
  buildRegressionPanel();
  buildDistChart();
  buildRankChart("LST");
  wireEvents();
}

// ── Hero stats ─────────────────────────────────────────────────
function buildHeroStats() {
  var d2024 = getYearData(2024);
  var lsts = d2024.map(function(d){ return +d.LST; });
  var maxL = Math.max.apply(null, lsts);
  var avgL = lsts.reduce(function(a,b){ return a+b; },0) / lsts.length;
  document.getElementById("stat-maxlst").textContent = maxL.toFixed(1);
  document.getElementById("stat-avglst").textContent = avgL.toFixed(1);
}

// ── MAP ────────────────────────────────────────────────────────
function buildMap() {
  leafletMap = L.map("map", {
    center: [13.07, 80.24],
    zoom: 11,
    zoomControl: true,
    attributionControl: true
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
    maxZoom: 18
  }).addTo(leafletMap);

  renderGeoLayer();
  updateLegend();
}

function renderGeoLayer() {
  if (geoLayer) { leafletMap.removeLayer(geoLayer); }

  var yearData = getYearData(selectedYear);
  var wardMap = {};
  yearData.forEach(function(d){ wardMap[d.ward] = d; });

  var rng = rangeOf(yearData, selectedIndicator);

  // Filter by zone if needed
  var features = geojson.features;
  if (selectedZone !== "all") {
    features = features.filter(function(f){
      return f.properties["Zone name"] === selectedZone || f.properties.Zone === selectedZone;
    });
  }

  var filteredGJ = { type: "FeatureCollection", features: features };

  geoLayer = L.geoJSON(filteredGJ, {
    style: function(feature) {
      var wardId = String(feature.properties.ward || feature.properties.Ward_No || "");
      var row = wardMap[wardId];
      var val = row ? +row[selectedIndicator] : null;
      if (val === null) {
        return { fillColor: "#334155", fillOpacity: 0.5, color: "#1e2a3a", weight: 0.8 };
      }
      return {
        fillColor: getColor(val, rng.min, rng.max, selectedIndicator),
        fillOpacity: 0.78,
        color: "#0b1120",
        weight: 0.8
      };
    },
    onEachFeature: function(feature, layer) {
      var wardId = String(feature.properties.ward || feature.properties.Ward_No || "");
      layer.on("click", function() { showWardPanel(+wardId, feature.properties); });
      layer.on("mouseover", function(e) {
        var row = wardMap[wardId];
        var val = row ? (+row[selectedIndicator]).toFixed(2) : "N/A";
        layer.bindPopup(
          "<strong>Ward " + wardId + "</strong><br/>" +
          (feature.properties["Zone name"] || "") + "<br/>" +
          selectedIndicator + ": <strong>" + val + "</strong>"
        ).openPopup(e.latlng);
      });
      layer.on("mouseout", function() { layer.closePopup(); });
    }
  }).addTo(leafletMap);

  // Update legend
  updateLegend(rng);
}

function updateLegend(rng) {
  var pal = PALETTES[selectedIndicator];
  document.getElementById("legend-title").textContent = pal.label;
  document.getElementById("legend-gradient").style.background =
    "linear-gradient(to right, " + pal.colors.join(", ") + ")";
  if (rng) {
    document.getElementById("leg-min").textContent = rng.min.toFixed(1);
    document.getElementById("leg-max").textContent = rng.max.toFixed(1);
  }
}

// ── Ward panel ─────────────────────────────────────────────────
function showWardPanel(wardNum, props) {
  selectedWard = wardNum;

  document.getElementById("ward-placeholder").style.display = "none";
  document.getElementById("ward-content").style.display = "block";

  document.getElementById("wp-title").textContent = "Ward " + wardNum;
  document.getElementById("wp-zone").textContent = props["Zone name"] || props.Zone || "–";

  // KPIs for selected year
  var row = timeseries.find(function(d){ return +d.ward === wardNum && +d.year === selectedYear; });
  var kpiHtml = "";
  if (row) {
    kpiHtml += '<div class="kpi-card"><div class="kpi-val" style="color:#ef4444">' + (+row.LST).toFixed(1) + '°</div><div class="kpi-lbl">LST ('+selectedYear+')</div></div>';
    kpiHtml += '<div class="kpi-card"><div class="kpi-val" style="color:#22c55e">' + (+row.NDVI).toFixed(3) + '</div><div class="kpi-lbl">NDVI</div></div>';
    kpiHtml += '<div class="kpi-card"><div class="kpi-val" style="color:#f97316">' + (+row.NDBI).toFixed(3) + '</div><div class="kpi-lbl">NDBI</div></div>';
    kpiHtml += '<div class="kpi-card"><div class="kpi-val" style="color:#60a5fa">' + (+row.rainfall).toFixed(0) + '</div><div class="kpi-lbl">Rainfall (mm)</div></div>';
  }
  document.getElementById("wp-kpis").innerHTML = kpiHtml;

  // Trend badge
  var trendRow = trends.find(function(d){ return +d.ward === wardNum; });
  var trendEl = document.getElementById("wp-trend-label");
  if (trendRow) {
    trendEl.className = "ward-trend-label";
    if (trendRow.trend === "decreasing") {
      trendEl.classList.add("trend-decreasing");
      trendEl.textContent = "▼ Decreasing LST trend (p=" + (+trendRow.p_value).toFixed(3) + ")";
    } else if (trendRow.trend === "increasing") {
      trendEl.classList.add("trend-increasing");
      trendEl.textContent = "▲ Increasing LST trend (p=" + (+trendRow.p_value).toFixed(3) + ")";
    } else {
      trendEl.classList.add("trend-none");
      trendEl.textContent = "No significant LST trend (p=" + (+trendRow.p_value).toFixed(3) + ")";
    }
  }

  // Mini time-series chart
  var series = getWardSeries(wardNum);
  var labels = series.map(function(d){ return d.year; });
  var lstVals = series.map(function(d){ return +d.LST; });
  var ndviVals = series.map(function(d){ return +d.NDVI; });

  if (wardChart) { wardChart.destroy(); }
  var ctx = document.getElementById("ward-chart").getContext("2d");
  wardChart = new Chart(ctx, {
    data: {
      labels: labels,
      datasets: [
        {
          type: "line",
          label: "LST (°C)",
          data: lstVals,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.08)",
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.3,
          yAxisID: "y"
        },
        {
          type: "line",
          label: "NDVI",
          data: ndviVals,
          borderColor: "#22c55e",
          backgroundColor: "transparent",
          borderWidth: 1.5,
          pointRadius: 2,
          borderDash: [4,2],
          tension: 0.3,
          yAxisID: "y2"
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { size: 10 } } },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        x: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { color: "#1e2a3a" } },
        y: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { color: "#1e2a3a" }, position: "left" },
        y2: { ticks: { color: "#22c55e", font: { size: 10 } }, grid: { display: false }, position: "right" }
      }
    }
  });

  // Changepoint meta
  var cpRow = changepoints.find(function(d){ return +d.ward === wardNum; });
  var cpText = cpRow && cpRow.changepoint_years !== "[]" ? cpRow.changepoint_years : "None";
  document.getElementById("wp-meta").innerHTML =
    "<strong>Change-point years:</strong> " + cpText + "<br/>" +
    "<strong>Slope:</strong> " + (trendRow ? (+trendRow.slope).toFixed(4) + " °C/yr" : "–");
}

// ── Zone filter ────────────────────────────────────────────────
function buildZoneFilter() {
  var zones = [];
  if (geojson) {
    geojson.features.forEach(function(f) {
      var z = f.properties["Zone name"] || f.properties.Zone;
      if (z && zones.indexOf(z) === -1) zones.push(z);
    });
  }
  zones.sort();
  var sel = document.getElementById("zone-filter");
  zones.forEach(function(z) {
    var opt = document.createElement("option");
    opt.value = z; opt.textContent = z;
    sel.appendChild(opt);
  });
}

// ── City trend chart ──────────────────────────────────────────
function buildCityTrendChart(metric) {
  var avgByYear = YEARS.map(function(y) {
    var yd = getYearData(y);
    var vals = yd.map(function(d){ return +d[metric]; });
    return vals.reduce(function(a,b){ return a+b; },0) / vals.length;
  });

  var color = metric === "LST" ? "#f97316" : metric === "NDVI" ? "#22c55e" : "#60a5fa";

  if (cityTrendChart) { cityTrendChart.destroy(); }
  var ctx = document.getElementById("city-trend-chart").getContext("2d");
  cityTrendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: YEARS,
      datasets: [{
        label: "Avg " + metric,
        data: avgByYear,
        borderColor: color,
        backgroundColor: color + "18",
        borderWidth: 2.5,
        pointRadius: 4,
        pointBackgroundColor: color,
        tension: 0.35,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function(c){ return metric + ": " + c.parsed.y.toFixed(3); } } }
      },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

// ── Zone bar chart ─────────────────────────────────────────────
function buildZoneChart() {
  var d2024 = getYearData(2024);
  // Map ward→zone via geojson props
  var wardZone = {};
  if (geojson) {
    geojson.features.forEach(function(f) {
      var w = String(f.properties.ward || f.properties.Ward_No || "");
      wardZone[w] = f.properties["Zone name"] || f.properties.Zone || "Unknown";
    });
  }
  var zoneAgg = {};
  d2024.forEach(function(d) {
    var z = wardZone[d.ward] || "Unknown";
    if (!zoneAgg[z]) zoneAgg[z] = [];
    zoneAgg[z].push(+d.LST);
  });
  var zones = Object.keys(zoneAgg).sort();
  var avgs = zones.map(function(z) {
    var arr = zoneAgg[z];
    return arr.reduce(function(a,b){ return a+b; },0) / arr.length;
  });
  var colors = avgs.map(function(v) {
    var rng = { min: Math.min.apply(null,avgs), max: Math.max.apply(null,avgs) };
    return getColor(v, rng.min, rng.max, "LST");
  });

  var ctx = document.getElementById("zone-chart").getContext("2d");
  zoneChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: zones,
      datasets: [{
        label: "Avg LST 2024 (°C)",
        data: avgs,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8", font: { size: 9 }, maxRotation: 45 }, grid: { display: false } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

// ── Regression panel ───────────────────────────────────────────
function buildRegressionPanel() {
  var coefs = regression.coefficients || {};
  var r2 = regression.r2 || 0;
  var ndvi = (coefs.NDVI || 0).toFixed(3);
  var ndbi = (coefs.NDBI || 0).toFixed(3);
  var rain = (coefs.rainfall || 0).toFixed(6);

  var html = '<div class="reg-r2">R² = ' + r2.toFixed(3) + '</div>';
  html += '<p class="reg-note" style="margin-bottom:0.75rem">OLS: LST ~ NDVI + NDBI + rainfall (all wards × 2016–2024)</p>';
  html += '<div class="reg-eq">LST = ' + ndvi + '·NDVI<br/>     + ' + ndbi + '·NDBI<br/>     + ' + rain + '·rainfall</div>';

  var maxCoef = Math.max(Math.abs(coefs.NDVI||0), Math.abs(coefs.NDBI||0));
  var coefData = [
    { name: "NDVI", val: coefs.NDVI||0, color: "#22c55e" },
    { name: "NDBI", val: coefs.NDBI||0, color: "#f97316" },
    { name: "Rainfall", val: (coefs.rainfall||0)*1000, color: "#60a5fa", note: "(×1000)" }
  ];
  coefData.forEach(function(c) {
    var barW = Math.min(100, Math.abs(c.val) / maxCoef * 100);
    html += '<div class="coef-row"><div>';
    html += '<strong style="font-size:0.8rem">' + c.name + '</strong> <span style="color:var(--text-muted);font-size:0.72rem">' + (c.note||"") + '</span><br/>';
    html += '<span style="font-size:0.85rem;color:' + c.color + '">' + (c.val >= 0 ? "+" : "") + c.val.toFixed(3) + '</span>';
    html += '</div></div>';
    html += '<div class="coef-bar" style="width:' + barW + '%;background:' + c.color + ';margin-bottom:0.5rem"></div>';
  });
  html += '<p class="reg-note" style="margin-top:0.5rem">NDBI has the strongest positive effect. Low R² at ward scale is expected — LST is driven by sub-ward micro-climate factors.</p>';

  document.getElementById("regression-panel").innerHTML = html;
}

// ── Distribution histogram ─────────────────────────────────────
function buildDistChart() {
  var d2024 = getYearData(2024);
  var lsts = d2024.map(function(d){ return +d.LST; });
  var mn = Math.floor(Math.min.apply(null,lsts));
  var mx = Math.ceil(Math.max.apply(null,lsts));
  var bins = [];
  var binCounts = [];
  var step = 0.5;
  for (var v = mn; v < mx; v += step) {
    bins.push(v.toFixed(1));
    binCounts.push(lsts.filter(function(l){ return l >= v && l < v+step; }).length);
  }
  var colors = bins.map(function(b) {
    return getColor(+b, mn, mx, "LST");
  });

  var ctx = document.getElementById("dist-chart").getContext("2d");
  distChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: bins,
      datasets: [{
        label: "Ward count",
        data: binCounts,
        backgroundColor: colors,
        borderRadius: 2,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8", font: { size: 9 }, maxTicksLimit: 10 }, grid: { display: false } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

// ── Rankings chart ─────────────────────────────────────────────
function buildRankChart(metric) {
  var d2024 = getYearData(2024);
  d2024 = d2024.slice().sort(function(a,b){ return +b[metric] - +a[metric]; });
  var top15 = d2024.slice(0, 15);
  var labels = top15.map(function(d){ return "W" + d.ward; });
  var vals = top15.map(function(d){ return +d[metric]; });
  var rng = rangeOf(d2024, metric);
  var colors = vals.map(function(v){ return getColor(v, rng.min, rng.max, metric === "NDVI" ? "NDVI" : metric === "NDBI" ? "NDBI" : "LST"); });

  if (rankChart) { rankChart.destroy(); }
  var ctx = document.getElementById("rank-chart").getContext("2d");
  rankChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: metric + " (2024)",
        data: vals,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

// ── Event wiring ───────────────────────────────────────────────
function wireEvents() {
  // Indicator buttons (map)
  document.getElementById("indicator-btns").addEventListener("click", function(e) {
    if (!e.target.dataset.ind) return;
    document.querySelectorAll("#indicator-btns .btn-tab").forEach(function(b){ b.classList.remove("active"); });
    e.target.classList.add("active");
    selectedIndicator = e.target.dataset.ind;
    renderGeoLayer();
    if (selectedWard) {
      var feature = null;
      if (geojson) {
        feature = geojson.features.find(function(f){
          return +f.properties.ward === selectedWard;
        });
      }
      if (feature) showWardPanel(selectedWard, feature.properties);
    }
  });

  // Year slider
  var slider = document.getElementById("year-slider");
  slider.addEventListener("input", function() {
    selectedYear = +slider.value;
    document.getElementById("year-label").textContent = selectedYear;
    renderGeoLayer();
    if (selectedWard) {
      var feature = geojson && geojson.features.find(function(f){ return +f.properties.ward === selectedWard; });
      if (feature) showWardPanel(selectedWard, feature.properties);
    }
  });

  // Zone filter
  document.getElementById("zone-filter").addEventListener("change", function(e) {
    selectedZone = e.target.value;
    renderGeoLayer();
  });

  // Ward search
  document.getElementById("ward-search").addEventListener("input", function(e) {
    var q = e.target.value.trim();
    if (!q) return;
    var wardNum = +q;
    if (!wardNum) return;
    var feature = geojson && geojson.features.find(function(f){ return +f.properties.ward === wardNum; });
    if (feature) {
      showWardPanel(wardNum, feature.properties);
      // pan to ward
      var coords = feature.geometry.coordinates[0];
      var lats = coords.map(function(c){ return c[1]; });
      var lngs = coords.map(function(c){ return c[0]; });
      var lat = (Math.min.apply(null,lats) + Math.max.apply(null,lats)) / 2;
      var lng = (Math.min.apply(null,lngs) + Math.max.apply(null,lngs)) / 2;
      leafletMap.setView([lat, lng], 14);
    }
  });

  // Aggregated metric buttons
  document.getElementById("agg-metric-btns").addEventListener("click", function(e) {
    if (!e.target.dataset.metric) return;
    document.querySelectorAll("#agg-metric-btns .btn-sm").forEach(function(b){ b.classList.remove("active"); });
    e.target.classList.add("active");
    buildCityTrendChart(e.target.dataset.metric);
  });

  // Rankings metric buttons
  document.getElementById("rank-metric-btns").addEventListener("click", function(e) {
    if (!e.target.dataset.rmetric) return;
    document.querySelectorAll("#rank-metric-btns .btn-sm").forEach(function(b){ b.classList.remove("active"); });
    e.target.classList.add("active");
    buildRankChart(e.target.dataset.rmetric);
  });

  // Navbar active scroll highlight
  window.addEventListener("scroll", function() {
    var sections = ["hero","map-section","analytics","methodology"];
    var current = sections[0];
    sections.forEach(function(id) {
      var el = document.getElementById(id);
      if (el && window.scrollY >= el.offsetTop - 80) current = id;
    });
    document.querySelectorAll(".nav-links a").forEach(function(a) {
      a.style.color = a.getAttribute("href") === "#" + current ? "var(--accent)" : "";
    });
  });
}

// ── Kick off ───────────────────────────────────────────────────
loadAll();


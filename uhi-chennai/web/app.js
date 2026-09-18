// ═══════════════════════════════════════════════════════════════
//  Chennai UHI Monitor — app.js
//  All API calls go to /api/v1/...
//  Linear flow: init → load → render → wire events
// ═══════════════════════════════════════════════════════════════

var API = window.API_BASE + "/api/v1";
var YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024];

// ── State ──────────────────────────────────────────────────────
var state = {
  indicator: "lst",
  year: 2024,
  zone: "",
  selectedWard: null,
  geojsonCache: {},   // key: "year-indicator"
  wardCache: {},      // key: ward_id
  wardChart: null,
  trendChart: null,
  zoneChart: null,
  distChart: null,
  rankChart: null,
  leafletMap: null,
  geoLayer: null,
};

// ── Color palettes ─────────────────────────────────────────────
var PALETTES = {
  lst:      ["#1e3a8a", "#3b82f6", "#fde68a", "#f97316", "#ef4444", "#7f1d1d"],
  ndvi:     ["#7f1d1d", "#f97316", "#fde68a", "#86efac", "#22c55e", "#14532d"],
  ndbi:     ["#14532d", "#22c55e", "#fde68a", "#f97316", "#ef4444", "#7f1d1d"],
  rainfall: ["#7f1d1d", "#f97316", "#fde68a", "#93c5fd", "#3b82f6", "#1e3a8a"],
};
var LABELS = { lst: "LST (°C)", ndvi: "NDVI", ndbi: "NDBI", rainfall: "Rainfall (mm)" };
var KPI_COLORS = { lst: "#ef4444", ndvi: "#4ade80", ndbi: "#f97316", rainfall: "#60a5fa" };

function hexToRgb(h) { return [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)]; }
function lerp(a,b,t) { return a + (b-a)*t; }

function colorScale(val, min, max, indicator) {
  var t = max === min ? 0.5 : Math.max(0, Math.min(1, (val - min) / (max - min)));
  var pal = PALETTES[indicator] || PALETTES.lst;
  var seg = Math.min(Math.floor(t * (pal.length - 1)), pal.length - 2);
  var st  = t * (pal.length - 1) - seg;
  var c1 = hexToRgb(pal[seg]);
  var c2 = hexToRgb(pal[seg + 1]);
  return "rgb(" + [0,1,2].map(function(i){ return Math.round(lerp(c1[i], c2[i], st)); }).join(",") + ")";
}

function gradientCSS(indicator) {
  return "linear-gradient(to right, " + (PALETTES[indicator] || PALETTES.lst).join(", ") + ")";
}

// ── Fetch helpers ──────────────────────────────────────────────
function get(url) {
  return fetch(API + url).then(function(r) {
    if (!r.ok) throw new Error(r.status + " " + r.statusText);
    return r.json();
  });
}

// ── API status indicator ───────────────────────────────────────
function initStatusCheck() {
  get("/health").then(function(h) {
    document.getElementById("status-dot").className = "status-dot ok";
    document.getElementById("status-text").textContent = "API v" + h.version + " · " + h.ward_count + " wards";
  }).catch(function() {
    document.getElementById("status-dot").className = "status-dot err";
    document.getElementById("status-text").textContent = "API unavailable";
  });
}

// ── Hero KPIs ──────────────────────────────────────────────────
function loadHeroKPIs() {
  get("/wards?year=2024&limit=200").then(function(wards) {
    var lsts = wards.map(function(w){ return w.lst; });
    var max = Math.max.apply(null, lsts);
    var avg = lsts.reduce(function(a,b){ return a+b; },0) / lsts.length;
    var zones = new Set(wards.map(function(w){ return w.zone_name; }).filter(Boolean));
    document.getElementById("k-wards").textContent = wards.length;
    document.getElementById("k-maxlst").textContent = max.toFixed(1) + "°";
    document.getElementById("k-avglst").textContent = avg.toFixed(1) + "°";
    document.getElementById("k-zones").textContent = zones.size;
  }).catch(function(e){ console.error("KPI load failed", e); });
}

// ── Zone filter dropdown ───────────────────────────────────────
function loadZones() {
  get("/analytics/zones/list").then(function(data) {
    var sel = document.getElementById("zone-sel");
    data.zones.forEach(function(z) {
      var opt = document.createElement("option");
      opt.value = z; opt.textContent = z;
      sel.appendChild(opt);
    });
  });
}

// ── MAP ────────────────────────────────────────────────────────
function initMap() {
  state.leafletMap = L.map("map", {
    center: [13.07, 80.24], zoom: 11,
    zoomControl: true,
  });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '© <a href="https://carto.com">CARTO</a> © <a href="https://openstreetmap.org">OSM</a>',
    maxZoom: 18,
  }).addTo(state.leafletMap);

  refreshMap();
}

function refreshMap() {
  var cacheKey = state.year + "-" + state.indicator;
  if (state.geojsonCache[cacheKey]) {
    renderGeoLayer(state.geojsonCache[cacheKey]);
    return;
  }
  get("/wards/geojson?year=" + state.year + "&indicator=" + state.indicator)
    .then(function(gj) {
      state.geojsonCache[cacheKey] = gj;
      renderGeoLayer(gj);
    })
    .catch(function(e){ console.error("GeoJSON fetch failed", e); });
}

function renderGeoLayer(gj) {
  if (state.geoLayer) { state.leafletMap.removeLayer(state.geoLayer); }

  var vals = gj.features.map(function(f){ return f.properties[state.indicator] || 0; });
  var mn = Math.min.apply(null, vals);
  var mx = Math.max.apply(null, vals);

  // Filter by zone
  var features = gj.features;
  if (state.zone) {
    features = features.filter(function(f){
      return (f.properties.zone_name || "").toLowerCase() === state.zone.toLowerCase();
    });
  }

  state.geoLayer = L.geoJSON({ type: "FeatureCollection", features: features }, {
    style: function(f) {
      var val = f.properties[state.indicator] || 0;
      return {
        fillColor: colorScale(val, mn, mx, state.indicator),
        fillOpacity: 0.78,
        color: "#060d18",
        weight: 0.8,
      };
    },
    onEachFeature: function(f, layer) {
      var wid = f.properties.ward;
      layer.on("click", function() { openWardPanel(wid); });
      layer.on("mouseover", function(e) {
        var val = (f.properties[state.indicator] || 0).toFixed(3);
        L.popup({ closeButton: false, offset: [0, -4] })
          .setLatLng(e.latlng)
          .setContent(
            "<b>Ward " + wid + "</b><br/>" +
            (f.properties.zone_name || "") + "<br/>" +
            LABELS[state.indicator] + ": <b>" + val + "</b>"
          )
          .openOn(state.leafletMap);
      });
      layer.on("mouseout", function() { state.leafletMap.closePopup(); });
    },
  }).addTo(state.leafletMap);

  // Update legend
  document.getElementById("legend-bar").style.background = gradientCSS(state.indicator);
  document.getElementById("legend-label").textContent = LABELS[state.indicator];
  document.getElementById("leg-lo").textContent = mn.toFixed(2);
  document.getElementById("leg-hi").textContent = mx.toFixed(2);
}

// ── Ward detail panel ──────────────────────────────────────────
function openWardPanel(wardId) {
  state.selectedWard = wardId;
  document.getElementById("empty-panel").style.display = "none";
  document.getElementById("ward-detail").style.display = "flex";

  if (state.wardCache[wardId]) {
    renderWardPanel(state.wardCache[wardId], wardId);
    return;
  }

  get("/wards/" + wardId).then(function(data) {
    state.wardCache[wardId] = data;
    renderWardPanel(data, wardId);
  }).catch(function(e) {
    console.error("Ward fetch failed", e);
  });
}

function renderWardPanel(data, wardId) {
  document.getElementById("wd-title").textContent = "Ward " + wardId;
  document.getElementById("wd-zone").textContent = (data.zone_name || "") + (data.zone ? " · " + data.zone : "");

  // Trend badge
  var tb = document.getElementById("wd-trend");
  if (data.trend === "increasing") {
    tb.className = "trend-badge trend-inc"; tb.textContent = "▲ Warming";
  } else if (data.trend === "decreasing") {
    tb.className = "trend-badge trend-dec"; tb.textContent = "▼ Cooling";
  } else {
    tb.className = "trend-badge trend-none"; tb.textContent = "→ Stable";
  }

  // Latest year KPIs
  var ts = data.timeseries;
  var latest = ts[ts.length - 1] || {};
  var kpis = document.getElementById("wd-kpis");
  kpis.innerHTML = [
    { v: (latest.lst || 0).toFixed(1) + "°", l: "LST 2024", c: "#ef4444" },
    { v: (latest.ndvi || 0).toFixed(3), l: "NDVI 2024", c: "#4ade80" },
    { v: (latest.ndbi || 0).toFixed(3), l: "NDBI 2024", c: "#f97316" },
    { v: Math.round(latest.rainfall || 0) + " mm", l: "Rainfall 2024", c: "#60a5fa" },
  ].map(function(k) {
    return '<div class="wd-kpi"><div class="v" style="color:' + k.c + '">' + k.v + '</div><div class="l">' + k.l + '</div></div>';
  }).join("");

  // Mini chart
  var years = ts.map(function(d){ return d.year; });
  var lsts  = ts.map(function(d){ return +d.lst; });
  var ndvis = ts.map(function(d){ return +d.ndvi; });

  if (state.wardChart) { state.wardChart.destroy(); }
  var ctx = document.getElementById("ward-chart").getContext("2d");
  state.wardChart = new Chart(ctx, {
    data: {
      labels: years,
      datasets: [
        {
          type: "line", label: "LST (°C)", data: lsts,
          borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.08)",
          borderWidth: 2, pointRadius: 3, tension: 0.35, fill: true, yAxisID: "y",
        },
        {
          type: "line", label: "NDVI", data: ndvis,
          borderColor: "#4ade80", backgroundColor: "transparent",
          borderWidth: 1.5, pointRadius: 2, borderDash: [4, 2],
          tension: 0.35, yAxisID: "y2",
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#7a95b5", font: { size: 10 }, boxWidth: 16 } },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x:  { ticks: { color: "#7a95b5", font: { size: 9 } }, grid: { color: "#1e3352" } },
        y:  { ticks: { color: "#7a95b5", font: { size: 9 } }, grid: { color: "#1e3352" }, position: "left" },
        y2: { ticks: { color: "#4ade80", font: { size: 9 } }, grid: { display: false }, position: "right" },
      },
    },
  });

  // Meta info
  var slope = data.slope ? data.slope.toFixed(4) + " °C/yr" : "–";
  var pval  = data.p_value ? data.p_value.toFixed(4) : "–";
  var cp    = data.changepoint_years || "[]";
  document.getElementById("wd-meta").innerHTML =
    "<strong>Slope:</strong> " + slope + "&nbsp;&nbsp;" +
    "<strong>p-value:</strong> " + pval + "<br/>" +
    "<strong>Change-point years:</strong> " + cp;

  // Min/max summary
  var maxLST = Math.max.apply(null, lsts);
  var minLST = Math.min.apply(null, lsts);
  var rangeCSS = maxLST - minLST;
  document.getElementById("wd-stat-row").innerHTML =
    '<div class="wd-stat"><strong>' + minLST.toFixed(1) + '°</strong>Min LST</div>' +
    '<div class="wd-stat"><strong>' + maxLST.toFixed(1) + '°</strong>Max LST</div>' +
    '<div class="wd-stat"><strong>' + rangeCSS.toFixed(1) + '°</strong>Range</div>';

  // Pan map to ward
  if (state.geoLayer) {
    state.geoLayer.eachLayer(function(layer) {
      if (layer.feature && layer.feature.properties.ward === wardId) {
        try { state.leafletMap.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 14 }); } catch(e) {}
      }
    });
  }
}

// ── City trend chart ───────────────────────────────────────────
function loadTrendChart(metric) {
  get("/analytics/city-trend?metric=" + metric).then(function(rows) {
    var color = KPI_COLORS[metric] || "#f97316";
    if (state.trendChart) { state.trendChart.destroy(); }
    var ctx = document.getElementById("trend-chart").getContext("2d");
    state.trendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: rows.map(function(r){ return r.year; }),
        datasets: [{
          label: LABELS[metric] || metric,
          data: rows.map(function(r){ return r.value; }),
          borderColor: color, backgroundColor: color + "18",
          borderWidth: 2.5, pointRadius: 5, pointBackgroundColor: color,
          tension: 0.35, fill: true,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function(c){ return LABELS[metric] + ": " + c.parsed.y.toFixed(4); } } },
        },
        scales: {
          x: { ticks: { color: "#7a95b5" }, grid: { color: "#1e3352" } },
          y: { ticks: { color: "#7a95b5" }, grid: { color: "#1e3352" } },
        },
      },
    });
  });
}

// ── Zone chart ─────────────────────────────────────────────────
function loadZoneChart() {
  get("/analytics/zones?year=2024").then(function(rows) {
    var avgs   = rows.map(function(r){ return r.avg_lst; });
    var mn = Math.min.apply(null, avgs), mx = Math.max.apply(null, avgs);
    var colors = avgs.map(function(v){ return colorScale(v, mn, mx, "lst"); });

    if (state.zoneChart) { state.zoneChart.destroy(); }
    var ctx = document.getElementById("zone-chart").getContext("2d");
    state.zoneChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: rows.map(function(r){ return r.zone_name || r.zone; }),
        datasets: [{ label: "Avg LST (°C)", data: avgs, backgroundColor: colors, borderRadius: 4, borderSkipped: false }],
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#7a95b5", font: { size: 10 }, maxRotation: 40 }, grid: { display: false } },
          y: { ticks: { color: "#7a95b5" }, grid: { color: "#1e3352" } },
        },
      },
    });
  });
}

// ── Distribution chart ─────────────────────────────────────────
function loadDistChart() {
  get("/analytics/distribution?metric=lst&year=2024&bins=20").then(function(buckets) {
    var vals = buckets.map(function(b){ return (b.bucket_start + b.bucket_end) / 2; });
    var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
    var colors = vals.map(function(v){ return colorScale(v, mn, mx, "lst"); });

    if (state.distChart) { state.distChart.destroy(); }
    var ctx = document.getElementById("dist-chart").getContext("2d");
    state.distChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: buckets.map(function(b){ return b.bucket_start.toFixed(1); }),
        datasets: [{ label: "Ward count", data: buckets.map(function(b){ return b.count; }), backgroundColor: colors, borderRadius: 2, borderSkipped: false }],
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#7a95b5", font: { size: 9 }, maxTicksLimit: 10 }, grid: { display: false } },
          y: { ticks: { color: "#7a95b5" }, grid: { color: "#1e3352" } },
        },
      },
    });
  });
}

// ── Regression panel ───────────────────────────────────────────
function loadRegressionPanel() {
  get("/analytics/regression").then(function(data) {
    var coefs  = data.coefficients || {};
    var r2     = data.r2 || 0;
    var ndbi   = coefs.NDBI || 0;
    var ndvi   = coefs.NDVI || 0;
    var rain   = coefs.rainfall || 0;
    var maxAbs = Math.max(Math.abs(ndbi), Math.abs(ndvi), Math.abs(rain * 1000));

    function barW(v) { return Math.round(Math.abs(v) / maxAbs * 100) + "%"; }

    var html = '<div class="reg-r2-block">';
    html += '<div class="reg-r2-val">R² = ' + r2.toFixed(3) + '</div>';
    html += '<div class="reg-r2-lbl">OLS · all wards × 2016–2024</div></div>';

    html += '<div class="reg-equation">';
    html += 'LST = ' + ndvi.toFixed(3) + ' · NDVI<br/>';
    html += '    + ' + ndbi.toFixed(3) + ' · NDBI<br/>';
    html += '    + ' + rain.toFixed(6) + ' · rainfall</div>';

    html += '<div class="reg-coef-list">';
    var coefList = [
      { name: "NDBI", val: ndbi, color: "#f97316" },
      { name: "NDVI", val: ndvi, color: "#4ade80" },
      { name: "Rainfall", val: rain * 1000, color: "#60a5fa", note: "×1000" },
    ];
    coefList.forEach(function(c) {
      html += '<div class="reg-coef">';
      html += '<span class="reg-coef-name">' + c.name + (c.note ? ' <span style="font-size:0.65rem;color:var(--text-muted)">('+c.note+')</span>' : '') + '</span>';
      html += '<div class="reg-coef-bar-wrap"><div class="reg-coef-bar" style="width:' + barW(c.val) + ';background:' + c.color + '"></div></div>';
      html += '<span class="reg-coef-val" style="color:' + c.color + '">' + (c.val >= 0 ? "+" : "") + c.val.toFixed(3) + '</span>';
      html += '</div>';
    });
    html += '</div>';
    html += '<div class="reg-interp">' + data.interpretation + '</div>';

    document.getElementById("reg-panel").innerHTML = html;
  });
}

// ── Rankings chart ─────────────────────────────────────────────
function loadRankChart(metric) {
  get("/analytics/rankings?metric=" + metric + "&year=2024&limit=15").then(function(rows) {
    var vals   = rows.map(function(r){ return r.value; });
    var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
    var colors = vals.map(function(v){ return colorScale(v, mn, mx, metric); });

    if (state.rankChart) { state.rankChart.destroy(); }
    var ctx = document.getElementById("rank-chart").getContext("2d");
    state.rankChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: rows.map(function(r){ return "W" + r.ward; }),
        datasets: [{
          label: LABELS[metric] + " (2024)",
          data: vals, backgroundColor: colors, borderRadius: 4, borderSkipped: false,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(c) {
                var ward = rows[c.dataIndex];
                return LABELS[metric] + ": " + c.parsed.y.toFixed(3) + " · " + (ward.zone_name || "");
              }
            }
          }
        },
        scales: {
          x: { ticks: { color: "#7a95b5" }, grid: { display: false } },
          y: { ticks: { color: "#7a95b5" }, grid: { color: "#1e3352" } },
        },
      },
    });
  });
}

// ── Nav scroll highlighting ────────────────────────────────────
function initNavHighlight() {
  var sections = ["overview", "map-section", "analytics", "methodology"];
  window.addEventListener("scroll", function() {
    var cur = sections[0];
    sections.forEach(function(id) {
      var el = document.getElementById(id);
      if (el && window.scrollY >= el.offsetTop - 80) cur = id;
    });
    document.querySelectorAll(".nav-link").forEach(function(a) {
      var href = a.getAttribute("href").replace("#", "");
      a.classList.toggle("active", href === cur);
    });
  });
}

// ── Event wiring ───────────────────────────────────────────────
function wireEvents() {
  // Indicator pills
  document.getElementById("ind-group").addEventListener("click", function(e) {
    if (!e.target.dataset.ind) return;
    document.querySelectorAll("#ind-group .pill").forEach(function(p){ p.classList.remove("active"); });
    e.target.classList.add("active");
    state.indicator = e.target.dataset.ind;
    refreshMap();
  });

  // Year slider
  var slider = document.getElementById("year-slider");
  slider.addEventListener("input", function() {
    state.year = +slider.value;
    document.getElementById("year-badge").textContent = state.year;
    refreshMap();
    // Refresh ward panel if open
    if (state.selectedWard) {
      // Clear cache for that ward (year-specific panel gets fresh data)
      openWardPanel(state.selectedWard);
    }
  });

  // Zone filter
  document.getElementById("zone-sel").addEventListener("change", function(e) {
    state.zone = e.target.value;
    if (state.geojsonCache[state.year + "-" + state.indicator]) {
      renderGeoLayer(state.geojsonCache[state.year + "-" + state.indicator]);
    }
  });

  // Ward search
  document.getElementById("ward-search").addEventListener("input", function(e) {
    var q = parseInt(e.target.value.trim(), 10);
    if (!isNaN(q) && q > 0) openWardPanel(q);
  });

  // City trend tabs
  document.getElementById("trend-tabs").addEventListener("click", function(e) {
    if (!e.target.dataset.metric) return;
    document.querySelectorAll("#trend-tabs .tab").forEach(function(t){ t.classList.remove("active"); });
    e.target.classList.add("active");
    loadTrendChart(e.target.dataset.metric);
  });

  // Rankings tabs
  document.getElementById("rank-tabs").addEventListener("click", function(e) {
    if (!e.target.dataset.rmetric) return;
    document.querySelectorAll("#rank-tabs .tab").forEach(function(t){ t.classList.remove("active"); });
    e.target.classList.add("active");
    loadRankChart(e.target.dataset.rmetric);
  });
}

// ── Chart.js global defaults ───────────────────────────────────
Chart.defaults.color = "#7a95b5";
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = "#14253d";
Chart.defaults.plugins.tooltip.borderColor = "#1e3352";
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.titleColor = "#e2e8f0";
Chart.defaults.plugins.tooltip.bodyColor = "#7a95b5";

// ── Boot sequence ──────────────────────────────────────────────
initStatusCheck();
loadHeroKPIs();
loadZones();
initMap();
loadTrendChart("lst");
loadZoneChart();
loadDistChart();
loadRegressionPanel();
loadRankChart("lst");
wireEvents();
initNavHighlight();


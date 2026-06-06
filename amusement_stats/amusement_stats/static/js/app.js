function initDashboardCharts() {
  const hotRankEl = document.getElementById("hotRankChart");
  const hotScoreEl = document.getElementById("hotScoreChart");
  const trafficEl = document.getElementById("trafficLineChart");
  const statusEl = document.getElementById("statusPieChart");

  const rankLabelsScript = document.getElementById("rank-labels");
  const rankValuesScript = document.getElementById("rank-values");
  const scoreLabelsScript = document.getElementById("score-labels");
  const scoreValuesScript = document.getElementById("score-values");
  const trafficLabelsScript = document.getElementById("traffic-labels");
  const trafficValuesScript = document.getElementById("traffic-values");
  const statusDataScript = document.getElementById("status-data");
  const typeRatioDataScript = document.getElementById("type-ratio-data");
  const repeatRateScript = document.getElementById("repeat-rate");
  const turnoverLabelsScript = document.getElementById("turnover-labels");
  const turnoverValuesScript = document.getElementById("turnover-values");
  const regionHeatmapXScript = document.getElementById("region-heatmap-x-labels");
  const regionHeatmapYScript = document.getElementById("region-heatmap-y-labels");
  const regionHeatmapDataScript = document.getElementById("region-heatmap-data");
  const regionHeatmapMaxScript = document.getElementById("region-heatmap-max");
  const sparkLabelsScript = document.getElementById("spark-labels");
  const sparkVisitsScript = document.getElementById("spark-visits");
  const sparkQueueScript = document.getElementById("spark-queue");

  const rankLabels = rankLabelsScript ? JSON.parse(rankLabelsScript.textContent) : ["暂无数据"];
  const rankValues = rankValuesScript ? JSON.parse(rankValuesScript.textContent) : [0];
  const scoreLabels = scoreLabelsScript ? JSON.parse(scoreLabelsScript.textContent) : [];
  const scoreValues = scoreValuesScript ? JSON.parse(scoreValuesScript.textContent) : [];
  const trafficLabels = trafficLabelsScript ? JSON.parse(trafficLabelsScript.textContent) : ["10:00", "11:00", "12:00"];
  const trafficValues = trafficValuesScript ? JSON.parse(trafficValuesScript.textContent) : [0, 0, 0];
  const statusData = statusDataScript
    ? JSON.parse(statusDataScript.textContent)
    : [
        { value: 0, name: "正常" },
        { value: 0, name: "维护" },
        { value: 0, name: "关闭" },
      ];
  const typeRatioData = typeRatioDataScript ? JSON.parse(typeRatioDataScript.textContent) : [];
  const repeatRate = repeatRateScript ? JSON.parse(repeatRateScript.textContent) : 0;
  const turnoverLabels = turnoverLabelsScript ? JSON.parse(turnoverLabelsScript.textContent) : [];
  const turnoverValues = turnoverValuesScript ? JSON.parse(turnoverValuesScript.textContent) : [];
  const regionHeatmapXLabels = regionHeatmapXScript ? JSON.parse(regionHeatmapXScript.textContent) : [];
  const regionHeatmapYLabels = regionHeatmapYScript ? JSON.parse(regionHeatmapYScript.textContent) : [];
  const regionHeatmapData = regionHeatmapDataScript ? JSON.parse(regionHeatmapDataScript.textContent) : [];
  const regionHeatmapMax = regionHeatmapMaxScript ? JSON.parse(regionHeatmapMaxScript.textContent) : 0;
  const sparkLabels = sparkLabelsScript ? JSON.parse(sparkLabelsScript.textContent) : [];
  const sparkVisits = sparkVisitsScript ? JSON.parse(sparkVisitsScript.textContent) : [];
  const sparkQueue = sparkQueueScript ? JSON.parse(sparkQueueScript.textContent) : [];

  if (hotRankEl && window.echarts) {
    const hotRankChart = echarts.init(hotRankEl);
    hotRankChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 30, bottom: 40 },
      xAxis: { type: "category", data: rankLabels, axisLabel: { interval: 0, rotate: 20 } },
      yAxis: { type: "value", name: "人次" },
      series: [{ type: "bar", data: rankValues, itemStyle: { color: "#0d6efd" }, barWidth: "52%" }],
    });
    window.addEventListener("resize", () => hotRankChart.resize());
  }

  if (hotScoreEl && window.echarts && scoreLabels.length) {
    const chart = echarts.init(hotScoreEl);
    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 30, bottom: 50 },
      xAxis: { type: "category", data: scoreLabels, axisLabel: { interval: 0, rotate: 20 } },
      yAxis: { type: "value", name: "Score(0-100)" },
      series: [{ type: "bar", data: scoreValues, itemStyle: { color: "#6366f1" }, barWidth: "52%" }],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  if (trafficEl && window.echarts) {
    const trafficChart = echarts.init(trafficEl);
    trafficChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 45, right: 20, top: 30, bottom: 35 },
      xAxis: { type: "category", data: trafficLabels },
      yAxis: { type: "value", name: "客流" },
      series: [{ type: "line", smooth: true, data: trafficValues, lineStyle: { width: 3, color: "#20c997" }, areaStyle: { color: "rgba(32,201,151,0.18)" }, symbolSize: 7 }],
    });
    window.addEventListener("resize", () => trafficChart.resize());
  }

  if (statusEl && window.echarts) {
    const statusChart = echarts.init(statusEl);
    statusChart.setOption({
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [{ type: "pie", radius: ["45%", "72%"], avoidLabelOverlap: false, data: statusData }],
    });
    window.addEventListener("resize", () => statusChart.resize());
  }

  const sparkVisitsEl = document.getElementById("sparkVisits");
  if (sparkVisitsEl && window.echarts && sparkLabels.length) {
    const chart = echarts.init(sparkVisitsEl);
    chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 4 },
      xAxis: { type: "category", data: sparkLabels, show: false },
      yAxis: { type: "value", show: false },
      series: [{ type: "line", data: sparkVisits, smooth: true, symbol: "none", lineStyle: { width: 2, color: "#0d6efd" } }],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  const sparkQueueEl = document.getElementById("sparkQueue");
  if (sparkQueueEl && window.echarts && sparkLabels.length) {
    const chart = echarts.init(sparkQueueEl);
    chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 4 },
      xAxis: { type: "category", data: sparkLabels, show: false },
      yAxis: { type: "value", show: false },
      series: [{ type: "line", data: sparkQueue, smooth: true, symbol: "none", lineStyle: { width: 2, color: "#20c997" } }],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  const typeRatioEl = document.getElementById("typeRatioChart");
  if (typeRatioEl && window.echarts) {
    const chart = echarts.init(typeRatioEl);
    chart.setOption({
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [{ type: "pie", radius: ["35%", "70%"], data: typeRatioData }],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  const repeatRateEl = document.getElementById("repeatRateChart");
  if (repeatRateEl && window.echarts) {
    const chart = echarts.init(repeatRateEl);
    const value = Math.max(0, Math.min(100, Number(repeatRate) || 0));
    chart.setOption({
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          radius: ["55%", "80%"],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: "center",
            formatter: `{value|${value.toFixed(1)}%}\n{name|重复游玩率}`,
            rich: {
              value: { fontSize: 22, fontWeight: 700, color: "#0d6efd" },
              name: { fontSize: 12, color: "#6c757d", padding: [6, 0, 0, 0] },
            },
          },
          labelLine: { show: false },
          data: [
            { value: value, name: "重复游玩" },
            { value: Math.max(0, 100 - value), name: "非重复" },
          ],
          itemStyle: { color: (params) => (params.dataIndex === 0 ? "#0d6efd" : "#e9ecef") },
        },
      ],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  const turnoverEl = document.getElementById("turnoverChart");
  if (turnoverEl && window.echarts && turnoverLabels.length) {
    const chart = echarts.init(turnoverEl);
    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 30, bottom: 60 },
      xAxis: { type: "category", data: turnoverLabels, axisLabel: { interval: 0, rotate: 20 } },
      yAxis: { type: "value", name: "周转率(%)" },
      series: [{ type: "bar", data: turnoverValues, itemStyle: { color: "#f59e0b" }, barWidth: "52%" }],
    });
    window.addEventListener("resize", () => chart.resize());
  }

  const regionHeatmapEl = document.getElementById("regionHeatmapChart");
  if (regionHeatmapEl && window.echarts && regionHeatmapData.length) {
    const chart = echarts.init(regionHeatmapEl);
    chart.setOption({
      tooltip: {
        position: "top",
        formatter: (p) => {
          const regionName = p.data && p.data.name ? p.data.name : "未知区域";
          const x = regionHeatmapXLabels[p.value[0]] || p.value[0];
          const y = regionHeatmapYLabels[p.value[1]] || p.value[1];
          return `${regionName}<br/>位置(${x},${y})<br/>热度: ${p.value[2]}`;
        },
      },
      visualMap: { min: 0, max: regionHeatmapMax || 1, calculable: true, orient: "horizontal", left: "center", bottom: 0 },
      grid: { left: 10, right: 10, top: 30, bottom: 25 },
      xAxis: { type: "category", data: regionHeatmapXLabels, splitArea: { show: true } },
      yAxis: { type: "category", data: regionHeatmapYLabels, splitArea: { show: true } },
      series: [{ type: "heatmap", data: regionHeatmapData, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.2)" } } }],
    });
    window.addEventListener("resize", () => chart.resize());
  }
}

function initThemeToggle() {
  const key = "amusement-theme";
  const btn = document.getElementById("themeToggleBtn");
  const apply = (mode) => {
    document.body.classList.toggle("dark-theme", mode === "dark");
    if (btn) {
      btn.textContent = mode === "dark" ? "浅色模式" : "深色模式";
    }
  };

  const preferred = document.body.dataset.defaultTheme || "light";
  const saved = localStorage.getItem(key) || preferred;
  apply(saved);

  if (btn) {
    btn.addEventListener("click", () => {
      const next = document.body.classList.contains("dark-theme") ? "light" : "dark";
      localStorage.setItem(key, next);
      apply(next);
    });
  }
}

function getApiDateRange() {
  const startInput = document.querySelector('input[name="start_date"]');
  const endInput = document.querySelector('input[name="end_date"]');
  return { start: startInput ? startInput.value : "", end: endInput ? endInput.value : "" };
}

async function fetchApiJson(url) {
  const resp = await fetch(url, { credentials: "same-origin" });
  return await resp.json();
}

function getOrInitChart(dom) {
  if (!dom || !window.echarts) return null;
  const exist = echarts.getInstanceByDom(dom);
  return exist || echarts.init(dom);
}

async function refreshDashboardChartsByApi() {
  const { start, end } = getApiDateRange();
  if (!start || !end) return;

  const rankUrl = `/api/rank/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}&limit=8`;
  const scoreUrl = `/api/hot_score/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}&limit=8`;
  const trafficUrl = `/api/traffic/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}&bucket=hour`;
  const typeRatioUrl = `/api/type_ratio/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;

  try {
    const [rankRes, scoreRes, trafficRes, typeRes] = await Promise.all([
      fetchApiJson(rankUrl),
      fetchApiJson(scoreUrl),
      fetchApiJson(trafficUrl),
      fetchApiJson(typeRatioUrl),
    ]);

    if (rankRes && rankRes.code === 0) {
      const chart = getOrInitChart(document.getElementById("hotRankChart"));
      if (chart) {
        chart.setOption({
          tooltip: { trigger: "axis" },
          grid: { left: 40, right: 20, top: 30, bottom: 40 },
          xAxis: { type: "category", data: rankRes.data?.labels || [], axisLabel: { interval: 0, rotate: 20 } },
          yAxis: { type: "value", name: "人次" },
          series: [{ type: "bar", data: rankRes.data?.values || [], itemStyle: { color: "#0d6efd" }, barWidth: "52%" }],
        });
      }
    }

    if (scoreRes && scoreRes.code === 0) {
      const chart = getOrInitChart(document.getElementById("hotScoreChart"));
      if (chart) {
        chart.setOption({
          tooltip: { trigger: "axis" },
          grid: { left: 40, right: 20, top: 30, bottom: 50 },
          xAxis: { type: "category", data: scoreRes.data?.labels || [], axisLabel: { interval: 0, rotate: 20 } },
          yAxis: { type: "value", name: "Score(0-100)" },
          series: [{ type: "bar", data: scoreRes.data?.values || [], itemStyle: { color: "#6366f1" }, barWidth: "52%" }],
        });
      }
    }

    if (trafficRes && trafficRes.code === 0) {
      const chart = getOrInitChart(document.getElementById("trafficLineChart"));
      if (chart) {
        chart.setOption({
          tooltip: { trigger: "axis" },
          grid: { left: 45, right: 20, top: 30, bottom: 35 },
          xAxis: { type: "category", data: trafficRes.data?.labels || [] },
          yAxis: { type: "value", name: "客流" },
          series: [{ type: "line", smooth: true, data: trafficRes.data?.values || [], lineStyle: { width: 3, color: "#20c997" }, areaStyle: { color: "rgba(32,201,151,0.18)" }, symbolSize: 7 }],
        });
      }
    }

    if (typeRes && typeRes.code === 0) {
      const chart = getOrInitChart(document.getElementById("typeRatioChart"));
      if (chart) {
        chart.setOption({ tooltip: { trigger: "item" }, legend: { bottom: 0 }, series: [{ type: "pie", radius: ["35%", "70%"], data: typeRes.data?.data || [] }] });
      }
    }
  } catch (e) {
    console.warn("dashboard api refresh failed:", e);
  }
}

function initSidebarToggle() {
  const key = "amusement-sidebar-collapsed";
  const btn = document.getElementById("sidebarToggleBtn");
  const apply = (collapsed) => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    if (btn) btn.textContent = collapsed ? "展开菜单" : "折叠菜单";
  };
  apply(localStorage.getItem(key) === "1");
  if (btn) {
    btn.addEventListener("click", () => {
      const next = !document.body.classList.contains("sidebar-collapsed");
      localStorage.setItem(key, next ? "1" : "0");
      apply(next);
    });
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

async function refreshPredictByApi() {
  const badgeEl = document.getElementById("predictAlertBadge");
  const boxEl = document.getElementById("predictAlertBox");
  const tbodyEl = document.getElementById("predictTableBody");
  if (!badgeEl || !boxEl || !tbodyEl) return;

  try {
    const res = await fetchApiJson("/api/predict/?days=7");
    if (!res || res.code !== 0) return;

    const predictionRows = res.data?.prediction_rows || [];
    const alertRows = res.data?.alert_rows || [];

    if (alertRows.length > 0) {
      badgeEl.classList.remove("text-bg-success");
      badgeEl.classList.add("text-bg-danger");
      badgeEl.textContent = `预警 ${alertRows.length} 项`;
      boxEl.classList.remove("d-none");
      boxEl.innerHTML = alertRows.map((a) => `<div>【${escapeHtml(a.name)}】预测次日客流 ${escapeHtml(a.predicted_next_day)}，超过阈值 ${escapeHtml(a.threshold)}</div>`).join("");
    } else {
      badgeEl.classList.remove("text-bg-danger");
      badgeEl.classList.add("text-bg-success");
      badgeEl.textContent = "暂无预警";
      boxEl.classList.add("d-none");
      boxEl.innerHTML = "";
    }

    const topRows = predictionRows.slice(0, 10);
    if (!topRows.length) {
      tbodyEl.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无可预测数据。</td></tr>';
      return;
    }

    tbodyEl.innerHTML = topRows
      .map((r) => {
        const statusBadge = r.is_alert ? '<span class="badge text-bg-danger">预警</span>' : '<span class="badge text-bg-success">正常</span>';
        return `<tr><td>${escapeHtml(r.name)}</td><td>${escapeHtml(r.predicted_next_day)}</td><td>${escapeHtml(r.predicted_lr)}</td><td>${escapeHtml(r.threshold)} / ${escapeHtml(r.capacity_risk_threshold)}</td><td>${statusBadge}</td></tr>`;
      })
      .join("");
  } catch (e) {
    console.warn("refreshPredictByApi failed:", e);
  }
}

async function refreshRegionHeatmapByApi() {
  const regionEl = document.getElementById("regionHeatmapChart");
  if (!regionEl || !window.echarts) return;

  try {
    const { start, end } = getApiDateRange();
    if (!start || !end) return;

    const res = await fetchApiJson(`/api/region_heatmap/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`);
    if (!res || res.code !== 0) return;

    const xLabels = res.data?.region_heatmap_x_labels || [];
    const yLabels = res.data?.region_heatmap_y_labels || [];
    const data = res.data?.region_heatmap_data || [];
    const maxVal = res.data?.region_heatmap_max || 0;

    const chart = getOrInitChart(regionEl);
    if (!chart) return;

    chart.setOption({
      tooltip: {
        position: "top",
        formatter: (p) => {
          const regionName = p.data?.name || "未知区域";
          const x = xLabels[p.value[0]] || p.value[0];
          const y = yLabels[p.value[1]] || p.value[1];
          return `${regionName}<br/>位置(${x},${y})<br/>热度: ${p.value[2]}`;
        },
      },
      visualMap: { min: 0, max: maxVal || 1, calculable: true, orient: "horizontal", left: "center", bottom: 0 },
      grid: { left: 10, right: 10, top: 30, bottom: 25 },
      xAxis: { type: "category", data: xLabels, splitArea: { show: true } },
      yAxis: { type: "category", data: yLabels, splitArea: { show: true } },
      series: [{ type: "heatmap", data, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.2)" } } }],
    });
    chart.resize();
  } catch (e) {
    console.warn("refreshRegionHeatmapByApi failed:", e);
  }
}

async function refreshHeatDecayByApi() {
  const tbodyEl = document.getElementById("decayTableBody");
  if (!tbodyEl) return;

  try {
    const { start, end } = getApiDateRange();
    if (!start || !end) return;

    const res = await fetchApiJson(`/api/heat_decay/?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`);
    if (!res || res.code !== 0) return;

    const rows = res.data?.decay_rows || [];
    if (!rows.length) {
      tbodyEl.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">暂无衰减周期数据。</td></tr>';
      return;
    }

    tbodyEl.innerHTML = rows
      .map((r) => {
        const decayDays = r.decay_days !== null && r.decay_days !== undefined ? r.decay_days : "-";
        return `<tr><td>${escapeHtml(r.name)}</td><td>${escapeHtml(r.peak)}（${escapeHtml(r.peak_day)}）</td><td>${escapeHtml(decayDays)}</td></tr>`;
      })
      .join("");
  } catch (e) {
    console.warn("refreshHeatDecayByApi failed:", e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initSidebarToggle();
  initThemeToggle();
  initDashboardCharts();
  refreshDashboardChartsByApi();
  refreshPredictByApi();
  refreshRegionHeatmapByApi();
  refreshHeatDecayByApi();
});

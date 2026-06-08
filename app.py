import json
import re
from itertools import product as iproduct
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

CSV_PATH = "2606 Indianapolis Prison Island Naming Feedback - Prison Island Indianapolis.csv"

CITY_MAP = {"6": "New York", "16": "Los Angeles", "21": "Chicago", "52": "Denver", "54": "Dallas", "114": "Cincinnati"}
GROUP_MAP = {"a": "A", "b": "B", "c": "C", "d": "D"}
WELCOME_MAP = {"v": "Welcome", "n": "No Welcome"}
JAIL_MAP = {"l": "Jail"}

NAME_COLORS = {
    "Prison Island":                 "#E8630A",
    "BRKThrough":                    "#4C6EF5",
    "BRKThrough (vs Prison Island)": "#A0B4FA",
    "BRKThrough (vs Glow or Go)":    "#1A3ACC",
    "Glow or Go":                    "#E91E8C",
}

CITY_COLORS = {
    "New York":    "#2196F3",
    "Los Angeles": "#FF9800",
    "Chicago":     "#4CAF50",
    "Denver":      "#9C27B0",
    "Dallas":      "#F44336",
    "Cincinnati":  "#00BCD4",
    "Unknown":     "#9E9E9E",
}

CITY_ORDER = ["New York", "Los Angeles", "Chicago", "Denver", "Dallas", "Cincinnati"]

FREQ_ORDER = ["More than once a week", "Once a week", "Every other week",
              "Once or twice a month", "Every other month", "Once or twice a year", "Less than that"]

AGE_ORDER = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "Skip question"]

SCALE_FIRST  = {1: "1 — Not at all", 2: "2", 3: "3", 4: "4", 5: "5 — Very likely"}
SCALE_SECOND = {1: "1 — Worse than", 2: "2", 3: "3 — About the same", 4: "4", 5: "5 — Better than"}

ORDER_PI_BRK = ["BRKThrough is much better", "BRKThrough is slightly better",
                "They're about the same", "Prison Island is slightly better", "Prison Island is much better"]
ORDER_BRK_GOG = ["BRKThrough is much better", "BRKThrough is slightly better",
                 "They're about the same", "Glow or Go is slightly better", "Glow or Go is much better"]


def name_color_map(labels):
    return {l: NAME_COLORS.get(l, "#888888") for l in labels}

def clean_text(s):
    return re.sub(r"\*+", "", str(s)).strip()

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH, header=0)
    raw_cols = df.columns.tolist()
    col_ad, col_af, col_ag, col_ah = raw_cols[29], raw_cols[31], raw_cols[32], raw_cols[33]
    df = df.rename(columns={col_ad: "_city", col_af: "_group", col_ag: "_welcome", col_ah: "_jail"})
    df["_city"] = pd.to_numeric(df["_city"], errors="coerce").astype("Int64").astype(str).str.replace("<NA>", "")
    df["_city"] = df["_city"].map(CITY_MAP).fillna("Unknown")
    df["_group"]   = df["_group"].astype(str).str.strip().map(GROUP_MAP).fillna("Unknown")
    df["_welcome"] = df["_welcome"].astype(str).str.strip().map(WELCOME_MAP).fillna("Unknown")
    df["_jail"]    = df["_jail"].astype(str).str.strip().map(JAIL_MAP).fillna("No Jail")
    for c in df.columns:
        if not c.startswith("_"):
            df[c] = df[c].apply(lambda x: clean_text(x) if pd.notna(x) else x)
    return df

def apply_filters(df, cities, groups, jails):
    mask = pd.Series(True, index=df.index)
    if cities:   mask &= df["_city"].isin(cities)
    if groups:   mask &= df["_group"].isin(groups)
    if jails:    mask &= df["_jail"].isin(jails)
    return df[mask]


# ── Beeswarm component ───────────────────────────────────────────────────────

_BEESWARM_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0e1117; color: #fafafa; overflow: hidden;
}
#app { width: 100%; height: 100vh; display: flex; flex-direction: column; }
#controls { padding: 12px 20px 0; display: flex; flex-direction: column; gap: 7px; }
.ctrl-row { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.row-label {
  font-size: 10px; color: #555; letter-spacing: 0.08em;
  text-transform: uppercase; width: 58px; flex-shrink: 0;
}
.dim-btn {
  padding: 4px 11px; border-radius: 14px;
  border: 1.5px solid #252525; background: transparent;
  color: #666; font-size: 12px; cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  white-space: nowrap;
}
.dim-btn:hover { border-color: #555; color: #bbb; }
.dim-btn.active { border-color: #ccc; color: #fff; background: rgba(255,255,255,0.09); }
.dim-btn.soft { border-color: #444; color: #999; background: rgba(255,255,255,0.04); }
#color-row { display: none; }
#narrative { padding: 5px 20px 1px; font-size: 12px; color: #555; min-height: 20px; }
#legend {
  padding: 2px 20px 4px; display: flex; gap: 12px;
  flex-wrap: wrap; min-height: 22px; align-items: center;
}
.leg-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #888; cursor: pointer; border-radius: 4px; padding: 2px 4px; transition: background .15s; }
.leg-item:hover { background: #1e1e1e; }
.leg-item.leg-active { background: #222; color: #ddd; }
.leg-item.leg-dimmed { opacity: 0.35; }
.leg-sw { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.leg-pct { margin-left: auto; color: #aaa; font-size: 10px; font-variant-numeric: tabular-nums; }
#chart-wrap { flex: 1; min-height: 0; position: relative; }
svg { width: 100%; height: 100%; overflow: visible; }
#tooltip {
  position: fixed; display: none;
  background: rgba(10,12,20,0.97); border: 1px solid #282828;
  border-radius: 8px; padding: 10px 14px;
  font-size: 12px; line-height: 1.85; max-width: 265px;
  pointer-events: none; z-index: 9999;
  box-shadow: 0 8px 30px rgba(0,0,0,0.7);
}
#col-detail {
  display: none; position: fixed;
  background: #141414; border: 1px solid #2a2a2a;
  border-radius: 8px; padding: 13px 16px;
  z-index: 9998; min-width: 200px; max-width: 280px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.7);
  font-size: 11px; color: #bbb;
}
#col-detail h4 { margin: 0 0 10px; font-size: 12px; color: #fff; font-weight: 600; }
#col-detail table { border-collapse: collapse; width: 100%; }
#col-detail td { padding: 3px 0; vertical-align: middle; }
#col-detail td.num { text-align: right; padding-left: 12px; font-variant-numeric: tabular-nums; }
#col-detail td.pct { text-align: right; padding-left: 6px; color: #555; font-variant-numeric: tabular-nums; }
#col-detail .close-hint { margin-top: 10px; font-size: 10px; color: #444; text-align: right; }
.tt-row { display: flex; gap: 8px; }
.tt-k { color: #555; min-width: 78px; flex-shrink: 0; font-size: 11px; }
.tt-v { color: #ddd; }
</style>
</head>
<body>
<div id="app">
  <div id="controls">
    <div class="ctrl-row">
      <span class="row-label">Group by</span>
      <div id="group-btns" style="display:flex;gap:6px;flex-wrap:wrap;"></div>
    </div>
    <div class="ctrl-row" id="color-row">
      <span class="row-label">Colour by</span>
      <div id="color-btns" style="display:flex;gap:6px;flex-wrap:wrap;"></div>
    </div>
  </div>
  <div id="narrative"></div>
  <div id="legend"></div>
  <div id="chart-wrap"><svg id="chart"></svg></div>
</div>
<div id="tooltip"></div>
<div id="col-detail"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const RAW = __DATA__;

const AGE_ORDER     = ["18-24","25-34","35-44","45-54","55-64","65-74","75-84","Skip question","Unknown"];
const CITY_ORDER    = ["New York","Los Angeles","Chicago","Denver","Dallas","Cincinnati","Unknown"];
const FREQ_ORDER    = ["More than once a week","Once a week","Every other week","Once or twice a month","Every other month","Once or twice a year","Less than that","Unknown"];
const RATE_ORDER    = ["1","2","3","4","5","—"];
const PI_BRK_ORDER  = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Prison Island is slightly better","Prison Island is much better","—"];
const BRK_GOG_ORDER = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Glow or Go is slightly better","Glow or Go is much better","—"];

const SHORT = {
  "More than once a week":"  >1/wk","Once a week":"1/wk",
  "Every other week":"2x/mo","Once or twice a month":"1–2/mo",
  "Every other month":"1–2/6mo","Once or twice a year":"1–2/yr",
  "Less than that":"<1/yr",
  "BRKThrough is much better":"BRK ↑↑","BRKThrough is slightly better":"BRK ↑",
  "They're about the same":"≈ same",
  "Prison Island is slightly better":"PI ↑","Prison Island is much better":"PI ↑↑",
  "Glow or Go is slightly better":"GoG ↑","Glow or Go is much better":"GoG ↑↑",
};
function sl(v) { return SHORT[v] || v; }

const COLORS = {
  age: {
    "18-24":"#FF4444","25-34":"#FF7722","35-44":"#FFCC00",
    "45-54":"#88CC00","55-64":"#00BBAA","65-74":"#4488FF",
    "75-84":"#9966FF","Skip question":"#555","Unknown":"#555",
  },
  city: {
    "New York":"#2196F3","Los Angeles":"#FF9800","Chicago":"#4CAF50",
    "Denver":"#9C27B0","Dallas":"#F44336","Cincinnati":"#00BCD4","Unknown":"#9E9E9E",
  },
  freq: {
    "More than once a week":"#FF4444","Once a week":"#FF7722",
    "Every other week":"#FFCC00","Once or twice a month":"#88CC44",
    "Every other month":"#44BBAA","Once or twice a year":"#4488FF",
    "Less than that":"#9966FF","Unknown":"#555",
  },
  rating: {
    "1":"#E74C3C","2":"#E67E22","3":"#F1C40F","4":"#2ECC71","5":"#16A085","—":"#252525",
  },
  pi_vs_brk: {
    "BRKThrough is much better":"#4C6EF5",
    "BRKThrough is slightly better":"#8FA8FF",
    "They're about the same":"#777",
    "Prison Island is slightly better":"#FFAA66",
    "Prison Island is much better":"#E8630A",
    "—":"#252525",
  },
  brk_vs_gog: {
    "BRKThrough is much better":"#4C6EF5",
    "BRKThrough is slightly better":"#8FA8FF",
    "They're about the same":"#777",
    "Glow or Go is slightly better":"#FF77AA",
    "Glow or Go is much better":"#E91E8C",
    "—":"#252525",
  },
};

const DIMS = [
  {key:"age",       label:"Age",         field:"age",        order:AGE_ORDER,     colors:COLORS.age},
  {key:"city",      label:"City",        field:"city",       order:CITY_ORDER,    colors:COLORS.city},
  {key:"freq",      label:"Frequency",   field:"freq",       order:FREQ_ORDER,    colors:COLORS.freq},
  {key:"pi_rate",   label:"PI rating",   field:"pi_rate",    order:RATE_ORDER,    colors:COLORS.rating},
  {key:"brk_rate",  label:"BRK rating",  field:"brk_rate",   order:RATE_ORDER,    colors:COLORS.rating},
  {key:"gog_rate",  label:"GoG rating",  field:"gog_rate",   order:RATE_ORDER,    colors:COLORS.rating},
  {key:"pi_vs_brk", label:"PI vs BRK",   field:"pi_vs_brk",  order:PI_BRK_ORDER,  colors:COLORS.pi_vs_brk},
  {key:"brk_vs_gog",label:"BRK vs GoG",  field:"brk_vs_gog", order:BRK_GOG_ORDER, colors:COLORS.brk_vs_gog},
];
const DIM_MAP = Object.fromEntries(DIMS.map(d => [d.key, d]));

// Normalise null → "—" for all rating / choice fields
RAW.forEach(d => {
  ["pi_rate","brk_rate","gog_rate"].forEach(f => {
    d[f] = (d[f] === null || d[f] === undefined) ? "—" : String(d[f]);
  });
  ["pi_vs_brk","brk_vs_gog"].forEach(f => {
    if (!d[f] || d[f] === "nan") d[f] = "—";
  });
  if (!d.freq || d.freq === "nan") d.freq = "Unknown";
});

const R = 5.5;
const IDLE = "#404040";
const nodes = RAW.map((d, i) => Object.assign({x:0,y:0,vx:0,vy:0}, d, {_i:i}));

let W, H, groupKey = null, colorKey = null;
let filterField = null, filterVal = null;
let circles;

const svg       = d3.select("#chart");
const tooltipEl = document.getElementById("tooltip");
const legendEl  = document.getElementById("legend");
const narrativeEl = document.getElementById("narrative");

// ── Force sim ───────────────────────────────────────────────────────────────
const sim = d3.forceSimulation(nodes)
  .force("collide", d3.forceCollide(R + 1.8).strength(0.8).iterations(2))
  .force("x", d3.forceX(0).strength(0.04))
  .force("y", d3.forceY(0).strength(0.04))
  .alphaDecay(0.011)
  .velocityDecay(0.30)
  .on("tick", () => circles.attr("cx", d => d.x).attr("cy", d => d.y));

// ── Build button rows ────────────────────────────────────────────────────────
function buildButtons() {
  const gWrap = document.getElementById("group-btns");
  const cWrap = document.getElementById("color-btns");
  DIMS.forEach(d => {
    [gWrap, cWrap].forEach((wrap, ci) => {
      const b = document.createElement("button");
      b.className = "dim-btn"; b.textContent = d.label; b.dataset.key = d.key;
      wrap.appendChild(b);
    });
  });
  gWrap.addEventListener("click", e => {
    const b = e.target.closest(".dim-btn"); if (!b) return;
    const k = b.dataset.key;
    if (groupKey === k) { groupKey = null; colorKey = null; idle(); }
    else { groupKey = k; colorKey = null; go(); }
  });
  cWrap.addEventListener("click", e => {
    const b = e.target.closest(".dim-btn"); if (!b) return;
    colorKey = (b.dataset.key === groupKey) ? null : b.dataset.key;
    recolor(); refreshColorBtns(); renderLegend(); updateNarrative();
  });
}

function refreshGroupBtns() {
  document.querySelectorAll("#group-btns .dim-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.key === groupKey));
  document.getElementById("color-row").style.display = groupKey ? "flex" : "none";
}
function refreshColorBtns() {
  const eff = colorKey || groupKey;
  document.querySelectorAll("#color-btns .dim-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.key === eff && colorKey !== null);
    b.classList.toggle("soft",   b.dataset.key === eff && colorKey === null);
  });
}

// ── Color helpers ────────────────────────────────────────────────────────────
function effColorDim() { return DIM_MAP[colorKey] || DIM_MAP[groupKey]; }
function dotColor(d) {
  const dim = effColorDim(); if (!dim) return IDLE;
  return dim.colors[String(d[dim.field])] || "#888";
}
function recolor() {
  if (filterVal !== null) { applyFilter(filterField, filterVal, false); return; }
  circles.transition().duration(1100).ease(d3.easeCubicInOut)
    .attr("fill", d => dotColor(d)).attr("fill-opacity", 0.88);
}

// ── Legend filter ─────────────────────────────────────────────────────────────
function applyFilter(field, val, updateLegend) {
  filterField = field; filterVal = val;
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => d[field] === val ? dotColor(d) : IDLE)
    .attr("fill-opacity", d => d[field] === val ? 0.92 : 0.10);
  updateColLabels();
  if (updateLegend !== false) refreshLegendFilter();
}
function clearFilter() {
  filterField = null; filterVal = null;
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => dotColor(d))
    .attr("fill-opacity", groupKey ? 0.88 : 0.65);
  updateColLabels();
  refreshLegendFilter();
}
function refreshLegendFilter() {
  legendEl.querySelectorAll(".leg-item").forEach(el => {
    el.classList.toggle("leg-active", filterVal !== null && el.dataset.val === filterVal);
    el.classList.toggle("leg-dimmed", filterVal !== null && el.dataset.val !== filterVal);
  });
}

// ── Legend ───────────────────────────────────────────────────────────────────
function renderLegend() {
  legendEl.innerHTML = "";
  const dim = effColorDim(); if (!dim) return;
  const present = dim.order.filter(v => v !== "—" && nodes.some(d => d[dim.field] === String(v)));
  const total = present.reduce((s, v) => s + nodes.filter(d => d[dim.field] === String(v)).length, 0);
  present.forEach(v => {
    const c = dim.colors[String(v)] || "#888";
    const count = nodes.filter(d => d[dim.field] === String(v)).length;
    const pct = total > 0 ? Math.round(count / total * 100) : 0;
    const el = document.createElement("div");
    el.className = "leg-item";
    el.dataset.val = String(v);
    el.innerHTML = `<div class="leg-sw" style="background:${c}"></div><span>${v}</span><span class="leg-pct">${pct}%</span>`;
    el.addEventListener("click", () => {
      if (filterVal === String(v) && filterField === dim.field) clearFilter();
      else applyFilter(dim.field, String(v));
    });
    legendEl.appendChild(el);
  });
  if (filterField === dim.field) refreshLegendFilter();
}

// ── Narrative ────────────────────────────────────────────────────────────────
function updateNarrative() {
  const n = nodes.length;
  if (!groupKey) { narrativeEl.textContent = `${n} people · click a dimension to explore`; return; }
  const gL = DIM_MAP[groupKey].label;
  if (!colorKey) { narrativeEl.textContent = `${n} people · grouped by ${gL}`; }
  else { narrativeEl.textContent = `${n} people · grouped by ${gL} · coloured by ${DIM_MAP[colorKey].label}`; }
}

// ── Column positions ─────────────────────────────────────────────────────────
function computeColumns(dimKey) {
  const dim = DIM_MAP[dimKey];
  const present = dim.order.filter(v => nodes.some(d => d[dim.field] === String(v)));
  const n = present.length;
  const pad = 55, usable = W - pad * 2;
  return present.map((v, i) => ({
    val: String(v),
    x: n === 1 ? W / 2 : pad + (i / (n - 1)) * usable,
  }));
}

// ── Column detail popup ───────────────────────────────────────────────────────
const colDetailEl = document.getElementById("col-detail");
function showColDetail(colVal, groupDim, effDim, pageX, pageY) {
  const colNodes = nodes.filter(d => d[groupDim.field] === colVal);
  const n = colNodes.length; if (!n) return;
  const breakDim = effDim !== groupDim ? effDim : groupDim;
  const present = breakDim.order.filter(v => v !== "—" && colNodes.some(d => d[breakDim.field] === String(v)));
  const rows = present.map(v => {
    const c = colNodes.filter(d => d[breakDim.field] === String(v)).length;
    const pct = Math.round(c / n * 100);
    const col = breakDim.colors[String(v)] || "#888";
    return `<tr>
      <td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:7px;flex-shrink:0"></span>${v}</td>
      <td class="num">${c}</td><td class="pct">${pct}%</td>
    </tr>`;
  }).join("");
  colDetailEl.innerHTML =
    `<h4>${colVal} <span style="font-weight:400;color:#555">n=${n}</span></h4>` +
    `<table>${rows}</table>` +
    `<div class="close-hint">click anywhere to close</div>`;
  const pw = 240;
  let left = pageX + 14;
  if (left + pw > window.innerWidth - 8) left = pageX - pw - 14;
  colDetailEl.style.left = left + "px";
  colDetailEl.style.display = "block";
  const ph = colDetailEl.offsetHeight;
  let top = pageY - 20;
  if (top + ph > window.innerHeight - 8) top = pageY - ph + 20;
  colDetailEl.style.top = Math.max(8, top) + "px";
}
function hideColDetail() { colDetailEl.style.display = "none"; }
document.addEventListener("click", e => {
  if (!colDetailEl.contains(e.target)) hideColDetail();
});

// ── Column label renderer (filter-aware) ─────────────────────────────────────
let colState = null; // { cols, dim, eff }
function updateColLabels() {
  svg.selectAll(".col-label").remove();
  if (!colState) return;
  const { cols, dim, eff } = colState;
  const pool = (filterVal !== null) ? nodes.filter(d => d[filterField] === filterVal) : nodes;
  const validTotal = cols.filter(({val}) => val !== "—")
    .reduce((s, {val}) => s + pool.filter(d => d[dim.field] === val).length, 0);
  // Column spacing for hit areas
  const spacing = cols.length > 1 ? Math.abs(cols[1].x - cols[0].x) : 120;
  cols.forEach(({val, x}) => {
    const count = pool.filter(d => d[dim.field] === val).length;
    if (val !== "—" && validTotal > 0) {
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
        .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
        .text(Math.round(count/validTotal*100)+"%");
    }
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
      .attr("fill","#4a4a4a").attr("font-size","10px")
      .text("n="+count);
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-28).attr("text-anchor","middle")
      .attr("fill","#999999").attr("font-size","12px")
      .style("cursor","pointer")
      .text(sl(val));
    // Invisible click rect over label area
    svg.append("rect").attr("class","col-label")
      .attr("x", x - spacing * 0.44).attr("y", H - 96)
      .attr("width", spacing * 0.88).attr("height", 80)
      .attr("fill","transparent").style("cursor","pointer")
      .on("click", (event) => {
        event.stopPropagation();
        showColDetail(val, dim, eff || dim, event.pageX, event.pageY);
      });
  });
}

// ── Go (apply grouping) ──────────────────────────────────────────────────────
function go() {
  hideColDetail();
  const cols = computeColumns(groupKey);
  const xFor = Object.fromEntries(cols.map(c => [c.val, c.x]));
  nodes.forEach(d => { d.targetX = xFor[d[DIM_MAP[groupKey].field]] ?? W / 2; });

  sim.force("x").x(d => d.targetX).strength(0.09);
  sim.force("y").y(H * 0.44).strength(0.055);
  sim.alpha(1.0).restart();

  recolor();
  const eff = colorKey ? DIM_MAP[colorKey] : DIM_MAP[groupKey];
  colState = { cols, dim: DIM_MAP[groupKey], eff };
  updateColLabels();
  refreshGroupBtns(); refreshColorBtns(); renderLegend(); updateNarrative();
}

// ── Idle ─────────────────────────────────────────────────────────────────────
function idle() {
  filterField = null; filterVal = null; colState = null;
  nodes.forEach(d => { delete d.targetX; });
  sim.force("x").x(W / 2).strength(0.035);
  sim.force("y").y(H * 0.44).strength(0.035);
  sim.alpha(0.75).restart();
  circles.transition().duration(900).ease(d3.easeCubicInOut)
    .attr("fill", IDLE).attr("fill-opacity", 0.65);
  svg.selectAll(".col-label").remove();
  legendEl.innerHTML = "";
  refreshGroupBtns(); refreshColorBtns(); updateNarrative();
}

// ── Tooltip ──────────────────────────────────────────────────────────────────
function tr(k, v) {
  if (v === null || v === undefined || v === "" || v === "—") return "";
  return `<div class="tt-row"><span class="tt-k">${k}</span><span class="tt-v">${v}</span></div>`;
}
function onHover(event, d) {
  tooltipEl.innerHTML =
    tr("Age", d.age) + tr("City", d.city) + tr("Frequency", d.freq) +
    tr("Attends with", d.t_who) +
    (d.pi_rate  !== "—" ? tr("PI rating",  d.pi_rate  + " / 5") : "") +
    (d.brk_rate !== "—" ? tr("BRK rating", d.brk_rate + " / 5") : "") +
    (d.gog_rate !== "—" ? tr("GoG rating", d.gog_rate + " / 5") : "") +
    tr("PI vs BRK",  d.pi_vs_brk) + tr("BRK vs GoG", d.brk_vs_gog) +
    (d.t_reaction ? tr("Reaction", d.t_reaction.length > 68 ? d.t_reaction.slice(0,68)+"…" : d.t_reaction) : "");
  tooltipEl.style.display = "block";
  d3.select(this).raise().attr("r", R+2.5).attr("stroke","#fff").attr("stroke-width",1.5).attr("fill-opacity",1);
  posTooltip(event);
}
function onLeave() {
  tooltipEl.style.display = "none";
  d3.select(this).attr("r",R).attr("stroke","none").attr("fill-opacity", groupKey ? 0.88 : 0.65);
}
function posTooltip(e) {
  const x = e.clientX + 16, y = e.clientY - 10;
  tooltipEl.style.left = (x + 270 > window.innerWidth ? e.clientX - 282 : x) + "px";
  tooltipEl.style.top  = y + "px";
}
document.addEventListener("mousemove", e => { if (tooltipEl.style.display === "block") posTooltip(e); });

// ── Init ─────────────────────────────────────────────────────────────────────
function init() {
  W = document.getElementById("chart-wrap").clientWidth;
  H = document.getElementById("chart-wrap").clientHeight;
  nodes.forEach(d => {
    d.x = W / 2 + (Math.random() - 0.5) * 150;
    d.y = H * 0.44 + (Math.random() - 0.5) * 110;
  });
  svg.selectAll("*").remove();
  circles = svg.selectAll(".dot").data(nodes).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("fill",IDLE).attr("fill-opacity",0.65).attr("stroke","none")
    .style("cursor","pointer")
    .on("mouseenter", onHover)
    .on("mousemove",  (e) => posTooltip(e))
    .on("mouseleave", onLeave);
  sim.force("x").x(W/2).strength(0.035);
  sim.force("y").y(H*0.44).strength(0.04);
  sim.alpha(0.65).restart();
  updateNarrative();
}

window.addEventListener("resize", () => { init(); if (groupKey) go(); });
setInterval(() => { if (!groupKey && sim.alpha() < 0.04) sim.alpha(0.1).restart(); }, 4500);

buildButtons();
updateNarrative();
requestAnimationFrame(init);
</script>
</body>
</html>
"""


def show_beeswarm(fdf):
    def clean(v):
        return re.sub(r"\*+", "", str(v)).strip() if pd.notna(v) else ""

    def first_rate(row, *indices):
        for i in indices:
            v = row.iloc[i]
            if pd.notna(v):
                try:
                    return int(float(v))
                except (ValueError, TypeError):
                    pass
        return None

    def first_clean(row, *indices):
        for i in indices:
            v = row.iloc[i]
            c = re.sub(r"\*+", "", str(v)).strip() if pd.notna(v) else ""
            if c and c != "nan":
                return c
        return None

    records = []
    for _, row in fdf.iterrows():
        records.append({
            "age":        clean(row.iloc[3]) or "Unknown",
            "city":       str(row["_city"]),
            "freq":       clean(row.iloc[1]) or "Unknown",
            "pi_rate":      first_rate(row, 7),
            "brk_rate":     first_rate(row, 9, 13),
            "brk_pi_rate":  first_rate(row, 9),
            "gog_rate":     first_rate(row, 11),
            "pi_vs_brk":    first_clean(row, 15, 16) or "—",
            "brk_vs_gog":   first_clean(row, 17, 18) or "—",
            "t_who":        clean(row.iloc[2]),
            "t_reaction":   clean(row.iloc[4]),
        })

    html = _BEESWARM_HTML.replace("__DATA__", json.dumps(records))
    components.html(html, height=720, scrolling=False)


# ── Presentation component ────────────────────────────────────────────────────

_PRESENTATION_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0e1117; color: #fafafa; overflow: hidden; height: 100vh; }
#app { display: flex; height: 100vh; }

/* ── Left panel ─────────────────────────────────────────── */
#panel {
  width: 268px; flex-shrink: 0; display: flex; flex-direction: column;
  padding: 28px 24px 18px; border-right: 1px solid #161616; background: #090a0f;
}
#slide-num { font-size: 10px; color: #333; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 22px; flex-shrink: 0; }
#text-wrap { flex: 1; min-height: 0; }
#slide-title { font-size: 21px; font-weight: 600; color: #eee; line-height: 1.2; margin-bottom: 6px; transition: opacity 0.28s ease; }
#slide-sub   { font-size: 11px; color: #484848; margin-bottom: 16px; transition: opacity 0.28s ease; }
#slide-body  { font-size: 13px; color: #757575; line-height: 1.78; transition: opacity 0.28s ease; }

/* ── Explore controls (last slide) ─────────────────────── */
#explore-wrap { display: none; flex: 1; flex-direction: column; gap: 11px; }
.ctrl-row { display: flex; align-items: flex-start; gap: 6px; }
.row-label { font-size: 10px; color: #444; letter-spacing: 0.08em; text-transform: uppercase; width: 50px; flex-shrink: 0; padding-top: 5px; }
.btn-group { display: flex; gap: 5px; flex-wrap: wrap; }
.dim-btn { padding: 3px 10px; border-radius: 12px; border: 1.5px solid #222; background: transparent; color: #666; font-size: 11px; cursor: pointer; transition: border-color 0.15s, color 0.15s, background 0.15s; white-space: nowrap; }
.dim-btn:hover { border-color: #555; color: #bbb; }
.dim-btn.active { border-color: #ccc; color: #fff; background: rgba(255,255,255,0.09); }
.dim-btn.soft   { border-color: #3a3a3a; color: #999; background: rgba(255,255,255,0.03); }
#color-row { display: none; }

/* ── Legend ─────────────────────────────────────────────── */
#legend-area { margin-top: 16px; display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
.leg-item { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #777; cursor: pointer; border-radius: 4px; padding: 2px 4px; transition: background .15s; }
.leg-item:hover { background: #1e1e1e; }
.leg-item.leg-active { background: #222; color: #ddd; }
.leg-item.leg-dimmed { opacity: 0.35; }
.leg-sw { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.leg-pct { margin-left: auto; color: #aaa; font-size: 10px; font-variant-numeric: tabular-nums; }

/* ── Nav ─────────────────────────────────────────────────── */
#nav { display: flex; align-items: center; gap: 10px; padding-top: 14px; margin-top: 14px; border-top: 1px solid #161616; flex-shrink: 0; }
.nav-btn { background: none; border: 1px solid #1e1e1e; border-radius: 5px; color: #404040; font-size: 16px; cursor: pointer; width: 28px; height: 26px; display: flex; align-items: center; justify-content: center; transition: border-color 0.15s, color 0.15s; user-select: none; }
.nav-btn:hover:not([disabled]) { border-color: #666; color: #ccc; }
.nav-btn[disabled] { opacity: 0.15; cursor: default; }
#progress { display: flex; gap: 6px; flex: 1; justify-content: center; align-items: center; }
.pdot { width: 5px; height: 5px; border-radius: 50%; background: #222; cursor: pointer; transition: background 0.25s, transform 0.25s; }
.pdot.on { background: #777; transform: scale(1.35); }

/* ── Chart area ─────────────────────────────────────────── */
#chart-wrap { flex: 1; position: relative; }
svg { width: 100%; height: 100%; overflow: visible; }

/* ── Tooltip ─────────────────────────────────────────────── */
#tooltip { position: fixed; display: none; background: rgba(10,12,20,0.97); border: 1px solid #282828; border-radius: 8px; padding: 10px 14px; font-size: 12px; line-height: 1.85; max-width: 255px; pointer-events: none; z-index: 9999; box-shadow: 0 8px 28px rgba(0,0,0,0.7); }
#col-detail { display: none; position: fixed; background: #141414; border: 1px solid #2a2a2a; border-radius: 8px; padding: 13px 16px; z-index: 9998; min-width: 200px; max-width: 280px; max-height: 80vh; overflow-y: auto; box-shadow: 0 6px 24px rgba(0,0,0,0.7); font-size: 11px; color: #bbb; }
#col-detail h4 { margin: 0 0 10px; font-size: 12px; color: #fff; font-weight: 600; }
#col-detail table { border-collapse: collapse; width: 100%; }
#col-detail td { padding: 3px 0; vertical-align: middle; }
#col-detail td.num { text-align: right; padding-left: 12px; font-variant-numeric: tabular-nums; }
#col-detail td.pct { text-align: right; padding-left: 6px; color: #555; font-variant-numeric: tabular-nums; }
#col-detail .close-hint { margin-top: 10px; font-size: 10px; color: #444; text-align: right; }
.tt-row { display: flex; gap: 8px; }
.tt-k { color: #555; min-width: 78px; flex-shrink: 0; font-size: 11px; }
.tt-v { color: #ddd; }
</style>
</head>
<body>
<div id="app">
  <div id="panel">
    <div id="slide-num"></div>
    <div id="text-wrap">
      <div id="slide-title"></div>
      <div id="slide-sub"></div>
      <div id="slide-body"></div>
    </div>
    <div id="explore-wrap">
      <div class="ctrl-row">
        <span class="row-label">Group</span>
        <div class="btn-group" id="group-btns"></div>
      </div>
      <div class="ctrl-row" id="color-row">
        <span class="row-label">Colour</span>
        <div class="btn-group" id="color-btns"></div>
      </div>
    </div>
    <div id="legend-area"></div>
    <div id="nav">
      <button class="nav-btn" id="prev-btn">&#8592;</button>
      <div id="progress"></div>
      <button class="nav-btn" id="next-btn">&#8594;</button>
    </div>
  </div>
  <div id="chart-wrap"><svg id="chart"></svg></div>
</div>
<div id="tooltip"></div>
<div id="col-detail"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const RAW = __DATA__;

// ── Slides ───────────────────────────────────────────────────────────────────
const SLIDES = [
  {
    title: "258 people",
    sub: "6 cities · does the name get in the way?",
    body: "Experience-goers across New York, Los Angeles, Chicago, Denver, Dallas and Cincinnati were shown the Prison Island concept and asked to rate it — then compare it against an alternative name. Each dot is one person.",
    group: null, color: "city",
  },
  {
    title: "Where they're from",
    sub: "No single market dominates",
    body: "Chicago leads the sample, with Denver and Los Angeles close behind. The spread matters: this is not a coastal read or a Midwest read. It is a broad, multi-market picture.",
    group: "city", color: "age",
  },
  {
    title: "Who they are",
    sub: "Coloured by how they voted in the head-to-head",
    body: "The 35–44 band is the largest group — and the core audience for an experience like this. They are regular concert-goers, cinema-goers, escape room players. The name lands with people who already buy this kind of thing.",
    group: "age", color: "pi_vs_brk",
  },
  {
    title: "First impressions",
    sub: "Likelihood to attend, rated 1–5 · separate groups · no comparison yet",
    body: "Each group saw only one name, cold. Prison Island and BRKThrough both land around 3 out of 5. Neither name excites. Neither name repels. The starting point is the same.",
    dual: { left:"brk_pi_rate", leftLabel:"BRKThrough", right:"pi_rate", rightLabel:"Prison Island" },
  },
  {
    title: "Head to head",
    sub: "After seeing both names",
    body: "45% call it a draw. 29% lean Prison Island. 26% lean BRKThrough. No name generates a runaway lead. No name generates a backlash. The split is as close to a tie as survey data gets.",
    group: "pi_vs_brk", color: null,
  },
  {
    title: "The age cut",
    sub: "Does preference shift by generation?",
    body: "The 35–44 cohort — the biggest group, the target audience — leans toward Prison Island when forced to choose. Younger respondents tilt slightly toward BRKThrough. The differences are real but not dramatic. No age group is a dealbreaker for either name.",
    group: "age", color: "pi_vs_brk",
  },
  {
    title: "The verdict",
    sub: "No case against Prison Island",
    body: "The name does not get in the way. Tested cold against a purpose-built alternative, Prison Island held its ground. No city turned against it. No age group rejected it. The core audience leans its way. Renaming carries cost and uncertainty — this data does not justify either. A deeper probe may yet change the picture. But on this evidence: run as Prison Island.",
    group: null, color: "pi_vs_brk",
  },
  {
    title: "Explore the data",
    sub: "Controls now live",
    body: "Group and colour the 258 dots however you like.",
    group: null, color: null, free: true,
  },
];

// ── Colour / dimension config ────────────────────────────────────────────────
const AGE_ORDER     = ["18-24","25-34","35-44","45-54","55-64","65-74","75-84","Skip question","Unknown"];
const CITY_ORDER    = ["New York","Los Angeles","Chicago","Denver","Dallas","Cincinnati","Unknown"];
const FREQ_ORDER    = ["More than once a week","Once a week","Every other week","Once or twice a month","Every other month","Once or twice a year","Less than that","Unknown"];
const RATE_ORDER    = ["1","2","3","4","5","—"];
const PI_BRK_ORDER  = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Prison Island is slightly better","Prison Island is much better","—"];
const BRK_GOG_ORDER = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Glow or Go is slightly better","Glow or Go is much better","—"];

const SHORT = {
  "More than once a week":">1/wk","Once a week":"1/wk","Every other week":"2x/mo",
  "Once or twice a month":"1–2/mo","Every other month":"1–2/6mo",
  "Once or twice a year":"1–2/yr","Less than that":"<1/yr",
  "BRKThrough is much better":"BRK ↑↑","BRKThrough is slightly better":"BRK ↑",
  "They're about the same":"≈ same",
  "Prison Island is slightly better":"PI ↑","Prison Island is much better":"PI ↑↑",
  "Glow or Go is slightly better":"GoG ↑","Glow or Go is much better":"GoG ↑↑",
};
const sl = v => SHORT[v] || v;

const COLORS = {
  age:      {"18-24":"#FF4444","25-34":"#FF7722","35-44":"#FFCC00","45-54":"#88CC00","55-64":"#00BBAA","65-74":"#4488FF","75-84":"#9966FF","Skip question":"#555","Unknown":"#555"},
  city:     {"New York":"#2196F3","Los Angeles":"#FF9800","Chicago":"#4CAF50","Denver":"#9C27B0","Dallas":"#F44336","Cincinnati":"#00BCD4","Unknown":"#9E9E9E"},
  freq:     {"More than once a week":"#FF4444","Once a week":"#FF7722","Every other week":"#FFCC00","Once or twice a month":"#88CC44","Every other month":"#44BBAA","Once or twice a year":"#4488FF","Less than that":"#9966FF","Unknown":"#555"},
  rating:   {"1":"#E74C3C","2":"#E67E22","3":"#F1C40F","4":"#2ECC71","5":"#16A085","—":"#1e1e1e"},
  pi_vs_brk:  {"BRKThrough is much better":"#4C6EF5","BRKThrough is slightly better":"#8FA8FF","They're about the same":"#666","Prison Island is slightly better":"#FFAA66","Prison Island is much better":"#E8630A","—":"#1e1e1e"},
  brk_vs_gog: {"BRKThrough is much better":"#4C6EF5","BRKThrough is slightly better":"#8FA8FF","They're about the same":"#666","Glow or Go is slightly better":"#FF77AA","Glow or Go is much better":"#E91E8C","—":"#1e1e1e"},
};

const DIMS = [
  {key:"age",       label:"Age",        field:"age",       order:AGE_ORDER,     colors:COLORS.age},
  {key:"city",      label:"City",       field:"city",      order:CITY_ORDER,    colors:COLORS.city},
  {key:"freq",      label:"Frequency",  field:"freq",      order:FREQ_ORDER,    colors:COLORS.freq},
  {key:"pi_rate",   label:"PI rating",  field:"pi_rate",   order:RATE_ORDER,    colors:COLORS.rating},
  {key:"brk_rate",  label:"BRK rating", field:"brk_rate",  order:RATE_ORDER,    colors:COLORS.rating},
  {key:"gog_rate",  label:"GoG rating", field:"gog_rate",  order:RATE_ORDER,    colors:COLORS.rating},
  {key:"pi_vs_brk", label:"PI vs BRK",  field:"pi_vs_brk", order:PI_BRK_ORDER,  colors:COLORS.pi_vs_brk},
  {key:"brk_vs_gog",label:"BRK vs GoG", field:"brk_vs_gog",order:BRK_GOG_ORDER, colors:COLORS.brk_vs_gog},
];
const DIM_MAP = Object.fromEntries(DIMS.map(d => [d.key, d]));

RAW.forEach(d => {
  ["pi_rate","brk_rate","brk_pi_rate","gog_rate"].forEach(f => { d[f] = d[f]===null ? "—" : String(d[f]); });
  ["pi_vs_brk","brk_vs_gog"].forEach(f => { if (!d[f]||d[f]==="nan") d[f]="—"; });
  if (!d.freq||d.freq==="nan") d.freq="Unknown";
});

// ── Force simulation ─────────────────────────────────────────────────────────
const R = 5.5, IDLE_C = "#383838";
const nodes = RAW.map((d,i) => Object.assign({x:0,y:0,vx:0,vy:0},d,{_i:i}));
let W, H, circles, groupKey=null, colorKey=null;
let filterField=null, filterVal=null;

const svg       = d3.select("#chart");
const tooltipEl = document.getElementById("tooltip");
const legendEl  = document.getElementById("legend-area");

const sim = d3.forceSimulation(nodes)
  .force("collide", d3.forceCollide(R+1.8).strength(0.8).iterations(2))
  .force("x", d3.forceX(0).strength(0.04))
  .force("y", d3.forceY(0).strength(0.04))
  .alphaDecay(0.011).velocityDecay(0.30)
  .on("tick", () => circles.attr("cx", d=>d.x).attr("cy", d=>d.y));

function initChart() {
  W = document.getElementById("chart-wrap").clientWidth;
  H = document.getElementById("chart-wrap").clientHeight;
  nodes.forEach(d => {
    d.x = W/2 + (Math.random()-.5)*160;
    d.y = H*.44 + (Math.random()-.5)*120;
  });
  svg.selectAll("*").remove();
  circles = svg.selectAll(".dot").data(nodes).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("fill",IDLE_C).attr("fill-opacity",0.62).attr("stroke","none")
    .style("cursor","pointer")
    .on("mouseenter",onHover).on("mousemove",e=>posTooltip(e)).on("mouseleave",onLeave);
  sim.force("x").x(W/2).strength(0.04);
  sim.force("y").y(H*.44).strength(0.04);
  sim.alpha(0.75).restart();
}

// ── Dual-beeswarm state ──────────────────────────────────────────────────────
let dualSim = null;

function teardownDual() {
  if (dualSim) { dualSim.stop(); dualSim = null; }
  // Rebind circles to original nodes
  circles = svg.selectAll(".dot").data(nodes).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("fill",IDLE_C).attr("fill-opacity",0.62).attr("stroke","none")
    .style("cursor","pointer")
    .on("mouseenter",onHover).on("mousemove",e=>posTooltip(e)).on("mouseleave",onLeave);
  sim.on("tick", () => circles.attr("cx", d=>d.x).attr("cy", d=>d.y));
}

function goDual(leftField, leftLabel, rightField, rightLabel, filterField) {
  groupKey = null; colorKey = null;
  if (!W) return;
  if (dualSim) { dualSim.stop(); dualSim = null; }
  svg.selectAll(".col-label").remove();
  legendEl.innerHTML = "";

  const gap = 32, pad = 48;
  const midX = W / 2;
  const RATE_VALS = ["1","2","3","4","5"];

  // If filterField is set, only include respondents who have data for that field
  const pool = filterField ? nodes.filter(d => d[filterField] !== "—") : nodes;

  // Virtual nodes: one copy per panel per respondent (if they have data)
  const leftVNodes = pool.filter(d => d[leftField] !== "—")
    .map(d => Object.assign({}, d, {vx:0, vy:0, _vfield: leftField, _vval: d[leftField], _vlabel: leftLabel}));
  const rightVNodes = pool.filter(d => d[rightField] !== "—")
    .map(d => Object.assign({}, d, {vx:0, vy:0, _vfield: rightField, _vval: d[rightField], _vlabel: rightLabel}));

  const allV = [...leftVNodes, ...rightVNodes];

  // X positions within each half
  const leftUsable  = midX - gap/2 - pad;
  const rightUsable = W - (midX + gap/2) - pad;

  const leftPresent  = RATE_VALS.filter(v => leftVNodes.some(d => d._vval === v));
  const rightPresent = RATE_VALS.filter(v => rightVNodes.some(d => d._vval === v));

  const lXFor = Object.fromEntries(leftPresent.map((v,i) =>
    [v, pad + (leftPresent.length === 1 ? leftUsable/2 : (i/(leftPresent.length-1))*leftUsable)]));
  const rXFor = Object.fromEntries(rightPresent.map((v,i) =>
    [v, midX + gap/2 + pad + (rightPresent.length === 1 ? rightUsable/2 : (i/(rightPresent.length-1))*rightUsable)]));

  allV.forEach(d => {
    const xFor = d._vlabel === leftLabel ? lXFor : rXFor;
    d.tx = xFor[d._vval] ?? W/2;
    d.x  = d.tx + (Math.random()-.5)*20;
    d.y  = H*.44 + (Math.random()-.5)*60;
  });

  // New circles for virtual nodes
  svg.selectAll(".dot").remove();
  const dualCircles = svg.selectAll(".dot").data(allV).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("cx", d => d.x).attr("cy", d => d.y)
    .attr("fill", d => COLORS.rating[d._vval] || "#888").attr("fill-opacity",0.85)
    .attr("stroke","none").style("cursor","pointer")
    .on("mouseenter", function(event, d) {
      tooltipEl.innerHTML =
        tr("Name", d._vlabel) +
        tr("Rating", d._vval + "/5") +
        tr("Age",d.age)+tr("City",d.city)+tr("Frequency",d.freq)+
        tr("PI vs BRK",d.pi_vs_brk);
      tooltipEl.style.display="block";
      d3.select(this).raise().attr("r",R+2.5).attr("stroke","#fff").attr("stroke-width",1.5).attr("fill-opacity",1);
      posTooltip(event);
    })
    .on("mousemove",e=>posTooltip(e))
    .on("mouseleave", function() {
      tooltipEl.style.display="none";
      d3.select(this).attr("r",R).attr("stroke","none").attr("fill-opacity",0.85);
    });

  dualSim = d3.forceSimulation(allV)
    .force("collide", d3.forceCollide(R+1.8).strength(0.8).iterations(2))
    .force("x", d3.forceX(d => d.tx).strength(0.09))
    .force("y", d3.forceY(H*.44).strength(0.055))
    .alphaDecay(0.011).velocityDecay(0.30)
    .on("tick", () => dualCircles.attr("cx", d=>d.x).attr("cy", d=>d.y));
  dualSim.alpha(1.0).restart();

  // Data labels for both panels
  [[leftPresent, lXFor, leftVNodes, leftLabel],[rightPresent, rXFor, rightVNodes, rightLabel]].forEach(([present, xFor, vNodes, lbl]) => {
    const validTotal = present.filter(v => v!=="—").reduce((s,v) => s+(vNodes.filter(d=>d._vval===v).length), 0);
    present.forEach(v => {
      const x = xFor[v];
      const count = vNodes.filter(d => d._vval === v).length;
      if (v !== "—" && validTotal > 0) {
        svg.append("text").attr("class","col-label")
          .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
          .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
          .text(Math.round(count/validTotal*100)+"%");
      }
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
        .attr("fill","#4a4a4a").attr("font-size","10px")
        .text("n="+count);
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-28).attr("text-anchor","middle")
        .attr("fill","#999999").attr("font-size","12px")
        .text(v);
    });
    // Panel header
    svg.append("text").attr("class","col-label")
      .attr("x", present.length > 1 ? (xFor[present[0]] + xFor[present[present.length-1]]) / 2 : xFor[present[0]])
      .attr("y", H-88).attr("text-anchor","middle")
      .attr("fill","#ffffff").attr("font-size","13px").attr("font-weight","700")
      .text(lbl);
  });

  // Divider line
  svg.append("line").attr("class","col-label")
    .attr("x1", midX).attr("x2", midX).attr("y1", 20).attr("y2", H-16)
    .attr("stroke","#333").attr("stroke-width",1).attr("stroke-dasharray","4,4");

  // Legend: rating scale
  renderLegend(DIM_MAP["pi_rate"]);
  // Prepend scale anchor labels
  const hdr = document.createElement("div");
  hdr.style.cssText = "font-size:10px;color:#666;margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase";
  hdr.textContent = "1 = not likely · 5 = very likely";
  legendEl.insertBefore(hdr, legendEl.firstChild);
}

// ── Column detail popup ───────────────────────────────────────────────────────
const colDetailEl = document.getElementById("col-detail");
function showColDetail(colVal, groupDim, effDim, pageX, pageY) {
  const colNodes = nodes.filter(d => d[groupDim.field] === colVal);
  const n = colNodes.length; if (!n) return;
  const breakDim = effDim !== groupDim ? effDim : groupDim;
  const present = breakDim.order.filter(v => v !== "—" && colNodes.some(d => d[breakDim.field] === String(v)));
  const rows = present.map(v => {
    const c = colNodes.filter(d => d[breakDim.field] === String(v)).length;
    const pct = Math.round(c / n * 100);
    const col = breakDim.colors[String(v)] || "#888";
    return `<tr>
      <td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:7px"></span>${v}</td>
      <td class="num">${c}</td><td class="pct">${pct}%</td>
    </tr>`;
  }).join("");
  colDetailEl.innerHTML =
    `<h4>${colVal} <span style="font-weight:400;color:#555">n=${n}</span></h4>` +
    `<table>${rows}</table>` +
    `<div class="close-hint">click anywhere to close</div>`;
  const pw = 240;
  let left = pageX + 14;
  if (left + pw > window.innerWidth - 8) left = pageX - pw - 14;
  colDetailEl.style.left = left + "px";
  colDetailEl.style.display = "block";
  const ph = colDetailEl.offsetHeight;
  let top = pageY - 20;
  if (top + ph > window.innerHeight - 8) top = pageY - ph + 20;
  colDetailEl.style.top = Math.max(8, top) + "px";
}
function hideColDetail() { colDetailEl.style.display = "none"; }
document.addEventListener("click", e => { if (!colDetailEl.contains(e.target)) hideColDetail(); });

// ── Column label renderer (filter-aware) ─────────────────────────────────────
let colState = null;
function updateColLabels() {
  svg.selectAll(".col-label").remove();
  if (!colState) return;
  const { cols, dim, eff } = colState;
  const pool = (filterVal !== null) ? nodes.filter(d => d[filterField] === filterVal) : nodes;
  const validTotal = cols.filter(({val}) => val !== "—")
    .reduce((s, {val}) => s + pool.filter(d => d[dim.field] === val).length, 0);
  const spacing = cols.length > 1 ? Math.abs(cols[1].x - cols[0].x) : 120;
  cols.forEach(({val, x}) => {
    const count = pool.filter(d => d[dim.field] === val).length;
    if (val !== "—" && validTotal > 0) {
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
        .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
        .text(Math.round(count/validTotal*100)+"%");
    }
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
      .attr("fill","#4a4a4a").attr("font-size","10px")
      .text("n="+count);
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-28).attr("text-anchor","middle")
      .attr("fill","#999999").attr("font-size","12px")
      .style("cursor","pointer")
      .text(sl(val));
    svg.append("rect").attr("class","col-label")
      .attr("x", x - spacing*0.44).attr("y", H-96)
      .attr("width", spacing*0.88).attr("height", 80)
      .attr("fill","transparent").style("cursor","pointer")
      .on("click", (event) => {
        event.stopPropagation();
        showColDetail(val, dim, eff||dim, event.pageX, event.pageY);
      });
  });
}

// ── Beeswarm go / idle ───────────────────────────────────────────────────────
function go(gKey, cKey) {
  if (dualSim) teardownDual();
  hideColDetail();
  groupKey = gKey; colorKey = cKey || null;
  if (!W) return;
  const dim = DIM_MAP[gKey];
  const present = dim.order.filter(v => nodes.some(d => d[dim.field]===String(v)));
  const n = present.length, pad=55, usable=W-pad*2;
  const xFor = Object.fromEntries(present.map((v,i) => [String(v), n===1?W/2:pad+(i/(n-1))*usable]));
  nodes.forEach(d => { d.tx = xFor[d[dim.field]] ?? W/2; });
  sim.force("x").x(d=>d.tx).strength(0.09);
  sim.force("y").y(H*.44).strength(0.055);
  sim.alpha(1.0).restart();
  const eff = DIM_MAP[colorKey] || dim;
  circles.transition().duration(1100).ease(d3.easeCubicInOut)
    .attr("fill", d => eff.colors[d[eff.field]] || "#888").attr("fill-opacity",0.88);
  colState = { cols: present.map((v,i) => ({ val: String(v), x: n===1?W/2:pad+(i/(n-1))*usable })), dim, eff };
  updateColLabels();
  renderLegend(eff);
}

function idle(cKey) {
  if (dualSim) teardownDual();
  groupKey=null; colorKey=cKey||null; colState=null;
  nodes.forEach(d=>{ delete d.tx; });
  sim.force("x").x(W/2).strength(0.035);
  sim.force("y").y(H*.44).strength(0.035);
  sim.alpha(0.75).restart();
  const dim = cKey ? DIM_MAP[cKey] : null;
  circles.transition().duration(900).ease(d3.easeCubicInOut)
    .attr("fill", dim ? d => (dim.colors[d[dim.field]] || "#888") : IDLE_C)
    .attr("fill-opacity", dim ? 0.82 : 0.62);
  svg.selectAll(".col-label").remove();
  if (dim) renderLegend(dim); else legendEl.innerHTML="";
}

// ── Legend filter ────────────────────────────────────────────────────────────
function applyFilter(field, val, updateLegend) {
  filterField=field; filterVal=val;
  const eff = colorKey ? DIM_MAP[colorKey] : (groupKey ? DIM_MAP[groupKey] : null);
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => d[field]===val ? (eff ? eff.colors[d[eff.field]]||"#888" : "#888") : IDLE_C)
    .attr("fill-opacity", d => d[field]===val ? 0.92 : 0.10);
  updateColLabels();
  if (updateLegend!==false) refreshLegendFilter();
}
function clearFilter() {
  filterField=null; filterVal=null;
  const eff = colorKey ? DIM_MAP[colorKey] : (groupKey ? DIM_MAP[groupKey] : null);
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => eff ? eff.colors[d[eff.field]]||"#888" : IDLE_C)
    .attr("fill-opacity", groupKey ? 0.88 : 0.62);
  updateColLabels();
  refreshLegendFilter();
}
function refreshLegendFilter() {
  legendEl.querySelectorAll(".leg-item").forEach(el=>{
    el.classList.toggle("leg-active", filterVal!==null && el.dataset.val===filterVal);
    el.classList.toggle("leg-dimmed", filterVal!==null && el.dataset.val!==filterVal);
  });
}

function renderLegend(dim) {
  legendEl.innerHTML="";
  const present = dim.order.filter(v=>v!=="—"&&nodes.some(d=>d[dim.field]===String(v)));
  const total = present.reduce((s,v)=>s+nodes.filter(d=>d[dim.field]===String(v)).length, 0);
  present.forEach(v=>{
    const count = nodes.filter(d=>d[dim.field]===String(v)).length;
    const pct = total>0 ? Math.round(count/total*100) : 0;
    const el=document.createElement("div"); el.className="leg-item";
    el.dataset.val=String(v);
    el.innerHTML=`<div class="leg-sw" style="background:${dim.colors[String(v)]||'#888'}"></div><span>${v}</span><span class="leg-pct">${pct}%</span>`;
    el.addEventListener("click",()=>{
      if(filterVal===String(v)&&filterField===dim.field) clearFilter();
      else applyFilter(dim.field, String(v));
    });
    legendEl.appendChild(el);
  });
  if(filterField===dim.field) refreshLegendFilter();
}

// ── Tooltip ──────────────────────────────────────────────────────────────────
function tr(k,v) {
  if(!v||v==="—") return "";
  return `<div class="tt-row"><span class="tt-k">${k}</span><span class="tt-v">${v}</span></div>`;
}
function onHover(event,d) {
  tooltipEl.innerHTML =
    tr("Age",d.age)+tr("City",d.city)+tr("Frequency",d.freq)+tr("Attends with",d.t_who)+
    (d.pi_rate!=="—"?tr("PI rating",d.pi_rate+"/5"):"")+
    (d.brk_rate!=="—"?tr("BRK rating",d.brk_rate+"/5"):"")+
    tr("PI vs BRK",d.pi_vs_brk)+tr("BRK vs GoG",d.brk_vs_gog)+
    (d.t_reaction?tr("Reaction",d.t_reaction.length>65?d.t_reaction.slice(0,65)+"…":d.t_reaction):"");
  tooltipEl.style.display="block";
  d3.select(this).raise().attr("r",R+2.5).attr("stroke","#fff").attr("stroke-width",1.5).attr("fill-opacity",1);
  posTooltip(event);
}
function onLeave() {
  tooltipEl.style.display="none";
  d3.select(this).attr("r",R).attr("stroke","none").attr("fill-opacity",groupKey?0.88:0.62);
}
function posTooltip(e) {
  const x=e.clientX+16, y=e.clientY-10;
  tooltipEl.style.left=(x+265>window.innerWidth?e.clientX-275:x)+"px";
  tooltipEl.style.top=y+"px";
}
document.addEventListener("mousemove",e=>{ if(tooltipEl.style.display==="block") posTooltip(e); });

// ── Free-explore buttons ─────────────────────────────────────────────────────
let expGroup=null, expColor=null;
function buildExpButtons() {
  const gW=document.getElementById("group-btns"), cW=document.getElementById("color-btns");
  DIMS.forEach(d=>{
    [gW,cW].forEach(wrap=>{
      const b=document.createElement("button");
      b.className="dim-btn"; b.textContent=d.label; b.dataset.key=d.key;
      wrap.appendChild(b);
    });
  });
  gW.addEventListener("click",e=>{
    const b=e.target.closest(".dim-btn"); if(!b) return;
    const k=b.dataset.key;
    if(expGroup===k){expGroup=null;expColor=null;idle();}
    else{expGroup=k;expColor=null;go(k,null);}
    refreshExpBtns();
  });
  cW.addEventListener("click",e=>{
    const b=e.target.closest(".dim-btn"); if(!b) return;
    expColor=(b.dataset.key===expGroup)?null:b.dataset.key;
    go(expGroup,expColor);
    refreshExpBtns();
  });
}
function refreshExpBtns() {
  document.querySelectorAll("#group-btns .dim-btn").forEach(b=>b.classList.toggle("active",b.dataset.key===expGroup));
  document.getElementById("color-row").style.display=expGroup?"flex":"none";
  const eff=expColor||expGroup;
  document.querySelectorAll("#color-btns .dim-btn").forEach(b=>{
    b.classList.toggle("active",b.dataset.key===eff&&expColor!==null);
    b.classList.toggle("soft",  b.dataset.key===eff&&expColor===null);
  });
}

// ── Slide engine ─────────────────────────────────────────────────────────────
let current=0;
const TOTAL=SLIDES.length;

function showSlide(idx) {
  filterField=null; filterVal=null;
  current=Math.max(0,Math.min(TOTAL-1,idx));
  const s=SLIDES[current];
  document.getElementById("slide-num").textContent=`${current+1} / ${TOTAL}`;

  const tw=document.getElementById("text-wrap");
  const ew=document.getElementById("explore-wrap");

  if (s.free) {
    tw.style.display="none";
    ew.style.display="flex";
    if(expGroup) go(expGroup,expColor); else idle();
    refreshExpBtns();
  } else {
    tw.style.display="block";
    ew.style.display="none";
    // Fade text out → update → fade in
    ["slide-title","slide-sub","slide-body"].forEach(id=>{ document.getElementById(id).style.opacity="0"; });
    setTimeout(()=>{
      document.getElementById("slide-title").textContent=s.title;
      const subEl=document.getElementById("slide-sub");
      subEl.textContent=s.sub||""; subEl.style.display=s.sub?"":"none";
      document.getElementById("slide-body").textContent=s.body||"";
      ["slide-title","slide-sub","slide-body"].forEach(id=>{ document.getElementById(id).style.opacity="1"; });
    }, 280);
    if(s.dual) goDual(s.dual.left, s.dual.leftLabel, s.dual.right, s.dual.rightLabel, s.dual.filterField||null);
    else if(s.group) go(s.group, s.color||null);
    else idle(s.color||null);
  }

  document.getElementById("prev-btn").disabled=(current===0);
  document.getElementById("next-btn").disabled=(current===TOTAL-1);
  document.querySelectorAll(".pdot").forEach((d,i)=>d.classList.toggle("on",i===current));
}

function nav(dir) {
  if(dir===-1&&current>0) showSlide(current-1);
  if(dir===1&&current<TOTAL-1) showSlide(current+1);
}

function buildProgress() {
  const prog=document.getElementById("progress");
  SLIDES.forEach((_,i)=>{
    const d=document.createElement("div"); d.className="pdot";
    d.onclick=()=>showSlide(i); prog.appendChild(d);
  });
}

document.getElementById("prev-btn").onclick=()=>nav(-1);
document.getElementById("next-btn").onclick=()=>nav(1);
document.addEventListener("keydown",e=>{
  if(e.key==="ArrowRight"||e.key==="ArrowDown") nav(1);
  if(e.key==="ArrowLeft"||e.key==="ArrowUp") nav(-1);
});

// ── Boot ─────────────────────────────────────────────────────────────────────
window.addEventListener("resize",()=>{
  initChart();
  const s=SLIDES[current];
  if(s.dual) goDual(s.dual.left,s.dual.leftLabel,s.dual.right,s.dual.rightLabel,s.dual.filterField||null);
  else if(s.group) go(s.group,s.color||null);
  else idle(s.color||null);
});
setInterval(()=>{ if(!groupKey&&sim.alpha()<0.04) sim.alpha(0.1).restart(); },4500);

buildExpButtons();
buildProgress();
requestAnimationFrame(()=>{ initChart(); showSlide(0); });
</script>
</body>
</html>
"""


def show_presentation(fdf):
    def clean(v):
        return re.sub(r"\*+", "", str(v)).strip() if pd.notna(v) else ""

    def first_rate(row, *indices):
        for i in indices:
            v = row.iloc[i]
            if pd.notna(v):
                try:
                    return int(float(v))
                except (ValueError, TypeError):
                    pass
        return None

    def first_clean(row, *indices):
        for i in indices:
            v = row.iloc[i]
            c = re.sub(r"\*+", "", str(v)).strip() if pd.notna(v) else ""
            if c and c != "nan":
                return c
        return None

    records = []
    for _, row in fdf.iterrows():
        records.append({
            "age":        clean(row.iloc[3]) or "Unknown",
            "city":       str(row["_city"]),
            "freq":       clean(row.iloc[1]) or "Unknown",
            "pi_rate":      first_rate(row, 7),
            "brk_rate":     first_rate(row, 9, 13),
            "brk_pi_rate":  first_rate(row, 9),
            "gog_rate":     first_rate(row, 11),
            "pi_vs_brk":    first_clean(row, 15, 16) or "—",
            "brk_vs_gog":   first_clean(row, 17, 18) or "—",
            "t_who":        clean(row.iloc[2]),
            "t_reaction":   clean(row.iloc[4]),
        })

    html = _PRESENTATION_HTML.replace("__DATA__", json.dumps(records))
    components.html(html, height=730, scrolling=False)


# ── Overview chart functions ──────────────────────────────────────────────────

def bar_chart(series, title, use_pct, note=None, order=None):
    counts = series.dropna().replace("", pd.NA).dropna()
    is_multi = counts.str.contains(",").any()
    n_respondents = len(counts)
    if is_multi:
        counts = counts.str.split(",").explode().str.strip()
    counts = counts.value_counts().reset_index()
    counts.columns = ["Response", "Count"]
    if order:
        counts["Response"] = pd.Categorical(counts["Response"], categories=order, ordered=True)
        counts = counts.sort_values("Response")
    base = n_respondents if is_multi else counts["Count"].sum()

    if use_pct:
        counts["Value"] = (counts["Count"] / base * 100).round(1)
        y_label = "% of respondents"
        text_vals = counts["Value"].apply(lambda v: f"{v:.1f}%")
    else:
        counts["Value"] = counts["Count"]
        y_label = "Count"
        text_vals = counts["Value"]

    full_title = f"{title} (n={base})"
    if note:
        full_title += f"  —  {note}"

    cat_order = {"Response": order} if order else {}
    fig = px.bar(counts, x="Response", y="Value", title=full_title,
                 text=text_vals, color_discrete_sequence=["#4C6EF5"],
                 category_orders=cat_order)
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title=y_label,
                      title_font_size=14, margin=dict(t=60, b=40),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def rating_chart(series_list, labels, title, use_pct, scale_labels=None):
    default_scale = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
    scale = scale_labels or default_scale
    ordered_ticks = [scale[i] for i in [1, 2, 3, 4, 5]]

    frames = []
    for s, label in zip(series_list, labels):
        clean = pd.to_numeric(s.dropna().replace("", pd.NA).dropna(), errors="coerce").dropna().astype(int)
        base = len(clean)
        counts = clean.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0).reset_index()
        counts.columns = ["Response", "Count"]
        counts["Response"] = counts["Response"].map(scale)
        counts["Name"] = label
        counts["Base"] = base
        frames.append(counts)
    combined = pd.concat(frames)

    if use_pct:
        combined["Value"] = (combined["Count"] / combined["Base"] * 100).round(1)
        y_label = "% of respondents"
        combined["TextVal"] = combined["Value"].apply(lambda v: f"{v:.1f}%")
    else:
        combined["Value"] = combined["Count"]
        y_label = "Count"
        combined["TextVal"] = combined["Value"]

    n_label = "  |  ".join(f"{l}: n={combined[combined['Name']==l]['Base'].iloc[0]}" for l in labels)
    fig = px.bar(combined, x="Response", y="Value", color="Name", barmode="group",
                 title=f"{title}  ({n_label})", text="TextVal",
                 color_discrete_map=name_color_map(labels),
                 category_orders={"Response": ordered_ticks})
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=100),
                      xaxis=dict(type="category", tickangle=-20),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def audience_chart(series_list, labels, title, use_pct):
    frames = []
    for s, label in zip(series_list, labels):
        clean = s.dropna().replace("", pd.NA).dropna()
        base = len(clean)
        counts = clean.str.split(",").explode().str.strip().value_counts().reset_index()
        counts.columns = ["Response", "Count"]
        counts["Name"] = label
        counts["Base"] = base
        frames.append(counts)
    combined = pd.concat(frames)

    if use_pct:
        combined["Value"] = (combined["Count"] / combined["Base"] * 100).round(1)
        y_label = "% of respondents"
        combined["TextVal"] = combined["Value"].apply(lambda v: f"{v:.1f}%")
    else:
        combined["Value"] = combined["Count"]
        y_label = "Count"
        combined["TextVal"] = combined["Value"]

    n_label = "  |  ".join(f"{l}: n={combined[combined['Name']==l]['Base'].iloc[0]}" for l in labels)
    fig = px.bar(combined, x="Response", y="Value", color="Name", barmode="group",
                 title=f"{title}  ({n_label})", text="TextVal",
                 color_discrete_map=name_color_map(labels))
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=40),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def price_chart(series_list, labels, title, use_pct):
    frames = []
    for s, label in zip(series_list, labels):
        clean = pd.to_numeric(s.dropna().replace("", pd.NA).dropna(), errors="coerce").dropna()
        base = len(clean)
        counts = clean.value_counts().reset_index()
        counts.columns = ["Response", "Count"]
        counts["Name"] = label
        counts["Base"] = base
        frames.append(counts)
    combined = pd.concat(frames)
    combined["Response"] = combined["Response"].astype(int)
    combined = combined.sort_values("Response")

    if use_pct:
        combined["Value"] = (combined["Count"] / combined["Base"] * 100).round(1)
        y_label = "% of respondents"
        combined["TextVal"] = combined["Value"].apply(lambda v: f"{v:.1f}%")
    else:
        combined["Value"] = combined["Count"]
        y_label = "Count"
        combined["TextVal"] = combined["Value"]

    n_label = "  |  ".join(f"{l}: n={combined[combined['Name']==l]['Base'].iloc[0]}" for l in labels)
    fig = px.bar(combined, x="Response", y="Value", color="Name", barmode="group",
                 title=f"{title}  ({n_label})", text="TextVal",
                 color_discrete_map=name_color_map(labels))
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Price ($)", yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=40),
                      xaxis=dict(type="category"),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def price_summary(series_list, labels):
    cols = st.columns(len(labels))
    for col, s, label in zip(cols, series_list, labels):
        clean = pd.to_numeric(s.dropna().replace("", pd.NA).dropna(), errors="coerce").dropna()
        col.metric(f"{label} — Mean", f"${clean.mean():.2f}")
        col.metric(f"{label} — Median", f"${clean.median():.2f}")


# ── By-city chart functions ───────────────────────────────────────────────────

def _pct_or_count(counts_df, use_pct):
    if use_pct:
        counts_df["Value"] = (counts_df["Count"] / counts_df["Base"] * 100).round(1)
        counts_df["TextVal"] = counts_df["Value"].apply(lambda v: f"{v:.1f}%")
        return counts_df, "% of respondents"
    else:
        counts_df["Value"] = counts_df["Count"]
        counts_df["TextVal"] = counts_df["Value"]
        return counts_df, "Count"

def _city_cat_order(present):
    return [c for c in CITY_ORDER if c in present]


def city_bar_chart(series, city_series, title, use_pct, order=None):
    df = pd.DataFrame({"Response": series.values, "City": city_series.values})
    df = df[df["Response"].notna() & (df["Response"].astype(str).str.strip() != "") & (df["Response"].astype(str) != "nan")]

    is_multi = df["Response"].astype(str).str.contains(",").any()
    base_per_city = df.groupby("City").size()
    if is_multi:
        df = df.copy()
        df["Response"] = df["Response"].astype(str).str.split(",")
        df = df.explode("Response")
        df["Response"] = df["Response"].str.strip()

    counts = df.groupby(["City", "Response"]).size().reset_index(name="Count")
    counts["Base"] = counts["City"].map(base_per_city)
    counts, y_label = _pct_or_count(counts, use_pct)

    present = df["City"].unique()
    city_ord = _city_cat_order(present)
    cat_order = {"City": city_ord}
    if order:
        cat_order["Response"] = order

    fig = px.bar(counts, x="Response", y="Value", color="City", barmode="group",
                 title=f"{title} (n={base_per_city.sum()})", text="TextVal",
                 color_discrete_map=CITY_COLORS, category_orders=cat_order)
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=40),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def city_rating_chart(series, city_series, title, use_pct, scale_labels=None):
    default_scale = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
    scale = scale_labels or default_scale
    ordered_ticks = [scale[i] for i in [1, 2, 3, 4, 5]]

    df = pd.DataFrame({
        "Response": pd.to_numeric(series.values, errors="coerce"),
        "City": city_series.values,
    }).dropna(subset=["Response"])
    df["Response"] = df["Response"].astype(int).map(scale)

    base_per_city = df.groupby("City").size()
    counts = df.groupby(["City", "Response"]).size().reset_index(name="Count")

    present_cities = df["City"].unique()
    full_idx = pd.DataFrame(list(iproduct(present_cities, ordered_ticks)), columns=["City", "Response"])
    counts = full_idx.merge(counts, on=["City", "Response"], how="left").fillna(0)
    counts["Count"] = counts["Count"].astype(int)
    counts["Base"] = counts["City"].map(base_per_city)
    counts, y_label = _pct_or_count(counts, use_pct)

    city_ord = _city_cat_order(present_cities)
    n_label = "  |  ".join(f"{c}: n={base_per_city[c]}" for c in city_ord if c in base_per_city)

    fig = px.bar(counts, x="Response", y="Value", color="City", barmode="group",
                 title=f"{title}  ({n_label})", text="TextVal",
                 color_discrete_map=CITY_COLORS,
                 category_orders={"Response": ordered_ticks, "City": city_ord})
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=100),
                      xaxis=dict(type="category", tickangle=-20),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def city_price_chart(series, city_series, experience_name, use_pct):
    df = pd.DataFrame({
        "Response": pd.to_numeric(series.values, errors="coerce"),
        "City": city_series.values,
    }).dropna(subset=["Response"])
    df["Response"] = df["Response"].astype(int)

    base_per_city = df.groupby("City").size()
    counts = df.groupby(["City", "Response"]).size().reset_index(name="Count")
    counts["Base"] = counts["City"].map(base_per_city)
    counts = counts.sort_values("Response")
    counts, y_label = _pct_or_count(counts, use_pct)

    city_ord = _city_cat_order(df["City"].unique())
    n_label = "  |  ".join(f"{c}: n={base_per_city[c]}" for c in city_ord if c in base_per_city)

    fig = px.bar(counts, x="Response", y="Value", color="City", barmode="group",
                 title=f"Expected ticket price — {experience_name}  ({n_label})", text="TextVal",
                 color_discrete_map=CITY_COLORS, category_orders={"City": city_ord})
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Price ($)", yaxis_title=y_label,
                      title_font_size=14, legend_title=None, margin=dict(t=60, b=40),
                      xaxis=dict(type="category"),
                      yaxis_range=[0, 100] if use_pct else None)
    st.plotly_chart(fig, use_container_width=True)


def city_price_summary(series_list, exp_labels, city_series):
    rows = []
    for s, exp in zip(series_list, exp_labels):
        df = pd.DataFrame({
            "Price": pd.to_numeric(s.values, errors="coerce"),
            "City": city_series.values,
        }).dropna(subset=["Price"])
        for city, grp in df.groupby("City"):
            rows.append({"Experience": exp, "City": city,
                         "Mean ($)": round(grp["Price"].mean(), 2),
                         "Median ($)": round(grp["Price"].median(), 2)})
    tbl = pd.DataFrame(rows)
    pivot = tbl.pivot_table(index="City", columns="Experience", values=["Mean ($)", "Median ($)"])
    pivot.columns = [f"{exp} — {metric}" for metric, exp in pivot.columns]
    pivot = pivot.reindex([c for c in CITY_ORDER if c in pivot.index])
    st.dataframe(pivot, use_container_width=True)


# ── Page renderers ────────────────────────────────────────────────────────────

def show_overview(fdf, use_pct):
    st.divider()
    st.subheader("Background questions")
    bar_chart(fdf.iloc[:, 0], "Types of ticketed experience attended (past 5 years)", use_pct)
    bar_chart(fdf.iloc[:, 1], "How often do you go to these activities?", use_pct, order=FREQ_ORDER)
    bar_chart(fdf.iloc[:, 2], "Who do you typically spend your free time with?", use_pct)
    bar_chart(fdf.iloc[:, 3], "Age", use_pct, order=AGE_ORDER)

    st.divider()
    st.subheader("Concept reaction")
    bar_chart(fdf.iloc[:, 4], "Reaction to concept description", use_pct)

    st.divider()
    st.subheader("Themes evoked by description")
    bar_chart(fdf.iloc[:, 5], "Themes evoked — Col F", use_pct)
    bar_chart(fdf.iloc[:, 6], "Themes evoked — Col G", use_pct)

    st.divider()
    st.subheader("Concept Pitch — first exposure")
    rating_chart(
        [fdf.iloc[:, 7], pd.concat([fdf.iloc[:, 9], fdf.iloc[:, 13]]), fdf.iloc[:, 11]],
        ["Prison Island", "BRKThrough", "Glow or Go"],
        "Likelihood to attend", use_pct, scale_labels=SCALE_FIRST,
    )

    st.subheader("Concept Pitch — second exposure")
    rating_chart(
        [fdf.iloc[:, 10], fdf.iloc[:, 8], fdf.iloc[:, 12], fdf.iloc[:, 14]],
        ["Prison Island", "BRKThrough (vs Prison Island)", "BRKThrough (vs Glow or Go)", "Glow or Go"],
        "Second concept vs first", use_pct, scale_labels=SCALE_SECOND,
    )

    st.divider()
    st.subheader("Overall decision — Concept Pitch")
    bar_chart(pd.concat([fdf.iloc[:, 15], fdf.iloc[:, 16]]),
              "Prison Island vs BRKThrough", use_pct, order=ORDER_PI_BRK)
    bar_chart(pd.concat([fdf.iloc[:, 17], fdf.iloc[:, 18]]),
              "BRKThrough vs Glow or Go", use_pct, order=ORDER_BRK_GOG)

    st.divider()
    st.subheader("Which would most people prefer?")
    bar_chart(fdf.iloc[:, 19], "Most people prefer — Prison Island vs BRKThrough", use_pct)
    bar_chart(fdf.iloc[:, 20], "Most people prefer — BRKThrough vs Glow or Go", use_pct)

    st.divider()
    st.subheader("Audience & price expectations")
    audience_chart(
        [fdf.iloc[:, 21], fdf.iloc[:, 23], fdf.iloc[:, 25]],
        ["Prison Island", "BRKThrough", "Glow or Go"],
        "Who would have a better time?", use_pct,
    )
    price_chart(
        [fdf.iloc[:, 22], fdf.iloc[:, 24], fdf.iloc[:, 26]],
        ["Prison Island", "BRKThrough", "Glow or Go"],
        "Expected ticket price ($)", use_pct,
    )
    price_summary([fdf.iloc[:, 22], fdf.iloc[:, 24], fdf.iloc[:, 26]],
                  ["Prison Island", "BRKThrough", "Glow or Go"])


def show_by_city(fdf, use_pct):
    city = fdf["_city"]

    st.divider()
    st.subheader("Background questions")
    city_bar_chart(fdf.iloc[:, 0], city, "Types of ticketed experience attended (past 5 years)", use_pct)
    city_bar_chart(fdf.iloc[:, 1], city, "How often do you go to these activities?", use_pct, order=FREQ_ORDER)
    city_bar_chart(fdf.iloc[:, 2], city, "Who do you typically spend your free time with?", use_pct)
    city_bar_chart(fdf.iloc[:, 3], city, "Age", use_pct, order=AGE_ORDER)

    st.divider()
    st.subheader("Concept reaction")
    city_bar_chart(fdf.iloc[:, 4], city, "Reaction to concept description", use_pct)

    st.divider()
    st.subheader("Themes evoked by description")
    city_bar_chart(fdf.iloc[:, 5], city, "Themes evoked — Col F", use_pct)
    city_bar_chart(fdf.iloc[:, 6], city, "Themes evoked — Col G", use_pct)

    st.divider()
    st.subheader("Concept Pitch — first exposure")
    city_rating_chart(fdf.iloc[:, 7], city,
                      "Prison Island — likelihood to attend", use_pct, scale_labels=SCALE_FIRST)
    brk_first   = pd.concat([fdf.iloc[:, 9],  fdf.iloc[:, 13]]).reset_index(drop=True)
    city_brk_f  = pd.concat([city, city]).reset_index(drop=True)
    city_rating_chart(brk_first, city_brk_f,
                      "BRKThrough — likelihood to attend", use_pct, scale_labels=SCALE_FIRST)
    city_rating_chart(fdf.iloc[:, 11], city,
                      "Glow or Go — likelihood to attend", use_pct, scale_labels=SCALE_FIRST)

    st.subheader("Concept Pitch — second exposure")
    city_rating_chart(fdf.iloc[:, 10], city,
                      "Prison Island (vs BRKThrough) — second vs first", use_pct, scale_labels=SCALE_SECOND)
    city_rating_chart(fdf.iloc[:, 8],  city,
                      "BRKThrough (vs Prison Island) — second vs first", use_pct, scale_labels=SCALE_SECOND)
    city_rating_chart(fdf.iloc[:, 12], city,
                      "BRKThrough (vs Glow or Go) — second vs first", use_pct, scale_labels=SCALE_SECOND)
    city_rating_chart(fdf.iloc[:, 14], city,
                      "Glow or Go (vs BRKThrough) — second vs first", use_pct, scale_labels=SCALE_SECOND)

    st.divider()
    st.subheader("Overall decision — Concept Pitch")
    pq = pd.concat([fdf.iloc[:, 15], fdf.iloc[:, 16]]).reset_index(drop=True)
    city_pq = pd.concat([city, city]).reset_index(drop=True)
    city_bar_chart(pq, city_pq, "Prison Island vs BRKThrough", use_pct, order=ORDER_PI_BRK)

    rs = pd.concat([fdf.iloc[:, 17], fdf.iloc[:, 18]]).reset_index(drop=True)
    city_rs = pd.concat([city, city]).reset_index(drop=True)
    city_bar_chart(rs, city_rs, "BRKThrough vs Glow or Go", use_pct, order=ORDER_BRK_GOG)

    st.divider()
    st.subheader("Which would most people prefer?")
    city_bar_chart(fdf.iloc[:, 19], city, "Most people prefer — Prison Island vs BRKThrough", use_pct)
    city_bar_chart(fdf.iloc[:, 20], city, "Most people prefer — BRKThrough vs Glow or Go", use_pct)

    st.divider()
    st.subheader("Audience & price expectations")
    city_bar_chart(fdf.iloc[:, 21], city, "Who would have a better time at Prison Island?", use_pct)
    city_bar_chart(fdf.iloc[:, 23], city, "Who would have a better time at BRKThrough?", use_pct)
    city_bar_chart(fdf.iloc[:, 25], city, "Who would have a better time at Glow or Go?", use_pct)
    city_price_chart(fdf.iloc[:, 22], city, "Prison Island", use_pct)
    city_price_chart(fdf.iloc[:, 24], city, "BRKThrough", use_pct)
    city_price_chart(fdf.iloc[:, 26], city, "Glow or Go", use_pct)
    st.markdown("**Mean / Median ticket price by city**")
    city_price_summary([fdf.iloc[:, 22], fdf.iloc[:, 24], fdf.iloc[:, 26]],
                       ["Prison Island", "BRKThrough", "Glow or Go"], city)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Prison Island — Naming Feedback", layout="wide")
    st.title("Prison Island — Naming Feedback Dashboard")

    df = load_data()

    st.sidebar.header("Filters")
    cities   = st.sidebar.multiselect("City (C)",    sorted(df["_city"].unique()))
    groups   = st.sidebar.multiselect("Group (G)",   sorted(df["_group"].unique()))
    jails    = st.sidebar.multiselect("Jail (J)",    sorted(df["_jail"].unique()))

    st.sidebar.divider()
    use_pct = st.sidebar.toggle("Show as percentages", value=False)

    st.sidebar.divider()
    page = st.sidebar.radio("View", ["Presentation", "Explore", "Overview", "By City"])

    fdf = apply_filters(df, cities, groups, jails)
    st.caption(f"Showing **{len(fdf)}** of **{len(df)}** responses")

    if page == "Presentation":
        show_presentation(fdf)
    elif page == "Explore":
        show_beeswarm(fdf)
    elif page == "Overview":
        show_overview(fdf, use_pct)
    else:
        show_by_city(fdf, use_pct)


if __name__ == "__main__":
    main()

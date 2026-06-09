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
.ctrl-row { display: flex; align-items: center; gap: 7px; overflow-x: auto; scrollbar-width: none; flex-wrap: nowrap; }
.ctrl-row::-webkit-scrollbar { display: none; }
#group-btns, #color-btns { display: flex !important; gap: 6px; flex-wrap: nowrap !important; }
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
#main-row { display: flex; flex: 1; min-height: 0; }
#chart-wrap { flex: 1; min-height: 0; position: relative; }
#summary-panel {
  width: 230px; flex-shrink: 0; border-left: 1px solid #161616;
  background: #090a0f; overflow-y: auto; padding: 14px 0 8px;
  display: flex; flex-direction: column;
}
#summary-hint {
  color: #333; font-size: 11px; padding: 20px 16px; line-height: 1.6;
}
#summary-table-wrap { padding: 0 0 8px; }
.st-head {
  font-size: 9px; color: #333; text-transform: uppercase;
  letter-spacing: .1em; padding: 0 16px 6px;
}
.st-row {
  display: flex; align-items: center; gap: 7px;
  padding: 3px 16px; font-size: 11px; color: #888;
  transition: opacity .2s;
}
.st-row.st-dimmed { opacity: 0.22; }
.st-row.st-sub { padding-left: 32px; color: #555; font-size: 10px; }
.st-swatch { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.st-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.st-n { color: #444; font-variant-numeric: tabular-nums; font-size: 10px; flex-shrink: 0; }
.st-pct { color: #666; font-variant-numeric: tabular-nums; font-size: 10px; width: 34px; text-align: right; flex-shrink: 0; }
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
  <div id="main-row">
    <div id="chart-wrap"><svg id="chart"></svg></div>
    <div id="summary-panel">
      <div id="summary-hint">Select a dimension above to see a breakdown.</div>
      <div id="summary-table-wrap"></div>
    </div>
  </div>
</div>
<div id="tooltip"></div>
<div id="col-detail"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const RAW = __DATA__;

const AGE_ORDER          = ["18-24","25-34","35-44","45-54","55-64","65-74","75-84","Skip question","Unknown"];
const CITY_ORDER         = ["New York","Los Angeles","Chicago","Denver","Dallas","Cincinnati","Unknown"];
const FREQ_ORDER         = ["More than once a week","Once a week","Every other week","Once or twice a month","Every other month","Once or twice a year","Less than that","Unknown"];
const RATE_ORDER         = ["1","2","3","4","5","—"];
const PI_BRK_ORDER       = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Prison Island is slightly better","Prison Island is much better","—"];
const BRK_GOG_ORDER      = ["BRKThrough is much better","BRKThrough is slightly better","They're about the same","Glow or Go is slightly better","Glow or Go is much better","—"];
const SURVEY_GROUP_ORDER = ["PI-first","BRK-first","GoG-first","BRK-vs-GoG","—"];
const REACTION_ORDER     = ["Just found out, interested","Really enjoy these","Done this myself","Just found out, not for me","Knew this, not for me","Know people who do this","Know people who'd like it","—"];
const H2H_ORDER          = ["much prefer BRK","slightly prefer BRK","about the same","slightly prefer PI/GoG","much prefer PI/GoG","—"];
const CROWD_ORDER        = ["Prison Island","BRKThrough","Glow or Go","—"];
const STUDY_ORDER        = ["PI study","GoG study","—"];

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
  survey_group: {
    "PI-first":"#E8630A","BRK-first":"#4C6EF5","GoG-first":"#E91E8C","BRK-vs-GoG":"#9966FF","—":"#252525",
  },
  reaction: {
    "Just found out, interested":"#2ECC71","Really enjoy these":"#16A085","Done this myself":"#F1C40F",
    "Just found out, not for me":"#E67E22","Knew this, not for me":"#E74C3C",
    "Know people who do this":"#8FA8FF","Know people who'd like it":"#4C6EF5","—":"#252525",
  },
  h2h: {
    "much prefer BRK":"#4C6EF5","slightly prefer BRK":"#8FA8FF","about the same":"#777",
    "slightly prefer PI/GoG":"#FFAA66","much prefer PI/GoG":"#E8630A","—":"#252525",
  },
  crowd: {
    "Prison Island":"#E8630A","BRKThrough":"#4C6EF5","Glow or Go":"#E91E8C","—":"#252525",
  },
  study: {
    "PI study":"#E8630A","GoG study":"#E91E8C","—":"#252525",
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
  {key:"survey_group", label:"Survey group",  field:"survey_group", order:SURVEY_GROUP_ORDER, colors:COLORS.survey_group},
  {key:"reaction",     label:"1st reaction",  field:"reaction",     order:REACTION_ORDER,     colors:COLORS.reaction},
  {key:"cold_rate",    label:"Cold rating",   field:"cold_rate",    order:RATE_ORDER,          colors:COLORS.rating},
  {key:"h2h",          label:"Head to head",  field:"h2h",          order:H2H_ORDER,           colors:COLORS.h2h},
  {key:"crowd_unified",label:"Crowd pick",    field:"crowd_unified",order:CROWD_ORDER,          colors:COLORS.crowd},
  {key:"study",        label:"Study",         field:"study",        order:STUDY_ORDER,          colors:COLORS.study},
];
const DIM_MAP = Object.fromEntries(DIMS.map(d => [d.key, d]));

// Normalise null → "—" for all rating / choice fields
RAW.forEach(d => {
  ["pi_rate","brk_rate","gog_rate","cold_rate"].forEach(f => {
    d[f] = (d[f] === null || d[f] === undefined) ? "—" : String(d[f]);
  });
  ["pi_vs_brk","brk_vs_gog","h2h","crowd_unified","survey_group","reaction","study"].forEach(f => {
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
  renderTable();
}

// ── Legend filter ─────────────────────────────────────────────────────────────
function applyFilter(field, val, updateLegend) {
  filterField = field; filterVal = val;
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => d[field] === val ? dotColor(d) : IDLE)
    .attr("fill-opacity", d => d[field] === val ? 0.92 : 0.10);
  updateColLabels();
  if (updateLegend !== false) refreshLegendFilter();
  renderTable();
}
function clearFilter() {
  filterField = null; filterVal = null;
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill", d => dotColor(d))
    .attr("fill-opacity", groupKey ? 0.88 : 0.65);
  updateColLabels();
  refreshLegendFilter();
  renderTable();
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

// ── Summary table ─────────────────────────────────────────────────────────────
const summaryHint = document.getElementById("summary-hint");
const summaryWrap = document.getElementById("summary-table-wrap");

function renderTable() {
  summaryWrap.innerHTML = "";
  if (!groupKey) {
    summaryHint.style.display = "block";
    return;
  }
  summaryHint.style.display = "none";
  const gDim = DIM_MAP[groupKey];
  const cDim = colorKey ? DIM_MAP[colorKey] : null;
  const pool = (filterVal !== null) ? nodes.filter(d => d[filterField] === filterVal) : nodes;
  const groupVals = gDim.order.filter(v => nodes.some(d => d[gDim.field] === String(v)));
  const total = groupVals.reduce((s, v) => s + pool.filter(d => d[gDim.field] === String(v)).length, 0);

  const head = document.createElement("div");
  head.className = "st-head";
  head.textContent = gDim.label + (cDim ? "  ·  " + cDim.label : "");
  summaryWrap.appendChild(head);

  groupVals.forEach(v => {
    const vStr = String(v);
    const grpNodes = pool.filter(d => d[gDim.field] === vStr);
    const n = grpNodes.length;
    const pct = total > 0 ? Math.round(n / total * 100) : 0;
    const col = gDim.colors[vStr] || "#888";
    const isDimmed = filterVal !== null && !(filterField === gDim.field && filterVal === vStr);

    const row = document.createElement("div");
    row.className = "st-row" + (isDimmed ? " st-dimmed" : "");
    row.innerHTML = `<div class="st-swatch" style="background:${col}"></div>` +
      `<span class="st-label">${vStr}</span>` +
      `<span class="st-n">n=${n}</span>` +
      `<span class="st-pct">${pct}%</span>`;
    summaryWrap.appendChild(row);

    if (cDim && cDim !== gDim && n > 0) {
      const cVals = cDim.order.filter(cv => grpNodes.some(d => d[cDim.field] === String(cv)));
      cVals.forEach(cv => {
        const cvStr = String(cv);
        const cn = grpNodes.filter(d => d[cDim.field] === cvStr).length;
        if (!cn) return;
        const cpct = Math.round(cn / n * 100);
        const ccol = cDim.colors[cvStr] || "#666";
        const sub = document.createElement("div");
        sub.className = "st-row st-sub" + (isDimmed ? " st-dimmed" : "");
        sub.innerHTML = `<div class="st-swatch" style="background:${ccol}"></div>` +
          `<span class="st-label">${cvStr}</span>` +
          `<span class="st-n">${cn}</span>` +
          `<span class="st-pct">${cpct}%</span>`;
        summaryWrap.appendChild(sub);
      });
    }
  });
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
  refreshGroupBtns(); refreshColorBtns(); renderLegend(); updateNarrative(); renderTable();
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
  refreshGroupBtns(); refreshColorBtns(); updateNarrative(); renderTable();
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
    tr("Survey group", d.survey_group) +
    tr("1st reaction", d.reaction) +
    (d.cold_rate !== "—" ? tr("Cold rating", d.cold_rate + " / 5") : "") +
    (d.pi_rate   !== "—" ? tr("PI rating",   d.pi_rate   + " / 5") : "") +
    (d.brk_rate  !== "—" ? tr("BRK rating",  d.brk_rate  + " / 5") : "") +
    (d.gog_rate  !== "—" ? tr("GoG rating",  d.gog_rate  + " / 5") : "") +
    tr("Head to head", d.h2h) +
    tr("Crowd pick",   d.crowd_unified) +
    tr("PI vs BRK",    d.pi_vs_brk) + tr("BRK vs GoG", d.brk_vs_gog);
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

    def is_num(x):
        try: float(x); return True
        except (ValueError, TypeError): return False

    def survey_group_val(row):
        if pd.notna(row.iloc[7])  and is_num(row.iloc[7]):  return "PI-first"
        if pd.notna(row.iloc[9])  and is_num(row.iloc[9]):  return "BRK-first"
        if pd.notna(row.iloc[11]) and is_num(row.iloc[11]): return "GoG-first"
        if pd.notna(row.iloc[13]) and is_num(row.iloc[13]): return "BRK-vs-GoG"
        return "—"

    def reaction_val(row):
        v = clean(row.iloc[4])
        return v.split(",")[0].strip() if v and v != "nan" else "—"

    def cold_rate_val(row, sg):
        if sg == "PI-first":    return first_rate(row, 7)
        if sg == "BRK-first":   return first_rate(row, 9)
        if sg == "GoG-first":   return first_rate(row, 11)
        if sg == "BRK-vs-GoG":  return first_rate(row, 13)
        return None

    PI_TO_H2H = {
        "BRKThrough is much better":        "much prefer BRK",
        "BRKThrough is slightly better":    "slightly prefer BRK",
        "They're about the same":           "about the same",
        "Prison Island is slightly better": "slightly prefer PI/GoG",
        "Prison Island is much better":     "much prefer PI/GoG",
    }
    GOG_TO_H2H = {
        "BRKThrough is much better":    "much prefer BRK",
        "BRKThrough is slightly better":"slightly prefer BRK",
        "They're about the same":       "about the same",
        "Glow or Go is slightly better":"slightly prefer PI/GoG",
        "Glow or Go is much better":    "much prefer PI/GoG",
    }
    def h2h_val(row, sg):
        if sg in ("PI-first", "BRK-first"):
            raw = first_clean(row, 15, 16)
            return PI_TO_H2H.get(raw, "—") if raw else "—"
        if sg in ("GoG-first", "BRK-vs-GoG"):
            raw = first_clean(row, 17, 18)
            return GOG_TO_H2H.get(raw, "—") if raw else "—"
        return "—"

    def crowd_unified_val(row, sg):
        v = first_clean(row, 19) if sg in ("PI-first", "BRK-first") else first_clean(row, 20)
        return v if v else "—"

    records = []
    for _, row in fdf.iterrows():
        sg = survey_group_val(row)
        cr = cold_rate_val(row, sg)
        records.append({
            "age":          clean(row.iloc[3]) or "Unknown",
            "city":         str(row["_city"]),
            "freq":         clean(row.iloc[1]) or "Unknown",
            "pi_rate":      first_rate(row, 7),
            "brk_rate":     first_rate(row, 9, 13),
            "brk_pi_rate":  first_rate(row, 9),
            "gog_rate":     first_rate(row, 11),
            "pi_vs_brk":    first_clean(row, 15, 16) or "—",
            "brk_vs_gog":   first_clean(row, 17, 18) or "—",
            "t_who":        clean(row.iloc[2]),
            "t_reaction":   clean(row.iloc[4]),
            "survey_group": sg,
            "reaction":     reaction_val(row),
            "cold_rate":    cr,
            "h2h":          h2h_val(row, sg),
            "crowd_unified":crowd_unified_val(row, sg),
            "study":        "PI study" if sg in ("PI-first","BRK-first") else ("GoG study" if sg in ("GoG-first","BRK-vs-GoG") else "—"),
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
#nav { display: flex; align-items: center; gap: 12px; padding-top: 14px; margin-top: 14px; border-top: 1px solid #161616; flex-shrink: 0; }
.nav-btn { background: #111318; border: 1px solid #2e2e2e; border-radius: 8px; color: #888; font-size: 18px; cursor: pointer; width: 40px; height: 36px; display: flex; align-items: center; justify-content: center; transition: border-color 0.15s, color 0.15s, background 0.15s; user-select: none; }
.nav-btn:hover:not([disabled]) { border-color: #888; color: #eee; background: #1a1a20; }
.nav-btn[disabled] { opacity: 0.18; cursor: default; }
#nav-hint { font-size: 9px; color: #2a2a2a; letter-spacing: .08em; text-transform: uppercase; flex-shrink: 0; }
#progress { display: flex; gap: 6px; flex: 1; justify-content: center; align-items: center; }
.pdot { width: 5px; height: 5px; border-radius: 50%; background: #222; cursor: pointer; transition: background 0.25s, transform 0.25s; }
.pdot.on { background: #777; transform: scale(1.35); }

/* ── Chart area ─────────────────────────────────────────── */
#chart-wrap { flex: 1; position: relative; overflow: hidden; }
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
      <span id="nav-hint">&#8592;&#8594; keys</span>
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
    group: null, color: "city", hideLegend: true,
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
    if(s.hideLegend) legendEl.innerHTML="";
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


# ── New presentation component ────────────────────────────────────────────────

_NEW_PRESENTATION_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0e1117; color: #fafafa; overflow: hidden; height: 100vh; }
#outer { display: flex; flex-direction: column; height: 100vh; }
#top-bar { height: 44px; flex-shrink: 0; display: flex; align-items: center; padding: 0 24px; border-bottom: 1px solid #161616; background: #090a0f; }
#top-headline { font-size: 14px; font-weight: 700; color: #fff; letter-spacing: 0.01em; transition: opacity 0.28s ease; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#app { display: flex; flex: 1; min-height: 0; }

#panel {
  width: 268px; flex-shrink: 0; display: flex; flex-direction: column;
  padding: 28px 24px 18px; border-right: 1px solid #161616; background: #090a0f;
}
#slide-num { font-size: 10px; color: #333; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 22px; flex-shrink: 0; }
#text-wrap { flex: 1; min-height: 0; }
#slide-title { font-size: 21px; font-weight: 600; color: #eee; line-height: 1.2; margin-bottom: 6px; transition: opacity 0.28s ease; }
#slide-sub   { font-size: 11px; color: #484848; margin-bottom: 16px; transition: opacity 0.28s ease; }
#slide-body  { font-size: 13px; color: #757575; line-height: 1.78; transition: opacity 0.28s ease; }

#explore-wrap { display: none; flex: 1; flex-direction: column; gap: 11px; }
.ctrl-row { display: flex; align-items: flex-start; gap: 6px; }
.row-label { font-size: 10px; color: #444; letter-spacing: 0.08em; text-transform: uppercase; width: 50px; flex-shrink: 0; padding-top: 5px; }
.btn-group { display: flex; gap: 5px; flex-wrap: wrap; }
.dim-btn { padding: 3px 10px; border-radius: 12px; border: 1.5px solid #222; background: transparent; color: #666; font-size: 11px; cursor: pointer; transition: border-color 0.15s, color 0.15s, background 0.15s; white-space: nowrap; }
.dim-btn:hover { border-color: #555; color: #bbb; }
.dim-btn.active { border-color: #ccc; color: #fff; background: rgba(255,255,255,0.09); }
.dim-btn.soft   { border-color: #3a3a3a; color: #999; background: rgba(255,255,255,0.03); }
#color-row { display: none; }

#legend-area { margin-top: 16px; display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
.leg-item { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #777; cursor: pointer; border-radius: 4px; padding: 2px 4px; transition: background .15s; }
.leg-item:hover { background: #1e1e1e; }
.leg-item.leg-active { background: #222; color: #ddd; }
.leg-item.leg-dimmed { opacity: 0.35; }
.leg-sw { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.leg-pct { margin-left: auto; color: #aaa; font-size: 10px; font-variant-numeric: tabular-nums; }

#nav { display: flex; align-items: center; gap: 12px; padding-top: 14px; margin-top: 14px; border-top: 1px solid #161616; flex-shrink: 0; }
.nav-btn { background: #111318; border: 1px solid #2e2e2e; border-radius: 8px; color: #888; font-size: 18px; cursor: pointer; width: 40px; height: 36px; display: flex; align-items: center; justify-content: center; transition: border-color 0.15s, color 0.15s, background 0.15s; user-select: none; }
.nav-btn:hover:not([disabled]) { border-color: #888; color: #eee; background: #1a1a20; }
.nav-btn[disabled] { opacity: 0.18; cursor: default; }
#nav-hint { font-size: 9px; color: #2a2a2a; letter-spacing: .08em; text-transform: uppercase; flex-shrink: 0; }
#progress { display: flex; gap: 6px; flex: 1; justify-content: center; align-items: center; }
.pdot { width: 5px; height: 5px; border-radius: 50%; background: #222; cursor: pointer; transition: background 0.25s, transform 0.25s; }
.pdot.on { background: #777; transform: scale(1.35); }

#chart-wrap { flex: 1; position: relative; overflow: hidden; }
svg { width: 100%; height: 100%; overflow: visible; }

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

/* Filter buttons */
#filter-btn-row { position: absolute; bottom: 108px; left: 0; right: 0; display: none; justify-content: center; gap: 8px; z-index: 10; }
.filter-btn { padding: 4px 14px; border-radius: 14px; border: 1.5px solid #2a2a2a; background: transparent; color: #666; font-size: 11px; cursor: pointer; transition: border-color .15s, color .15s, background .15s; }
.filter-btn:hover { border-color: #555; color: #bbb; }
.filter-btn.fb-active { border-color: #aaa; color: #fff; background: rgba(255,255,255,0.09); }

/* Qualitative overlay */
#qual-wrap { display: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0; overflow-y: auto; padding: 28px 36px; }
.quote-card { background: #111318; border: 1px solid #1e1e1e; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; font-size: 13px; color: #999; line-height: 1.75; }
.quote-card .q-meta { font-size: 10px; color: #383838; margin-top: 8px; text-transform: uppercase; letter-spacing: .06em; }
.quote-highlight { color: #E8630A; }
</style>
</head>
<body>
<div id="outer">
<div id="top-bar"><span id="top-headline"></span></div>
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
      <span id="nav-hint">&#8592;&#8594; keys</span>
    </div>
  </div>
  <div id="chart-wrap">
    <svg id="chart"></svg>
    <div id="qual-wrap"></div>
    <div id="filter-btn-row"></div>
  </div>
</div>
<div id="tooltip"></div>
<div id="col-detail"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const RAW = __DATA__;

// ── Dimension constants ───────────────────────────────────────────────────────
const AGE_ORDER     = ["18-24","25-34","35-44","45-54","55-64","65-74","75-84","Skip question","Unknown"];
const CITY_ORDER    = ["New York","Los Angeles","Chicago","Denver","Dallas","Cincinnati","Unknown"];
const FREQ_ORDER    = ["More than once a week","Once a week","Every other week","Once or twice a month","Every other month","Once or twice a year","Less than that","Unknown"];
const RATE_ORDER    = ["1","2","3","4","5","—"];
const PI_BRK_ORDER  = ["much prefer Breakthrough","slightly prefer Breakthrough","about the same","slightly prefer Prison Island","much prefer Prison Island","\u2014"];

const PI_BRK_REMAP = {
  "BRKThrough is much better":       "much prefer Breakthrough",
  "BRKThrough is slightly better":   "slightly prefer Breakthrough",
  "They're about the same":          "about the same",
  "Prison Island is slightly better":"slightly prefer Prison Island",
  "Prison Island is much better":    "much prefer Prison Island",
};

const H2H_ORDER  = ["much prefer Breakthrough","slightly prefer Breakthrough","about the same","slightly prefer Prison Island / GoG","much prefer Prison Island / GoG","\\u2014"];
const H2H_COLORS = {"much prefer Breakthrough":"#4C6EF5","slightly prefer Breakthrough":"#8FA8FF","about the same":"#666","slightly prefer Prison Island / GoG":"#FFAA66","much prefer Prison Island / GoG":"#E8630A","\\u2014":"#1e1e1e"};

const REACTION_REMAP = {
  "Don't know":                        "Don't get it",
  "Just found out but not for me":     "Didn't know, not for me",
  "I knew this but not for me":        "Knew it, not for me",
  "Just found out and am interested":  "Didn't know, interested",
  "I knew this and am interested":     "Knew it, interested",
  "I know people who would like this": "Know people who'd enjoy this",
  "I know people who do this":         "Know people who do this",
  "I've done this myself in the past": "Have done this myself",
  "Actually I really enjoy these":     "Really enjoy these",
};
const REACTION_ORDER = [
  "Don't get it",
  "Didn't know, not for me",
  "Knew it, not for me",
  "Didn't know, interested",
  "Knew it, interested",
  "Know people who'd enjoy this",
  "Know people who do this",
  "Have done this myself",
  "Really enjoy these",
];
const SURVEY_GROUP_ORDER = ["PI-first","BRK-first","GoG-first","BRK-vs-GoG"];
const GOG_GROUPS = new Set(["GoG-first","BRK-vs-GoG"]);
const CROWD_PICK_ORDER   = ["Prison Island","BRKThrough","—"];
const PRICE_BUCKET_ORDER = ["Under $25","$25\\u201334","$35\\u201344","$45\\u201354","$55+","—"];

const FORMATS_ORDER = [
  "Music Concerts","Movies / Cinema","Exhibitions / Museums",
  "Theatre / Performances","Immersive Experiences","Nightlife / Festivals",
  "Comedy Shows","Sports / Competitions","Talks / Conferences",
];
const GROUPS_ORDER = [
  "Young groups of friends","Mature groups of friends",
  "Friend gatherings / Birthdays","Work groups / Teambuilding",
  "Families (only adults)","Families (with kids)","Tourists","School trips",
];

const COLORS = {
  age:  {"18-24":"#FF4444","25-34":"#FF7722","35-44":"#FFCC00","45-54":"#88CC00","55-64":"#00BBAA","65-74":"#4488FF","75-84":"#9966FF","Skip question":"#555","Unknown":"#555"},
  city: {"New York":"#2196F3","Los Angeles":"#FF9800","Chicago":"#4CAF50","Denver":"#9C27B0","Dallas":"#F44336","Cincinnati":"#00BCD4","Unknown":"#9E9E9E"},
  freq: {"More than once a week":"#FF4444","Once a week":"#FF7722","Every other week":"#FFCC00","Once or twice a month":"#88CC44","Every other month":"#44BBAA","Once or twice a year":"#4488FF","Less than that":"#9966FF","Unknown":"#555"},
  rating: {"1":"#E74C3C","2":"#E67E22","3":"#F1C40F","4":"#2ECC71","5":"#16A085","—":"#1e1e1e"},
  pi_vs_brk: {"much prefer Breakthrough":"#4C6EF5","slightly prefer Breakthrough":"#8FA8FF","about the same":"#666","slightly prefer Prison Island":"#FFAA66","much prefer Prison Island":"#E8630A","\u2014":"#1e1e1e"},
  reaction: {
    "Don't get it":               "#4a4a4a",
    "Didn't know, not for me":    "#c0392b",
    "Knew it, not for me":        "#e74c3c",
    "Didn't know, interested":    "#58d68d",
    "Knew it, interested":        "#27ae60",
    "Know people who'd enjoy this":"#5dade2",
    "Know people who do this":    "#2980b9",
    "Have done this myself":      "#8e44ad",
    "Really enjoy these":         "#6c3483",
    "\\u2014": "#1e1e1e",
  },
  survey_group: {"PI-first":"#E8630A","BRK-first":"#4C6EF5","GoG-first":"#E91E8C","BRK-vs-GoG":"#9C64D0"},
  crowd_pick:   {"Prison Island":"#E8630A","BRKThrough":"#4C6EF5","—":"#1e1e1e"},
  price_bucket: {"Under $25":"#4CAF50","$25\\u201334":"#8BC34A","$35\\u201344":"#FFCC00","$45\\u201354":"#FF9800","$55+":"#F44336","—":"#1e1e1e"},
  formats: {
    "Music Concerts":"#F44336","Movies / Cinema":"#E91E8C","Exhibitions / Museums":"#9C27B0",
    "Theatre / Performances":"#673AB7","Immersive Experiences":"#E8630A",
    "Nightlife / Festivals":"#FF9800","Comedy Shows":"#FFCC00",
    "Sports / Competitions":"#4CAF50","Talks / Conferences":"#2196F3",
  },
  groups: {
    "Young groups of friends":"#F44336","Mature groups of friends":"#FF9800",
    "Friend gatherings / Birthdays":"#FFCC00","Work groups / Teambuilding":"#4CAF50",
    "Families (only adults)":"#2196F3","Families (with kids)":"#9C27B0",
    "Tourists":"#00BCD4","School trips":"#607D8B",
  },
};

const SHORT = {
  "More than once a week":">1/wk","Once a week":"1/wk","Every other week":"2x/mo",
  "Once or twice a month":"1\\u20132/mo","Every other month":"1\\u20132/6mo",
  "Once or twice a year":"1\\u20132/yr","Less than that":"<1/yr",
  "BRKThrough is much better":"BRK \\u2191\\u2191","BRKThrough is slightly better":"BRK \\u2191",
  "They're about the same":"\\u2248 same",
  "Prison Island is slightly better":"PI \\u2191","Prison Island is much better":"PI \\u2191\\u2191",
  "Just found out and am interested":"Interested",
  "Actually I really enjoy these":"Already enjoy",
  "I knew this and am interested":"Knew & interested",
  "I've done this myself in the past":"Done this",
  "I know people who would like this":"Know fans",
  "Just found out but not for me":"Not for me",
  "I knew this but not for me":"Knew, not for me",
  "I know people who do this":"Know participants",
};
const sl = v => SHORT[v] || (v.length > 20 ? v.slice(0,18)+"\\u2026" : v);

// ── Slides ────────────────────────────────────────────────────────────────────
const SLIDES = [
  {
    headline: "Prison Island Indianapolis Naming, v1. Click arrows on bottom left, or use keyboard arrows, to navigate",
    title: "Executive summary",
    sub: "Prison Island naming study \\u00b7 258 respondents \\u00b7 6 US cities",
    body: "",
    textOnly: `
      <div style="max-width:500px;margin:0 auto;padding:48px 20px;">
        <div style="font-size:22px;color:#fff;font-weight:600;line-height:1.4;margin-bottom:32px;">
          Did not find substantial opposition<br>to Prison Island naming.
        </div>
        <div style="border-left:2px solid #E8630A;padding-left:18px;margin-bottom:32px;">
          <div style="font-size:13px;color:#fff;line-height:1.9;">
            Cold ratings for Prison Island and BRKThrough landed near-identical (~3/5).<br>
            Head-to-head preference was close: 45% draw, 29% lean Prison Island, 26% lean BRKThrough.<br>
            Crowd wisdom split 52/48 \\u2014 no consensus that one name is clearly better.<br>
            No significant backlash to the Prison Island name in open-ended responses.
          </div>
        </div>
        <div style="font-size:11px;color:#333;text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px;">Status</div>
        <div style="font-size:13px;color:#555;line-height:1.8;">
          Confirmatory study WIP \\u2014 refined questions, larger sample (~400). Results this week.
        </div>
      </div>
    `,
  },
  {
    headline: "",
    title: "258 people",
    sub: "6 cities \\u00b7 leisure-goers across the US",
    body: "Experience-goers across New York, Los Angeles, Chicago, Denver, Dallas and Cincinnati were shown the Prison Island concept and asked a series of questions. Each dot is one person.",
    group: "city", color: "city", hideLegend: true,
  },
  {
    headline: "",
    title: "Who they are",
    sub: "Age distribution \\u00b7 coloured by city",
    body: "The 35\\u201344 band is the largest cohort \\u2014 and the core audience for a physical, competitive experience. They are regular concert-goers, cinema-goers, escape room players. The 25\\u201334 group is the next largest.",
    group: "age", color: "city",
  },
  {
    headline: "This Fever audience is already primed for the category \\u2014 and the core age group skews competitive.",
    title: "What they like to do",
    sub: "Ticketed formats attended in the last 5 years \\u00b7 multi-select",
    body: "Music, cinema, museums, and theatre top the list \\u2014 but Immersive Experiences rank fifth out of nine, ahead of nightlife and comedy. The 35\\u201344 cohort over-indexes most strongly on Sports & Competitions (+9pp above base) \\u2014 the format closest in spirit to Prison Island. The audience is not just category-aware; the biggest group in it leans competitive.",
    multi: { field: "formats", order: FORMATS_ORDER, colors: COLORS.formats, yField: "age", yOrder: AGE_ORDER },
  },
  {
    headline: "Half of respondents hadn\\u2019t come across one of these before, but most of them were interested. Target audience appears to be 25\\u201355.",
    title: "Reaction to concept description",
    sub: "Concept described in words only \\u2014 no name, no branding. How did people react?",
    body: "25\\u201354 is where discovery is cleanest: 66\\u201369% had never seen this and immediately wanted to go. The 35\\u201344 core skews more familiar \\u2014 26% already do this. Above 55, the concept polarises.",
    group: "reaction", color: "reaction", yField: "age",
  },
  {
    headline: "",
    title: "So what about the name?",
    sub: "The question this survey was built to answer",
    body: "Respondents were split into two groups. One saw Prison Island first, then BRKThrough. The other saw BRKThrough first, then Prison Island. Both groups were then asked to compare. The question: does the name Prison Island get in the way?",
    group: null, color: "survey_group",
  },
  {
    headline: "Similar averages, but BRKThrough attracts more enthusiasm and fewer hard rejections cold.",
    title: "First impressions",
    sub: "Cold rating of first event seen \\u00b7 1\\u20135 likelihood to attend",
    body: "Prison Island and BRKThrough both land around 3 out of 5. Neither name excites on its own. Neither name repels. The starting point is identical \\u2014 the name alone is not moving the needle either way.",
    group: "cold_rate", color: "first_event", yField: "first_event",

  },
  {
    headline: "We asked people which they preferred. Prison Island vs. BRKThrough was a near-draw. Glow or Go vs. BRKThrough was a landslide.",
    title: "Head to head",
    sub: "After seeing both names \\u00b7 top row: PI study \\u00b7 bottom row: GoG study",
    body: "45% call it a draw. 29% lean Prison Island. 26% lean BRKThrough. No name generates a runaway lead \\u2014 and no name generates a backlash.",
    group: "h2h", color: "survey_group", yField: "study",

  },
  {
    headline: "Crowd prediction: BRKThrough vs. Prison Island was 52\\u201348. BRKThrough vs. Glow or Go was 59\\u201341 \\u2014 a clearer verdict.",
    title: "Wisdom of crowd",
    sub: "Which name do most people prefer? \\u00b7 n=88 who answered",
    body: "When asked to predict the crowd rather than state their own preference: 52% say BRKThrough, 48% say Prison Island. The split mirrors the head-to-head almost exactly. There is no consensus that the crowd prefers one name over the other.",
    group: "crowd_unified", color: "city", yField: "study",
  },
  {
    headline: "Prison Island owns the adult social occasion. BRKThrough leads on families with kids (42% vs 24%) and work teams (58% vs 47%).",
    title: "Who\\u2019s it for?",
    sub: "Audience expectations \\u00b7 multi-select \\u00b7 compared to BRKThrough",
    body: "Prison Island over-indexes on mature friend groups (+8pp vs BRKThrough) and adult-only families (+9pp). BRKThrough pulls ahead on families with kids (+18pp) and work teams (+10pp). The name signals an edgier, grown-up night out \\u2014 which is an asset for the target audience, and a natural ceiling for the family and corporate market.",
    multi: { field:"pi_groups", order:GROUPS_ORDER, colors:COLORS.groups, yField:"age", yOrder:AGE_ORDER },
    cohort: { field:"survey_group", vals:["PI-first","BRK-first"] },
  },
  // archived: Who's it for? BRKThrough (multi, brk_groups, yField:age)
  // archived: Who's it for? Glow or Go (multi, gog_groups, yField:age, cohort:GoG study)
  {
    headline: "All three concepts anchor price expectations in the same band \\u2014 median $30\\u201332, mean $33\\u201335 across the board.",
    title: "What would they pay?",
    sub: "Expected ticket price \\u00b7 one dot per event rated \\u00b7 respondents may appear in multiple rows",
    body: "All three events anchor around the $25\\u201334 band. Neither name is dramatically repricing expectations upward or downward.",
    priceRows: true,
  },
  {
    headline: "Open responses show no notable backlash to the Prison Island name.",
    title: "What they said",
    sub: "Open-ended responses \\u00b7 mentions of \\u2018prison\\u2019 or \\u2018name\\u2019 in orange",
    body: "Verbatim feedback from respondents who added a comment at the end of the survey.",
    qualitative: true,
  },
  {
    headline: "What’s next.",
    title: "What\\u2019s next",
    sub: "Next steps",
    body: "",
    textOnly: `
      <div style="max-width:520px;margin:0 auto;padding:40px 20px;">
        <p style="font-size:15px;color:#fff;line-height:1.8;margin-bottom:28px;">
          No red flags. Both names tested without generating any meaningful backlash,
          and the audience responses were broadly positive across cities and age groups.
          The head-to-head result is close \\u2014 which is itself a finding worth noting.
        </p>
        <p style="font-size:13px;color:#ddd;line-height:1.8;margin-bottom:32px;">
          That said, the sample size is modest and the questions were designed as a first pass.
          To be more confident in the direction, we recommend running this again with a slightly
          refined question set and a larger respondent pool.
        </p>
        <div style="border-top:1px solid #2a2a2a;padding-top:24px;">
          <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.1em;margin-bottom:14px;">This week</div>
          <div style="font-size:13px;color:#ccc;line-height:2;">
            \\u2192&nbsp; Revise question wording based on open-ended feedback<br>
            \\u2192&nbsp; Increase sample to ~400 respondents<br>
            \\u2192&nbsp; Re-run survey and compare results
          </div>
        </div>
      </div>
    `,
  },
];

// ── DIMS / DIM_MAP ─────────────────────────────────────────────────────────────
const DIMS = [
  {key:"age",          label:"Age",          field:"age",          order:AGE_ORDER,         colors:COLORS.age},
  {key:"city",         label:"City",         field:"city",         order:CITY_ORDER,         colors:COLORS.city},
  {key:"freq",         label:"Frequency",    field:"freq",         order:FREQ_ORDER,         colors:COLORS.freq},
  {key:"pi_rate",      label:"PI rating",    field:"pi_rate",      order:RATE_ORDER,         colors:COLORS.rating},
  {key:"brk_pi_rate",  label:"BRK rating",   field:"brk_pi_rate",  order:RATE_ORDER,         colors:COLORS.rating},
  {key:"cold_rate",    label:"Cold rating",  field:"cold_rate",    order:RATE_ORDER,         colors:COLORS.rating},
  {key:"first_event",  label:"First event",  field:"first_event",  order:["Prison Island","BRKThrough","Glow or Go"], colors:{"Prison Island":"#E8630A","Glow or Go":"#E91E8C","BRKThrough":"#4C6EF5","\\u2014":"#1e1e1e"}},
  {key:"pi_vs_brk",    label:"PI vs BRK",    field:"pi_vs_brk",    order:PI_BRK_ORDER,       colors:COLORS.pi_vs_brk},
  {key:"h2h",          label:"Head to head", field:"h2h",          order:H2H_ORDER,          colors:H2H_COLORS},
  {key:"study",        label:"Study",        field:"study",        order:["GoG study","PI study"], colors:{"PI study":"#aaa","GoG study":"#aaa","\\u2014":"#1e1e1e"}},
  {key:"reaction",     label:"Reaction",     field:"reaction",     order:REACTION_ORDER,     colors:COLORS.reaction},
  {key:"survey_group", label:"Survey group", field:"survey_group", order:SURVEY_GROUP_ORDER, colors:COLORS.survey_group},
  {key:"crowd_pick",   label:"Crowd pick",   field:"crowd_pick",   order:CROWD_PICK_ORDER,   colors:COLORS.crowd_pick},
  {key:"crowd_unified",label:"Crowd pick",   field:"crowd_unified",order:["Prison Island","BRKThrough","Glow or Go","\\u2014"], colors:{"Prison Island":"#E8630A","BRKThrough":"#4C6EF5","Glow or Go":"#E91E8C","\\u2014":"#1e1e1e"}},
];
const DIM_MAP = Object.fromEntries(DIMS.map(d => [d.key, d]));
const Y_OMIT = new Set(["Skip question","Unknown"]);

RAW.forEach(d => {
  ["pi_rate","brk_pi_rate"].forEach(f => { d[f] = d[f]===null ? "\\u2014" : String(d[f]); });
  d.cold_rate = d.cold_rate===null||d.cold_rate===undefined ? "\\u2014" : String(d.cold_rate);
  ["pi_vs_brk"].forEach(f => { if (!d[f]||d[f]==="nan") d[f]="\\u2014"; else if(PI_BRK_REMAP[d[f]]) d[f]=PI_BRK_REMAP[d[f]]; });
  if (!d.h2h||d.h2h==="nan") d.h2h="\\u2014";
  if (!d.study||d.study==="nan") d.study="\\u2014";
  if (!d.freq||d.freq==="nan")        d.freq="Unknown";
  if (!d.reaction||d.reaction==="nan") d.reaction="\\u2014";
  else if (REACTION_REMAP[d.reaction]) d.reaction=REACTION_REMAP[d.reaction];
  if (!d.survey_group||d.survey_group==="\\u2014"||d.survey_group==="nan") d.survey_group="—";
  if (!d.crowd_pick||d.crowd_pick==="") d.crowd_pick="\\u2014";
  if (!d.crowd_unified||d.crowd_unified==="") d.crowd_unified="\\u2014";
  if (!Array.isArray(d.formats))       d.formats=[];
  if (!Array.isArray(d.pi_groups))     d.pi_groups=[];
  if (!Array.isArray(d.brk_groups))    d.brk_groups=[];
  if (!Array.isArray(d.gog_groups))    d.gog_groups=[];
  if (!d.t_qual)                       d.t_qual="";
});

// ── Force simulation ──────────────────────────────────────────────────────────
const R = 5.5, IDLE_C = "#383838";
const nodes = RAW.map((d,i) => Object.assign({x:0,y:0,vx:0,vy:0},d,{_i:i}));
let W, H, circles, groupKey=null, colorKey=null;
let filterField=null, filterVal=null;
let cohortFilter=null;

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

// ── Dual-beeswarm state ───────────────────────────────────────────────────────
let dualSim = null;

function teardownDual() {
  if (dualSim) { dualSim.stop(); dualSim = null; }
  svg.selectAll(".mdot").remove();
  circles = svg.selectAll(".dot").data(nodes).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("fill",IDLE_C).attr("fill-opacity",0.62).attr("stroke","none")
    .style("cursor","pointer")
    .on("mouseenter",onHover).on("mousemove",e=>posTooltip(e)).on("mouseleave",onLeave);
  sim.on("tick", () => circles.attr("cx", d=>d.x).attr("cy", d=>d.y));
}

// ── Multi-field beeswarm state ────────────────────────────────────────────────
let multiSim = null;

function teardownMulti() {
  if (multiSim) { multiSim.stop(); multiSim = null; }
  svg.selectAll(".mdot").remove();
  circles.attr("fill-opacity", groupKey ? 0.88 : 0.62);
  sim.on("tick", () => circles.attr("cx", d=>d.x).attr("cy", d=>d.y));
}

// ── goPriceRows: 3-row beeswarm, one row per event, exploded from price fields ──
function goPriceRows() {
  hideColDetail();
  if (dualSim)  { dualSim.stop();  dualSim  = null; }
  if (multiSim) { multiSim.stop(); multiSim = null; }
  groupKey=null; colorKey=null; colState=null;
  if (!W) return;

  const PRICE_EVENT_COLORS = {"Prison Island":"#E8630A","BRKThrough":"#4C6EF5","Glow or Go":"#E91E8C"};
  const PRICE_EVENT_ORDER  = ["Prison Island","BRKThrough","Glow or Go"];
  const PRICE_ROWS = [
    {field:"pi_price_bucket",  event:"Prison Island"},
    {field:"brk_price_bucket", event:"BRKThrough"},
    {field:"gog_price_bucket", event:"Glow or Go"},
  ];
  const PBORDER = ["Under $25","$25\\u201334","$35\\u201344","$45\\u201354","$55+"];

  let vNodes = [];
  nodes.forEach(d => {
    PRICE_ROWS.forEach(({field, event}) => {
      const val = d[field];
      if (!val || val === "\\u2014") return;
      vNodes.push(Object.assign({}, d, {vx:0, vy:0, _pb:val, _pe:event}));
    });
  });

  const present = PBORDER.filter(v => vNodes.some(n => n._pb === v));
  const yTop = 28, yBottom = H - 90;
  const yPresent = PRICE_EVENT_ORDER.filter(e => vNodes.some(d => d._pe === e)).reverse();
  const ny = yPresent.length;
  const step = ny > 1 ? Math.min(90, (yBottom-yTop)/(ny-1)) : 0;
  const cy = (yTop+yBottom)/2;
  const yFor = Object.fromEntries(yPresent.map((v,i) => [v, ny===1?cy:cy-step*(ny-1)/2+i*step]));

  const leftPad=68, rightPad=55, usable=W-leftPad-rightPad;
  const xFor = Object.fromEntries(present.map((v,i) => [v, present.length===1?leftPad+usable/2:leftPad+(i/(present.length-1))*usable]));

  vNodes.forEach(d => {
    d.tx = xFor[d._pb] ?? leftPad+usable/2;
    d.ty = yFor[d._pe] ?? H*.44;
    d.x  = d.tx + (Math.random()-.5)*20;
    d.y  = d.ty + (Math.random()-.5)*20;
  });

  circles.attr("fill-opacity", 0);
  svg.selectAll(".mdot").remove();
  const mCircles = svg.selectAll(".mdot").data(vNodes).join("circle")
    .attr("class","mdot").attr("r",R)
    .attr("cx",d=>d.x).attr("cy",d=>d.y)
    .attr("fill",d=>PRICE_EVENT_COLORS[d._pe]||"#888").attr("fill-opacity",0.85)
    .attr("stroke","none").style("cursor","pointer")
    .on("mouseenter",function(event,d){
      tooltipEl.innerHTML=tr("Event",d._pe)+tr("Price",d._pb)+tr("Age",d.age)+tr("City",d.city);
      tooltipEl.style.display="block";
      d3.select(this).raise().attr("r",R+2.5).attr("stroke","#fff").attr("stroke-width",1.5);
      posTooltip(event);
    })
    .on("mousemove",e=>posTooltip(e))
    .on("mouseleave",function(){
      tooltipEl.style.display="none";
      d3.select(this).attr("r",R).attr("stroke","none");
    });

  multiSim = d3.forceSimulation(vNodes)
    .force("collide",d3.forceCollide(R+1.8).strength(0.8).iterations(2))
    .force("x",d3.forceX(d=>d.tx).strength(0.09))
    .force("y",d3.forceY(d=>d.ty).strength(0.22))
    .alphaDecay(0.011).velocityDecay(0.30)
    .on("tick",()=>mCircles.attr("cx",d=>d.x).attr("cy",d=>d.y));
  multiSim.alpha(1.0).restart();

  svg.selectAll(".col-label").remove();

  // Y axis gridlines and labels
  yPresent.forEach(v => {
    const y = yFor[v];
    svg.append("line").attr("class","col-label")
      .attr("x1",leftPad-4).attr("x2",W-rightPad+4).attr("y1",y).attr("y2",y)
      .attr("stroke","#1e1e1e").attr("stroke-width",1);
    svg.append("text").attr("class","col-label")
      .attr("x",leftPad-10).attr("y",y+4).attr("text-anchor","end")
      .attr("fill","#555").attr("font-size","10px").text(v);
  });

  // X column labels (bottom)
  const total = vNodes.length;
  present.forEach(v => {
    const x = xFor[v];
    const count = vNodes.filter(d => d._pb === v).length;
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
      .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
      .text(Math.round(count/total*100)+"%");
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
      .attr("fill","#4a4a4a").attr("font-size","10px").text("n="+count);
    const vParts = wrapLabel(sl(v));
    const vEl = svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",vParts.length>1?H-34:H-28).attr("text-anchor","middle")
      .attr("fill","#aaaaaa").attr("font-size","12px");
    vParts.forEach((p,i)=>vEl.append("tspan").attr("x",x).attr("dy",i===0?0:"1.25em").text(p));
  });


  // Legend: event names
  legendEl.innerHTML="";
  yPresent.forEach(e=>{
    const n=vNodes.filter(d=>d._pe===e).length;
    const el=document.createElement("div"); el.className="leg-item";
    el.innerHTML=`<div class="leg-sw" style="background:${PRICE_EVENT_COLORS[e]}"></div><span>${e}</span><span class="leg-pct">n=${n}</span>`;
    legendEl.appendChild(el);
  });
}

// ── goDual (extended with optional vals + colorsObj) ──────────────────────────
function goDual(leftField, leftLabel, rightField, rightLabel, filterFieldArg, vals, colorsObj) {
  groupKey = null; colorKey = null;
  if (!W) return;
  if (dualSim)  { dualSim.stop();  dualSim  = null; }
  if (multiSim) { multiSim.stop(); multiSim = null; }
  svg.selectAll(".mdot").remove();
  svg.selectAll(".col-label").remove();
  legendEl.innerHTML = "";

  const gap = 32, pad = 48;
  const midX = W / 2;
  const VALS = vals || ["1","2","3","4","5"];
  const colorLookup = colorsObj || COLORS.rating;

  const piOnly=SLIDES[current]?.piOnly;
  const basePool = piOnly ? nodes.filter(d=>!GOG_GROUPS.has(d.survey_group)) : nodes;
  const pool = filterFieldArg ? basePool.filter(d => d[filterFieldArg] !== "\\u2014") : basePool;

  const leftVNodes = pool.filter(d => d[leftField] !== "\\u2014")
    .map(d => Object.assign({}, d, {vx:0,vy:0,_vfield:leftField,_vval:d[leftField],_vlabel:leftLabel}));
  const rightVNodes = pool.filter(d => d[rightField] !== "\\u2014")
    .map(d => Object.assign({}, d, {vx:0,vy:0,_vfield:rightField,_vval:d[rightField],_vlabel:rightLabel}));

  const allV = [...leftVNodes, ...rightVNodes];
  const leftUsable  = midX - gap/2 - pad;
  const rightUsable = W - (midX + gap/2) - pad;

  const leftPresent  = VALS.filter(v => leftVNodes.some(d => d._vval === v));
  const rightPresent = VALS.filter(v => rightVNodes.some(d => d._vval === v));

  const lXFor = Object.fromEntries(leftPresent.map((v,i) =>
    [v, pad + (leftPresent.length===1 ? leftUsable/2 : (i/(leftPresent.length-1))*leftUsable)]));
  const rXFor = Object.fromEntries(rightPresent.map((v,i) =>
    [v, midX+gap/2+pad + (rightPresent.length===1 ? rightUsable/2 : (i/(rightPresent.length-1))*rightUsable)]));

  allV.forEach(d => {
    const xFor = d._vlabel===leftLabel ? lXFor : rXFor;
    d.tx = xFor[d._vval] ?? W/2;
    d.x  = d.tx + (Math.random()-.5)*20;
    d.y  = H*.44 + (Math.random()-.5)*60;
  });

  svg.selectAll(".dot").remove();
  const dualCircles = svg.selectAll(".dot").data(allV).join("circle")
    .attr("class","dot").attr("r",R)
    .attr("cx", d=>d.x).attr("cy", d=>d.y)
    .attr("fill", d => colorLookup[d._vval] || "#888").attr("fill-opacity",0.85)
    .attr("stroke","none").style("cursor","pointer")
    .on("mouseenter", function(event, d) {
      tooltipEl.innerHTML =
        tr("Name", d._vlabel) +
        tr("Rating", d._vval.includes("$") ? d._vval : d._vval+"/5") +
        tr("Age",d.age)+tr("City",d.city)+tr("PI vs BRK",d.pi_vs_brk);
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
    .force("x", d3.forceX(d=>d.tx).strength(0.09))
    .force("y", d3.forceY(H*.44).strength(0.055))
    .alphaDecay(0.011).velocityDecay(0.30)
    .on("tick", () => dualCircles.attr("cx",d=>d.x).attr("cy",d=>d.y));
  dualSim.alpha(1.0).restart();

  [[leftPresent,lXFor,leftVNodes,leftLabel],[rightPresent,rXFor,rightVNodes,rightLabel]].forEach(([present,xFor,vNodes,lbl]) => {
    const validTotal = present.filter(v=>v!=="\\u2014").reduce((s,v)=>s+vNodes.filter(d=>d._vval===v).length, 0);
    present.forEach(v => {
      const x = xFor[v];
      const count = vNodes.filter(d=>d._vval===v).length;
      if (v!=="\\u2014"&&validTotal>0) {
        svg.append("text").attr("class","col-label")
          .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
          .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
          .text(Math.round(count/validTotal*100)+"%");
      }
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
        .attr("fill","#4a4a4a").attr("font-size","10px").text("n="+count);
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-28).attr("text-anchor","middle")
        .attr("fill","#999999").attr("font-size","12px").text(v);
    });
    svg.append("text").attr("class","col-label")
      .attr("x", present.length>1?(xFor[present[0]]+xFor[present[present.length-1]])/2:xFor[present[0]])
      .attr("y",H-88).attr("text-anchor","middle")
      .attr("fill","#ffffff").attr("font-size","13px").attr("font-weight","700")
      .text(lbl);
  });

  svg.append("line").attr("class","col-label")
    .attr("x1",midX).attr("x2",midX).attr("y1",20).attr("y2",H-16)
    .attr("stroke","#333").attr("stroke-width",1).attr("stroke-dasharray","4,4");

  if (colorsObj) {
    legendEl.innerHTML="";
    const hdr=document.createElement("div");
    hdr.style.cssText="font-size:10px;color:#555;margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase";
    hdr.textContent="expected ticket price";
    legendEl.appendChild(hdr);
    VALS.forEach(v=>{
      const el=document.createElement("div"); el.className="leg-item";
      el.innerHTML=`<div class="leg-sw" style="background:${colorsObj[v]||'#888'}"></div><span>${v}</span>`;
      legendEl.appendChild(el);
    });
  } else {
    renderLegend(DIM_MAP["pi_rate"]);
    const hdr=document.createElement("div");
    hdr.style.cssText="font-size:10px;color:#666;margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase";
    hdr.textContent="1 = not likely \\u00b7 5 = very likely";
    legendEl.insertBefore(hdr, legendEl.firstChild);
  }
}

// ── goMultiField ──────────────────────────────────────────────────────────────
function goMultiField(field, orderArr, colorsObj, yField, yOrder) {
  hideColDetail();
  groupKey=null; colorKey=null; colState=null;
  if (!W) return;

  const piOnly=SLIDES[current]?.piOnly;
  let vNodes = [];
  nodes.forEach(d => {
    if (piOnly&&GOG_GROUPS.has(d.survey_group)) return;
    if (cohortFilter&&!cohortFilter.vals.has(d[cohortFilter.field])) return;
    const tags = d[field];
    if (!tags||tags.length===0) return;
    tags.forEach(tag => vNodes.push(Object.assign({},d,{vx:0,vy:0,_vtag:tag,_vfield:field})));
  });

  // Y axis setup (before filtering vNodes so we know which y-values are present)
  const yTop = 28, yBottom = H - 90;
  let yFor = null, yPresent = null;
  if (yField && yOrder) {
    yPresent = yOrder.filter(v => !Y_OMIT.has(v) && vNodes.some(d=>d[yField]===v)).reverse();
    const ny = yPresent.length;
    yFor = Object.fromEntries(yPresent.map((v,i)=>[v, ny===1?(yTop+yBottom)/2 : yTop+(i/(ny-1))*(yBottom-yTop)]));
    vNodes = vNodes.filter(d => yFor[d[yField]] !== undefined);
  }

  const present = orderArr.filter(v => vNodes.some(n=>n._vtag===v));
  const leftPad = yField ? 68 : 55, rightPad = 55;
  const usable = W - leftPad - rightPad;
  const xFor = Object.fromEntries(present.map((v,i)=>[v, present.length===1?leftPad+usable/2:leftPad+(i/(present.length-1))*usable]));

  vNodes.forEach(d => {
    d.tx = xFor[d._vtag] ?? leftPad+usable/2;
    d.ty = yFor ? yFor[d[yField]] : H*.44;
    d.x  = d.tx + (Math.random()-.5)*20;
    d.y  = d.ty + (Math.random()-.5)*20;
  });

  circles.attr("fill-opacity",0);
  svg.selectAll(".mdot").remove();
  const multiCircles = svg.selectAll(".mdot").data(vNodes).join("circle")
    .attr("class","mdot").attr("r",R)
    .attr("cx",d=>d.x).attr("cy",d=>d.y)
    .attr("fill",d=>(yField ? (DIM_MAP[yField].colors[d[yField]]||"#888") : (colorsObj[d._vtag]||"#888"))).attr("fill-opacity",0.85)
    .attr("stroke","none").style("cursor","pointer")
    .on("mouseenter",function(event,d){
      tooltipEl.innerHTML=tr("Format",d._vtag)+tr("Age",d.age)+tr("City",d.city)+tr("Reaction",d.reaction);
      tooltipEl.style.display="block";
      d3.select(this).raise().attr("r",R+2.5).attr("stroke","#fff").attr("stroke-width",1.5);
      posTooltip(event);
    })
    .on("mousemove",e=>posTooltip(e))
    .on("mouseleave",function(){
      tooltipEl.style.display="none";
      d3.select(this).attr("r",R).attr("stroke","none");
    });

  multiSim = d3.forceSimulation(vNodes)
    .force("collide",d3.forceCollide(R+1.8).strength(0.8).iterations(2))
    .force("x",d3.forceX(d=>d.tx).strength(0.09))
    .force("y",d3.forceY(d=>d.ty).strength(yField ? 0.22 : 0.055))
    .alphaDecay(0.011).velocityDecay(0.30)
    .on("tick",()=>multiCircles.attr("cx",d=>d.x).attr("cy",d=>d.y));
  multiSim.alpha(1.0).restart();

  svg.selectAll(".col-label").remove();

  // Y axis gridlines and labels
  if (yFor && yPresent) {
    yPresent.forEach(v => {
      const y = yFor[v];
      svg.append("line").attr("class","col-label")
        .attr("x1",leftPad-4).attr("x2",W-rightPad+4).attr("y1",y).attr("y2",y)
        .attr("stroke","#1e1e1e").attr("stroke-width",1);
      svg.append("text").attr("class","col-label")
        .attr("x",leftPad-10).attr("y",y+4).attr("text-anchor","end")
        .attr("fill","#555").attr("font-size","10px").text(v);
    });
  }

  // X column labels (bottom) — with click handler for age breakdown
  const totalV = vNodes.length;
  const totalRespondents = nodes.filter(d=>d[field]&&d[field].length>0).length;
  present.forEach(v => {
    const x=xFor[v], count=vNodes.filter(d=>d._vtag===v).length;
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
      .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
      .text(Math.round(count/totalRespondents*100)+"%");
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
      .attr("fill","#4a4a4a").attr("font-size","10px").text("n="+count);
    // Clickable format name (two-line wrap if long)
    const vParts=wrapLabel(sl(v));
    const vEl=svg.append("text").attr("class","col-label").style("cursor", yField ? "pointer" : "default")
      .attr("x",x).attr("y",vParts.length>1?H-34:H-28).attr("text-anchor","middle")
      .attr("fill", yField ? "#aaaaaa" : "#999999").attr("font-size","12px");
    vParts.forEach((p,i)=>vEl.append("tspan").attr("x",x).attr("dy",i===0?0:"1.25em").text(p));
    vEl.on("click", yField ? function(event) {
        event.stopPropagation();
        const tagNodes = nodes.filter(d => d[field] && d[field].includes(v));
        const n = tagNodes.length; if (!n) return;
        const ageDim = DIM_MAP[yField];
        const agePresent = ageDim.order.filter(a => !Y_OMIT.has(a) && tagNodes.some(d=>d[yField]===a));
        const rows = agePresent.map(a => {
          const c = tagNodes.filter(d=>d[yField]===a).length;
          const pct = Math.round(c/n*100);
          const col = ageDim.colors[a] || "#888";
          return `<tr>
            <td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:7px"></span>${a}</td>
            <td class="num">${c}</td><td class="pct">${pct}%</td>
          </tr>`;
        }).join("");
        colDetailEl.innerHTML =
          `<h4>${v} <span style="font-weight:400;color:#555">n=${n}</span></h4>` +
          `<table>${rows}</table>` +
          `<div class="close-hint">click anywhere to close</div>`;
        const pw = 240;
        let left = event.pageX + 14;
        if (left + pw > window.innerWidth - 8) left = event.pageX - pw - 14;
        colDetailEl.style.left = left + "px";
        colDetailEl.style.display = "block";
        const ph = colDetailEl.offsetHeight;
        let top = event.pageY - 20;
        if (top + ph > window.innerHeight - 8) top = event.pageY - ph + 20;
        colDetailEl.style.top = Math.max(8, top) + "px";
      } : null);
  });

  // Legend: show age bands when Y axis is active, otherwise show format colours
  legendEl.innerHTML="";
  const hdr=document.createElement("div");
  hdr.style.cssText="font-size:10px;color:#555;margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase";
  hdr.textContent=`${totalV} selections \\u00b7 ${totalRespondents} respondents`;
  legendEl.appendChild(hdr);
  if (yField && yPresent) {
    const ageDim = DIM_MAP[yField];
    yPresent.slice().reverse().forEach(v=>{
      const el=document.createElement("div"); el.className="leg-item";
      el.innerHTML=`<div class="leg-sw" style="background:${ageDim.colors[v]||'#888'}"></div><span>${v}</span>`;
      legendEl.appendChild(el);
    });
  } else {
    present.forEach(v=>{
      const el=document.createElement("div"); el.className="leg-item";
      el.innerHTML=`<div class="leg-sw" style="background:${colorsObj[v]||'#888'}"></div><span>${v}</span>`;
      legendEl.appendChild(el);
    });
  }
}

// ── goDualMulti ───────────────────────────────────────────────────────────────
function goDualMulti(leftField, leftLabel, rightField, rightLabel, yField) {
  groupKey=null; colorKey=null;
  if (!W) return;
  if (dualSim)  { dualSim.stop();  dualSim  = null; }
  if (multiSim) { multiSim.stop(); multiSim = null; }
  svg.selectAll(".col-label").remove();
  svg.selectAll(".mdot").remove();
  circles.attr("fill-opacity",0);
  legendEl.innerHTML="";

  const yLeftPad=yField?68:48;
  const gap=32, pad=yLeftPad, midX=W/2;
  const leftUsable=midX-gap/2-pad, rightUsable=W-(midX+gap/2)-pad;

  const piOnly=SLIDES[current]?.piOnly;
  const leftVNodes=[], rightVNodes=[];
  nodes.forEach(d=>{
    if (piOnly&&GOG_GROUPS.has(d.survey_group)) return;
    (d[leftField]||[]).forEach(tag=>leftVNodes.push(Object.assign({},d,{vx:0,vy:0,_vtag:tag,_vside:"left",_vlabel:leftLabel})));
    (d[rightField]||[]).forEach(tag=>rightVNodes.push(Object.assign({},d,{vx:0,vy:0,_vtag:tag,_vside:"right",_vlabel:rightLabel})));
  });

  // Y axis
  const yTop=28, yBottom=H-90;
  let yFor=null, yPresent=null;
  if(yField){
    const yDim=DIM_MAP[yField];
    const allVTemp=[...leftVNodes,...rightVNodes];
    yPresent=yDim.order.filter(v=>!Y_OMIT.has(v)&&allVTemp.some(d=>d[yField]===v)).reverse();
    const ny=yPresent.length;
    const step=ny>1?Math.min(90,(yBottom-yTop)/(ny-1)):0;
    const cy=(yTop+yBottom)/2;
    yFor=Object.fromEntries(yPresent.map((v,i)=>[v,ny===1?cy:cy-step*(ny-1)/2+i*step]));
    // filter out nodes with no Y position
    const keep=v=>yFor[v]!==undefined;
    leftVNodes.splice(0,leftVNodes.length,...leftVNodes.filter(d=>keep(d[yField])));
    rightVNodes.splice(0,rightVNodes.length,...rightVNodes.filter(d=>keep(d[yField])));
  }

  const allV=[...leftVNodes,...rightVNodes];

  const leftPresent  = GROUPS_ORDER.filter(v=>leftVNodes.some(d=>d._vtag===v));
  const rightPresent = GROUPS_ORDER.filter(v=>rightVNodes.some(d=>d._vtag===v));

  const lXFor=Object.fromEntries(leftPresent.map((v,i)=>[v,pad+(leftPresent.length===1?leftUsable/2:(i/(leftPresent.length-1))*leftUsable)]));
  const rXFor=Object.fromEntries(rightPresent.map((v,i)=>[v,midX+gap/2+pad+(rightPresent.length===1?rightUsable/2:(i/(rightPresent.length-1))*rightUsable)]));

  allV.forEach(d=>{
    const xFor=d._vside==="left"?lXFor:rXFor;
    d.tx=xFor[d._vtag]??(d._vside==="left"?midX/2:midX+midX/2);
    d.ty=yFor?(yFor[d[yField]]??H*.44):H*.44;
    d.x=d.tx+(Math.random()-.5)*20;
    d.y=d.ty+(Math.random()-.5)*40;
  });

  const dualMultiCircles=svg.selectAll(".mdot").data(allV).join("circle")
    .attr("class","mdot").attr("r",R)
    .attr("cx",d=>d.x).attr("cy",d=>d.y)
    .attr("fill",d=>COLORS.groups[d._vtag]||"#888").attr("fill-opacity",0.85)
    .attr("stroke","none").style("cursor","pointer")
    .on("mouseenter",function(event,d){
      tooltipEl.innerHTML=tr("Panel",d._vlabel)+tr("Group",d._vtag)+tr("Age",d.age)+tr("City",d.city);
      tooltipEl.style.display="block";
      d3.select(this).raise().attr("r",R+2.5).attr("stroke","#fff").attr("stroke-width",1.5);
      posTooltip(event);
    })
    .on("mousemove",e=>posTooltip(e))
    .on("mouseleave",function(){
      tooltipEl.style.display="none";
      d3.select(this).attr("r",R).attr("stroke","none");
    });

  dualSim=d3.forceSimulation(allV)
    .force("collide",d3.forceCollide(R+1.8).strength(0.8).iterations(2))
    .force("x",d3.forceX(d=>d.tx).strength(0.09))
    .force("y",d3.forceY(d=>d.ty).strength(yField?0.22:0.055))
    .alphaDecay(0.011).velocityDecay(0.30)
    .on("tick",()=>dualMultiCircles.attr("cx",d=>d.x).attr("cy",d=>d.y));
  dualSim.alpha(1.0).restart();

  [[leftPresent,lXFor,leftVNodes,leftLabel,leftField],[rightPresent,rXFor,rightVNodes,rightLabel,rightField]].forEach(([present,xFor,vNodes,lbl,fld])=>{
    const respCount=nodes.filter(d=>d[fld]&&d[fld].length>0).length;
    const totalTags=vNodes.length;
    present.forEach(v=>{
      const x=xFor[v], count=vNodes.filter(d=>d._vtag===v).length;
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
        .attr("fill","#cccccc").attr("font-size","12px").attr("font-weight","600")
        .text(Math.round(count/totalTags*100)+"%");
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
        .attr("fill","#4a4a4a").attr("font-size","10px").text("n="+count);
      const vParts=wrapLabel(v);
      const labEl=svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",vParts.length>1?H-34:H-28).attr("text-anchor","middle")
        .attr("fill","#999999").attr("font-size","11px");
      vParts.forEach((p,i)=>labEl.append("tspan").attr("x",x).attr("dy",i===0?0:"1.25em").text(p));
    });
    const midLabelX=present.length>1?(xFor[present[0]]+xFor[present[present.length-1]])/2:xFor[present[0]];
    svg.append("text").attr("class","col-label")
      .attr("x",midLabelX).attr("y",H-88).attr("text-anchor","middle")
      .attr("fill","#ffffff").attr("font-size","13px").attr("font-weight","700")
      .text(`${lbl} (n=${respCount})`);
  });

  svg.append("line").attr("class","col-label")
    .attr("x1",midX).attr("x2",midX).attr("y1",20).attr("y2",H-16)
    .attr("stroke","#333").attr("stroke-width",1).attr("stroke-dasharray","4,4");

  if(yFor&&yPresent){
    const x0=pad-30, x1=W-pad+30;
    yPresent.forEach(v=>{
      const y=yFor[v];
      svg.append("line").attr("class","col-label")
        .attr("x1",x0).attr("x2",x1).attr("y1",y).attr("y2",y)
        .attr("stroke","#1e1e1e").attr("stroke-width",1);
      svg.append("text").attr("class","col-label")
        .attr("x",x0-6).attr("y",y+4).attr("text-anchor","end")
        .attr("fill","#555").attr("font-size","10px").text(v);
    });
  }

  legendEl.innerHTML="";
  const hdr=document.createElement("div");
  hdr.style.cssText="font-size:10px;color:#555;margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase";
  hdr.textContent="expected audience group";
  legendEl.appendChild(hdr);
  if(yFor&&yPresent){
    const ageDim=DIM_MAP[yField];
    yPresent.slice().reverse().forEach(v=>{
      const el=document.createElement("div"); el.className="leg-item";
      el.innerHTML=`<div class="leg-sw" style="background:${ageDim.colors[v]||'#888'}"></div><span>${v}</span>`;
      legendEl.appendChild(el);
    });
  } else {
    GROUPS_ORDER.forEach(v=>{
      const lc=leftVNodes.filter(d=>d._vtag===v).length;
      const rc=rightVNodes.filter(d=>d._vtag===v).length;
      if(!lc&&!rc) return;
      const el=document.createElement("div"); el.className="leg-item";
      el.innerHTML=`<div class="leg-sw" style="background:${COLORS.groups[v]||'#888'}"></div><span>${v}</span><span class="leg-pct">${lc}\\u00b7${rc}</span>`;
      legendEl.appendChild(el);
    });
  }
}

// ── showQualitative / hideQualitative ─────────────────────────────────────────
function showQualitative() {
  document.getElementById("chart").style.display="none";
  const qw=document.getElementById("qual-wrap");
  qw.innerHTML="";
  qw.style.display="block";
  const piOnly=SLIDES[current]?.piOnly;
  const quotes=RAW.filter(d=>d.t_qual&&d.t_qual.length>0&&(!piOnly||!GOG_GROUPS.has(d.survey_group)))
    .sort((a,b)=>/\bprison\b/i.test(b.t_qual)-/\bprison\b/i.test(a.t_qual));
  if(!quotes.length){
    qw.innerHTML='<div style="color:#444;padding:40px;text-align:center">No responses recorded.</div>';
    return;
  }
  const hdr=document.createElement("div");
  hdr.style.cssText="font-size:10px;color:#383838;letter-spacing:.08em;text-transform:uppercase;margin-bottom:18px";
  hdr.textContent=`${quotes.length} open-ended responses`;
  qw.appendChild(hdr);
  quotes.forEach(d=>{
    const card=document.createElement("div"); card.className="quote-card";
    const highlighted=d.t_qual.replace(/\\b(prison|name)\\b/gi,m=>`<span class="quote-highlight">${m}</span>`);
    card.innerHTML=`<div>${highlighted}</div>`;
    const meta=document.createElement("div"); meta.className="q-meta";
    const parts=[];
    if(d.age&&d.age!=="Unknown") parts.push(d.age);
    if(d.city&&d.city!=="Unknown") parts.push(d.city);
    if(d.reaction&&d.reaction!=="\\u2014") parts.push(d.reaction);
    meta.textContent=parts.join(" \\u00b7 ");
    card.appendChild(meta);
    qw.appendChild(card);
  });
}
function hideQualitative() {
  document.getElementById("chart").style.display="";
  document.getElementById("qual-wrap").style.display="none";
}

// ── showFilterBtns / hideFilterBtns ──────────────────────────────────────────
const filterBtnRow=document.getElementById("filter-btn-row");
function showFilterBtns(btns) {
  filterBtnRow.innerHTML="";
  filterBtnRow.style.display="flex";
  const allBtn=document.createElement("button");
  allBtn.className="filter-btn fb-active"; allBtn.textContent="All";
  allBtn.addEventListener("click",()=>{
    clearFilter();
    filterBtnRow.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("fb-active"));
    allBtn.classList.add("fb-active");
  });
  filterBtnRow.appendChild(allBtn);
  btns.forEach(btn=>{
    const el=document.createElement("button");
    el.className="filter-btn"; el.textContent=btn.label;
    el.addEventListener("click",()=>{
      if(filterField===btn.field&&filterVal===btn.val){ clearFilter(); filterBtnRow.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("fb-active")); allBtn.classList.add("fb-active"); }
      else{ applyFilter(btn.field,btn.val); filterBtnRow.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("fb-active")); el.classList.add("fb-active"); }
    });
    filterBtnRow.appendChild(el);
  });
}
function hideFilterBtns() { filterBtnRow.style.display="none"; filterBtnRow.innerHTML=""; }

function showCohortBtns(btns) {
  filterBtnRow.innerHTML="";
  filterBtnRow.style.display="flex";
  const allBtn=document.createElement("button");
  allBtn.className="filter-btn fb-active"; allBtn.textContent="All";
  allBtn.addEventListener("click",()=>{
    cohortFilter=null;
    filterBtnRow.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("fb-active"));
    allBtn.classList.add("fb-active");
    const s=SLIDES[current]; go(s.group,s.color||null,s.yField||null);
  });
  filterBtnRow.appendChild(allBtn);
  btns.forEach(btn=>{
    const el=document.createElement("button");
    el.className="filter-btn"; el.textContent=btn.label;
    el.addEventListener("click",()=>{
      cohortFilter={field:btn.field, vals:new Set(btn.vals)};
      filterBtnRow.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("fb-active"));
      el.classList.add("fb-active");
      const s=SLIDES[current]; go(s.group,s.color||null,s.yField||null);
    });
    filterBtnRow.appendChild(el);
  });
}

// ── Column detail popup ───────────────────────────────────────────────────────
const colDetailEl=document.getElementById("col-detail");
function showColDetail(colVal,groupDim,effDim,pageX,pageY) {
  const colNodes=nodes.filter(d=>d[groupDim.field]===colVal);
  const n=colNodes.length; if(!n) return;
  const breakDim=effDim!==groupDim?effDim:groupDim;
  const present=breakDim.order.filter(v=>v!=="\\u2014"&&colNodes.some(d=>d[breakDim.field]===String(v)));
  const rows=present.map(v=>{
    const c=colNodes.filter(d=>d[breakDim.field]===String(v)).length;
    const pct=Math.round(c/n*100);
    const col=breakDim.colors[String(v)]||"#888";
    return `<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:7px"></span>${v}</td><td class="num">${c}</td><td class="pct">${pct}%</td></tr>`;
  }).join("");
  colDetailEl.innerHTML=`<h4>${colVal} <span style="font-weight:400;color:#555">n=${n}</span></h4><table>${rows}</table><div class="close-hint">click anywhere to close</div>`;
  const pw=240;
  let left=pageX+14;
  if(left+pw>window.innerWidth-8) left=pageX-pw-14;
  colDetailEl.style.left=left+"px";
  colDetailEl.style.display="block";
  const ph=colDetailEl.offsetHeight;
  let top=pageY-20;
  if(top+ph>window.innerHeight-8) top=pageY-ph+20;
  colDetailEl.style.top=Math.max(8,top)+"px";
}
function hideColDetail() { colDetailEl.style.display="none"; }
document.addEventListener("click",e=>{ if(!colDetailEl.contains(e.target)) hideColDetail(); });

// ── Column label renderer ─────────────────────────────────────────────────────
function wrapLabel(s){
  if(s.length<=13) return [s];
  const mid=Math.floor(s.length/2);
  const after=s.indexOf(' ',mid), before=s.lastIndexOf(' ',mid);
  const cut=(after>=0&&after-mid<=mid-before)?after:before;
  return cut>0?[s.slice(0,cut),s.slice(cut+1)]:[s];
}
let colState=null;
function updateColLabels() {
  svg.selectAll(".col-label").remove();
  if(!colState) return;
  const {cols,dim,eff,yFor,yPresent}=colState;
  // Y axis gridlines and labels
  if(yFor&&yPresent){
    const x0=cols[0]?.x??55, x1=cols[cols.length-1]?.x??(W-55);
    yPresent.forEach(v=>{
      const y=yFor[v];
      svg.append("line").attr("class","col-label")
        .attr("x1",x0-30).attr("x2",x1+30).attr("y1",y).attr("y2",y)
        .attr("stroke","#1e1e1e").attr("stroke-width",1);
      svg.append("text").attr("class","col-label")
        .attr("x",x0-36).attr("y",y+4).attr("text-anchor","end")
        .attr("fill","#555").attr("font-size","10px").text(v);
    });
  }
  let pool=cohortFilter?nodes.filter(d=>cohortFilter.vals.has(d[cohortFilter.field])):nodes;
  if(filterVal!==null) pool=pool.filter(d=>d[filterField]===filterVal);
  const validTotal=cols.filter(({val})=>val!=="\\u2014").reduce((s,{val})=>s+pool.filter(d=>d[dim.field]===val).length,0);
  const spacing=cols.length>1?Math.abs(cols[1].x-cols[0].x):120;
  cols.forEach(({val,x})=>{
    const count=pool.filter(d=>d[dim.field]===val).length;
    if(val!=="\\u2014"&&validTotal>0){
      svg.append("text").attr("class","col-label")
        .attr("x",x).attr("y",H-66).attr("text-anchor","middle")
        .attr("fill","#cccccc").attr("font-size","13px").attr("font-weight","600")
        .text(Math.round(count/validTotal*100)+"%");
    }
    svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",H-48).attr("text-anchor","middle")
      .attr("fill","#4a4a4a").attr("font-size","10px").text("n="+count);
    const parts=wrapLabel(sl(val));
    const labelEl=svg.append("text").attr("class","col-label")
      .attr("x",x).attr("y",parts.length>1?H-34:H-28).attr("text-anchor","middle")
      .attr("fill","#999999").attr("font-size","12px").style("cursor","pointer");
    parts.forEach((p,i)=>labelEl.append("tspan").attr("x",x).attr("dy",i===0?0:"1.25em").text(p));
    svg.append("rect").attr("class","col-label")
      .attr("x",x-spacing*0.44).attr("y",H-96)
      .attr("width",spacing*0.88).attr("height",92)
      .attr("fill","transparent").style("cursor","pointer")
      .on("click",event=>{ event.stopPropagation(); showColDetail(val,dim,colState.yKey?DIM_MAP[colState.yKey]:(eff||dim),event.pageX,event.pageY); });
  });
  // Sub-labels for rating scales
  if(["cold_rate","pi_rate","brk_pi_rate"].includes(dim.key)&&cols.length>1){
    const c1=cols.find(c=>c.val==="1"), c5=cols.find(c=>c.val==="5");
    if(c1) svg.append("text").attr("class","col-label")
      .attr("x",c1.x).attr("y",H-6).attr("text-anchor","middle")
      .attr("fill","#555").attr("font-size","9px").attr("letter-spacing","0.04em")
      .text("not likely at all to attend");
    if(c5) svg.append("text").attr("class","col-label")
      .attr("x",c5.x).attr("y",H-6).attr("text-anchor","middle")
      .attr("fill","#555").attr("font-size","9px").attr("letter-spacing","0.04em")
      .text("very likely to attend");
  }
  // Direction hint for ordered scales
  if(dim.key==="reaction"&&cols.length>1){
    const x0=cols[0].x, x1=cols[cols.length-1].x, y=H-82;
    svg.append("line").attr("class","col-label")
      .attr("x1",x0-18).attr("x2",x1+18).attr("y1",y).attr("y2",y)
      .attr("stroke","#2a2a2a").attr("stroke-width",1)
      .attr("marker-end","url(#arrow-tip)");
    if(!svg.select("defs #arrow-tip").node()){
      const defs=svg.append("defs");
      defs.append("marker").attr("id","arrow-tip").attr("markerWidth",6).attr("markerHeight",6)
        .attr("refX",5).attr("refY",3).attr("orient","auto")
        .append("path").attr("d","M0,0 L0,6 L6,3 z").attr("fill","#2a2a2a");
    }
    svg.append("text").attr("class","col-label")
      .attr("x",x0-20).attr("y",y+4).attr("text-anchor","end")
      .attr("fill","#333").attr("font-size","9px").attr("letter-spacing","0.05em")
      .text("least interested");
  }
}

// ── Beeswarm go / idle ────────────────────────────────────────────────────────
function go(gKey,cKey,yKey) {
  if(dualSim) teardownDual();
  if(multiSim) teardownMulti();
  hideColDetail();
  groupKey=gKey; colorKey=cKey||null;
  if(!W) return;
  const piOnly=SLIDES[current]?.piOnly;
  let pool=piOnly?nodes.filter(d=>!GOG_GROUPS.has(d.survey_group)):nodes;
  if(cohortFilter) pool=pool.filter(d=>cohortFilter.vals.has(d[cohortFilter.field]));
  const dim=DIM_MAP[gKey];
  const present=dim.order.filter(v=>pool.some(d=>d[dim.field]===String(v)));
  const leftPad=yKey?68:55, rightPad=55, usable=W-leftPad-rightPad;
  const xFor=Object.fromEntries(present.map((v,i)=>[String(v),present.length===1?leftPad+usable/2:leftPad+(i/(present.length-1))*usable]));
  // Y axis
  const yTop=28, yBottom=H-90;
  let yFor=null, yPresent=null;
  if(yKey){
    const yDim=DIM_MAP[yKey];
    yPresent=yDim.order.filter(v=>!Y_OMIT.has(v)&&pool.some(d=>d[yDim.field]===v)).reverse();
    const ny=yPresent.length;
    const step=ny>1?Math.min(90,(yBottom-yTop)/(ny-1)):0;
    const cy=(yTop+yBottom)/2;
    yFor=Object.fromEntries(yPresent.map((v,i)=>[v,ny===1?cy:cy-step*(ny-1)/2+i*step]));
  }
  const parkX=W-72, parkY=yFor?Object.values(yFor).reduce((a,b)=>a+b,0)/Object.keys(yFor).length:H*.44;
  nodes.forEach(d=>{
    const gog=piOnly&&GOG_GROUPS.has(d.survey_group);
    const parked=!gog&&cohortFilter&&!cohortFilter.vals.has(d[cohortFilter.field]);
    d._parked=parked;
    d.tx=gog?-200:parked?parkX:(xFor[d[dim.field]]??leftPad+usable/2);
    d.ty=gog?H*.44:parked?parkY:(yFor?(yFor[d[DIM_MAP[yKey].field]]??H*.44):H*.44);
  });
  const eff=DIM_MAP[colorKey]||dim;
  sim.force("x").x(d=>d.tx).strength(0.09);
  sim.force("y").y(d=>d.ty).strength(yKey?0.22:0.055);
  sim.alpha(1.0).restart();
  circles.transition().duration(1100).ease(d3.easeCubicInOut)
    .attr("fill",d=>d._parked?"#444":(eff.colors[d[eff.field]]||"#888"))
    .attr("fill-opacity",d=>(piOnly&&GOG_GROUPS.has(d.survey_group))?0:d._parked?0.45:0.88);
  // Parked-cohort annotation box
  svg.selectAll(".park-box").remove();
  if(nodes.some(d=>d._parked)){
    const bw=84,bh=52,bx=parkX-bw/2,by=parkY-bh/2-4;
    svg.append("rect").attr("class","park-box col-label")
      .attr("x",bx).attr("y",by).attr("width",bw).attr("height",bh)
      .attr("rx",6).attr("fill","none")
      .attr("stroke","#333").attr("stroke-width",1).attr("stroke-dasharray","4,3");
    svg.append("text").attr("class","park-box col-label")
      .attr("x",parkX).attr("y",by+bh+13).attr("text-anchor","middle")
      .attr("fill","#444").attr("font-size","9px")
      .text("Glow or Go results");
    svg.append("text").attr("class","park-box col-label")
      .attr("x",parkX).attr("y",by+bh+24).attr("text-anchor","middle")
      .attr("fill","#444").attr("font-size","9px")
      .text("\\u2014 more on this later");
  }
  colState={cols:present.map((v,i)=>({val:String(v),x:present.length===1?leftPad+usable/2:leftPad+(i/(present.length-1))*usable})),dim,eff,yFor,yPresent,yKey};
  updateColLabels();
  renderLegend(eff);
}

function idle(cKey) {
  if(dualSim) teardownDual();
  if(multiSim) teardownMulti();
  groupKey=null; colorKey=cKey||null; colState=null;
  nodes.forEach(d=>{delete d.tx;});
  sim.force("x").x(W/2).strength(0.035);
  sim.force("y").y(H*.44).strength(0.035);
  sim.alpha(0.75).restart();
  const dim=cKey?DIM_MAP[cKey]:null;
  const piOnly=SLIDES[current]?.piOnly;
  circles.transition().duration(900).ease(d3.easeCubicInOut)
    .attr("fill",dim?d=>(dim.colors[d[dim.field]]||"#888"):IDLE_C)
    .attr("fill-opacity",d=>(piOnly&&GOG_GROUPS.has(d.survey_group))?0:(dim?0.82:0.62));
  svg.selectAll(".col-label").remove();
  if(dim) renderLegend(dim); else legendEl.innerHTML="";
}

// ── Filter ────────────────────────────────────────────────────────────────────
function applyFilter(field,val,updateLeg) {
  filterField=field; filterVal=val;
  const eff=colorKey?DIM_MAP[colorKey]:(groupKey?DIM_MAP[groupKey]:null);
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill",d=>d[field]===val?(eff?eff.colors[d[eff.field]]||"#888":"#888"):IDLE_C)
    .attr("fill-opacity",d=>d[field]===val?0.92:0.10);
  updateColLabels();
  if(updateLeg!==false) refreshLegendFilter();
}
function clearFilter() {
  filterField=null; filterVal=null;
  const eff=colorKey?DIM_MAP[colorKey]:(groupKey?DIM_MAP[groupKey]:null);
  circles.transition().duration(350).ease(d3.easeCubicInOut)
    .attr("fill",d=>eff?eff.colors[d[eff.field]]||"#888":IDLE_C)
    .attr("fill-opacity",groupKey?0.88:0.62);
  updateColLabels();
  refreshLegendFilter();
}
function refreshLegendFilter() {
  legendEl.querySelectorAll(".leg-item").forEach(el=>{
    el.classList.toggle("leg-active",filterVal!==null&&el.dataset.val===filterVal);
    el.classList.toggle("leg-dimmed",filterVal!==null&&el.dataset.val!==filterVal);
  });
}
function renderLegend(dim) {
  legendEl.innerHTML="";
  const present=dim.order.filter(v=>v!=="\\u2014"&&nodes.some(d=>d[dim.field]===String(v)));
  const total=present.reduce((s,v)=>s+nodes.filter(d=>d[dim.field]===String(v)).length,0);
  present.forEach(v=>{
    const count=nodes.filter(d=>d[dim.field]===String(v)).length;
    const pct=total>0?Math.round(count/total*100):0;
    const el=document.createElement("div"); el.className="leg-item";
    el.dataset.val=String(v);
    el.innerHTML=`<div class="leg-sw" style="background:${dim.colors[String(v)]||'#888'}"></div><span>${v}</span><span class="leg-pct">${pct}%</span>`;
    el.addEventListener("click",()=>{
      if(filterVal===String(v)&&filterField===dim.field) clearFilter();
      else applyFilter(dim.field,String(v));
    });
    legendEl.appendChild(el);
  });
  if(filterField===dim.field) refreshLegendFilter();
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
function tr(k,v) {
  if(!v||v==="\\u2014") return "";
  return `<div class="tt-row"><span class="tt-k">${k}</span><span class="tt-v">${v}</span></div>`;
}
function onHover(event,d) {
  tooltipEl.innerHTML=
    tr("Age",d.age)+tr("City",d.city)+tr("Reaction",d.reaction)+
    tr("Survey group",d.survey_group)+tr("Crowd pick",d.crowd_pick)+
    (d.pi_rate!=="\\u2014"?tr("PI rating",d.pi_rate+"/5"):"")+
    (d.brk_pi_rate!=="\\u2014"?tr("BRK rating",d.brk_pi_rate+"/5"):"")+
    tr("PI vs BRK",d.pi_vs_brk)+
    tr("PI price",d.pi_price_bucket)+tr("BRK price",d.brk_price_bucket);
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

// ── Free-explore buttons ──────────────────────────────────────────────────────
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

// ── Slide engine ──────────────────────────────────────────────────────────────
let current=0;
const TOTAL=SLIDES.length;

function showSlide(idx) {
  filterField=null; filterVal=null; cohortFilter=null;
  current=Math.max(0,Math.min(TOTAL-1,idx));
  const s=SLIDES[current];
  document.getElementById("slide-num").textContent=`${current+1} / ${TOTAL}`;

  hideQualitative();
  if(dualSim) teardownDual();
  if(multiSim) teardownMulti();
  hideColDetail();
  if(s.cohort) cohortFilter={field:s.cohort.field, vals:new Set(s.cohort.vals)};

  const tw=document.getElementById("text-wrap");
  const ew=document.getElementById("explore-wrap");

  if(s.free){
    tw.style.display="none";
    ew.style.display="flex";
    if(expGroup) go(expGroup,expColor); else idle();
    refreshExpBtns();
    hideFilterBtns();
  } else {
    tw.style.display="block";
    ew.style.display="none";
    ["slide-title","slide-sub","slide-body"].forEach(id=>{document.getElementById(id).style.opacity="0";});
    const hlEl=document.getElementById("top-headline");
    hlEl.style.opacity="0";
    setTimeout(()=>{
      document.getElementById("slide-title").textContent=s.title;
      const subEl=document.getElementById("slide-sub");
      subEl.textContent=s.sub||""; subEl.style.display=s.sub?"":"none";
      document.getElementById("slide-body").innerHTML=s.body||"";
      ["slide-title","slide-sub","slide-body"].forEach(id=>{document.getElementById(id).style.opacity="1";});
      hlEl.textContent=s.headline||""; hlEl.style.opacity="1";
    },280);

    if(s.textOnly) {
      document.getElementById("chart").style.display="none";
      const qw=document.getElementById("qual-wrap");
      qw.innerHTML=s.textOnly; qw.style.display="block";
    } else if(s.qualitative) {
      showQualitative();
    } else {
      document.getElementById("chart").style.display="";
      document.getElementById("qual-wrap").style.display="none";
      if(s.dualMulti) {
        goDualMulti(s.dualMulti.left,s.dualMulti.leftLabel,s.dualMulti.right,s.dualMulti.rightLabel,s.dualMulti.yField||null);
      } else if(s.multi) {
        goMultiField(s.multi.field,s.multi.order,s.multi.colors,s.multi.yField||null,s.multi.yOrder||null);
      } else if(s.priceRows) {
        goPriceRows();
      } else if(s.dual) {
        goDual(s.dual.left,s.dual.leftLabel,s.dual.right,s.dual.rightLabel,
               s.dual.filterField||null,s.dual.vals||null,s.dual.colors||null);
      } else if(s.group) {
        go(s.group,s.color||null,s.yField||null);
      } else {
        idle(s.color||null);
      }
    }

    if(s.cohortBtns) showCohortBtns(s.cohortBtns);
    else if(s.filterBtns) showFilterBtns(s.filterBtns);
    else hideFilterBtns();
    if(s.hideLegend) legendEl.innerHTML="";
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

window.addEventListener("resize",()=>{
  initChart();
  const s=SLIDES[current];
  if(s.textOnly||s.qualitative){showSlide(current);return;}
  document.getElementById("chart").style.display="";
  document.getElementById("qual-wrap").style.display="none";
  if(s.dualMulti) goDualMulti(s.dualMulti.left,s.dualMulti.leftLabel,s.dualMulti.right,s.dualMulti.rightLabel,s.dualMulti.yField||null);
  else if(s.multi) goMultiField(s.multi.field,s.multi.order,s.multi.colors,s.multi.yField||null,s.multi.yOrder||null);
  else if(s.priceRows) goPriceRows();
  else if(s.dual)  goDual(s.dual.left,s.dual.leftLabel,s.dual.right,s.dual.rightLabel,s.dual.filterField||null,s.dual.vals||null,s.dual.colors||null);
  else if(s.group) go(s.group,s.color||null,s.yField||null);
  else             idle(s.color||null);
  if(s.cohort) cohortFilter={field:s.cohort.field,vals:new Set(s.cohort.vals)};
  if(s.cohortBtns) showCohortBtns(s.cohortBtns);
  else if(s.filterBtns) showFilterBtns(s.filterBtns);
  else hideFilterBtns();
});
setInterval(()=>{if(!groupKey&&!multiSim&&sim.alpha()<0.04) sim.alpha(0.1).restart();},4500);

buildExpButtons();
buildProgress();
requestAnimationFrame(()=>{initChart();showSlide(0);});
</script>
</div>
</body>
</html>
"""


def show_new_presentation(fdf):
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

    def split_multi(row, col_idx):
        v = row.iloc[col_idx]
        if pd.isna(v):
            return []
        c = re.sub(r"\*+", "", str(v)).strip()
        if not c or c == "nan":
            return []
        return [x.strip() for x in c.split(", ") if x.strip()]

    def price_bucket(row, col_idx):
        v = row.iloc[col_idx]
        if pd.isna(v):
            return "—"
        try:
            n = float(v)
        except (ValueError, TypeError):
            return "—"
        if n < 25:   return "Under $25"
        elif n < 35: return "$25–34"
        elif n < 45: return "$35–44"
        elif n < 55: return "$45–54"
        else:        return "$55+"

    def reaction_val(row):
        v = clean(row.iloc[4])
        if not v or v == "nan":
            return "—"
        return v.split(",")[0].strip()

    def survey_group_val(row):
        def is_num(x):
            try:
                float(x)
                return True
            except (ValueError, TypeError):
                return False
        if pd.notna(row.iloc[7])  and is_num(row.iloc[7]):  return "PI-first"
        if pd.notna(row.iloc[9])  and is_num(row.iloc[9]):  return "BRK-first"
        if pd.notna(row.iloc[11]) and is_num(row.iloc[11]): return "GoG-first"
        if pd.notna(row.iloc[13]) and is_num(row.iloc[13]): return "BRK-vs-GoG"
        return "—"

    def cold_rate_val(row, group):
        if group == "PI-first":               return first_rate(row, 7)
        if group == "BRK-first":              return first_rate(row, 9)
        if group == "GoG-first":              return first_rate(row, 11)
        if group == "BRK-vs-GoG":             return first_rate(row, 13)
        return None

    def first_event_val(group):
        if group == "PI-first":               return "Prison Island"
        if group in ("BRK-first","BRK-vs-GoG"): return "BRKThrough"
        if group == "GoG-first":              return "Glow or Go"
        return "—"

    PI_TO_H2H = {
        "BRKThrough is much better":       "much prefer Breakthrough",
        "BRKThrough is slightly better":   "slightly prefer Breakthrough",
        "They're about the same":          "about the same",
        "Prison Island is slightly better":"slightly prefer Prison Island / GoG",
        "Prison Island is much better":    "much prefer Prison Island / GoG",
    }
    GOG_TO_H2H = {
        "BRKThrough is much better":    "much prefer Breakthrough",
        "BRKThrough is slightly better":"slightly prefer Breakthrough",
        "They're about the same":       "about the same",
        "Glow or Go is slightly better":"slightly prefer Prison Island / GoG",
        "Glow or Go is much better":    "much prefer Prison Island / GoG",
    }

    def h2h_val(row, sg):
        if sg in ("PI-first", "BRK-first"):
            raw = first_clean(row, 15, 16)
            return PI_TO_H2H.get(raw, "—") if raw else "—"
        if sg in ("GoG-first", "BRK-vs-GoG"):
            raw = first_clean(row, 17, 18)
            return GOG_TO_H2H.get(raw, "—") if raw else "—"
        return "—"

    def study_val(sg):
        if sg in ("PI-first", "BRK-first"):    return "PI study"
        if sg in ("GoG-first", "BRK-vs-GoG"):  return "GoG study"
        return "—"

    def crowd_pick_val(row):
        v = first_clean(row, 19)
        return v if v else "—"

    def crowd_unified_val(row, sg):
        if sg in ("PI-first", "BRK-first"):
            v = first_clean(row, 19)
        else:
            v = first_clean(row, 20)
        return v if v else "—"

    def tqual_val(row):
        v = clean(row.iloc[27])
        if not v or v == "nan":
            return ""
        return v if len(v) > 20 else ""

    records = []
    for _, row in fdf.iterrows():
        sg = survey_group_val(row)
        records.append({
            "age":              clean(row.iloc[3]) or "Unknown",
            "city":             str(row["_city"]),
            "freq":             clean(row.iloc[1]) or "Unknown",
            "pi_rate":          first_rate(row, 7),
            "brk_pi_rate":      first_rate(row, 9),
            "pi_vs_brk":        first_clean(row, 15, 16) or "—",
            "formats":          split_multi(row, 0),
            "reaction":         reaction_val(row),
            "crowd_pick":       crowd_pick_val(row),
            "crowd_unified":    crowd_unified_val(row, sg),
            "survey_group":     sg,
            "cold_rate":        cold_rate_val(row, sg),
            "first_event":      first_event_val(sg),
            "h2h":              h2h_val(row, sg),
            "study":            study_val(sg),
            "pi_price_bucket":  price_bucket(row, 22),
            "brk_price_bucket": price_bucket(row, 24),
            "gog_price_bucket": price_bucket(row, 26),
            "pi_groups":        split_multi(row, 21),
            "brk_groups":       split_multi(row, 23),
            "gog_groups":       split_multi(row, 25),
            "t_qual":           tqual_val(row),
        })

    html = _NEW_PRESENTATION_HTML.replace("__DATA__", json.dumps(records))
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
    st.markdown("""<style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stStatusWidget"], .stDeployButton, #MainMenu { display: none !important; }
        /* Hide Streamlit's own top toolbar and tighten padding */
        [data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0 !important; }
        /* Fix all radio groups to bottom-right corner */
        [data-testid="stRadio"] {
            position: fixed !important;
            bottom: 18px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            z-index: 9999;
            background: transparent;
        }
        [data-testid="stRadio"] > div {
            gap: 2px;
            flex-direction: row;
        }
        /* Discrete pill style for radio options */
        [data-testid="stRadio"] label {
            font-size: 11px !important;
            color: #444 !important;
            padding: 3px 10px !important;
            border-radius: 10px;
            cursor: pointer;
            transition: color 0.15s;
        }
        [data-testid="stRadio"] label:hover { color: #999 !important; }
        [data-testid="stRadio"] label[data-checked="true"],
        [data-testid="stRadio"] label[aria-checked="true"] { color: #ccc !important; }
        /* Hide the radio circle dots */
        [data-testid="stRadio"] input[type="radio"] { display: none !important; }
    </style>""", unsafe_allow_html=True)

    df = load_data()
    fdf = df  # no filters in current embodiment

    page = st.radio("", ["Story", "Explore"], horizontal=True, label_visibility="collapsed")

    if page == "Story":
        show_new_presentation(fdf)
    elif page == "Explore":
        show_beeswarm(fdf)


if __name__ == "__main__":
    main()

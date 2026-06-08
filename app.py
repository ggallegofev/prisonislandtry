import re
from itertools import product as iproduct
import pandas as pd
import streamlit as st
import plotly.express as px

CSV_PATH = "2606 Indianapolis Prison Island Naming Feedback - Prison Island Indianapolis.csv"

CITY_MAP = {"6": "New York", "16": "Los Angeles", "21": "Chicago", "52": "Denver", "54": "Dallas", "114": "Cincinnati"}
GROUP_MAP = {"a": "A", "b": "B", "c": "C", "d": "D"}
WELCOME_MAP = {"v": "Welcome", "n": "No Welcome"}
JAIL_MAP = {"j": "Jail", "l": "L", "n": "No Jail"}

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
    df["_jail"]    = df["_jail"].astype(str).str.strip().map(JAIL_MAP).fillna("Unknown")
    for c in df.columns:
        if not c.startswith("_"):
            df[c] = df[c].apply(lambda x: clean_text(x) if pd.notna(x) else x)
    return df

def apply_filters(df, cities, groups, welcomes, jails):
    mask = pd.Series(True, index=df.index)
    if cities:   mask &= df["_city"].isin(cities)
    if groups:   mask &= df["_group"].isin(groups)
    if welcomes: mask &= df["_welcome"].isin(welcomes)
    if jails:    mask &= df["_jail"].isin(jails)
    return df[mask]


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
    welcomes = st.sidebar.multiselect("Welcome (V)", sorted(df["_welcome"].unique()))
    jails    = st.sidebar.multiselect("Jail (J)",    sorted(df["_jail"].unique()))

    st.sidebar.divider()
    use_pct = st.sidebar.toggle("Show as percentages", value=False)

    st.sidebar.divider()
    page = st.sidebar.radio("View", ["Overview", "By City"])

    fdf = apply_filters(df, cities, groups, welcomes, jails)
    st.caption(f"Showing **{len(fdf)}** of **{len(df)}** responses")

    if page == "Overview":
        show_overview(fdf, use_pct)
    else:
        show_by_city(fdf, use_pct)


if __name__ == "__main__":
    main()

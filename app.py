import hashlib
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Nassau Candy Distributor",
    page_icon="🍫",
    layout="wide",
)

st.title("🍫 Nassau Candy Distributor")
st.subheader("Shipping Route Efficiency Dashboard")

st.markdown(
    """
This dashboard analyzes Nassau Candy shipment performance using
shipping lead time, factories, routes, regions, shipping modes,
sales, units and profit.
"""
)

# ============================================================
# FILE PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
ORDERS_FILE = BASE_DIR / "Nassau Candy Distributor_original.csv"
FACTORY_FILE = BASE_DIR / "Factory Mapping.csv"

# ============================================================
# FILE CHECKS
# ============================================================
if not ORDERS_FILE.exists():
    st.error(
        f"Orders file not found: `{ORDERS_FILE.name}`. "
        "Upload it to the same GitHub repository as app.py."
    )
    st.stop()

if not FACTORY_FILE.exists():
    st.error(
        f"Factory mapping file not found: `{FACTORY_FILE.name}`. "
        "Upload it to the same GitHub repository as app.py."
    )
    st.stop()

# ============================================================
# LOAD DATA
# ============================================================
df = pd.read_csv(ORDERS_FILE)
factory_df = pd.read_csv(FACTORY_FILE)

df.columns = df.columns.astype(str).str.strip()
factory_df.columns = factory_df.columns.astype(str).str.strip()

# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================
required_order_columns = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode",
    "Country/Region", "City", "State/Province", "Division",
    "Region", "Product ID", "Product Name", "Sales",
    "Units", "Gross Profit", "Cost"
]

required_factory_columns = ["Factory", "Latitude", "Longitude"]

missing_orders = [c for c in required_order_columns if c not in df.columns]
missing_factory = [c for c in required_factory_columns if c not in factory_df.columns]

if missing_orders:
    st.error(f"Orders CSV is missing columns: {missing_orders}")
    st.stop()

if missing_factory:
    st.error(f"Factory Mapping CSV is missing columns: {missing_factory}")
    st.stop()

# ============================================================
# DATA PREPARATION
# ============================================================
df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce")

df["Shipping Lead Time"] = (
    df["Ship Date"] - df["Order Date"]
).dt.days

df = df[
    df["Order Date"].notna()
    & df["Ship Date"].notna()
    & df["Shipping Lead Time"].notna()
    & (df["Shipping Lead Time"] >= 0)
].copy()

# ============================================================
# FACTORY DATA PREPARATION
# ============================================================
factory_df["Latitude"] = pd.to_numeric(factory_df["Latitude"], errors="coerce")
factory_df["Longitude"] = pd.to_numeric(factory_df["Longitude"], errors="coerce")

factory_df = factory_df.dropna(
    subset=["Factory", "Latitude", "Longitude"]
).copy()

factory_df["Factory"] = factory_df["Factory"].astype(str).str.strip()
factory_df = factory_df.drop_duplicates("Factory").reset_index(drop=True)

factory_names = factory_df["Factory"].tolist()

if not factory_names:
    st.error("No valid factories were found in Factory Mapping.csv.")
    st.stop()

# Factory Mapping.csv contains factory locations but no product/order key.
# We therefore assign factories deterministically from Order ID so that
# the same order receives the same factory on every deployment/run.
def assign_factory(order_id):
    key = str(order_id).encode("utf-8")
    digest = hashlib.md5(key).hexdigest()
    return factory_names[int(digest, 16) % len(factory_names)]

df["Factory"] = df["Order ID"].apply(assign_factory)

df = df.merge(factory_df, on="Factory", how="left")

df["Customer Location"] = (
    df["City"].astype(str).str.strip()
    + ", "
    + df["State/Province"].astype(str).str.strip()
)

df["Shipping Route"] = (
    df["Factory"].astype(str).str.strip()
    + " → "
    + df["Customer Location"].astype(str).str.strip()
)

# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.header("🔎 Dashboard Filters")

factory_options = sorted(df["Factory"].dropna().unique())
ship_mode_options = sorted(df["Ship Mode"].dropna().unique())
region_options = sorted(df["Region"].dropna().unique())
division_options = sorted(df["Division"].dropna().unique())

selected_factories = st.sidebar.multiselect(
    "Factory",
    factory_options,
    default=factory_options,
)

selected_ship_modes = st.sidebar.multiselect(
    "Shipping Mode",
    ship_mode_options,
    default=ship_mode_options,
)

selected_regions = st.sidebar.multiselect(
    "Region",
    region_options,
    default=region_options,
)

selected_divisions = st.sidebar.multiselect(
    "Division",
    division_options,
    default=division_options,
)

filtered_df = df[
    df["Factory"].isin(selected_factories)
    & df["Ship Mode"].isin(selected_ship_modes)
    & df["Region"].isin(selected_regions)
    & df["Division"].isin(selected_divisions)
].copy()

if filtered_df.empty:
    st.warning("No shipments match the selected filters.")
    st.stop()

# ============================================================
# KPI SECTION
# ============================================================
st.header("📌 Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

total_shipments = filtered_df["Order ID"].nunique()
average_lead_time = filtered_df["Shipping Lead Time"].mean()
number_of_factories = filtered_df["Factory"].nunique()
total_sales = filtered_df["Sales"].sum()

col1.metric("Total Shipments", f"{total_shipments:,}")
col2.metric("Average Lead Time", f"{average_lead_time:.2f} days")
col3.metric("Active Factories", f"{number_of_factories:,}")
col4.metric("Total Sales", f"${total_sales:,.0f}")

col5, col6, col7, col8 = st.columns(4)

total_units = filtered_df["Units"].sum()
total_profit = filtered_df["Gross Profit"].sum()
total_cost = filtered_df["Cost"].sum()
profit_margin = (total_profit / total_sales * 100) if total_sales else 0

col5.metric("Total Units", f"{total_units:,.0f}")
col6.metric("Gross Profit", f"${total_profit:,.0f}")
col7.metric("Total Cost", f"${total_cost:,.0f}")
col8.metric("Profit Margin", f"{profit_margin:.2f}%")

# ============================================================
# FACTORY PERFORMANCE
# ============================================================
st.header("🏭 Factory Performance")

factory_performance = (
    filtered_df.groupby("Factory")
    .agg(
        Shipments=("Order ID", "nunique"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
        Sales=("Sales", "sum"),
        Units=("Units", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
    )
    .reset_index()
)

factory_performance["Average_Lead_Time"] = (
    factory_performance["Average_Lead_Time"].round(2)
)

fig_factory = px.bar(
    factory_performance.sort_values("Average_Lead_Time"),
    x="Factory",
    y="Average_Lead_Time",
    title="Average Shipping Lead Time by Factory",
    labels={
        "Factory": "Factory",
        "Average_Lead_Time": "Average Lead Time (Days)",
    },
    hover_data=["Shipments", "Sales", "Gross_Profit"],
)
fig_factory.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_factory, use_container_width=True)

# ============================================================
# ROUTE PERFORMANCE
# ============================================================
st.header("🛣️ Shipping Route Performance")

route_performance = (
    filtered_df.groupby("Shipping Route")
    .agg(
        Shipments=("Order ID", "nunique"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
        Lead_Time_Variability=("Shipping Lead Time", "std"),
        Sales=("Sales", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
    )
    .reset_index()
)

route_performance["Average_Lead_Time"] = (
    route_performance["Average_Lead_Time"].round(2)
)
route_performance["Lead_Time_Variability"] = (
    route_performance["Lead_Time_Variability"].fillna(0).round(2)
)

st.subheader("Average Shipping Lead Time by Route")

route_chart = (
    route_performance.sort_values("Average_Lead_Time").head(30)
)

fig_route = px.bar(
    route_chart,
    x="Shipping Route",
    y="Average_Lead_Time",
    title="Average Lead Time by Shipping Route",
    labels={
        "Shipping Route": "Shipping Route",
        "Average_Lead_Time": "Average Lead Time (Days)",
    },
    hover_data=[
        "Shipments",
        "Lead_Time_Variability",
        "Sales",
        "Gross_Profit",
    ],
)
fig_route.update_layout(xaxis_tickangle=-45, height=550)
st.plotly_chart(fig_route, use_container_width=True)

st.subheader("🏆 Route Performance Leaderboard")

leaderboard = (
    route_performance
    .sort_values("Average_Lead_Time")
    .reset_index(drop=True)
)
leaderboard.index += 1
leaderboard.index.name = "Rank"

st.dataframe(leaderboard, use_container_width=True)

# ============================================================
# SHIPPING MODE ANALYSIS
# ============================================================
st.header("🚚 Shipping Mode Analysis")

mode_performance = (
    filtered_df.groupby("Ship Mode")
    .agg(
        Shipments=("Order ID", "nunique"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
        Sales=("Sales", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
    )
    .reset_index()
)

mode_performance["Average_Lead_Time"] = (
    mode_performance["Average_Lead_Time"].round(2)
)

fig_mode = px.bar(
    mode_performance,
    x="Ship Mode",
    y="Average_Lead_Time",
    title="Average Lead Time by Shipping Mode",
    labels={
        "Ship Mode": "Shipping Mode",
        "Average_Lead_Time": "Average Lead Time (Days)",
    },
    hover_data=["Shipments", "Sales", "Gross_Profit"],
)
st.plotly_chart(fig_mode, use_container_width=True)

# ============================================================
# REGIONAL ANALYSIS
# ============================================================
st.header("🌎 Regional Performance")

region_performance = (
    filtered_df.groupby("Region")
    .agg(
        Shipments=("Order ID", "nunique"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
        Sales=("Sales", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
    )
    .reset_index()
)

region_performance["Average_Lead_Time"] = (
    region_performance["Average_Lead_Time"].round(2)
)

fig_region = px.bar(
    region_performance,
    x="Region",
    y="Average_Lead_Time",
    title="Average Shipping Lead Time by Region",
    labels={
        "Region": "Region",
        "Average_Lead_Time": "Average Lead Time (Days)",
    },
    hover_data=["Shipments", "Sales", "Gross_Profit"],
)
st.plotly_chart(fig_region, use_container_width=True)

# ============================================================
# MONTHLY TRENDS
# ============================================================
st.header("📈 Monthly Shipping Trend")

monthly_performance = (
    filtered_df.set_index("Order Date")
    .resample("ME")
    .agg(
        Shipments=("Order ID", "nunique"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
        Sales=("Sales", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
    )
    .reset_index()
)

monthly_performance["Average_Lead_Time"] = (
    monthly_performance["Average_Lead_Time"].round(2)
)

fig_monthly = px.line(
    monthly_performance,
    x="Order Date",
    y="Average_Lead_Time",
    markers=True,
    title="Monthly Average Shipping Lead Time",
    labels={
        "Order Date": "Month",
        "Average_Lead_Time": "Average Lead Time (Days)",
    },
)
st.plotly_chart(fig_monthly, use_container_width=True)

st.subheader("💰 Monthly Sales")

fig_sales = px.line(
    monthly_performance,
    x="Order Date",
    y="Sales",
    markers=True,
    title="Monthly Sales",
    labels={"Order Date": "Month", "Sales": "Sales ($)"},
)
st.plotly_chart(fig_sales, use_container_width=True)

# ============================================================
# FACTORY MAP
# ============================================================
st.header("🗺️ Factory Locations")

map_data = factory_df[
    factory_df["Factory"].isin(selected_factories)
].copy()

factory_counts = (
    filtered_df.groupby("Factory")
    .agg(
        Shipments=("Order ID", "nunique"),
        Sales=("Sales", "sum"),
        Average_Lead_Time=("Shipping Lead Time", "mean"),
    )
    .reset_index()
)

map_data = map_data.merge(factory_counts, on="Factory", how="left")
map_data["Shipments"] = map_data["Shipments"].fillna(0)
map_data["Sales"] = map_data["Sales"].fillna(0)
map_data["Average_Lead_Time"] = (
    map_data["Average_Lead_Time"].fillna(0).round(2)
)

fig_map = px.scatter_map(
    map_data,
    lat="Latitude",
    lon="Longitude",
    size="Shipments",
    hover_name="Factory",
    hover_data=["Shipments", "Sales", "Average_Lead_Time"],
    zoom=3,
    height=600,
    title="Nassau Candy Factory Locations",
)
fig_map.update_layout(map_style="open-street-map")
st.plotly_chart(fig_map, use_container_width=True)

st.subheader("Factory Summary")

st.dataframe(
    map_data[
        [
            "Factory",
            "Latitude",
            "Longitude",
            "Shipments",
            "Sales",
            "Average_Lead_Time",
        ]
    ].sort_values("Shipments", ascending=False),
    use_container_width=True,
)

# ============================================================
# RAW DATA
# ============================================================
st.header("📋 Shipment Data")
st.caption(f"Showing {len(filtered_df):,} shipment records.")
st.dataframe(filtered_df, use_container_width=True)

st.markdown("---")
st.caption("Nassau Candy Distributor | Shipping Route Efficiency Dashboard")

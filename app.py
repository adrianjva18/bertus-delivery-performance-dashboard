"""
Bertus Delivery Performance Dashboard
--------------------------------------
An interactive Streamlit dashboard analyzing delivery performance for a
physical media wholesale distributor (synthetic data modeled on Bertus
Distributie's real business: vinyl/CD/DVD/merch shipped to independent
stores, retail chains, and online retailers across NL, DE, BE, FR, UK, US).

Run locally with:
    streamlit run app.py

Data cleaning steps performed here (the raw CSV deliberately ships "dirty"):
    - Parse plain string dates into real datetime objects
    - Derive is_late (bool), delay_days (int), and order_month from the
      promised vs actual delivery dates, none of which exist in the raw data
    - Handle the empty delay_reason field for on-time shipments
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Bertus Delivery Performance", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv("data/bertus_shipments_raw.csv")

    # Data cleaning and feature engineering (this is the part that would be
    # real SQL or Pandas work in an actual ops analyst role)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["promised_delivery_date"] = pd.to_datetime(df["promised_delivery_date"])
    df["actual_delivery_date"] = pd.to_datetime(df["actual_delivery_date"])

    df["delay_days"] = (df["actual_delivery_date"] - df["promised_delivery_date"]).dt.days
    df["is_late"] = df["delay_days"] > 0
    df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
    df["delay_reason"] = df["delay_reason"].fillna("On time")

    return df


df = load_data()

st.title("Bertus Delivery Performance Dashboard")
st.caption(
    "Synthetic shipment data modeled on a physical media wholesale distribution "
    "business. Built to practice the exact SLA and delay reporting an operations "
    "or supply chain analyst role would own."
)

# Sidebar filters
st.sidebar.header("Filters")
carriers = st.sidebar.multiselect(
    "Carrier", sorted(df["carrier"].unique()), default=sorted(df["carrier"].unique())
)
customer_types = st.sidebar.multiselect(
    "Customer type",
    sorted(df["customer_type"].unique()),
    default=sorted(df["customer_type"].unique()),
)
countries = st.sidebar.multiselect(
    "Destination country",
    sorted(df["destination_country"].unique()),
    default=sorted(df["destination_country"].unique()),
)

filtered = df[
    df["carrier"].isin(carriers)
    & df["customer_type"].isin(customer_types)
    & df["destination_country"].isin(countries)
]

# Top line KPIs
total_shipments = len(filtered)
on_time_rate = (1 - filtered["is_late"].mean()) * 100 if total_shipments else 0
avg_delay = filtered.loc[filtered["is_late"], "delay_days"].mean() if filtered["is_late"].any() else 0
total_value = filtered["order_value_eur"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total shipments", f"{total_shipments}")
col2.metric("On time rate", f"{on_time_rate:.1f}%")
col3.metric("Avg delay when late", f"{avg_delay:.1f} days")
col4.metric("Total order value", f"EUR {total_value:,.0f}")

st.divider()

# Charts
c1, c2 = st.columns(2)

with c1:
    by_carrier = (
        filtered.groupby("carrier")["is_late"]
        .apply(lambda s: (1 - s.mean()) * 100)
        .reset_index(name="on_time_rate")
        .sort_values("on_time_rate", ascending=False)
    )
    fig = px.bar(
        by_carrier,
        x="carrier",
        y="on_time_rate",
        title="On time rate by carrier",
        labels={"on_time_rate": "On time rate (%)", "carrier": "Carrier"},
        text_auto=".1f",
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    by_month = (
        filtered.groupby("order_month")["is_late"]
        .apply(lambda s: (1 - s.mean()) * 100)
        .reset_index(name="on_time_rate")
        .sort_values("order_month")
    )
    fig = px.line(
        by_month,
        x="order_month",
        y="on_time_rate",
        title="On time rate trend by month",
        markers=True,
        labels={"on_time_rate": "On time rate (%)", "order_month": "Month"},
    )
    st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    reasons = filtered[filtered["is_late"]]["delay_reason"].value_counts().reset_index()
    reasons.columns = ["delay_reason", "count"]
    fig = px.pie(
        reasons,
        names="delay_reason",
        values="count",
        title="Delay reason breakdown (late shipments only)",
    )
    st.plotly_chart(fig, use_container_width=True)

with c4:
    by_country = (
        filtered.groupby("destination_country")
        .agg(shipments=("shipment_id", "count"), on_time_rate=("is_late", lambda s: (1 - s.mean()) * 100))
        .reset_index()
        .sort_values("shipments", ascending=False)
    )
    fig = px.bar(
        by_country,
        x="destination_country",
        y="shipments",
        color="on_time_rate",
        title="Shipment volume and on time rate by destination",
        labels={"shipments": "Shipments", "destination_country": "Country", "on_time_rate": "On time %"},
        color_continuous_scale="RdYlGn",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Filtered shipment data")
st.dataframe(filtered.sort_values("order_date", ascending=False), use_container_width=True)

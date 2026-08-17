import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Dataset Explorer")

st.markdown(
    """
    <style>
    h1 a {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True,
)

st.markdown(
    "Interactive view of the 2000-sample SPICE-characterized dataset "
    "(500 each of inverter, NAND2, NOR2, XOR2; sky130 PDK, tt corner)."
)

df = pd.read_csv("data/dataset.csv")

gate_types = sorted(df["gate_type"].unique())
selected_gates = st.multiselect("Gate types to show", gate_types, default=gate_types)
filtered = df[df["gate_type"].isin(selected_gates)]

st.caption(f"Showing {len(filtered)} of {len(df)} rows")

COMMON_COLS = ["vdd", "temp", "cload", "tpHL_ps", "tpLH_ps", "delay_ps", "power_mW", "pdp"]

tab1, tab2, tab3, tab4 = st.tabs(["Distributions", "Correlations", "Trends", "tpHL vs tpLH"])

with tab1:
    metric = st.selectbox("Metric", COMMON_COLS, index=COMMON_COLS.index("delay_ps"))
    fig = px.histogram(
        filtered, x=metric, color="gate_type", barmode="overlay", opacity=0.6,
        marginal="box", nbins=40,
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(
        "Correlation matrix computed **per gate type** (pooling across gates "
        "risks a misleading blended correlation, since different gates have "
        "different dominant relationships)."
    )
    corr_gate = st.selectbox("Gate type", selected_gates, key="corr_gate")
    corr = df[df["gate_type"] == corr_gate][COMMON_COLS].corr()
    fig = px.imshow(
        corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        title=f"Correlation matrix: {corr_gate}",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    param = st.selectbox("X-axis parameter", ["vdd", "temp", "cload"])
    target = st.selectbox("Y-axis metric", ["delay_ps", "power_mW", "tpHL_ps", "tpLH_ps"])
    fig = px.scatter(
        filtered, x=param, y=target, color="gate_type", opacity=0.5,
        title=f"{target} vs {param}",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown(
        "Points above the dashed line mean the low-to-high transition (tpLH) "
        "is slower than high-to-low (tpHL) -- e.g. NOR2's series-PMOS "
        "pull-up penalty shows up here clearly."
    )
    fig = px.scatter(
        filtered, x="tpHL_ps", y="tpLH_ps", color="gate_type", opacity=0.5,
        facet_col="gate_type",
    )
    max_val = max(filtered["tpHL_ps"].max(), filtered["tpLH_ps"].max()) * 1.05
    for axis in fig.layout:
        if axis.startswith("xaxis") or axis.startswith("yaxis"):
            pass
    fig.add_shape(
        type="line", x0=0, y0=0, x1=max_val, y1=max_val,
        line=dict(dash="dash", color="gray"),
        row="all", col="all",
    )
    st.plotly_chart(fig, use_container_width=True)
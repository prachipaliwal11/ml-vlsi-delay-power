import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))

import streamlit as st
import pandas as pd
import plotly.express as px

from predict import predict

st.title("Gate Comparison")

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
    "Compare predicted delay and power across gate types at **matched device "
    "sizing** -- every PMOS in the selected gates gets the same width, every "
    "NMOS gets the same width, so differences you see are due to gate "
    "topology, not arbitrary sizing choices."
)

gate_types = st.multiselect(
    "Gate types to compare", ["inverter", "nand2", "nor2", "xor2"],
    default=["nand2", "nor2"],
)

col1, col2, col3 = st.columns(3)
with col1:
    vdd = st.slider("Supply Voltage (V)", 1.4, 2.0, 1.8, 0.01)
with col2:
    temp = st.slider("Temperature (°C)", -40.0, 125.0, 27.0, 1.0)
with col3:
    cload = st.slider("Load Capacitance (fF)", 1.0, 20.0, 10.0, 0.5)

col4, col5 = st.columns(2)
with col4:
    pmos_w = st.slider("PMOS width, applied to every PMOS device (µm)", 0.5, 2.0, 1.0, 0.01)
with col5:
    nmos_w = st.slider("NMOS width, applied to every NMOS device (µm)", 0.5, 2.0, 1.0, 0.01)

xor2_static_state = None
if "xor2" in gate_types:
    xor2_static_state = st.radio(
        "XOR2 static input level",
        options=[0, 1],
        format_func=lambda x: f"{x} (non-inverting)" if x == 0 else f"{x} (inverting)",
        horizontal=True,
    )

GATE_WIDTH_KWARGS = {
    "inverter": lambda pw, nw: {"width_p": pw, "width_n": nw},
    "nand2": lambda pw, nw: {"width_p1": pw, "width_p2": pw, "width_n1": nw, "width_n2": nw},
    "nor2": lambda pw, nw: {"width_p1": pw, "width_p2": pw, "width_n1": nw, "width_n2": nw},
    "xor2": lambda pw, nw: {
        "width_inv": (pw + nw) / 2,
        "width_p1": pw, "width_p2": pw, "width_p3": pw, "width_p4": pw,
        "width_n1": nw, "width_n2": nw, "width_n3": nw, "width_n4": nw,
    },
}

if st.button("Compare", type="primary") and gate_types:
    rows = []
    for gate in gate_types:
        widths = GATE_WIDTH_KWARGS[gate](pmos_w, nmos_w)
        static_state = xor2_static_state if gate == "xor2" else None
        delay_ps, power_mW, pdp = predict(
            gate, vdd, temp, cload, static_state=static_state, **widths
        )
        rows.append({"gate_type": gate, "delay_ps": delay_ps, "power_mW": power_mW, "pdp": pdp})

    result_df = pd.DataFrame(rows)

    c1, c2, c3 = st.columns(3)
    with c1:
        fig = px.bar(result_df, x="gate_type", y="delay_ps", title="Predicted Delay (ps)",
                      color="gate_type")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(result_df, x="gate_type", y="power_mW", title="Predicted Power (mW)",
                      color="gate_type")
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        fig = px.bar(result_df, x="gate_type", y="pdp", title="Predicted PDP",
                      color="gate_type")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(result_df.style.format({"delay_ps": "{:.2f}", "power_mW": "{:.5f}", "pdp": "{:.4f}"}))
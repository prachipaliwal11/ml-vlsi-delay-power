import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from predict import predict

st.set_page_config(page_title="sky130 Inverter Delay/Power Predictor", layout="centered")

st.title("sky130 CMOS Inverter — Delay & Power Predictor")
st.markdown(
    "Predicts propagation delay and power consumption for a sky130 inverter "
    "using a Random Forest model trained on SPICE-characterized data."
)

col1, col2 = st.columns(2)
with col1:
    vdd = st.slider("Supply Voltage (V)", 1.4, 2.0, 1.8, 0.01)
    temp = st.slider("Temperature (°C)", -40.0, 125.0, 27.0, 1.0)
    cload = st.slider("Load Capacitance (fF)", 1.0, 20.0, 10.0, 0.5)
with col2:
    width_p = st.slider("PMOS Width (µm)", 0.5, 2.0, 1.0, 0.01)
    width_n = st.slider("NMOS Width (µm)", 0.5, 2.0, 1.0, 0.01)

if st.button("Predict", type="primary"):
    delay_ps, power_mW, pdp = predict(vdd, temp, width_p, width_n, cload)

    m1, m2, m3 = st.columns(3)
    m1.metric("Delay", f"{delay_ps:.2f} ps")
    m2.metric("Power", f"{power_mW:.5f} mW")
    m3.metric("PDP", f"{pdp:.4f}")

st.caption(
    "Model trained on 500 SPICE-simulated samples (sky130 PDK, tt corner). "
    "R² = 0.965 (delay), 0.960 (power)."
)
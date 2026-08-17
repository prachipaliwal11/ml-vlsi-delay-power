import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from predict import predict


st.markdown(
    """
    <div style="
        background: #6FA4FA;
        padding: 28px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
    ">
        <h1 style="color: #0E1117; margin: 0; font-size: 3.4rem; font-weight: 800;">GateSense</h1>
        <p style="color: #0E1117; margin: 4px 0 0 0; font-size: 1.50rem; opacity: 0.85;">
            sky130 CMOS Gate Delay &amp; Power Predictor
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.iframe(
    """
    <script>
    // Finds the h1 containing "GateSense" in the parent Streamlit page
    // and removes any <a>/link-icon elements next to it -- text-based
    // matching sidesteps needing to guess Streamlit's internal CSS
    // class names, which change between versions.
    const doc = window.parent.document;
    const headings = doc.querySelectorAll("h1");
    headings.forEach(function(h) {
        if (h.textContent.includes("GateSense")) {
            const links = h.querySelectorAll("a");
            links.forEach(function(a) { a.remove(); });
            // also check immediate next/previous siblings, in case the
            // anchor icon is injected as a sibling rather than a child
            if (h.nextElementSibling && h.nextElementSibling.tagName === "A") {
                h.nextElementSibling.remove();
            }
        }
    });
    </script>
    """,
    height=1,
)

st.markdown(
    "Predicts propagation delay and power consumption for a sky130 logic gate "
    "using Random Forest models trained on SPICE-characterized data across "
    "four gate types: inverter, NAND2, NOR2, XOR2."
)

gate_type = st.selectbox("Gate Type", ["inverter", "nand2", "nor2", "xor2"])

col1, col2 = st.columns(2)
with col1:
    vdd = st.slider("Supply Voltage (V)", 1.4, 2.0, 1.8, 0.01)
    temp = st.slider("Temperature (°C)", -40.0, 125.0, 27.0, 1.0)
    cload = st.slider("Load Capacitance (fF)", 1.0, 20.0, 10.0, 0.5)

widths = {}
static_state = None

with col2:
    if gate_type == "inverter":
        widths["width_p"] = st.slider("PMOS Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n"] = st.slider("NMOS Width (µm)", 0.5, 2.0, 1.0, 0.01)

    elif gate_type in ("nand2", "nor2"):
        widths["width_p1"] = st.slider("PMOS 1 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_p2"] = st.slider("PMOS 2 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n1"] = st.slider("NMOS 1 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n2"] = st.slider("NMOS 2 Width (µm)", 0.5, 2.0, 1.0, 0.01)

    elif gate_type == "xor2":
        widths["width_inv"] = st.slider("Local Inverter Width (µm)", 0.5, 1.5, 1.0, 0.01)
        widths["width_p1"] = st.slider("PMOS 1 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_p2"] = st.slider("PMOS 2 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_p3"] = st.slider("PMOS 3 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_p4"] = st.slider("PMOS 4 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n1"] = st.slider("NMOS 1 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n2"] = st.slider("NMOS 2 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n3"] = st.slider("NMOS 3 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        widths["width_n4"] = st.slider("NMOS 4 Width (µm)", 0.5, 2.0, 1.0, 0.01)
        static_state = st.radio(
            "Static input level",
            options=[0, 1],
            format_func=lambda x: f"{x} (non-inverting: out = A)" if x == 0
                                   else f"{x} (inverting: out = NOT A)",
        )

if st.button("Predict", type="primary"):
    delay_ps, power_mW, pdp = predict(
        gate_type, vdd, temp, cload, static_state=static_state, **widths
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Delay", f"{delay_ps:.2f} ps")
    m2.metric("Power", f"{power_mW:.5f} mW")
    m3.metric("PDP", f"{pdp:.4f}")

st.caption(
    "Model trained on 2000 SPICE-simulated samples (500 each of inverter, "
    "NAND2, NOR2, XOR2; sky130 PDK, tt corner).  \n"
    "R² = 0.841 (delay), 0.960 (power), 0.905 (tpHL), 0.839 (tpLH)."
)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))

import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

from feature_utils import build_training_matrix, FEATURE_COLUMNS

st.title("Model Insights")

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
    "Feature importances and held-out test performance for each trained "
    "Random Forest model, computed live using the same 80/20 split "
    "(`random_state=42`) used during training."
)

TARGET_MODELS = {
    "delay_ps": "models/delay_model.pkl",
    "tpHL_ps": "models/tpHL_model.pkl",
    "tpLH_ps": "models/tpLH_model.pkl",
    "power_mW": "models/power_model.pkl",
}

df = pd.read_csv("data/dataset.csv")
X = build_training_matrix(df)

target = st.selectbox("Target", list(TARGET_MODELS.keys()))

model_path = TARGET_MODELS[target]
if not os.path.exists(model_path):
    st.warning(f"No trained model found at `{model_path}` -- run `train_model.py` first.")
    st.stop()

model = joblib.load(model_path)
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
y_pred = model.predict(X_test)

r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)

c1, c2 = st.columns(2)
c1.metric("R² (held-out test set)", f"{r2:.4f}")
c2.metric("MAE (held-out test set)", f"{mae:.4f}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Feature Importance")
    importances = pd.Series(
        model.feature_importances_, index=FEATURE_COLUMNS
    ).sort_values(ascending=True)
    fig = px.bar(
        importances, orientation="h",
        labels={"value": "Importance", "index": "Feature"},
    )
    fig.update_layout(showlegend=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Actual vs Predicted (test set)")
    plot_df = pd.DataFrame({"actual": y_test.values, "predicted": y_pred})
    # color by gate_type for context, pulled from the original df using the
    # same test-set indices
    plot_df["gate_type"] = df.loc[y_test.index, "gate_type"].values
    fig = px.scatter(
        plot_df, x="actual", y="predicted", color="gate_type", opacity=0.5,
    )
    min_v = min(plot_df["actual"].min(), plot_df["predicted"].min())
    max_v = max(plot_df["actual"].max(), plot_df["predicted"].max())
    fig.add_shape(
        type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
        line=dict(dash="dash", color="gray"),
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Points on the dashed line = perfect prediction. Tighter clustering "
    "around the line indicates better model fit for that target/gate type."
)
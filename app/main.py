import streamlit as st

st.set_page_config(page_title="GateSense — sky130 Gate Predictor", layout="wide")

predictor = st.Page("Predictor.py", title="Predictor", default=True)
explorer = st.Page("pages/1_Dataset_Explorer.py", title="Dataset Explorer")
insights = st.Page("pages/2_Model_Insights.py", title="Model Insights")
comparison = st.Page("pages/3_Gate_Comparison.py", title="Gate Comparison")
methodology = st.Page("pages/4_Methodology.py", title="Methodology")

# Grouping into a dict renders each key as a section header in the sidebar,
# which visually separates the main Predictor from the read-only
# exploration/reference pages -- exactly the "divider" effect requested.
pg = st.navigation({
    "PREDICT": [predictor],
    "EXPLORE": [explorer, insights, comparison, methodology],
})

st.markdown(
    """
    <style>
    /* Adds breathing room between grouped sidebar nav sections
       ("Predict" vs "Explore & Understand"). Targets Streamlit's
       internal nav-section headers -- if this doesn't visibly apply
       after a hard refresh, right-click the section header text in
       the sidebar, choose Inspect, and check the actual class/testid
       so the selector can be adjusted. */
    [data-testid="stSidebarNav"] li:has(+ [data-testid="stSidebarNavSectionHeader"]) {
        margin-bottom: 28px;
    }
    [data-testid="stSidebarNavSectionHeader"] {
        margin-top: 28px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

pg.run()
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

os.makedirs("eda_plots", exist_ok=True)

df = pd.read_csv("data/dataset.csv")

# Columns common to every gate type -- width_p/width_n (inverter),
# width_p1/p2/n1/n2 (nand2/nor2), width_inv/p1-4/n1-4 (xor2) are NOT
# common, so they're excluded from the pooled analyses below and left
# for a per-gate-type deep dive if you want one later.
COMMON_COLS = ["vdd", "temp", "cload", "tpHL_ps", "tpLH_ps", "delay_ps", "power_mW", "pdp"]

print("=== Gate type counts ===")
print(df["gate_type"].value_counts())

print("\n=== Basic info (pooled across all gate types) ===")
print(df[COMMON_COLS].describe())

print("\n=== Basic info (per gate type) ===")
print(df.groupby("gate_type")[COMMON_COLS].describe().T)

print("\n=== Checking for anything broken ===")
print("Any negative delay?", (df["delay_ps"] < 0).any())
print("Any negative tpHL?", (df["tpHL_ps"] < 0).any())
print("Any negative tpLH?", (df["tpLH_ps"] < 0).any())
print("Any negative power?", (df["power_mW"] < 0).any())
print("Any missing values in common columns?\n", df[COMMON_COLS].isnull().sum())
# Note: gate-specific width_* columns WILL show missing values for rows
# belonging to other gate types -- that's expected (e.g. an inverter row
# has no width_p1/p2), not a data quality problem. Only COMMON_COLS
# missingness is meaningful here.

# --- Distributions of inputs and outputs, split by gate_type ---
fig, axes = plt.subplots(2, 4, figsize=(20, 8))
for ax, col in zip(axes.flat, COMMON_COLS):
    sns.histplot(data=df, x=col, hue="gate_type", bins=25, kde=True, ax=ax, element="step")
    ax.set_title(col)
plt.tight_layout()
plt.savefig("eda_plots/eda_distributions.png")
print("\nSaved eda_distributions.png")

# --- Correlation heatmap, one per gate_type ---
# Pooling all gates into a single correlation matrix risks a Simpson's-
# paradox-style misleading result (different gates can have different
# dominant relationships), so each gate type gets its own panel.
gate_types = sorted(df["gate_type"].unique())
fig, axes = plt.subplots(1, len(gate_types), figsize=(6 * len(gate_types), 5))
if len(gate_types) == 1:
    axes = [axes]
for ax, gate in zip(axes, gate_types):
    corr = df[df["gate_type"] == gate][COMMON_COLS].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax, cbar=False)
    ax.set_title(f"Correlation: {gate}")
plt.tight_layout()
plt.savefig("eda_plots/eda_correlation.png")
print("Saved eda_correlation.png")

# --- Physical trend checks: delay/power vs each key shared parameter, colored by gate_type ---
params = ["vdd", "temp", "cload"]
fig, axes = plt.subplots(2, len(params), figsize=(6 * len(params), 8))
for i, param in enumerate(params):
    sns.scatterplot(data=df, x=param, y="delay_ps", hue="gate_type", ax=axes[0, i], alpha=0.5, s=15)
    axes[0, i].set_title(f"Delay vs {param}")
    sns.scatterplot(data=df, x=param, y="power_mW", hue="gate_type", ax=axes[1, i], alpha=0.5, s=15)
    axes[1, i].set_title(f"Power vs {param}")
plt.tight_layout()
plt.savefig("eda_plots/trends.png")
print("Saved eda_trends.png")

# --- tpHL vs tpLH asymmetry per gate type (new, wasn't possible before
# the dual-direction extraction fix) ---
fig, axes = plt.subplots(1, len(gate_types), figsize=(5 * len(gate_types), 5))
if len(gate_types) == 1:
    axes = [axes]
for ax, gate in zip(axes, gate_types):
    sub = df[df["gate_type"] == gate]
    max_val = max(sub["tpHL_ps"].max(), sub["tpLH_ps"].max()) * 1.05
    ax.scatter(sub["tpHL_ps"], sub["tpLH_ps"], alpha=0.4, s=15)
    ax.plot([0, max_val], [0, max_val], "k--", linewidth=1, label="tpHL = tpLH")
    ax.set_xlabel("tpHL_ps")
    ax.set_ylabel("tpLH_ps")
    ax.set_title(f"{gate}: tpHL vs tpLH")
    ax.legend()
plt.tight_layout()
plt.savefig("eda_plots/eda_tphl_tplh.png")
print("Saved eda_tphl_tplh.png")
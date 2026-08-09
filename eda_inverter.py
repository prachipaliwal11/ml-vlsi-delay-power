import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("data/dataset.csv")

print("=== Basic info ===")
print(df[["vdd", "temp", "width_p", "width_n", "cload", "delay_ps", "power_mW", "pdp"]].describe())

print("\n=== Checking for anything broken ===")
print("Any negative delay?", (df["delay_ps"] < 0).any())
print("Any negative power?", (df["power_mW"] < 0).any())
print("Any missing values?\n", df.isnull().sum())

# --- Distributions of inputs and outputs ---
fig, axes = plt.subplots(2, 4, figsize=(18, 8))
cols = ["vdd", "temp", "width_p", "width_n", "cload", "delay_ps", "power_mW", "pdp"]
for ax, col in zip(axes.flat, cols):
    sns.histplot(df[col], bins=25, ax=ax, kde=True)
    ax.set_title(col)
plt.tight_layout()
plt.savefig("eda_distributions.png")
print("\nSaved eda_distributions.png")

# --- Correlation heatmap ---
plt.figure(figsize=(8, 6))
corr = df[["vdd", "temp", "width_p", "width_n", "cload", "delay_ps", "power_mW", "pdp"]].corr()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
plt.title("Correlation Matrix")
plt.tight_layout()
plt.savefig("eda_correlation.png")
print("Saved eda_correlation.png")

# --- Physical trend checks: delay/power vs each key parameter ---
fig, axes = plt.subplots(2, 5, figsize=(20, 8))
params = ["vdd", "temp", "width_p", "width_n", "cload"]
for i, param in enumerate(params):
    sns.scatterplot(data=df, x=param, y="delay_ps", ax=axes[0, i], alpha=0.5, s=15)
    axes[0, i].set_title(f"Delay vs {param}")
    sns.scatterplot(data=df, x=param, y="power_mW", ax=axes[1, i], alpha=0.5, s=15, color="orange")
    axes[1, i].set_title(f"Power vs {param}")
plt.tight_layout()
plt.savefig("eda_trends.png")
print("Saved eda_trends.png")
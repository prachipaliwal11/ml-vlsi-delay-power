import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display in WSL, so save to file instead of showing a window
import matplotlib.pyplot as plt

# wrdata with two vectors (v(in), v(out)) writes: time, in, time, out
df = pd.read_csv("inverter_output.txt", sep=r"\s+", header=None,
                  names=["time", "v_in", "time2", "v_out"])

plt.figure(figsize=(8, 4))
plt.plot(df["time"], df["v_in"], label="Input (in)")
plt.plot(df["time"], df["v_out"], label="Output (out)")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("Sky130 Inverter: Input vs Output")
plt.legend()
plt.grid(True)
plt.savefig("inverter_plot.png")
print("Saved plot to inverter_plot.png")
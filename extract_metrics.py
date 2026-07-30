import pandas as pd
import numpy as np

VDD = 1.8  # supply voltage used in this simulation

# wrdata with 3 vectors writes 3 (time, value) column pairs side by side
df = pd.read_csv("inverter_output.txt", sep=r"\s+", header=None,
                  names=["t1", "v_in", "t2", "v_out", "t3", "i_vdd"])

time = df["t1"].values
v_in = df["v_in"].values
v_out = df["v_out"].values
i_vdd = df["i_vdd"].values

def find_crossing_time(t, v, threshold, rising):
    """Find the first time `v` crosses `threshold`, going up (rising) or down (falling)."""
    for i in range(1, len(v)):
        if rising and v[i-1] < threshold <= v[i]:
            return t[i-1] + (t[i] - t[i-1]) * (threshold - v[i-1]) / (v[i] - v[i-1])
        if not rising and v[i-1] > threshold >= v[i]:
            return t[i-1] + (t[i] - t[i-1]) * (threshold - v[i-1]) / (v[i] - v[i-1])
    return None

threshold = VDD / 2  # 50% crossing point, standard delay measurement convention

# Input rises first (first pulse edge) -> output should fall in response
t_in_rise = find_crossing_time(time, v_in, threshold, rising=True)
t_out_fall = find_crossing_time(time, v_out, threshold, rising=False)

if t_in_rise is not None and t_out_fall is not None:
    delay_ps = (t_out_fall - t_in_rise) * 1e12  # convert seconds -> picoseconds
    print(f"Propagation delay (input rise -> output fall): {delay_ps:.3f} ps")
else:
    print("Could not find a clean crossing — check waveform.")

# Power: average of V(vdd) * I(vsupply) over the whole simulation
# ngspice reports source current with a sign convention where a source
# delivering current shows negative current, hence the abs().
power_watts = np.mean(np.abs(VDD * i_vdd))
power_mW = power_watts * 1e3
print(f"Average power: {power_mW:.6f} mW")
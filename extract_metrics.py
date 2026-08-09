import pandas as pd
import numpy as np
import os

# Column layout of each gate's wrdata output (value columns only, in the
# order the .cir template's `wrdata` line lists them). Add new gates here
# as they're built (e.g. "nor2": {"signals": ["a", "b", "out", "i_vdd"]}).
GATE_SIGNALS = {
    "inverter": ["v_in", "v_out", "i_vdd"],
    "nand2": ["v_a", "v_b", "v_out", "i_vdd"],
}

# Which manifest feeds which gate type. Add rows here as new gates come online.
MANIFESTS = [
    ("data/manifest.csv", "inverter"),
    ("data/manifest_nand2.csv", "nand2"),
]


def load_wrdata(output_file, signal_names):
    """wrdata repeats a time column before every value column
    (t, val1, t, val2, ...). Build column names accordingly and read."""
    cols = []
    for name in signal_names:
        cols += [f"t_{name}", name]
    df = pd.read_csv(output_file, sep=r"\s+", header=None, names=cols)
    # all t_* columns are identical (same simulation time base); just use the first
    time = df[f"t_{signal_names[0]}"].values
    return time, df


def find_crossing_time(t, v, threshold, rising, after_idx=0):
    """First time `v` crosses `threshold` in the given direction, searching
    only from index `after_idx` onward. Linear-interpolated between samples."""
    for i in range(max(1, after_idx), len(v)):
        if rising and v[i - 1] < threshold <= v[i]:
            return i, t[i - 1] + (t[i] - t[i - 1]) * (threshold - v[i - 1]) / (v[i] - v[i - 1])
        if not rising and v[i - 1] > threshold >= v[i]:
            return i, t[i - 1] + (t[i] - t[i - 1]) * (threshold - v[i - 1]) / (v[i] - v[i - 1])
    return None, None


def extract_one(output_file, vdd, gate_type, switching_signal):
    """Returns (delay_ps, power_mW) or (None, None) if no clean crossing found."""
    signal_names = GATE_SIGNALS[gate_type]
    time, df = load_wrdata(output_file, signal_names)

    threshold = vdd / 2  # 50% crossing point, standard delay measurement convention

    v_switch = df[switching_signal].values
    v_out = df["v_out"].values
    i_vdd = df["i_vdd"].values

    # Input always rises first (PULSE(0 vdd ...) in every template) -> output
    # response direction (falling) matches for inverter and NAND2 as built,
    # since NAND2's static input is always held high. If a future gate's
    # output rises in response instead, add a per-gate direction lookup here.
    switch_idx, t_switch_rise = find_crossing_time(time, v_switch, threshold, rising=True)
    if switch_idx is None:
        return None, None

    _, t_out_fall = find_crossing_time(time, v_out, threshold, rising=False, after_idx=switch_idx)
    if t_out_fall is None:
        return None, None

    delay_ps = (t_out_fall - t_switch_rise) * 1e12

    # Power: average of V(vdd) * I(vsupply) over the whole simulation.
    # ngspice reports source current with a sign convention where a source
    # delivering current shows negative current, hence the abs().
    power_mW = np.mean(np.abs(vdd * i_vdd)) * 1e3

    return delay_ps, power_mW


def main():
    dataset_rows = []

    for manifest_path, gate_type in MANIFESTS:
        if not os.path.exists(manifest_path):
            print(f"Skipping {gate_type}: {manifest_path} not found")
            continue

        manifest = pd.read_csv(manifest_path)
        for _, row in manifest.iterrows():
            vdd = float(row["vdd"])

            if gate_type == "inverter":
                switching_signal = "v_in"
            else:
                # NAND2 (and future multi-input gates): which input actually
                # switches varies per row -- MUST read from manifest, never
                # assume a fixed column, or you silently corrupt ~half the data.
                switching_signal = f"v_{row['switching_input']}"

            delay_ps, power_mW = extract_one(
                row["output_file"], vdd, gate_type, switching_signal
            )

            if delay_ps is None:
                print(f"WARNING: no clean crossing for {row['output_file']}, skipping")
                continue

            out_row = row.to_dict()
            out_row["gate_type"] = gate_type
            out_row["delay_ps"] = round(delay_ps, 4)
            out_row["power_mW"] = round(power_mW, 6)
            out_row["pdp"] = round(delay_ps * power_mW, 6)
            dataset_rows.append(out_row)

    if not dataset_rows:
        print("No data extracted. Check manifests and SPICE outputs exist.")
        return

    result_df = pd.DataFrame(dataset_rows)
    # pin the important columns to the front; keep the rest (gate-specific
    # width_* columns etc.) in whatever order pandas assembled them
    front = ["gate_type", "delay_ps", "power_mW", "pdp", "vdd", "temp", "cload"]
    remaining = [c for c in result_df.columns if c not in front]
    result_df = result_df[front + remaining]

    result_df.to_csv("data/dataset.csv", index=False)
    print(f"Wrote {len(result_df)} rows to data/dataset.csv")


if __name__ == "__main__":
    main()
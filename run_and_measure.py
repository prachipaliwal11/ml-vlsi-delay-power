import csv
import subprocess
import os
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

MANIFEST_PATH = "data/manifest.csv"
DATASET_PATH = "data/dataset.csv"

def find_crossing_time(t, v, threshold, rising):
    for i in range(1, len(v)):
        if rising and v[i-1] < threshold <= v[i]:
            return t[i-1] + (t[i] - t[i-1]) * (threshold - v[i-1]) / (v[i] - v[i-1])
        if not rising and v[i-1] > threshold >= v[i]:
            return t[i-1] + (t[i] - t[i-1]) * (threshold - v[i-1]) / (v[i] - v[i-1])
    return None

def measure(output_file, vdd):
    df = pd.read_csv(output_file, sep=r"\s+", header=None,
                      names=["t1", "v_in", "t2", "v_out", "t3", "i_vdd"])
    time, v_in, v_out, i_vdd = df["t1"].values, df["v_in"].values, df["v_out"].values, df["i_vdd"].values

    threshold = vdd / 2
    t_in_rise = find_crossing_time(time, v_in, threshold, rising=True)
    t_out_fall = find_crossing_time(time, v_out, threshold, rising=False)

    if t_in_rise is None or t_out_fall is None:
        return None, None

    delay_ps = (t_out_fall - t_in_rise) * 1e12
    power_mW = np.mean(np.abs(vdd * i_vdd)) * 1e3
    return delay_ps, power_mW

def run_one(row):
    deck_file = row["deck_file"]
    result = subprocess.run(["ngspice", "-b", deck_file], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {deck_file}")
        return None

    delay_ps, power_mW = measure(row["output_file"], float(row["vdd"]))
    if delay_ps is None:
        print(f"  Could not measure: {deck_file}")
        return None

    row["delay_ps"] = delay_ps
    row["power_mW"] = power_mW
    row["pdp"] = power_mW * delay_ps
    print(f"  done: {deck_file} -> delay={delay_ps:.2f}ps, power={power_mW:.5f}mW")
    return row

# --- Read manifest, run each deck, measure, collect results ---

if __name__ == "__main__":
    with open(MANIFEST_PATH) as f:
        rows = list(csv.DictReader(f))

    results = []
    max_workers = max(1, os.cpu_count() - 1)
    print(f"Running with {max_workers} parallel workers...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_one, row) for row in rows]
        for future in as_completed(futures):
            res = future.result()
            if res is not None:
                results.append(res)

# --- Save dataset ---

    if results:
        fieldnames = list(results[0].keys())
        with open(DATASET_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved {len(results)} rows to {DATASET_PATH}")
    else:
        print("No successful results to save.")
import csv
import os
import sys

# Maps each gate type to the wrdata column layout produced by its .cir template's
# `wrdata` line. Each entry lists the signal names in the order they appear
# (value columns only -- wrdata's repeated time columns are stripped during parsing).
GATE_SIGNAL_COLUMNS = {
    "inverter": {"signals": ["in", "out", "i_vsupply"]},
    "nand2": {"signals": ["a", "b", "out", "i_vsupply"]},
    "nor2": {"signals": ["a", "b", "out", "i_vsupply"]},
    "xor2": {"signals": ["a", "b", "out", "i_vsupply"]},
}


def parse_wrdata(output_file, signal_names):
    """Parse an ngspice `wrdata` output file into {signal_name: [values]} plus
    a shared `time` list. wrdata repeats the time column before every value
    column (time, val1, time, val2, ...), so we take every other column
    starting at 0 for time and every other starting at 1 for values."""
    time = []
    values = {name: [] for name in signal_names}
    with open(output_file) as f:
        for line in f:
            parts = line.split()
            expected_cols = 2 * len(signal_names)
            if len(parts) < expected_cols:
                continue  # skip malformed/truncated lines
            time.append(float(parts[0]))
            for i, name in enumerate(signal_names):
                values[name].append(float(parts[2 * i + 1]))
    return time, values


def find_next_crossing(time, voltages, threshold, after_idx=0):
    """First crossing of `voltages` through `threshold`, EITHER direction,
    searching from `after_idx` onward. Returns (index, interpolated_time,
    direction) or (None, None, None) if no crossing found."""
    for i in range(max(1, after_idx), len(time)):
        prev, curr = voltages[i - 1], voltages[i]
        if prev < threshold <= curr:
            t_cross = time[i - 1] + (time[i] - time[i - 1]) * (threshold - prev) / (curr - prev)
            return i, t_cross, "rising"
        if prev > threshold >= curr:
            t_cross = time[i - 1] + (time[i] - time[i - 1]) * (threshold - prev) / (curr - prev)
            return i, t_cross, "falling"
    return None, None, None


def extract_delay_power(output_file, gate_type, vdd, switching_node="in"):
    """
    Returns (tpHL_ps, tpLH_ps, delay_ps, avg_power_w), or None if a clean
    pair of measurements couldn't be found.

    Every deck's switching input is a PULSE(0 vdd ...) with TWO edges
    within the same transient run (~1ns rise, ~6ns fall) -- so both
    propagation directions are measured from one simulation. tpHL/tpLH
    are defined by the OUTPUT's actual direction (falling = tpHL, rising
    = tpLH), NOT assumed from the input's direction -- this matters
    because some gate configurations are non-inverting (e.g. XOR2 with
    its static input held at 0: out tracks the switching input directly,
    so an input RISE produces an output RISE, not a fall). Assuming
    input-rise-always-means-output-fall breaks silently for those cases.

    switching_node: name of the input signal that toggles in this run. For
    the inverter this is always "in". For NAND2/NOR2/XOR2 this MUST come
    from that row's manifest (e.g. row["switching_input"]), never assumed.
    """
    if gate_type not in GATE_SIGNAL_COLUMNS:
        raise ValueError(f"Unknown gate_type: {gate_type}")

    signal_names = GATE_SIGNAL_COLUMNS[gate_type]["signals"]
    if switching_node not in signal_names:
        raise ValueError(
            f"switching_node '{switching_node}' not in expected signals "
            f"{signal_names} for gate_type '{gate_type}'"
        )

    time, values = parse_wrdata(output_file, signal_names)
    if not time:
        return None

    half_vdd = vdd / 2
    v_switch = values[switching_node]
    v_out = values["out"]

    # First switching-input edge (either direction) -> nearest subsequent
    # output crossing (either direction) -> categorize by OUTPUT direction
    sw1_idx, t_sw1, _ = find_next_crossing(time, v_switch, half_vdd)
    if sw1_idx is None:
        return None
    out1_idx, t_out1, out1_dir = find_next_crossing(time, v_out, half_vdd, after_idx=sw1_idx + 1)
    if out1_idx is None:
        return None
    delay1_ps = (t_out1 - t_sw1) * 1e12

    # Second switching-input edge (the opposite direction, ~5ns later in
    # every template's PULSE definition) -> same pairing logic
    sw2_idx, t_sw2, _ = find_next_crossing(time, v_switch, half_vdd, after_idx=sw1_idx + 1)
    if sw2_idx is None:
        return None
    out2_idx, t_out2, out2_dir = find_next_crossing(time, v_out, half_vdd, after_idx=sw2_idx + 1)
    if out2_idx is None:
        return None
    delay2_ps = (t_out2 - t_sw2) * 1e12

    tpHL_ps = tpLH_ps = None
    for out_dir, delay_ps in [(out1_dir, delay1_ps), (out2_dir, delay2_ps)]:
        if out_dir == "falling":
            tpHL_ps = delay_ps
        elif out_dir == "rising":
            tpLH_ps = delay_ps

    if tpHL_ps is None or tpLH_ps is None:
        # both output responses landed on the same direction -- shouldn't
        # happen for a valid 2-edge measurement, treat as unmeasurable
        return None

    delay_ps = max(tpHL_ps, tpLH_ps)

    # average power over the full transient window (covers both edges)
    i_vals = values["i_vsupply"]
    avg_power_w = abs(sum(i * vdd for i in i_vals) / len(i_vals))

    return tpHL_ps, tpLH_ps, delay_ps, avg_power_w


def process_manifest(manifest_path, gate_type, dataset_rows):
    """Reads one manifest CSV, extracts metrics per row, appends dicts to
    dataset_rows (list, mutated in place) with a `gate_type` column added."""
    with open(manifest_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            vdd = float(row["vdd"])

            if gate_type == "inverter":
                switching_node = "in"
            else:
                # NAND2/NOR2/XOR2: must read from manifest, never assume
                switching_node = row["switching_input"]

            result = extract_delay_power(
                row["output_file"], gate_type, vdd, switching_node
            )
            if result is None:
                print(f"WARNING: no clean crossing pair for {row['output_file']}, skipping")
                continue

            tpHL_ps, tpLH_ps, delay_ps, power_w = result
            out_row = dict(row)
            out_row["gate_type"] = gate_type
            out_row["tpHL_ps"] = round(tpHL_ps, 4)
            out_row["tpLH_ps"] = round(tpLH_ps, 4)
            out_row["delay_ps"] = round(delay_ps, 4)
            out_row["power_mW"] = round(power_w * 1e3, 6)
            out_row["pdp"] = round(out_row["delay_ps"] * out_row["power_mW"], 6)
            dataset_rows.append(out_row)


def main():
    manifests = [
        ("data/manifest_inverter.csv", "inverter"),
        ("data/manifest_nand2.csv", "nand2"),
        ("data/manifest_nor2.csv", "nor2"),
        ("data/manifest_xor2.csv", "xor2"),
    ]

    dataset_rows = []
    for manifest_path, gate_type in manifests:
        if not os.path.exists(manifest_path):
            print(f"Skipping {gate_type}: {manifest_path} not found")
            continue
        process_manifest(manifest_path, gate_type, dataset_rows)

    if not dataset_rows:
        print("No data extracted. Check manifests and SPICE outputs exist.")
        sys.exit(1)

    # union of all fieldnames across gate types (different gates have
    # different width_* columns), sorted for stable output, with the
    # important columns pinned to the front
    all_fields = set()
    for row in dataset_rows:
        all_fields.update(row.keys())
    front = ["gate_type", "delay_ps", "tpHL_ps", "tpLH_ps", "power_mW", "pdp", "vdd", "temp", "cload"]
    remaining = sorted(all_fields - set(front))
    fieldnames = front + remaining

    out_path = "data/dataset.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in dataset_rows:
            writer.writerow(row)

    print(f"Wrote {len(dataset_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
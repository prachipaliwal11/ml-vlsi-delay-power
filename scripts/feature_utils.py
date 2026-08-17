import pandas as pd
import numpy as np

# Fixed order, single source of truth -- both train_model.py and predict.py
# import this rather than each computing their own one-hot column order,
# which is fragile (pd.get_dummies' column order isn't guaranteed stable
# across pandas versions / row orderings).
GATE_TYPES = ["inverter", "nand2", "nor2", "xor2"]

NUMERIC_FEATURES = [
    "vdd", "temp", "cload",
    "pmos_series_depth", "nmos_series_depth",
    "total_pmos_width", "total_nmos_width",
    "transistor_count", "inv_stage_width",
    "static_state",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + [f"gate_{g}" for g in GATE_TYPES]


def engineer_features(df):
    """
    Builds gate-agnostic structural features from each gate type's raw
    width_* columns, since the same column NAME (e.g. width_p1) refers to
    a structurally different transistor depending on gate_type. Used at
    training time on the full dataset.
    """
    def col(name):
        return out[name] if name in out.columns else pd.Series(0, index=out.index)

    out = df.copy()
    n = len(out)

    pmos_depth = np.zeros(n)
    nmos_depth = np.zeros(n)
    total_pmos_w = np.zeros(n)
    total_nmos_w = np.zeros(n)
    transistor_count = np.zeros(n)
    inv_stage_width = np.zeros(n)

    is_inv = out["gate_type"] == "inverter"
    pmos_depth[is_inv] = 1
    nmos_depth[is_inv] = 1
    total_pmos_w[is_inv] = col("width_p")[is_inv]
    total_nmos_w[is_inv] = col("width_n")[is_inv]
    transistor_count[is_inv] = 2

    is_nand2 = out["gate_type"] == "nand2"
    pmos_depth[is_nand2] = 1
    nmos_depth[is_nand2] = 2
    total_pmos_w[is_nand2] = col("width_p1")[is_nand2] + col("width_p2")[is_nand2]
    total_nmos_w[is_nand2] = col("width_n1")[is_nand2] + col("width_n2")[is_nand2]
    transistor_count[is_nand2] = 4

    is_nor2 = out["gate_type"] == "nor2"
    pmos_depth[is_nor2] = 2
    nmos_depth[is_nor2] = 1
    total_pmos_w[is_nor2] = col("width_p1")[is_nor2] + col("width_p2")[is_nor2]
    total_nmos_w[is_nor2] = col("width_n1")[is_nor2] + col("width_n2")[is_nor2]
    transistor_count[is_nor2] = 4

    is_xor2 = out["gate_type"] == "xor2"
    pmos_depth[is_xor2] = 2
    nmos_depth[is_xor2] = 2
    total_pmos_w[is_xor2] = (col("width_p1")[is_xor2] + col("width_p2")[is_xor2]
                              + col("width_p3")[is_xor2] + col("width_p4")[is_xor2])
    total_nmos_w[is_xor2] = (col("width_n1")[is_xor2] + col("width_n2")[is_xor2]
                              + col("width_n3")[is_xor2] + col("width_n4")[is_xor2])
    transistor_count[is_xor2] = 12
    inv_stage_width[is_xor2] = col("width_inv")[is_xor2]

    out["pmos_series_depth"] = pmos_depth
    out["nmos_series_depth"] = nmos_depth
    out["total_pmos_width"] = total_pmos_w
    out["total_nmos_width"] = total_nmos_w
    out["transistor_count"] = transistor_count
    out["inv_stage_width"] = inv_stage_width

    if "static_state" in out.columns:
        out["static_state"] = out["static_state"].fillna(-1)
    else:
        out["static_state"] = -1

    return out


def build_gate_dummies(gate_type_series):
    """Fixed-order one-hot encoding of gate_type (avoids relying on
    pd.get_dummies' incidental column ordering)."""
    return pd.DataFrame({
        f"gate_{g}": (gate_type_series == g).astype(int)
        for g in GATE_TYPES
    }, index=gate_type_series.index)


def build_training_matrix(df):
    """Full training-time feature matrix: engineer structural features,
    one-hot gate_type, return columns in FEATURE_COLUMNS order."""
    df = engineer_features(df)
    dummies = build_gate_dummies(df["gate_type"])
    X = pd.concat([df[NUMERIC_FEATURES], dummies], axis=1)
    return X[FEATURE_COLUMNS]


def build_feature_row(gate_type, vdd, temp, cload, static_state=None, **widths):
    """
    Build a single-row feature DataFrame for model.predict(), given raw
    circuit parameters for one specific sample. Mirrors engineer_features()
    exactly so training-time and prediction-time features never drift
    apart.

    widths (keyword args, depends on gate_type):
      inverter: width_p, width_n
      nand2:    width_p1, width_p2, width_n1, width_n2
      nor2:     width_p1, width_p2, width_n1, width_n2
      xor2:     width_inv, width_p1, width_p2, width_p3, width_p4,
                width_n1, width_n2, width_n3, width_n4

    static_state: only meaningful for xor2 (0 or 1, determines inverting
    vs. non-inverting behavior). Ignored for inverter (no second input).
    For nand2/nor2 it's fixed by circuit design (nand2=1, nor2=0) --
    always set correctly here regardless of what's passed in, since it's
    not a free choice for those gates.
    """
    if gate_type not in GATE_TYPES:
        raise ValueError(f"gate_type must be one of {GATE_TYPES}, got {gate_type!r}")

    if gate_type == "inverter":
        pmos_series_depth, nmos_series_depth = 1, 1
        total_pmos_width = widths["width_p"]
        total_nmos_width = widths["width_n"]
        transistor_count = 2
        inv_stage_width = 0
        resolved_static_state = -1  # no second input, matches training-time fillna(-1)

    elif gate_type == "nand2":
        pmos_series_depth, nmos_series_depth = 1, 2
        total_pmos_width = widths["width_p1"] + widths["width_p2"]
        total_nmos_width = widths["width_n1"] + widths["width_n2"]
        transistor_count = 4
        inv_stage_width = 0
        resolved_static_state = 1  # fixed by design (avoids output masking)

    elif gate_type == "nor2":
        pmos_series_depth, nmos_series_depth = 2, 1
        total_pmos_width = widths["width_p1"] + widths["width_p2"]
        total_nmos_width = widths["width_n1"] + widths["width_n2"]
        transistor_count = 4
        inv_stage_width = 0
        resolved_static_state = 0  # fixed by design (avoids output masking)

    elif gate_type == "xor2":
        pmos_series_depth, nmos_series_depth = 2, 2
        total_pmos_width = (widths["width_p1"] + widths["width_p2"]
                             + widths["width_p3"] + widths["width_p4"])
        total_nmos_width = (widths["width_n1"] + widths["width_n2"]
                             + widths["width_n3"] + widths["width_n4"])
        transistor_count = 12
        inv_stage_width = widths["width_inv"]
        if static_state is None:
            raise ValueError("xor2 requires static_state (0 or 1) -- it genuinely "
                              "affects inverting vs. non-inverting behavior")
        resolved_static_state = static_state

    row = {
        "vdd": vdd, "temp": temp, "cload": cload,
        "pmos_series_depth": pmos_series_depth,
        "nmos_series_depth": nmos_series_depth,
        "total_pmos_width": total_pmos_width,
        "total_nmos_width": total_nmos_width,
        "transistor_count": transistor_count,
        "inv_stage_width": inv_stage_width,
        "static_state": resolved_static_state,
    }
    for g in GATE_TYPES:
        row[f"gate_{g}"] = 1 if g == gate_type else 0

    return pd.DataFrame([row])[FEATURE_COLUMNS]
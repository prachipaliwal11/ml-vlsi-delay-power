import pandas as pd
import pytest

from feature_utils import (
    build_feature_row,
    build_training_matrix,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    GATE_TYPES,
)


def test_feature_columns_fixed_order():
    """FEATURE_COLUMNS must be stable -- this is what guarantees training-time
    and inference-time column order never drift apart."""
    assert FEATURE_COLUMNS == NUMERIC_FEATURES + [f"gate_{g}" for g in GATE_TYPES]


def test_build_feature_row_inverter():
    row = build_feature_row("inverter", vdd=1.8, temp=27, cload=10, width_p=1.0, width_n=1.0)
    assert list(row.columns) == FEATURE_COLUMNS
    assert row.loc[0, "gate_inverter"] == 1
    assert row.loc[0, "gate_nand2"] == 0
    assert row.loc[0, "pmos_series_depth"] == 1
    assert row.loc[0, "nmos_series_depth"] == 1
    assert row.loc[0, "transistor_count"] == 2


def test_build_feature_row_nand2():
    row = build_feature_row(
        "nand2", vdd=1.8, temp=27, cload=10,
        width_p1=1.0, width_p2=1.0, width_n1=1.2, width_n2=1.2,
    )
    # NAND2: parallel pull-up (no stacking), series pull-down
    assert row.loc[0, "pmos_series_depth"] == 1
    assert row.loc[0, "nmos_series_depth"] == 2
    assert row.loc[0, "total_pmos_width"] == pytest.approx(2.0)
    assert row.loc[0, "total_nmos_width"] == pytest.approx(2.4)
    assert row.loc[0, "transistor_count"] == 4
    assert row.loc[0, "gate_nand2"] == 1


def test_build_feature_row_nor2():
    row = build_feature_row(
        "nor2", vdd=1.8, temp=27, cload=10,
        width_p1=1.5, width_p2=1.5, width_n1=1.0, width_n2=1.0,
    )
    # NOR2: series pull-up (mirror of NAND2), parallel pull-down
    assert row.loc[0, "pmos_series_depth"] == 2
    assert row.loc[0, "nmos_series_depth"] == 1
    assert row.loc[0, "gate_nor2"] == 1


def test_build_feature_row_xor2_requires_static_state():
    """XOR2's static_state genuinely changes inverting vs. non-inverting
    behavior -- must be required, not silently defaulted."""
    with pytest.raises(ValueError):
        build_feature_row(
            "xor2", vdd=1.8, temp=27, cload=10,
            width_inv=1.0, width_p1=1.0, width_p2=1.0, width_p3=1.0, width_p4=1.0,
            width_n1=1.0, width_n2=1.0, width_n3=1.0, width_n4=1.0,
        )


def test_build_feature_row_xor2_valid():
    row = build_feature_row(
        "xor2", vdd=1.8, temp=27, cload=10, static_state=0,
        width_inv=1.0, width_p1=1.0, width_p2=1.0, width_p3=1.0, width_p4=1.0,
        width_n1=1.0, width_n2=1.0, width_n3=1.0, width_n4=1.0,
    )
    assert row.loc[0, "pmos_series_depth"] == 2
    assert row.loc[0, "nmos_series_depth"] == 2
    assert row.loc[0, "transistor_count"] == 12
    assert row.loc[0, "static_state"] == 0


def test_build_feature_row_unknown_gate_raises():
    with pytest.raises(ValueError):
        build_feature_row("and2", vdd=1.8, temp=27, cload=10)


def test_build_training_matrix_columns_and_row_count():
    df = pd.DataFrame([
        {"gate_type": "inverter", "vdd": 1.8, "temp": 27, "cload": 10,
         "width_p": 1.0, "width_n": 1.0},
        {"gate_type": "nand2", "vdd": 1.8, "temp": 27, "cload": 10,
         "width_p1": 1.0, "width_p2": 1.0, "width_n1": 1.0, "width_n2": 1.0},
    ])
    X = build_training_matrix(df)
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(X) == 2
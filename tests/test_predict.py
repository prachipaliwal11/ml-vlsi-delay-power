import os
import pytest

from predict import predict

MODELS_PRESENT = all(
    os.path.exists(f"models/{name}_model.pkl") for name in ["delay", "power"]
)

pytestmark = pytest.mark.skipif(
    not MODELS_PRESENT, reason="Trained models not present -- run train_model.py first"
)


def test_predict_inverter_returns_sane_values():
    delay, power, pdp = predict("inverter", vdd=1.8, temp=27, cload=10, width_p=1.0, width_n=1.0)
    assert delay > 0
    assert power > 0
    assert pdp == pytest.approx(delay * power)


def test_predict_nand2_returns_sane_values():
    delay, power, pdp = predict(
        "nand2", vdd=1.8, temp=27, cload=10,
        width_p1=1.0, width_p2=1.0, width_n1=1.0, width_n2=1.0,
    )
    assert delay > 0
    assert power > 0


def test_predict_nor2_returns_sane_values():
    delay, power, pdp = predict(
        "nor2", vdd=1.8, temp=27, cload=10,
        width_p1=1.0, width_p2=1.0, width_n1=1.0, width_n2=1.0,
    )
    assert delay > 0
    assert power > 0


def test_predict_xor2_returns_sane_values():
    delay, power, pdp = predict(
        "xor2", vdd=1.8, temp=27, cload=10, static_state=0,
        width_inv=1.0, width_p1=1.0, width_p2=1.0, width_p3=1.0, width_p4=1.0,
        width_n1=1.0, width_n2=1.0, width_n3=1.0, width_n4=1.0,
    )
    assert delay > 0
    assert power > 0


def test_nor2_slower_than_nand2_at_matched_widths():
    """Regression test for the physical finding validated in EDA: NOR2's
    series-PMOS pull-up should make it slower than NAND2's series-NMOS
    pull-down at matched device widths."""
    delay_nand2, _, _ = predict(
        "nand2", vdd=1.8, temp=27, cload=10,
        width_p1=1.0, width_p2=1.0, width_n1=1.0, width_n2=1.0,
    )
    delay_nor2, _, _ = predict(
        "nor2", vdd=1.8, temp=27, cload=10,
        width_p1=1.0, width_p2=1.0, width_n1=1.0, width_n2=1.0,
    )
    assert delay_nor2 > delay_nand2
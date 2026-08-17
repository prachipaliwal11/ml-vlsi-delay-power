import argparse
import joblib
import pandas as pd

from feature_utils import build_feature_row

def load_models():
    delay_model = joblib.load("models/delay_model.pkl")
    power_model = joblib.load("models/power_model.pkl")
    return delay_model, power_model


def predict(gate_type, vdd, temp, cload, static_state=None, **widths):
    delay_model, power_model = load_models()

    X = build_feature_row(
        gate_type, vdd=vdd, temp=temp, cload=cload,
        static_state=static_state, **widths,
    )

    delay_ps = delay_model.predict(X)[0]
    power_mW = power_model.predict(X)[0]
    pdp = delay_ps * power_mW

    return delay_ps, power_mW, pdp


def main():
    parser = argparse.ArgumentParser(
        description="Predict propagation delay and power for a sky130 CMOS gate "
                    "using trained Random Forest models."
    )
    subparsers = parser.add_subparsers(dest="gate", required=True, help="Gate type")

    # --- inverter ---
    p_inv = subparsers.add_parser("inverter", help="CMOS inverter")
    p_inv.add_argument("--vdd", type=float, required=True, help="Supply voltage (V), e.g. 1.8")
    p_inv.add_argument("--temp", type=float, required=True, help="Temperature (C), e.g. 27")
    p_inv.add_argument("--width_p", type=float, required=True, help="PMOS width (um)")
    p_inv.add_argument("--width_n", type=float, required=True, help="NMOS width (um)")
    p_inv.add_argument("--cload", type=float, required=True, help="Load capacitance (fF)")

    # --- nand2 ---
    p_nand2 = subparsers.add_parser("nand2", help="2-input NAND gate")
    p_nand2.add_argument("--vdd", type=float, required=True)
    p_nand2.add_argument("--temp", type=float, required=True)
    p_nand2.add_argument("--width_p1", type=float, required=True, help="PMOS 1 width (um)")
    p_nand2.add_argument("--width_p2", type=float, required=True, help="PMOS 2 width (um)")
    p_nand2.add_argument("--width_n1", type=float, required=True, help="NMOS 1 width (um)")
    p_nand2.add_argument("--width_n2", type=float, required=True, help="NMOS 2 width (um)")
    p_nand2.add_argument("--cload", type=float, required=True)

    # --- nor2 ---
    p_nor2 = subparsers.add_parser("nor2", help="2-input NOR gate")
    p_nor2.add_argument("--vdd", type=float, required=True)
    p_nor2.add_argument("--temp", type=float, required=True)
    p_nor2.add_argument("--width_p1", type=float, required=True, help="PMOS 1 width (um)")
    p_nor2.add_argument("--width_p2", type=float, required=True, help="PMOS 2 width (um)")
    p_nor2.add_argument("--width_n1", type=float, required=True, help="NMOS 1 width (um)")
    p_nor2.add_argument("--width_n2", type=float, required=True, help="NMOS 2 width (um)")
    p_nor2.add_argument("--cload", type=float, required=True)

    # --- xor2 ---
    p_xor2 = subparsers.add_parser("xor2", help="2-input XOR gate (12T static CMOS)")
    p_xor2.add_argument("--vdd", type=float, required=True)
    p_xor2.add_argument("--temp", type=float, required=True)
    p_xor2.add_argument("--width_inv", type=float, required=True, help="Local inverter width (um)")
    p_xor2.add_argument("--width_p1", type=float, required=True)
    p_xor2.add_argument("--width_p2", type=float, required=True)
    p_xor2.add_argument("--width_p3", type=float, required=True)
    p_xor2.add_argument("--width_p4", type=float, required=True)
    p_xor2.add_argument("--width_n1", type=float, required=True)
    p_xor2.add_argument("--width_n2", type=float, required=True)
    p_xor2.add_argument("--width_n3", type=float, required=True)
    p_xor2.add_argument("--width_n4", type=float, required=True)
    p_xor2.add_argument("--cload", type=float, required=True)
    p_xor2.add_argument(
        "--static_state", type=int, required=True, choices=[0, 1],
        help="Level held on the non-switching input (0 or 1) -- genuinely "
             "changes XOR2's behavior between non-inverting and inverting",
    )

    args = parser.parse_args()
    arg_dict = vars(args)
    gate_type = arg_dict.pop("gate")
    vdd = arg_dict.pop("vdd")
    temp = arg_dict.pop("temp")
    cload = arg_dict.pop("cload")
    static_state = arg_dict.pop("static_state", None)
    widths = arg_dict  # whatever's left is all width_* args for this gate

    delay_ps, power_mW, pdp = predict(
        gate_type, vdd, temp, cload, static_state=static_state, **widths
    )

    print(f"\nPredicted results for sky130 {gate_type}:")
    print(f"  Vdd={vdd}V, Temp={temp}C, Cload={cload}fF")
    for name, val in widths.items():
        print(f"  {name}={val}um")
    if static_state is not None:
        print(f"  static_state={static_state}")

    print(f"\n  Delay: {delay_ps:.3f} ps")
    print(f"  Power: {power_mW:.6f} mW")
    print(f"  PDP:   {pdp:.4f}\n")


if __name__ == "__main__":
    main()
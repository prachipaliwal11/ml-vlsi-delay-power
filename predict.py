import argparse
import joblib
import pandas as pd

FEATURES = ["vdd", "temp", "width_p", "width_n", "cload"]

def load_models():
    delay_model = joblib.load("models/delay_model.pkl")
    power_model = joblib.load("models/power_model.pkl")
    return delay_model, power_model

def predict(vdd, temp, width_p, width_n, cload):
    delay_model, power_model = load_models()

    X = pd.DataFrame([{
        "vdd": vdd, "temp": temp,
        "width_p": width_p, "width_n": width_n,
        "cload": cload,
    }])[FEATURES]

    delay_ps = delay_model.predict(X)[0]
    power_mW = power_model.predict(X)[0]
    pdp = delay_ps * power_mW

    return delay_ps, power_mW, pdp

def main():
    parser = argparse.ArgumentParser(
        description="Predict propagation delay and power for a sky130 CMOS inverter "
                    "using trained Random Forest models."
    )
    parser.add_argument("--vdd", type=float, required=True, help="Supply voltage (V), e.g. 1.8")
    parser.add_argument("--temp", type=float, required=True, help="Temperature (C), e.g. 27")
    parser.add_argument("--width_p", type=float, required=True, help="PMOS width (um)")
    parser.add_argument("--width_n", type=float, required=True, help="NMOS width (um)")
    parser.add_argument("--cload", type=float, required=True, help="Load capacitance (fF)")

    args = parser.parse_args()

    delay_ps, power_mW, pdp = predict(
        args.vdd, args.temp, args.width_p, args.width_n, args.cload
    )

    print(f"\nPredicted results for sky130 inverter:")
    print(f"  Vdd={args.vdd}V, Temp={args.temp}C, "
          f"width_p={args.width_p}um, width_n={args.width_n}um, cload={args.cload}fF")
    print(f"\n  Delay: {delay_ps:.3f} ps")
    print(f"  Power: {power_mW:.6f} mW")
    print(f"  PDP:   {pdp:.4f}\n")

if __name__ == "__main__":
    main()
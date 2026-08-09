import os
import random
import csv

# --- Locate the PDK library file dynamically (not hardcoded, works on any machine) ---
PDK_ROOT = os.environ.get("PDK_ROOT")
if not PDK_ROOT:
    raise RuntimeError("PDK_ROOT is not set. Run: export PDK_ROOT=$HOME/pdk")

MODEL_PATH = os.path.abspath("spice/models/sky130_tt_models.spice")  # same tt corner models
TEMPLATE_PATH = "spice/templates/nand2_template.cir"
DECK_DIR = "spice/generated"
OUTPUT_DIR = "spice/outputs"
MANIFEST_PATH = "data/manifest_nand2.csv"

N_SAMPLES = 500

random.seed(42)  # reproducible randomness -- same "random" values every run

with open(TEMPLATE_PATH) as f:
    template = f.read()

PULSE_TEMPLATE = "V{node} {node} 0 PULSE(0 {vdd} 1n 0.1n 0.1n 5n 10n)"
DC_TEMPLATE = "V{node} {node} 0 DC {level}"

rows = []
for i in range(N_SAMPLES):
    vdd = round(random.uniform(1.4, 2.0), 3)
    temp = round(random.uniform(-40, 125), 1)
    width_p1 = round(random.uniform(0.5, 2.0), 3)
    width_p2 = round(random.uniform(0.5, 2.0), 3)
    width_n1 = round(random.uniform(0.5, 2.0), 3)
    width_n2 = round(random.uniform(0.5, 2.0), 3)
    cload = round(random.uniform(1, 20), 2)  # femtofarads

    switching_input = random.choice(["a", "b"])
    static_input = "b" if switching_input == "a" else "a"
    static_state = random.choice([0, 1])
    static_level = vdd if static_state == 1 else 0

    vin_a_line = (PULSE_TEMPLATE.format(node="a", vdd=vdd)
                  if switching_input == "a"
                  else DC_TEMPLATE.format(node="a", level=static_level))
    vin_b_line = (PULSE_TEMPLATE.format(node="b", vdd=vdd)
                  if switching_input == "b"
                  else DC_TEMPLATE.format(node="b", level=static_level))

    deck_path = os.path.join(DECK_DIR, f"nand2_{i:04d}.cir")
    output_path = os.path.join(OUTPUT_DIR, f"nand2_{i:04d}_output.txt")

    content = template.format(
        model_path=MODEL_PATH, vdd=vdd, temp=temp,
        width_p1=width_p1, width_p2=width_p2,
        width_n1=width_n1, width_n2=width_n2, cload=cload,
        vin_a_line=vin_a_line, vin_b_line=vin_b_line,
        output_file=output_path,
    )
    with open(deck_path, "w") as f:
        f.write(content)

    rows.append({
        "deck_file": deck_path, "output_file": output_path,
        "vdd": vdd, "temp": temp,
        "width_p1": width_p1, "width_p2": width_p2,
        "width_n1": width_n1, "width_n2": width_n2, "cload": cload,
        "switching_input": switching_input,
        "static_input": static_input, "static_state": static_state,
    })

with open(MANIFEST_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {N_SAMPLES} decks in {DECK_DIR}, manifest saved to {MANIFEST_PATH}")
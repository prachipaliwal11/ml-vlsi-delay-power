import os
import glob
import random
import csv

# --- Locate the PDK library file dynamically (not hardcoded, works on any machine) ---
PDK_ROOT = os.environ.get("PDK_ROOT")
if not PDK_ROOT:
    raise RuntimeError("PDK_ROOT is not set. Run: export PDK_ROOT=$HOME/pdk")

MODEL_PATH = os.path.abspath("spice/models/sky130_tt_models.spice")
TEMPLATE_PATH = "spice/templates/inverter_template.cir"
DECK_DIR = "spice/generated"
OUTPUT_DIR = "spice/outputs"
MANIFEST_PATH = "data/manifest.csv"

N_SAMPLES = 500

random.seed(42)  # reproducible randomness -- same "random" values every run

with open(TEMPLATE_PATH) as f:
    template = f.read()

rows = []
for i in range(N_SAMPLES):
    vdd = round(random.uniform(1.4, 2.0), 3)
    temp = round(random.uniform(-40, 125), 1)
    width_p = round(random.uniform(0.5, 2.0), 3)
    width_n = round(random.uniform(0.5, 2.0), 3)
    cload = round(random.uniform(1, 20), 2)  # femtofarads

    deck_path = os.path.join(DECK_DIR, f"inverter_{i:04d}.cir")
    output_path = os.path.join(OUTPUT_DIR, f"inverter_{i:04d}_output.txt")

    content = template.format(
        model_path=MODEL_PATH, vdd=vdd, temp=temp,
        width_p=width_p, width_n=width_n, cload=cload,
        output_file=output_path,
    )
    with open(deck_path, "w") as f:
        f.write(content)

    rows.append({"deck_file": deck_path, "output_file": output_path,
                 "vdd": vdd, "temp": temp, "width_p": width_p,
                 "width_n": width_n, "cload": cload})

with open(MANIFEST_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {N_SAMPLES} decks in {DECK_DIR}, manifest saved to {MANIFEST_PATH}")
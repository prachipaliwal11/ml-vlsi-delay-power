# ML for VLSI: Delay & Power Prediction

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B)

> Predicting propagation delay (ps), power consumption (mW), and power-delay product (PDP) for CMOS logic gates — inverter, NAND2, NOR2, XOR2 — from voltage, temperature, transistor sizing, and load capacitance, using real sky130-PDK SPICE-characterized data and Random Forest.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Results](#results)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Methodology](#methodology)
- [Technical Details](#technical-details)
- [Uses](#uses)
- [Improvements](#improvements)
- [Future Scope](#future-scope)

---

## Overview

### Challenge
Characterizing a standard cell's delay and power normally means running a SPICE simulation every time you want a number — slow, and impractical for exploring a wide design space (different Vdd, temperature, transistor sizing, or load) quickly. Doing this across multiple gate topologies compounds the problem: each has a different transistor count and different structural constraints, and easy-to-miss circuit-design bugs (masked outputs, wrong-direction delay extraction) can silently corrupt half a dataset if not caught early.

### Solution
Simulate a broad, randomized sample space (500 configurations per gate, 2000 total) against real sky130 SPICE device models, extract both propagation directions (rise and fall) from each waveform, engineer gate-agnostic structural features so the different topologies can be pooled into one dataset, and train Random Forest models that predict delay and power in milliseconds instead of minutes — with a CLI and interactive app.

### Technology Used
- **Simulation:** ngspice, sky130 open-source PDK (via `volare`)
- **Machine Learning:** scikit-learn, NumPy, pandas, joblib
- **App:** Streamlit, Plotly

---

## Features
- **Four gate types characterized** — inverter, NAND2, NOR2, XOR2, each with a functionally-validated SPICE topology
- **Direction-aware delay extraction** — both `tpHL` (high-to-low) and `tpLH` (low-to-high) measured from a single simulation per sample
- **Power-delay product (PDP)** computed and surfaced everywhere alongside delay/power — dataset column, CLI output, EDA plots, and the app's Gate Comparison page
- **Unified, pooled model** — one set of models handles all four gate types via engineered structural features, not four separate models
- **CLI tool** (`predict.py`) with per-gate subcommands
- **5-page interactive app** — live predictor, dataset explorer, model insights, gate-to-gate comparison, methodology writeup

---

## Architecture

**Pipeline:**
```
SPICE deck generation
        |
        v
parallel ngspice simulation
        |
        v
delay/power extraction (tpHL/tpLH, output-direction-aware)
        |
        v
pooled dataset (data/dataset.csv)  --  delay_ps, power_mW, pdp, tpHL_ps, tpLH_ps
        |
        v
structural feature engineering (scripts/feature_utils.py)
        |
        v
Random Forest training (4 targets: delay, tpHL, tpLH, power)
        |
        +---- CLI (scripts/predict.py)          -- reports delay, power, PDP
        `---- Streamlit app (app/main.py)        -- reports delay, power, PDP
```
PDP is not trained as a separate model — it's a deterministic derived value (`delay_ps × power_mW`), computed the same way at every stage: written into `data/dataset.csv` by `extract_metrics.py`, printed by `predict.py`, and plotted in both `eda.py` and the app's Gate Comparison page.

**Directory structure:**
```
ml-vlsi-delay-power/
├── README.md                          # This file
├── NOTES.md                           # Technical decision log / bug history
├── requirements.txt                   # Python dependencies
├── .gitignore
├── .streamlit/
│   └── config.toml                    # Custom theme
│
├── scripts/                           # Core pipeline
│   ├── feature_utils.py               # Shared feature engineering (train + predict)
│   ├── generate_decks_inverter.py     # SPICE deck generator: inverter
│   ├── generate_decks_nand2.py        # SPICE deck generator: NAND2
│   ├── generate_decks_nor2.py         # SPICE deck generator: NOR2
│   ├── generate_decks_xor2.py         # SPICE deck generator: XOR2
│   ├── run_and_measure.py             # Parallel ngspice runner
│   ├── extract_metrics.py             # tpHL/tpLH-aware delay + power + PDP extraction
│   ├── train_model.py                 # Trains 4 Random Forest models
│   ├── predict.py                     # CLI, per-gate subcommands
│   └── eda.py                         # Exploratory data analysis
│
├── spice/
│   ├── templates/                     # Parameterized .cir templates (4 gates)
│   ├── models/
│   │   └── sky130_tt_models.spice     # sky130 tt-corner device models
│   ├── generated/                     # Generated decks (gitignored)
│   └── outputs/                       # Raw ngspice outputs (gitignored)
│
├── data/
│   ├── dataset.csv                    # Pooled dataset, all 4 gate types
│   └── manifest_{inverter,nand2,nor2,xor2}.csv
│
├── models/
│   ├── delay_model.pkl                # Predicts delay_ps (worst-case tpHL/tpLH)
│   ├── tpHL_model.pkl                 # Predicts high-to-low delay
│   ├── tpLH_model.pkl                 # Predicts low-to-high delay
│   └── power_model.pkl                # Predicts power_mW
│
├── eda_plots/
│   ├── eda_distributions.png          # Includes pdp distribution
│   ├── eda_correlation.png            # Includes pdp correlations
│   ├── eda_trends.png                 # delay/power vs vdd, temp, cload, per gate
│   └── eda_tphl_tplh.png              # tpHL vs tpLH asymmetry per gate
│
└── app/                               # Streamlit multi-page app
    ├── main.py                        # Entry point: streamlit run app/main.py
    ├── Predictor.py                   # Live prediction page (delay, power, PDP)
    └── pages/
        ├── 1_Dataset_Explorer.py      # Interactive EDA
        ├── 2_Model_Insights.py        # Feature importance, R², actual vs predicted
        ├── 3_Gate_Comparison.py       # Side-by-side delay/power/PDP comparison
        └── 4_Methodology.py           # Project writeup
```

---

## Results

| Target | R² |
|---|---|
| `delay_ps` (worst-case of tpHL/tpLH) | 0.841 |
| `tpHL_ps` | 0.905 |
| `tpLH_ps` | 0.839 |
| `power_mW` | 0.960 |
| `pdp` (derived: `delay_ps × power_mW`) | not separately trained — computed from the two predictions above |

Trained on 2000 samples (500 per gate type), 80/20 train-test split, `RandomizedSearchCV`-tuned Random Forest.

**Physical validation:** NOR2 shows a sharp `tpLH >> tpHL` asymmetry (series-PMOS pull-up penalty — the textbook reason NAND-based logic is generally preferred over NOR-based logic in CMOS design), while NAND2's asymmetry is much milder (series-NMOS pull-down, the faster device type). NOR2 and XOR2 also show the highest PDP of the four gates, compounding both their delay and power disadvantages — confirmed both in aggregate statistics and per-sample in the app's Dataset Explorer.

---

## Installation

```
git clone <repo-url> && cd ml-vlsi-delay-power
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export PDK_ROOT=$HOME/pdk
```

**Regenerate data from scratch:**
```
python3 scripts/generate_decks_inverter.py   # and _nand2 / _nor2 / _xor2
python3 scripts/run_and_measure.py           # --gates <type> to scope, --force to re-run
python3 scripts/extract_metrics.py           # pools all manifests into data/dataset.csv
python3 scripts/train_model.py
```

---

## Quick Start

```
git clone https://github.com/prachipaliwal11/ml-vlsi-delay-power.git && cd ml-vlsi-delay-power
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python3 scripts/predict.py nand2 --vdd 1.8 --temp 27 --width_p1 1.0 --width_p2 1.0 \
    --width_n1 1.0 --width_n2 1.0 --cload 10

streamlit run app/main.py
```
Assumes `data/dataset.csv` and `models/*.pkl` are already present (they are, if cloned as-is). See [Installation](#installation) above to regenerate everything from scratch, including the SPICE simulation step.

---

## Methodology

Each gate's SPICE topology was derived and functionally validated (truth-table checks in simulation) before generating any data — including catching, mid-project, that a naive random `static_state` for NAND2 silently masked ~49% of samples (holding the non-switching input at the wrong logic level pins the output permanently, producing no measurable delay). NOR2's mirror-image rule was applied correctly from the start the second time around.

500 samples per gate randomize Vdd (1.4–2.0V), temperature (-40 to 125°C), transistor widths, and load capacitance, simulated via `ngspice` against real sky130 `tt`-corner BSIM4 models. Since every switching input's `PULSE` waveform contains both a rising and falling edge within one transient run, both `tpHL` and `tpLH` are extracted from a single simulation — defined by the **output's** actual transition direction, not assumed from the input's direction (a distinction that matters for non-inverting configurations, like XOR2 with its static input held at 0). PDP is computed immediately alongside delay and power at this same extraction step and written into `data/dataset.csv` as its own column.

See `docs/DEVELOPMENT_LOG.md` for the full technical log — every bug found and fixed, and the reasoning behind each design decision.

---

## Technical Details

Raw transistor-width columns aren't comparable across gate types — the same column name (`width_p1`) refers to a structurally different transistor depending on topology (a parallel pull-up PMOS in NAND2 vs. a series pull-up PMOS in NOR2). Pooling them naively would silently mix incomparable quantities. Instead, every row is converted to **gate-agnostic structural features**: `pmos_series_depth` / `nmos_series_depth` (fixed per topology — the literal structural cause of the tpHL/tpLH asymmetries above), `total_pmos_width` / `total_nmos_width` (summed device width per network), `transistor_count`, plus `gate_type` as a one-hot feature.

Once the model has the structural features, `gate_type` itself ranks near the *bottom* of feature importance across all four trained targets — the structural features already encode nearly all the information gate identity would provide, suggesting the model learned something about *why* gates differ physically, not just a per-gate lookup table.

`scripts/feature_utils.py` is the single source of truth for this encoding, imported by both `train_model.py` and `predict.py`, guaranteeing training-time and inference-time features never drift apart.

**Why PDP isn't a trained target:** it's a fully deterministic function of two already-trained outputs (`delay_ps × power_mW`), so training a fifth model on it would just be re-learning a multiplication the two existing models already support — computing it directly from their predictions is exact, not approximate, and cheaper.

---

## Uses

- **Fast design-space estimation** — a delay/power/PDP estimate for a given sizing/Vdd/temp/load combination in milliseconds instead of a SPICE run
- **Sizing trade-off exploration** — the Gate Comparison app page shows how delay, power, *and* PDP shift across gate types at matched device sizing
- **CLI predictions**, scriptable into a larger flow:
  ```
  python3 scripts/predict.py nand2 --vdd 1.8 --temp 27 --width_p1 1.0 --width_p2 1.0 \
      --width_n1 1.2 --width_n2 1.2 --cload 10
  ```
  ```
  Delay: 95.443 ps
  Power: 0.005111 mW
  PDP:   0.4878
  ```
- **Interactive app**: `streamlit run app/main.py`

---

## Improvements
- Transistor widths are intentionally randomized independently rather than sized to compensate for series-stack resistance the way a real cell library would — deliberate, so the model learns a genuine width→delay/power relationship, but the dataset doesn't represent "well-designed" cells exclusively
- XOR2's local inverters share one width across all 4 transistors, rather than independently sized PMOS/NMOS
- Only the `tt` process corner is characterized — no `ff`/`ss` corner data
- No automated tests or CI yet

---

## Future Scope
- **Yosys-synthesized circuit-level estimation** — synthesize real Verilog designs into gate-level netlists (restricted to the 4 supported cell types), then aggregate per-gate predictions into a whole-circuit delay/power/PDP estimate
- **Real sky130 standard-cell library widths** — pull actual `sky130_fd_sc_hd` cell dimensions for netlist-level predictions reflecting real, taped-out cell sizing
- **Additional gate types** (AND2, OR2, 3-input gates, MUX) and **additional process corners** (`ff`/`ss`)

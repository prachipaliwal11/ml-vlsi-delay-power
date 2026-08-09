# ML for VLSI: Delay & Power Prediction

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange)

> Predicting circuit delay (ps) and power consumption (mW) from voltage, temperature, transistor sizing, and load capacitance — using SPICE-characterized data and Random Forest.

## Status
✅ Random Forest models trained: delay R²=0.965 (MAE 2.5ps), power R²=0.960 (MAE 0.0004mW). Feature importances confirm EDA findings — cload and width_n dominate delay; cload and vdd dominate power. Next: CLI prediction tool and demo.

## Overview
(coming soon — problem statement, approach)

## Setup
- Yosys, ngspice, sky130 PDK (via `volare`)
- Python 3.10+, see `requirements.txt`

## Project Structure
(coming soon)
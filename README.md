# ML for VLSI: Delay & Power Prediction

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange)

> Predicting circuit delay (ps) and power consumption (mW) from voltage, temperature, transistor sizing, and load capacitance — using SPICE-characterized data and Random Forest.

## Status
✅ Dataset generation complete: 500 samples from sky130 transistor-level SPICE simulation, sweeping Vdd (1.4-2.0V), temperature (-40 to 125°C), transistor sizing, and load capacitance.
Delay and power extracted via automated waveform measurement.
Next: exploratory data analysis and Random Forest training.

## Overview
(coming soon — problem statement, approach)

## Setup
- Yosys, ngspice, sky130 PDK (via `volare`)
- Python 3.10+, see `requirements.txt`

## Project Structure
(coming soon)
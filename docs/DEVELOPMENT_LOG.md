# Development Log

A running record of the technical decisions, bugs found, and design trade-offs behind this project. The `README.md` covers the summary; this log covers the reasoning and debugging trail behind it.

## Contents
- [Inverter Baseline: EDA Findings](#inverter-baseline-eda-findings)
- [Multi-Gate Expansion](#multi-gate-expansion)
- [Bug: NAND2 Output Masking](#bug-nand2-output-masking)
- [NOR2: Getting the Mirror-Image Rule Right the First Time](#nor2-getting-the-mirror-image-rule-right-the-first-time)
- [Bug: tpHL/tpLH Direction Assumption](#bug-tphltplh-direction-assumption)
- [Bug: Off-by-One in Edge Detection](#bug-off-by-one-in-edge-detection)
- [Timestep and Simulation Runtime](#timestep-and-simulation-runtime)
- [XOR2 Topology](#xor2-topology)
- [Structural Feature Engineering](#structural-feature-engineering)
- [Model Design: Unified vs. Per-Gate](#model-design-unified-vs-per-gate)
- [Finding: gate_type Ranks Low in Feature Importance](#finding-gate_type-ranks-low-in-feature-importance)
- [static_state Design Rules, by Gate](#static_state-design-rules-by-gate)

---

## Inverter Baseline: EDA Findings

Early single-gate exploration, before the multi-gate pipeline existed, used a delay measurement that only covered one transition (input rise → output fall). This produced a lopsided picture:

- Delay was dominated by `width_n` (correlation −0.57), while `width_p` showed almost no effect (−0.01) — expected, since `width_p` drives the opposite, unmeasured transition.
- `cload` was the single strongest driver of both delay (0.74) and power (0.71) — charging/discharging load capacitance dominates switching cost.
- `vdd` correlated moderately with power (0.53), consistent with power ∝ V².
- `width_p` still showed some power correlation (0.35) despite driving the "off" path during the measured transition — likely short-circuit/transition current, a subtlety worth flagging rather than a clean story.

Net early takeaway: `width_n` gave a real efficiency win (lower delay, minimal power cost), and `cload` was the dominant lever for both metrics. This one-sided delay measurement is exactly what later motivated the tpHL/tpLH rework described below.

---

## Multi-Gate Expansion

Extending from inverter-only to NAND2, NOR2, and XOR2 required deriving and validating each gate's SPICE topology before generating any data — series/parallel PMOS/NMOS stacks confirmed via truth-table simulation, not assumed from memory.

---

## Bug: NAND2 Output Masking

The original NAND2 deck generator randomized `static_state` (the level held on the non-switching input) between 0 and 1. For NAND2, holding the static input at **0** forces `NAND(x, 0) = 1` permanently — the pull-down network never conducts, so the switching input can't affect the output at all.

**Impact:** 243 of 500 rows (48.6%) were unmeasurable — `extract_metrics.py` correctly reported "no clean crossing" for each one, which is what surfaced the bug.

**Fix:** `static_state` hardcoded to `1` for NAND2.

---

## NOR2: Getting the Mirror-Image Rule Right the First Time

NOR2's pull-down network is parallel NMOS; its pull-up is series PMOS — the structural mirror of NAND2. This means the masking rule inverts too: holding NOR2's static input at **1** (not 0) permanently pins the output low.

This was verified by simulation *before* writing the generator (checking both `NOR(1,0)=0` and the masking case directly against a test deck), so `static_state=0` was correctly hardcoded for NOR2 from the start — no wasted regeneration cycle this time.

---

## Bug: tpHL/tpLH Direction Assumption

Every switching input's `PULSE(0, vdd, ...)` waveform contains both a rising edge (~1ns) and a falling edge (~6ns) within one transient run, so both propagation directions can be measured from a single simulation, without extra decks.

The first extraction implementation assumed a fixed mapping: "input rises → output falls" (`tpHL`) and "input falls → output rises" (`tpLH`). This silently broke for XOR2's non-inverting configuration (`static_state=0`, where the output tracks the switching input directly rather than inverting it) — an input rise there produces an output *rise*, not a fall. The algorithm kept scanning forward looking for a falling edge that would never come from that transition, and incorrectly latched onto the input's own *next* edge instead, producing phantom delays around 2770ps (roughly the full pulse period) instead of a real ~50-100ps measurement.

**Fix:** redefined `tpHL`/`tpLH` by the **output's** actual transition direction, pairing each switching-input edge with the nearest subsequent output crossing regardless of assumed polarity. This also generalizes correctly to any future non-inverting gate configuration without needing a per-gate special case.

---

## Bug: Off-by-One in Edge Detection

While fixing the above, a second bug surfaced: `find_next_crossing(..., after_idx=sw1_idx)` re-examined the same index pair that had just matched, instead of searching strictly after it — so the "second edge" search kept re-finding the first edge.

**Fix:** `after_idx=sw1_idx + 1`. Caught by directly testing `extract_delay_power()` against known files and inspecting intermediate index values rather than trusting the aggregate output.

---

## Timestep and Simulation Runtime

The original `.tran 0.02n 20n` (20ps print step) caused visible quantization in delay values once run against real BSIM4 models — many samples collapsed onto the same handful of grid points, since delays in the tens-of-ps range were coarser than the sampling grid.

Tightening to `.tran 0.001n 20n` fixed the quantization, but was only validated against a lightweight mock SPICE model. On real sky130 BSIM4 models, the same fine step across the full 20ns window caused simulation runtime to explode — one XOR2 corner hung for 29+ minutes with no sign of convergence. Root cause was mostly step count (BSIM4's per-timestep cost is far higher than a crude mock model's), compounded by a separate copy-paste mismatch that briefly left XOR2 at an even finer, unintended step size.

**Fix:** settled on `.tran 0.01n 20n` (10ps step) across all four templates — fine enough to avoid quantization, cheap enough to run in reasonable time. `run_and_measure.py` also gained a per-deck timeout and live progress counter, so a future pathological corner can't silently stall an entire batch again.

---

## XOR2 Topology

XOR2 has no simple series/parallel stack the way NAND2/NOR2 do. Implemented as the standard 12-transistor static CMOS structure: two local inverters generate `a_bar`/`b_bar`, then a complementary AOI-style network implements `Y = A'B + AB'` (pull-up) and its dual `Y' = AB + A'B'` (pull-down).

Functionally validated before scaling to 500 samples: confirmed `XOR(a,0)=a` (non-inverting) and `XOR(a,1)=NOT(a)` (inverting) both produce clean, non-degenerate transitions — meaning, unlike NAND2/NOR2, XOR2 has **no masking failure mode** at either static level, so `static_state` can safely stay randomized.

---

## Structural Feature Engineering

Raw width columns aren't comparable across gate types — the same column name (`width_p1`) refers to a structurally different transistor depending on topology: a parallel pull-up PMOS tied to `out` in NAND2, versus a series pull-up PMOS tied to an internal node in NOR2. Pooling them directly into one training matrix would silently mix incomparable quantities.

**Solution:** every row is converted to gate-agnostic structural features instead:
- `pmos_series_depth` / `nmos_series_depth` — how many transistors are stacked in series along that network. Fixed per gate type, and literally the structural cause of the tpHL/tpLH asymmetries below.
- `total_pmos_width` / `total_nmos_width` — summed device width per network, a proxy for drive strength.
- `transistor_count`, `inv_stage_width` (XOR2's local inverters only).

This logic lives in `feature_utils.py`, imported by both `train_model.py` and `predict.py`, so training-time and inference-time feature construction can never silently drift apart.

---

## Model Design: Unified vs. Per-Gate

Chose one unified model (with `gate_type` one-hot plus the structural features above) over four separate per-gate models. Trade-off: pooling four structurally different topologies is a harder learning task than fitting one gate's narrow behavior, so R² came in somewhat below the original inverter-only 0.965 — expected, not a regression. The per-gate-model alternative was kept as a documented fallback in case real-data R² had come out much worse; it didn't, so unified stood.

---

## Finding: gate_type Ranks Low in Feature Importance

Across all four trained targets (`delay_ps`, `tpHL_ps`, `tpLH_ps`, `power_mW`), the one-hot `gate_*` columns consistently rank near the *bottom* of feature importance.

This isn't the model ignoring gate identity — the structural features are themselves almost entirely determined by gate type (every NOR2 row has `pmos_series_depth=2`, always). They function as a physically meaningful stand-in for gate identity, rather than the model needing a raw label. This suggests the model learned something about *why* gates differ physically, not just a per-gate lookup table — and, in principle, should generalize more gracefully to a future gate type with similar structural features than a label-driven model would.

---

## static_state Design Rules, by Gate

| Gate | Rule | Reason |
|---|---|---|
| Inverter | N/A | Single input, no static/switching distinction |
| NAND2 | Must be `1` | `0` masks the output permanently high |
| NOR2 | Must be `0` | `1` masks the output permanently low (mirror of NAND2) |
| XOR2 | Free to vary (`0` or `1`) | No masking failure mode either way — `XOR(x,0)=x` and `XOR(x,1)=NOT(x)` are both valid, non-degenerate transitions |
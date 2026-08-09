## EDA Insights (to formalize into README later)

- Delay measurement covers only one transition (input rise -> output fall),
  so it's dominated by NMOS (width_n, corr=-0.57), while width_p shows
  almost no effect on delay (corr=-0.01) since it drives the opposite,
  unmeasured transition.
- cload is the single strongest driver of both delay (0.74) and power (0.71)
  -- charging/discharging load capacitance dominates switching cost.
- Vdd correlates moderately with power (0.53), consistent with power ~ V^2.
- width_p shows some power correlation (0.35) despite driving the
  "off" path during the measured transition -- likely short-circuit /
  transition current, worth flagging as a subtlety rather than a clean
  story.
- Net insight: width_n gives a real efficiency win (lower delay, minimal
  power cost); cload is the dominant lever for both metrics.
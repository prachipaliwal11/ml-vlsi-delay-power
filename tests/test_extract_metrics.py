from extract_metrics import find_next_crossing, extract_delay_power


def write_wrdata(path, signal_names, time, values):
    """Write a synthetic ngspice wrdata-style file: time, val1, time, val2, ..."""
    with open(path, "w") as f:
        for i in range(len(time)):
            row = []
            for name in signal_names:
                row.append(f"{time[i]:.9e}")
                row.append(f"{values[name][i]:.9e}")
            f.write(" ".join(row) + "\n")


def test_find_next_crossing_rising():
    time = [0.0, 1.0, 2.0, 3.0]
    v = [0.0, 0.0, 1.8, 1.8]
    idx, t, direction = find_next_crossing(time, v, 0.9)
    assert direction == "rising"
    assert 1.0 < t < 2.0


def test_find_next_crossing_falling():
    time = [0.0, 1.0, 2.0, 3.0]
    v = [1.8, 1.8, 0.0, 0.0]
    idx, t, direction = find_next_crossing(time, v, 0.9)
    assert direction == "falling"


def test_find_next_crossing_no_crossing_returns_none():
    time = [0.0, 1.0, 2.0]
    v = [0.0, 0.0, 0.0]
    idx, t, direction = find_next_crossing(time, v, 0.9)
    assert idx is None
    assert t is None
    assert direction is None


def test_extract_delay_power_inverting_gate(tmp_path):
    """Standard case: input rises -> output falls, input falls -> output
    rises (inverter/NAND2/NOR2's designed-correct configuration)."""
    signal_names = ["in", "out", "i_vsupply"]
    time = [i * 0.1e-9 for i in range(100)]  # 0 to 9.9ns

    def v_in(t):
        return 1.8 if 1.0e-9 <= t < 6.0e-9 else 0.0

    def v_out(t):
        # inverted response, offset ~0.2ns after input
        return 0.0 if 1.2e-9 <= t < 6.2e-9 else 1.8

    values = {
        "in": [v_in(t) for t in time],
        "out": [v_out(t) for t in time],
        "i_vsupply": [1e-6 for _ in time],
    }

    f = tmp_path / "test_inverter_output.txt"
    write_wrdata(str(f), signal_names, time, values)

    result = extract_delay_power(str(f), "inverter", vdd=1.8, switching_node="in")
    assert result is not None
    tpHL_ps, tpLH_ps, delay_ps, power_w = result

    assert 0 < tpHL_ps < 500
    assert 0 < tpLH_ps < 500
    assert delay_ps == max(tpHL_ps, tpLH_ps)


def test_extract_delay_power_non_inverting_gate_no_phantom_delay(tmp_path):
    """Regression test for the tpHL/tpLH direction bug: a non-inverting
    configuration (output tracks the switching input directly, e.g. XOR2
    with static_state=0) must still produce a small, valid tpHL/tpLH pair
    -- not a phantom near-full-period delay from incorrectly catching the
    input's own next edge instead of a real output response."""
    signal_names = ["a", "b", "out", "i_vsupply"]
    time = [i * 0.1e-9 for i in range(100)]

    def v_a(t):
        return 1.8 if 1.0e-9 <= t < 6.0e-9 else 0.0

    def v_out_noninverting(t):
        # non-inverting: output follows `a` directly, offset ~0.2ns
        return 1.8 if 1.2e-9 <= t < 6.2e-9 else 0.0

    values = {
        "a": [v_a(t) for t in time],
        "b": [0.0 for _ in time],
        "out": [v_out_noninverting(t) for t in time],
        "i_vsupply": [1e-6 for _ in time],
    }

    f = tmp_path / "test_xor2_noninverting_output.txt"
    write_wrdata(str(f), signal_names, time, values)

    result = extract_delay_power(str(f), "xor2", vdd=1.8, switching_node="a")
    assert result is not None
    tpHL_ps, tpLH_ps, delay_ps, power_w = result

    # The bug produced ~5000ps (roughly a full pulse period) instead of the
    # real ~200ps offset -- assert well below that phantom-value range.
    assert tpHL_ps < 1000
    assert tpLH_ps < 1000
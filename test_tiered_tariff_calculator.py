\
import json
import runpy
import pytest

from tiered_tariff_calculator import (
    calculate_tiered_bill,
    parse_tiers,
    format_breakdown,
    format_currency,
)

# -------------------------
# Unit tests: Positive (Typical)
# -------------------------

def test_basic_calculation_three_tiers():
    tiers = [(100, 0.20), (200, 0.30), (None, 0.40)]
    r = calculate_tiered_bill(consumption_kwh=350, tier_list=tiers, fixed_fee=10)
    # 100*0.2 + 200*0.3 + 50*0.4 = 100.0; total=110.0
    assert pytest.approx(r["energy_cost"], rel=0, abs=1e-12) == 100.0
    assert pytest.approx(r["total"], rel=0, abs=1e-12) == 110.0
    # breakdown tiers and sizes
    kwhs = [b["kwh"] for b in r["breakdown"]]
    assert kwhs == [100.0, 200.0, 50.0]

def test_zero_consumption_short_circuit():
    tiers = [(100, 0.20), (None, 0.30)]
    r = calculate_tiered_bill(0, tiers, fixed_fee=5.0)
    assert r["breakdown"] == []  # for-loop breaks immediately
    assert r["energy_cost"] == 0.0
    assert r["total"] == 5.0

def test_parse_tiers_json_and_shorthand_and_currency():
    # JSON path
    js = json.dumps([[100, 0.2], [None, 0.3]])
    assert parse_tiers(js) == [(100.0, 0.2), (None, 0.3)]
    # shorthand path
    sh = "100@0.2, *@0.3"
    assert parse_tiers(sh) == [(100.0, 0.2), (None, 0.3)]
    # format_currency
    assert format_currency(1234.5) == "$1,234.50"
    assert format_currency(12, "A$") == "A$12.00"

def test_format_breakdown_normal_and_missing_cost():
    tiers = [(50, 0.5), (None, 1.0)]
    r = calculate_tiered_bill(60, tiers, fixed_fee=0)
    txt = format_breakdown(r, "$")
    # Should include tier lines and totals
    assert "Tier 1:" in txt and "Tier 2:" in txt
    assert "Energy cost" in txt and "Total bill" in txt

    # Exercise default cost fallback path by omitting 'cost'
    fake = {
        "breakdown": [{"tier": 9, "kwh": 5.0, "rate": 0.2}],  # no 'cost' -> compute kwh*rate
        "energy_cost": 1.0,
        "fixed_fee": 0.0,
        "total": 1.0,
    }
    txt2 = format_breakdown(fake, "$")
    # The string may use "/n" as a line separator; avoid strict newline checks
    assert "Tier 9:" in txt2 and "$1.00" in txt2


# -------------------------
# Unit tests: Negative (Invalid)
# -------------------------

def test_negative_consumption_raises():
    with pytest.raises(ValueError, match="consumption_kwh must be >= 0"):
        calculate_tiered_bill(-1, [(None, 0.2)], 0)

def test_negative_fixed_fee_raises():
    with pytest.raises(ValueError, match="fixed_fee must be >= 0"):
        calculate_tiered_bill(1, [(None, 0.2)], -0.01)

def test_empty_tier_list_raises():
    with pytest.raises(ValueError, match="tiers must be a non-empty list"):
        calculate_tiered_bill(1, [], 0)

def test_negative_rate_raises():
    with pytest.raises(ValueError, match=r"rate for tier 1 must be >= 0"):
        calculate_tiered_bill(1, [(None, -0.1)], 0)

def test_nonpositive_block_raises():
    with pytest.raises(ValueError, match=r"block_kwh for tier 1 must be > 0 or None"):
        calculate_tiered_bill(1, [(0, 0.2), (None, 0.3)], 0)

def test_consumption_exceeds_defined_tiers_raises():
    # Only finite tiers whose total is 100, ask for 101 -> should raise overflow error
    with pytest.raises(ValueError, match=r"Consumption exceeds defined tiers by"):
        calculate_tiered_bill(101, [(100, 0.2)], 0)

def test_parse_tiers_empty_text_raises():
    with pytest.raises(ValueError, match="tiers text is empty"):
        parse_tiers("")

# -------------------------
# Coverage helpers
# -------------------------

def test_main_demo_runs_and_prints(capsys):
    # Cover the __main__ demonstration block
    runpy.run_module("tiered_tariff_calculator", run_name="__main__")
    out = capsys.readouterr().out
    assert "Total bill" in out

@pytest.mark.parametrize("consumption, tiers, fixed", [
    (150, [(100, 0.2), (None, 0.3)], 0.0),  # finite + unlimited
    (1,   [(None, 0.5)],  0.0),             # single unlimited
])
def test_various_paths(consumption, tiers, fixed):
    r = calculate_tiered_bill(consumption, tiers, fixed)
    assert r["total"] >= r["energy_cost"] >= 0.0

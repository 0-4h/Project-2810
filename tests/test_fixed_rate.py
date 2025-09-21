
# ---- 放在最前面 ----

# ---- 放在最前面，确保能找到 fixed_rate.py ----

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest
from fixed_rate import fixed_rate_bill, main


def test_fixed_rate_bill_normal():
    assert fixed_rate_bill(300, 0.25, 10) == 85

def test_fixed_rate_bill_zero_usage():
    assert fixed_rate_bill(0, 0.25, 10) == 10

def test_fixed_rate_bill_raises_on_negative():
    with pytest.raises(ValueError):
        fixed_rate_bill(-1, 0.25, 10)
    with pytest.raises(ValueError):
        fixed_rate_bill(100, -0.25, 10)
    with pytest.raises(ValueError):
        fixed_rate_bill(100, 0.25, -10)



# ================================
# A. 等价类测试（Typical cases）
# ================================
@pytest.mark.parametrize("usage, rate, fee, expected", [
    (100, 0.20, 10, 30),   # 典型情况 1
    (200, 0.25, 15, 65),   # 典型情况 2
    (300, 0.30, 20, 110),  # 典型情况 3
])
def test_fixed_rate_typical_cases(usage, rate, fee, expected):
    assert fixed_rate_bill(usage, rate, fee) == expected


# ================================
# B. 边界值测试（Boundary values）
# ================================
@pytest.mark.parametrize("usage, rate, fee, expected", [
    (0, 0.25, 10, 10),     # 用电量 = 0，下界
    (500, 0, 50, 50),      # 费率 = 0
    (1000, 0.25, 0, 250),  # 固定费用 = 0
])
def test_fixed_rate_boundary_cases(usage, rate, fee, expected):
    assert fixed_rate_bill(usage, rate, fee) == expected


# ================================
# C. 无效输入测试（Invalid inputs）
# ================================
# 数值为负 → ValueError
@pytest.mark.parametrize("usage, rate, fee", [
    (-1, 0.25, 10),        # 用电量为负
    (100, -0.25, 10),      # 费率为负
    (100, 0.25, -10),      # 固定费为负
])
def test_fixed_rate_invalid_valueerror(usage, rate, fee):
    with pytest.raises(ValueError):
        fixed_rate_bill(usage, rate, fee)

# 类型错误 → TypeError
@pytest.mark.parametrize("usage, rate, fee", [
    ("100", 0.25, 10),     # 用电量是字符串
    (None, 0.25, 10),      # 用电量是 None
    (100, "0.25", 10),     # 费率是字符串
    (100, 0.25, "10"),     # 固定费是字符串
])
def test_fixed_rate_invalid_typeerror(usage, rate, fee):
    with pytest.raises(TypeError):
        fixed_rate_bill(usage, rate, fee)


# ================================
# D. 主函数运行测试（I/O 隔离）
# ================================

def test_main_runs_without_error(monkeypatch, capsys):
    # 用假的 DataFrame 替代真实 CSV
    fake_df = pd.DataFrame({"kWh": [1.0, 2.0, 3.0]})
    monkeypatch.setattr("fixed_rate.pd.read_csv", lambda _: fake_df)

    main()
    out = capsys.readouterr().out
    assert "Total electricity consumption" in out
    assert "Bill Amount" in out

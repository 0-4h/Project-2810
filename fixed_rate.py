import pandas as pd

def fixed_rate_bill(total_usage, rate, fixed_fee):
    """固定费率电价：总用电量 * 费率 + 固定费。含输入校验，便于分支覆盖。"""
    if total_usage < 0 or rate < 0 or fixed_fee < 0:
        raise ValueError("Inputs must be non-negative.")
    return total_usage * rate + fixed_fee

def main():
    # 参数（按需调整）
    file_path = "sample_usage_data_month.csv"  # 你的CSV文件名
    rate = 0.25                                # $/kWh
    fixed_fee = 10                             # $/month

    # 读取与计算
    df = pd.read_csv(file_path)
    total_usage = df["kWh"].sum()              # 注意：你的列名是 kWh
    bill = fixed_rate_bill(total_usage, rate, fixed_fee)

    # 输出
    print("===== Fixed-Rate Bill =====")
    print("Total electricity consumption:", total_usage, "kWh")
    print("Rate: $", rate, "/kWh")
    print("Fixed fee: $", fixed_fee)
    print("Bill Amount: $", bill)

if __name__ == "__main__":# pragma: no cover
    main()

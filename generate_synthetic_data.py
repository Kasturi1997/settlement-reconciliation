from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


RANDOM_SEED = 42
BASE_START_DATE = datetime(2026, 4, 1, 9, 0, 0)
SIMULATION_DAYS = 35
GST_RATE = 0.18


MERCHANTS = [
    {
        "merchant_id": "M001",
        "merchant_name": "Apex Electronics",
        "category": "Electronics",
        "platform_fee_rate": 0.018,
        "settlement_tplus_days": 2,
        "merchant_city": "Bengaluru",
    },
    {
        "merchant_id": "M002",
        "merchant_name": "FreshBasket Foods",
        "category": "Grocery",
        "platform_fee_rate": 0.014,
        "settlement_tplus_days": 1,
        "merchant_city": "Mumbai",
    },
    {
        "merchant_id": "M003",
        "merchant_name": "UrbanStyle Apparel",
        "category": "Apparel",
        "platform_fee_rate": 0.020,
        "settlement_tplus_days": 2,
        "merchant_city": "Delhi",
    },
    {
        "merchant_id": "M004",
        "merchant_name": "SkillBridge Learning",
        "category": "EdTech",
        "platform_fee_rate": 0.016,
        "settlement_tplus_days": 3,
        "merchant_city": "Pune",
    },
    {
        "merchant_id": "M005",
        "merchant_name": "MediQuick Pharmacy",
        "category": "Healthcare",
        "platform_fee_rate": 0.012,
        "settlement_tplus_days": 1,
        "merchant_city": "Hyderabad",
    },
    {
        "merchant_id": "M006",
        "merchant_name": "TravelNest",
        "category": "Travel",
        "platform_fee_rate": 0.022,
        "settlement_tplus_days": 3,
        "merchant_city": "Gurugram",
    },
    {
        "merchant_id": "M007",
        "merchant_name": "HomeEase Services",
        "category": "Home Services",
        "platform_fee_rate": 0.017,
        "settlement_tplus_days": 2,
        "merchant_city": "Chennai",
    },
    {
        "merchant_id": "M008",
        "merchant_name": "FinEdge SaaS",
        "category": "SaaS",
        "platform_fee_rate": 0.015,
        "settlement_tplus_days": 2,
        "merchant_city": "Kolkata",
    },
]


PAYMENT_METHOD_FEE_RATE = {
    "UPI": 0.0020,
    "Card": 0.0105,
    "NetBanking": 0.0075,
    "Wallet": 0.0065,
}


CITY_POOL = [
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Pune",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
]


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _payment_amount_for_category(category: str) -> float:
    if category == "Travel":
        return random.uniform(2500, 18000)
    if category == "Electronics":
        return random.uniform(1200, 22000)
    if category == "SaaS":
        return random.uniform(799, 9999)
    if category == "EdTech":
        return random.uniform(499, 18000)
    if category == "Healthcare":
        return random.uniform(250, 6500)
    if category == "Grocery":
        return random.uniform(150, 3500)
    if category == "Apparel":
        return random.uniform(350, 9000)
    return random.uniform(250, 10000)


def _settlement_date(payment_datetime: datetime, tplus_days: int) -> str:
    return (payment_datetime.date() + timedelta(days=tplus_days)).isoformat()


def build_synthetic_raw_data(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Create deterministic synthetic data for a merchant settlement workflow."""
    random.seed(RANDOM_SEED)
    raw_dir.mkdir(parents=True, exist_ok=True)

    merchants_df = pd.DataFrame(MERCHANTS)
    merchants_df["gst_rate"] = GST_RATE
    merchants_df["status"] = "Active"

    orders: list[dict] = []
    payments: list[dict] = []
    refunds: list[dict] = []
    fees: list[dict] = []
    gst_rows: list[dict] = []
    chargebacks: list[dict] = []

    order_counter = 10001
    payment_counter = 70001
    refund_counter = 90001
    chargeback_counter = 30001

    for day_offset in range(SIMULATION_DAYS):
        order_day = BASE_START_DATE + timedelta(days=day_offset)
        for merchant in MERCHANTS:
            daily_orders = random.randint(3, 10)
            for _ in range(daily_orders):
                order_id = f"ORD{order_counter}"
                payment_id = f"PAY{payment_counter}"
                order_counter += 1
                payment_counter += 1

                order_datetime = order_day + timedelta(
                    hours=random.randint(0, 11),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )
                payment_datetime = order_datetime + timedelta(minutes=random.randint(1, 8))
                amount = _round_money(_payment_amount_for_category(merchant["category"]))
                method = random.choices(
                    list(PAYMENT_METHOD_FEE_RATE),
                    weights=[0.46, 0.28, 0.15, 0.11],
                    k=1,
                )[0]

                payment_status = random.choices(
                    ["Captured", "Failed"],
                    weights=[0.91, 0.09],
                    k=1,
                )[0]
                captured_amount = amount if payment_status == "Captured" else 0.0
                settlement_date = (
                    _settlement_date(payment_datetime, merchant["settlement_tplus_days"])
                    if payment_status == "Captured"
                    else ""
                )
                customer_city = random.choice(CITY_POOL)
                order_status = "Payment Captured" if payment_status == "Captured" else "Payment Failed"

                orders.append(
                    {
                        "order_id": order_id,
                        "merchant_id": merchant["merchant_id"],
                        "order_datetime": order_datetime.isoformat(sep=" "),
                        "customer_city": customer_city,
                        "order_amount": amount,
                        "order_status": order_status,
                    }
                )

                payments.append(
                    {
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "payment_datetime": payment_datetime.isoformat(sep=" "),
                        "payment_method": method,
                        "payment_status": payment_status,
                        "captured_amount": captured_amount,
                        "settlement_date": settlement_date,
                        "gateway_reference": f"GW{random.randint(10000000, 99999999)}",
                    }
                )

                if payment_status != "Captured":
                    continue

                platform_fee = _round_money(captured_amount * merchant["platform_fee_rate"])
                gateway_fee = _round_money(captured_amount * PAYMENT_METHOD_FEE_RATE[method])
                taxable_fee_amount = _round_money(platform_fee + gateway_fee)
                gst_on_fees = _round_money(taxable_fee_amount * GST_RATE)
                total_fee = _round_money(taxable_fee_amount + gst_on_fees)

                fees.append(
                    {
                        "fee_id": f"FEE{payment_id[-5:]}",
                        "order_id": order_id,
                        "payment_id": payment_id,
                        "settlement_date": settlement_date,
                        "platform_fee": platform_fee,
                        "gateway_fee": gateway_fee,
                        "total_fee_before_gst": taxable_fee_amount,
                        "gst_on_fees": gst_on_fees,
                        "total_fee_with_gst": total_fee,
                    }
                )

                is_intrastate = customer_city == merchant["merchant_city"]
                gst_rows.append(
                    {
                        "gst_id": f"GST{payment_id[-5:]}",
                        "order_id": order_id,
                        "payment_id": payment_id,
                        "settlement_date": settlement_date,
                        "taxable_fee_amount": taxable_fee_amount,
                        "gst_rate": GST_RATE,
                        "cgst_amount": _round_money(gst_on_fees / 2) if is_intrastate else 0.0,
                        "sgst_amount": _round_money(gst_on_fees / 2) if is_intrastate else 0.0,
                        "igst_amount": 0.0 if is_intrastate else gst_on_fees,
                        "total_gst_amount": gst_on_fees,
                    }
                )

                refund_probability = 0.075
                if random.random() < refund_probability:
                    refund_amount = captured_amount
                    if random.random() < 0.45:
                        refund_amount = _round_money(captured_amount * random.uniform(0.2, 0.75))
                    refund_date = payment_datetime + timedelta(days=random.randint(1, 14))
                    refund_adjustment_date = (refund_date.date() + timedelta(days=1)).isoformat()
                    refund_status = random.choices(
                        ["Success", "Initiated"],
                        weights=[0.92, 0.08],
                        k=1,
                    )[0]
                    refunds.append(
                        {
                            "refund_id": f"REF{refund_counter}",
                            "order_id": order_id,
                            "refund_datetime": refund_date.isoformat(sep=" "),
                            "refund_amount": refund_amount,
                            "refund_status": refund_status,
                            "refund_adjustment_date": refund_adjustment_date if refund_status == "Success" else "",
                            "refund_reason": random.choice(
                                [
                                    "Customer cancellation",
                                    "Duplicate payment",
                                    "Product return",
                                    "Service not delivered",
                                ]
                            ),
                        }
                    )
                    refund_counter += 1
                    orders[-1]["order_status"] = (
                        "Fully Refunded" if refund_amount == captured_amount else "Partially Refunded"
                    )

                chargeback_probability = 0.017
                if random.random() < chargeback_probability:
                    chargeback_amount = _round_money(captured_amount * random.uniform(0.4, 1.0))
                    chargeback_date = payment_datetime + timedelta(days=random.randint(5, 20))
                    chargeback_adjustment_date = (chargeback_date.date() + timedelta(days=1)).isoformat()
                    chargebacks.append(
                        {
                            "chargeback_id": f"CBK{chargeback_counter}",
                            "order_id": order_id,
                            "chargeback_datetime": chargeback_date.isoformat(sep=" "),
                            "chargeback_amount": chargeback_amount,
                            "chargeback_status": random.choice(["Accepted", "Accepted", "Under Review"]),
                            "chargeback_adjustment_date": chargeback_adjustment_date,
                            "reason_code": random.choice(
                                [
                                    "Customer dispute",
                                    "Fraud reported",
                                    "Authorization issue",
                                ]
                            ),
                        }
                    )
                    chargeback_counter += 1

    frames = {
        "merchants": merchants_df,
        "orders": pd.DataFrame(orders),
        "payments": pd.DataFrame(payments),
        "refunds": pd.DataFrame(refunds),
        "fees": pd.DataFrame(fees),
        "gst": pd.DataFrame(gst_rows),
        "chargebacks": pd.DataFrame(chargebacks),
    }

    settlements_df, payouts_df = _build_settlements_and_payouts(frames)
    frames["settlements"] = settlements_df
    frames["payouts"] = payouts_df

    for file_name, frame in frames.items():
        frame.to_csv(raw_dir / f"{file_name}.csv", index=False)

    return frames


def _build_settlements_and_payouts(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create processor settlement files with controlled exception scenarios."""
    merchants = frames["merchants"].set_index("merchant_id")
    orders = frames["orders"][["order_id", "merchant_id"]]
    payments = frames["payments"].merge(orders, on="order_id", how="left")
    captured = payments[payments["payment_status"] == "Captured"].copy()

    gross = (
        captured.groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(gross_captured_amount=("captured_amount", "sum"), captured_transaction_count=("payment_id", "count"))
    )

    refunds = frames["refunds"].merge(orders, on="order_id", how="left")
    refunds = refunds[refunds["refund_status"] == "Success"].copy()
    refund_group = (
        refunds.groupby(["merchant_id", "refund_adjustment_date"], as_index=False)
        .agg(refund_adjustment_amount=("refund_amount", "sum"), refund_count=("refund_id", "count"))
        .rename(columns={"refund_adjustment_date": "settlement_date"})
    )

    chargebacks = frames["chargebacks"].merge(orders, on="order_id", how="left")
    chargebacks = chargebacks[chargebacks["chargeback_status"] == "Accepted"].copy()
    chargeback_group = (
        chargebacks.groupby(["merchant_id", "chargeback_adjustment_date"], as_index=False)
        .agg(chargeback_amount=("chargeback_amount", "sum"), chargeback_count=("chargeback_id", "count"))
        .rename(columns={"chargeback_adjustment_date": "settlement_date"})
    )

    fees = frames["fees"].merge(orders, on="order_id", how="left")
    fee_group = (
        fees.groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(
            platform_fee=("platform_fee", "sum"),
            gateway_fee=("gateway_fee", "sum"),
            gst_on_fees=("gst_on_fees", "sum"),
        )
    )

    base = gross[["merchant_id", "settlement_date"]].copy()
    for frame in [refund_group, chargeback_group, fee_group]:
        base = pd.concat([base, frame[["merchant_id", "settlement_date"]]], ignore_index=True)
    base = base.drop_duplicates().sort_values(["merchant_id", "settlement_date"]).reset_index(drop=True)

    expected = (
        base.merge(gross, on=["merchant_id", "settlement_date"], how="left")
        .merge(refund_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(chargeback_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(fee_group, on=["merchant_id", "settlement_date"], how="left")
        .fillna(0)
    )
    expected["expected_settlement_amount"] = (
        expected["gross_captured_amount"]
        - expected["refund_adjustment_amount"]
        - expected["chargeback_amount"]
        - expected["platform_fee"]
        - expected["gateway_fee"]
        - expected["gst_on_fees"]
    ).round(2)

    target_scenarios = [
        "Refund Adjustment",
        "Fee Deduction",
        "Chargeback",
        "Settlement Delay",
        "Failed Capture",
        "GST / Tax Difference",
        "Excess Settlement",
        "Refund Adjustment",
        "Fee Deduction",
        "Chargeback",
        "Settlement Delay",
        "GST / Tax Difference",
    ]
    candidate_indexes = expected[expected["expected_settlement_amount"].abs() > 15000].index.tolist()
    random.shuffle(candidate_indexes)
    anomaly_map = {
        idx: target_scenarios[position]
        for position, idx in enumerate(candidate_indexes[: len(target_scenarios)])
    }

    settlements: list[dict] = []
    payouts: list[dict] = []
    settlement_counter = 50001
    payout_counter = 80001

    for idx, row in expected.iterrows():
        settlement_id = f"SET{settlement_counter}"
        payout_id = f"POUT{payout_counter}"
        settlement_counter += 1
        payout_counter += 1

        merchant = merchants.loc[row["merchant_id"]]
        expected_amount = _round_money(row["expected_settlement_amount"])
        adjustment_code = "MATCHED"
        processor_note = "Processor amount matches internal expectation."
        status = "Settled"
        variance = round(random.uniform(-2.0, 2.0), 2)

        scenario = anomaly_map.get(idx)
        if scenario == "Refund Adjustment":
            variance = -_round_money(max(350.0, abs(expected_amount) * random.uniform(0.025, 0.055)))
            adjustment_code = "REFUND_ADJ"
            processor_note = "Processor deducted a late refund adjustment not present in the internal refund file cutoff."
        elif scenario == "Fee Deduction":
            variance = -_round_money(max(250.0, row["gross_captured_amount"] * random.uniform(0.004, 0.009)))
            adjustment_code = "FEE_REVISION"
            processor_note = "Additional gateway fee and pricing revision applied by the processor."
        elif scenario == "Chargeback":
            variance = -_round_money(max(700.0, abs(expected_amount) * random.uniform(0.035, 0.08)))
            adjustment_code = "CHARGEBACK_ADJ"
            processor_note = "Chargeback debit applied after dispute update from issuing bank."
        elif scenario == "Settlement Delay":
            variance = -expected_amount if expected_amount > 0 else -2500.0
            adjustment_code = "PAYOUT_DELAY"
            processor_note = "Payout delayed due to processor settlement hold."
            status = "Delayed"
        elif scenario == "Failed Capture":
            variance = -_round_money(max(500.0, abs(expected_amount) * random.uniform(0.02, 0.04)))
            adjustment_code = "CAPTURE_REVERSAL"
            processor_note = "One captured transaction was reversed by gateway before payout."
        elif scenario == "GST / Tax Difference":
            variance = -_round_money(max(120.0, row["gst_on_fees"] * random.uniform(0.4, 0.9)))
            adjustment_code = "GST_DIFF"
            processor_note = "GST on processing fee differs from internal tax calculation."
        elif scenario == "Excess Settlement":
            variance = _round_money(max(450.0, abs(expected_amount) * random.uniform(0.015, 0.035)))
            adjustment_code = "PRIOR_RELEASE"
            processor_note = "Prior held settlement released in the current payout cycle."

        actual_amount = _round_money(expected_amount + variance)
        if status == "Delayed":
            actual_amount = 0.0 if expected_amount > 0 else actual_amount

        payout_date = datetime.fromisoformat(str(row["settlement_date"])) + timedelta(days=random.randint(0, 1))
        payout_status = "Delayed" if status == "Delayed" else "Paid"
        bank_reference = "" if payout_status == "Delayed" else f"UTR{random.randint(100000000000, 999999999999)}"

        settlements.append(
            {
                "settlement_id": settlement_id,
                "merchant_id": row["merchant_id"],
                "merchant_name": merchant["merchant_name"],
                "settlement_date": row["settlement_date"],
                "processor_gross_amount": _round_money(row["gross_captured_amount"]),
                "processor_deduction_amount": _round_money(
                    row["refund_adjustment_amount"]
                    + row["chargeback_amount"]
                    + row["platform_fee"]
                    + row["gateway_fee"]
                    + row["gst_on_fees"]
                    - min(variance, 0)
                ),
                "actual_settlement_amount": actual_amount,
                "settlement_status": status,
                "processor_adjustment_code": adjustment_code,
                "processor_note": processor_note,
            }
        )

        payouts.append(
            {
                "payout_id": payout_id,
                "settlement_id": settlement_id,
                "merchant_id": row["merchant_id"],
                "payout_date": payout_date.date().isoformat(),
                "payout_amount": actual_amount,
                "payout_status": payout_status,
                "bank_reference": bank_reference,
            }
        )

    return pd.DataFrame(settlements), pd.DataFrame(payouts)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    frames = build_synthetic_raw_data(raw_dir)
    print("Synthetic data generated:")
    for name, frame in frames.items():
        print(f"- {name}.csv: {len(frame):,} rows")


if __name__ == "__main__":
    main()

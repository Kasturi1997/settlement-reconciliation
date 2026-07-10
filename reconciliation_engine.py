from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


TOLERANCE_INR = 5.0


@dataclass(frozen=True)
class ReconciliationPaths:
    raw_dir: Path
    processed_dir: Path


def _money(series: pd.Series) -> pd.Series:
    return series.astype(float).round(2)


def _load_csv(raw_dir: Path, file_name: str) -> pd.DataFrame:
    path = raw_dir / file_name
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def run_reconciliation(
    raw_dir: Path,
    processed_dir: Path,
    tolerance: float = TOLERANCE_INR,
) -> dict[str, pd.DataFrame]:
    """Calculate expected settlements, compare with actuals, and write outputs."""
    processed_dir.mkdir(parents=True, exist_ok=True)

    merchants = _load_csv(raw_dir, "merchants.csv")
    orders = _load_csv(raw_dir, "orders.csv")
    payments = _load_csv(raw_dir, "payments.csv")
    refunds = _load_csv(raw_dir, "refunds.csv")
    fees = _load_csv(raw_dir, "fees.csv")
    gst = _load_csv(raw_dir, "gst.csv")
    chargebacks = _load_csv(raw_dir, "chargebacks.csv")
    settlements = _load_csv(raw_dir, "settlements.csv")
    payouts = _load_csv(raw_dir, "payouts.csv")

    merchant_lookup = merchants[["merchant_id", "merchant_name", "category", "settlement_tplus_days"]]
    order_merchants = orders[["order_id", "merchant_id"]]
    order_payment_context = orders[["order_id", "merchant_id", "order_amount"]]

    captured = payments[payments["payment_status"].eq("Captured")].merge(order_merchants, on="order_id", how="left")
    gross = (
        captured.groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(
            gross_captured_amount=("captured_amount", "sum"),
            captured_transaction_count=("payment_id", "count"),
        )
    )

    failed = payments[payments["payment_status"].eq("Failed")].merge(order_payment_context, on="order_id", how="left")
    failed = failed.merge(merchants[["merchant_id", "settlement_tplus_days"]], on="merchant_id", how="left")
    if not failed.empty:
        failed["payment_datetime"] = pd.to_datetime(failed["payment_datetime"])
        failed["settlement_date"] = (
            failed["payment_datetime"] + pd.to_timedelta(failed["settlement_tplus_days"], unit="D")
        ).dt.date.astype(str)
    failed_group = (
        failed.groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(failed_payment_count=("payment_id", "count"), failed_payment_amount=("order_amount", "sum"))
        if not failed.empty
        else pd.DataFrame(columns=["merchant_id", "settlement_date", "failed_payment_count", "failed_payment_amount"])
    )

    successful_refunds = refunds[refunds["refund_status"].eq("Success")].merge(order_merchants, on="order_id", how="left")
    refund_group = (
        successful_refunds.groupby(["merchant_id", "refund_adjustment_date"], as_index=False)
        .agg(refund_adjustment_amount=("refund_amount", "sum"), refund_count=("refund_id", "count"))
        .rename(columns={"refund_adjustment_date": "settlement_date"})
    )

    accepted_chargebacks = chargebacks[chargebacks["chargeback_status"].eq("Accepted")].merge(
        order_merchants, on="order_id", how="left"
    )
    chargeback_group = (
        accepted_chargebacks.groupby(["merchant_id", "chargeback_adjustment_date"], as_index=False)
        .agg(chargeback_amount=("chargeback_amount", "sum"), chargeback_count=("chargeback_id", "count"))
        .rename(columns={"chargeback_adjustment_date": "settlement_date"})
    )

    fee_group = (
        fees.merge(order_merchants, on="order_id", how="left")
        .groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(platform_fee=("platform_fee", "sum"), gateway_fee=("gateway_fee", "sum"))
    )
    gst_group = (
        gst.merge(order_merchants, on="order_id", how="left")
        .groupby(["merchant_id", "settlement_date"], as_index=False)
        .agg(gst_on_fees=("total_gst_amount", "sum"))
    )

    all_keys = pd.concat(
        [
            gross[["merchant_id", "settlement_date"]],
            refund_group[["merchant_id", "settlement_date"]],
            chargeback_group[["merchant_id", "settlement_date"]],
            fee_group[["merchant_id", "settlement_date"]],
            gst_group[["merchant_id", "settlement_date"]],
            settlements[["merchant_id", "settlement_date"]],
        ],
        ignore_index=True,
    ).drop_duplicates()

    result = (
        all_keys.merge(merchant_lookup, on="merchant_id", how="left")
        .merge(gross, on=["merchant_id", "settlement_date"], how="left")
        .merge(refund_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(chargeback_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(fee_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(gst_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(failed_group, on=["merchant_id", "settlement_date"], how="left")
        .merge(
            settlements[
                [
                    "settlement_id",
                    "merchant_id",
                    "settlement_date",
                    "actual_settlement_amount",
                    "settlement_status",
                    "processor_adjustment_code",
                    "processor_note",
                ]
            ],
            on=["merchant_id", "settlement_date"],
            how="left",
        )
        .merge(
            payouts[["settlement_id", "payout_status", "bank_reference"]],
            on="settlement_id",
            how="left",
        )
    )

    numeric_columns = [
        "gross_captured_amount",
        "captured_transaction_count",
        "refund_adjustment_amount",
        "refund_count",
        "chargeback_amount",
        "chargeback_count",
        "platform_fee",
        "gateway_fee",
        "gst_on_fees",
        "failed_payment_count",
        "failed_payment_amount",
        "actual_settlement_amount",
    ]
    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)

    result["settlement_status"] = result["settlement_status"].fillna("Missing In Processor File")
    result["payout_status"] = result["payout_status"].fillna("Not Found")
    result["processor_adjustment_code"] = result["processor_adjustment_code"].fillna("NO_PROCESSOR_RECORD")
    result["processor_note"] = result["processor_note"].fillna("No processor settlement row found for this merchant date.")

    result["expected_settlement_amount"] = (
        result["gross_captured_amount"]
        - result["refund_adjustment_amount"]
        - result["chargeback_amount"]
        - result["platform_fee"]
        - result["gateway_fee"]
        - result["gst_on_fees"]
    )
    result["variance_amount"] = result["actual_settlement_amount"] - result["expected_settlement_amount"]
    result["absolute_variance"] = result["variance_amount"].abs()

    money_columns = [
        "gross_captured_amount",
        "refund_adjustment_amount",
        "chargeback_amount",
        "platform_fee",
        "gateway_fee",
        "gst_on_fees",
        "actual_settlement_amount",
        "expected_settlement_amount",
        "variance_amount",
        "absolute_variance",
    ]
    for column in money_columns:
        result[column] = _money(result[column])

    result["exception_flag"] = result["absolute_variance"] > tolerance
    result["exception_type"] = result.apply(_classify_exception, axis=1)
    result["risk_priority"] = result.apply(_priority, axis=1)
    result["investigation_memo"] = result.apply(_memo, axis=1)

    result = result.sort_values(["exception_flag", "absolute_variance"], ascending=[False, False]).reset_index(drop=True)
    exceptions = result[result["exception_flag"]].copy().reset_index(drop=True)
    merchant_summary = _build_merchant_summary(result)

    result.to_csv(processed_dir / "reconciliation_results.csv", index=False)
    exceptions.to_csv(processed_dir / "exceptions.csv", index=False)
    merchant_summary.to_csv(processed_dir / "merchant_summary.csv", index=False)

    return {
        "reconciliation_results": result,
        "exceptions": exceptions,
        "merchant_summary": merchant_summary,
    }


def _classify_exception(row: pd.Series) -> str:
    if not bool(row["exception_flag"]):
        return "Matched"

    text = " ".join(
        [
            str(row.get("processor_adjustment_code", "")),
            str(row.get("processor_note", "")),
            str(row.get("settlement_status", "")),
            str(row.get("payout_status", "")),
        ]
    ).lower()

    if "delay" in text or "hold" in text or (
        row["actual_settlement_amount"] == 0 and row["expected_settlement_amount"] > TOLERANCE_INR
    ):
        return "Settlement Delay"
    if "chargeback" in text or "dispute" in text:
        return "Chargeback"
    if "refund" in text:
        return "Refund Adjustment"
    if "capture" in text or "reversal" in text:
        return "Failed Capture"
    if "gst" in text or "tax" in text:
        return "GST / Tax Difference"
    if "fee" in text or "pricing" in text:
        return "Fee Deduction"
    if row["variance_amount"] > 0:
        return "Excess Settlement"
    return "Unclassified Variance"


def _priority(row: pd.Series) -> str:
    if not bool(row["exception_flag"]):
        return "Normal"
    if row["absolute_variance"] >= 25000 or row["exception_type"] == "Settlement Delay":
        return "High"
    if row["absolute_variance"] >= 5000:
        return "Medium"
    return "Low"


def _format_inr(value: float) -> str:
    return f"INR {float(value):,.2f}"


def _memo(row: pd.Series) -> str:
    if not bool(row["exception_flag"]):
        return (
            f"{row['merchant_name']} settlement for {row['settlement_date']} matched within tolerance. "
            f"Expected {_format_inr(row['expected_settlement_amount'])} and received "
            f"{_format_inr(row['actual_settlement_amount'])}."
        )

    category = row["exception_type"]
    action_map = {
        "Settlement Delay": "Check processor SLA, payout UTR, bank return file, and whether the amount is held for risk review.",
        "Refund Adjustment": "Match refund ID, order ID, refund posting date, and processor cutoff timing.",
        "Chargeback": "Validate dispute reference, issuing bank update, and whether the chargeback was already booked internally.",
        "Fee Deduction": "Compare processor fee slab, gateway MDR, platform fee, and GST invoice against internal pricing rules.",
        "Failed Capture": "Verify gateway capture logs and confirm whether the order was reversed before payout.",
        "GST / Tax Difference": "Recalculate GST on processing fees and compare with tax invoice or processor GST statement.",
        "Excess Settlement": "Check whether a previous hold or delayed payout was released in this cycle.",
        "Unclassified Variance": "Review processor statement line items and internal ledger postings manually.",
    }
    direction = "short-settled" if row["variance_amount"] < 0 else "over-settled"
    return (
        f"{row['merchant_name']} was {direction} on {row['settlement_date']}. "
        f"Expected {_format_inr(row['expected_settlement_amount'])}, actual "
        f"{_format_inr(row['actual_settlement_amount'])}, variance "
        f"{_format_inr(row['variance_amount'])}. Likely reason: {category}. "
        f"Processor note: {row['processor_note']} Suggested action: {action_map[category]}"
    )


def _build_merchant_summary(result: pd.DataFrame) -> pd.DataFrame:
    summary = (
        result.groupby(["merchant_id", "merchant_name", "category"], as_index=False)
        .agg(
            settlement_days=("settlement_date", "nunique"),
            expected_settlement_amount=("expected_settlement_amount", "sum"),
            actual_settlement_amount=("actual_settlement_amount", "sum"),
            total_variance_amount=("variance_amount", "sum"),
            exception_count=("exception_flag", "sum"),
            high_priority_count=("risk_priority", lambda values: (values == "High").sum()),
        )
    )
    summary["exception_rate"] = (summary["exception_count"] / summary["settlement_days"]).round(4)
    money_columns = ["expected_settlement_amount", "actual_settlement_amount", "total_variance_amount"]
    for column in money_columns:
        summary[column] = _money(summary[column])
    return summary.sort_values(["exception_count", "total_variance_amount"], ascending=[False, True])


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    outputs = run_reconciliation(
        raw_dir=project_root / "data" / "raw",
        processed_dir=project_root / "data" / "processed",
    )
    result = outputs["reconciliation_results"]
    exceptions = outputs["exceptions"]
    print(f"Reconciled {len(result):,} merchant settlement rows.")
    print(f"Exceptions found: {len(exceptions):,}")


if __name__ == "__main__":
    main()

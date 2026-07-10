from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.reconciliation_engine import run_reconciliation


class ReconciliationEngineTest(unittest.TestCase):
    def test_expected_settlement_formula_and_exception_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            processed = root / "processed"
            raw.mkdir()

            pd.DataFrame(
                [
                    {
                        "merchant_id": "M001",
                        "merchant_name": "Test Merchant",
                        "category": "Test",
                        "platform_fee_rate": 0.02,
                        "settlement_tplus_days": 2,
                        "merchant_city": "Mumbai",
                        "gst_rate": 0.18,
                        "status": "Active",
                    }
                ]
            ).to_csv(raw / "merchants.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "order_id": "ORD1",
                        "merchant_id": "M001",
                        "order_datetime": "2026-04-01 10:00:00",
                        "customer_city": "Mumbai",
                        "order_amount": 1000,
                        "order_status": "Payment Captured",
                    },
                    {
                        "order_id": "ORD2",
                        "merchant_id": "M001",
                        "order_datetime": "2026-04-01 10:05:00",
                        "customer_city": "Pune",
                        "order_amount": 500,
                        "order_status": "Payment Captured",
                    },
                ]
            ).to_csv(raw / "orders.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "payment_id": "PAY1",
                        "order_id": "ORD1",
                        "payment_datetime": "2026-04-01 10:02:00",
                        "payment_method": "UPI",
                        "payment_status": "Captured",
                        "captured_amount": 1000,
                        "settlement_date": "2026-04-03",
                        "gateway_reference": "GW1",
                    },
                    {
                        "payment_id": "PAY2",
                        "order_id": "ORD2",
                        "payment_datetime": "2026-04-01 10:07:00",
                        "payment_method": "Card",
                        "payment_status": "Captured",
                        "captured_amount": 500,
                        "settlement_date": "2026-04-03",
                        "gateway_reference": "GW2",
                    },
                ]
            ).to_csv(raw / "payments.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "refund_id": "REF1",
                        "order_id": "ORD2",
                        "refund_datetime": "2026-04-02 09:00:00",
                        "refund_amount": 100,
                        "refund_status": "Success",
                        "refund_adjustment_date": "2026-04-03",
                        "refund_reason": "Customer cancellation",
                    }
                ]
            ).to_csv(raw / "refunds.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "fee_id": "FEE1",
                        "order_id": "ORD1",
                        "payment_id": "PAY1",
                        "settlement_date": "2026-04-03",
                        "platform_fee": 20,
                        "gateway_fee": 2,
                        "total_fee_before_gst": 22,
                        "gst_on_fees": 3.96,
                        "total_fee_with_gst": 25.96,
                    },
                    {
                        "fee_id": "FEE2",
                        "order_id": "ORD2",
                        "payment_id": "PAY2",
                        "settlement_date": "2026-04-03",
                        "platform_fee": 10,
                        "gateway_fee": 5.25,
                        "total_fee_before_gst": 15.25,
                        "gst_on_fees": 2.75,
                        "total_fee_with_gst": 18,
                    },
                ]
            ).to_csv(raw / "fees.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gst_id": "GST1",
                        "order_id": "ORD1",
                        "payment_id": "PAY1",
                        "settlement_date": "2026-04-03",
                        "taxable_fee_amount": 22,
                        "gst_rate": 0.18,
                        "cgst_amount": 1.98,
                        "sgst_amount": 1.98,
                        "igst_amount": 0,
                        "total_gst_amount": 3.96,
                    },
                    {
                        "gst_id": "GST2",
                        "order_id": "ORD2",
                        "payment_id": "PAY2",
                        "settlement_date": "2026-04-03",
                        "taxable_fee_amount": 15.25,
                        "gst_rate": 0.18,
                        "cgst_amount": 0,
                        "sgst_amount": 0,
                        "igst_amount": 2.75,
                        "total_gst_amount": 2.75,
                    },
                ]
            ).to_csv(raw / "gst.csv", index=False)
            pd.DataFrame(
                columns=[
                    "chargeback_id",
                    "order_id",
                    "chargeback_datetime",
                    "chargeback_amount",
                    "chargeback_status",
                    "chargeback_adjustment_date",
                    "reason_code",
                ]
            ).to_csv(raw / "chargebacks.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "settlement_id": "SET1",
                        "merchant_id": "M001",
                        "merchant_name": "Test Merchant",
                        "settlement_date": "2026-04-03",
                        "processor_gross_amount": 1500,
                        "processor_deduction_amount": 143.96,
                        "actual_settlement_amount": 1300,
                        "settlement_status": "Settled",
                        "processor_adjustment_code": "FEE_REVISION",
                        "processor_note": "Additional gateway fee applied by processor.",
                    }
                ]
            ).to_csv(raw / "settlements.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "payout_id": "POUT1",
                        "settlement_id": "SET1",
                        "merchant_id": "M001",
                        "payout_date": "2026-04-03",
                        "payout_amount": 1300,
                        "payout_status": "Paid",
                        "bank_reference": "UTR123",
                    }
                ]
            ).to_csv(raw / "payouts.csv", index=False)

            outputs = run_reconciliation(raw, processed)
            row = outputs["reconciliation_results"].iloc[0]

            self.assertAlmostEqual(row["expected_settlement_amount"], 1356.04)
            self.assertAlmostEqual(row["variance_amount"], -56.04)
            self.assertTrue(row["exception_flag"])
            self.assertEqual(row["exception_type"], "Fee Deduction")


if __name__ == "__main__":
    unittest.main()

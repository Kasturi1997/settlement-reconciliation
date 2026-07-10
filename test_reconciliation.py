"""
Unit tests for the Settlement Reconciliation Agent.

Run with: pytest tests/test_reconciliation.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import pandas as pd
from datetime import datetime

from config import CONFIG, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW
from data_generator import SyntheticDataGenerator
from reconciliation_engine import ReconciliationEngine, ReconciliationResult
from analytics import ReconciliationAnalytics


class TestConfig(unittest.TestCase):
    """Test configuration values."""

    def test_fee_rates(self):
        self.assertEqual(CONFIG.PLATFORM_FEE_PERCENT, 2.0)
        self.assertEqual(CONFIG.PAYMENT_GATEWAY_FEE_PERCENT, 1.5)
        self.assertEqual(CONFIG.GST_RATE, 18.0)

    def test_tolerance(self):
        self.assertEqual(CONFIG.EXCEPTION_TOLERANCE_ABSOLUTE, 0.01)
        self.assertEqual(CONFIG.EXCEPTION_TOLERANCE_PERCENT, 0.5)


class TestDataGenerator(unittest.TestCase):
    """Test synthetic data generation."""

    def setUp(self):
        self.generator = SyntheticDataGenerator()

    def test_merchant_generation(self):
        merchants = self.generator.merchants
        self.assertEqual(len(merchants), CONFIG.MERCHANT_COUNT)
        self.assertTrue(all("merchant_id" in m for m in merchants))
        self.assertTrue(all(m["merchant_id"].startswith("MERCH") for m in merchants))

    def test_orders_generation(self):
        orders = self.generator.generate_orders(n_orders=100)
        self.assertEqual(len(orders), 100)
        self.assertTrue(all(orders["order_amount"] > 0))
        self.assertTrue(all(orders["currency"] == "USD"))

    def test_payments_generation(self):
        orders = self.generator.generate_orders(n_orders=50)
        payments = self.generator.generate_payments(orders)
        self.assertTrue(len(payments) <= len(orders))
        self.assertTrue(all(payments["payment_amount"] > 0))

    def test_refunds_generation(self):
        orders = self.generator.generate_orders(n_orders=100)
        payments = self.generator.generate_payments(orders)
        refunds = self.generator.generate_refunds(payments)
        if not refunds.empty:
            self.assertTrue(all(refunds["refund_amount"] > 0))
            self.assertTrue(all(refunds["refund_amount"] <= refunds["refund_amount"].max()))

    def test_settlements_calculation(self):
        orders = self.generator.generate_orders(n_orders=100)
        payments = self.generator.generate_payments(orders)
        refunds = self.generator.generate_refunds(payments)
        chargebacks = self.generator.generate_chargebacks(payments)
        settlements = self.generator.generate_fees_and_settlements(orders, payments, refunds, chargebacks)

        if not settlements.empty:
            self.assertTrue(all(settlements["expected_settlement"] <= settlements["total_gmv"]))
            self.assertTrue(all(settlements["total_fees"] >= 0))


class TestReconciliationEngine(unittest.TestCase):
    """Test reconciliation logic."""

    def setUp(self):
        self.engine = ReconciliationEngine()

    def test_no_exception_within_tolerance(self):
        """Records within tolerance should not be flagged."""
        data = pd.DataFrame({
            "merchant_id": ["MERCH0001"],
            "settlement_date": ["2026-06-15"],
            "expected_settlement": [1000.00],
            "actual_settlement": [1000.00],
            "total_gmv": [1200.00],
            "n_transactions": [10],
            "total_fees": [200.00],
            "refund_amount": [0.0],
            "chargeback_amount": [0.0],
            "exception_type": [None],
        })

        results = self.engine.reconcile(data)
        self.assertFalse(results["is_exception"].iloc[0])

    def test_exception_above_tolerance(self):
        """Records exceeding tolerance should be flagged."""
        data = pd.DataFrame({
            "merchant_id": ["MERCH0001"],
            "settlement_date": ["2026-06-15"],
            "expected_settlement": [1000.00],
            "actual_settlement": [900.00],  # 10% difference
            "total_gmv": [1200.00],
            "n_transactions": [10],
            "total_fees": [200.00],
            "refund_amount": [0.0],
            "chargeback_amount": [0.0],
            "exception_type": [None],
        })

        results = self.engine.reconcile(data)
        self.assertTrue(results["is_exception"].iloc[0])
        self.assertEqual(results["difference"].iloc[0], -100.00)

    def test_severity_classification(self):
        """Test severity levels are correctly assigned."""
        data = pd.DataFrame({
            "merchant_id": ["MERCH0001", "MERCH0002", "MERCH0003"],
            "settlement_date": ["2026-06-15"] * 3,
            "expected_settlement": [1000.00, 1000.00, 1000.00],
            "actual_settlement": [500.00, 920.00, 1000.50],  # HIGH, MEDIUM, LOW/none
            "total_gmv": [1200.00, 1200.00, 1200.00],
            "n_transactions": [10, 10, 10],
            "total_fees": [200.00, 200.00, 200.00],
            "refund_amount": [0.0, 0.0, 0.0],
            "chargeback_amount": [0.0, 0.0, 0.0],
            "exception_type": [None, None, None],
        })

        results = self.engine.reconcile(data)
        self.assertEqual(results["severity"].iloc[0], SEVERITY_HIGH)
        self.assertEqual(results["severity"].iloc[1], SEVERITY_MEDIUM)

    def test_investigation_memo_generation(self):
        """Test that investigation memos are generated for exceptions."""
        data = pd.DataFrame({
            "merchant_id": ["MERCH0001"],
            "settlement_date": ["2026-06-15"],
            "expected_settlement": [1000.00],
            "actual_settlement": [900.00],
            "total_gmv": [1200.00],
            "n_transactions": [10],
            "total_fees": [200.00],
            "refund_amount": [0.0],
            "chargeback_amount": [0.0],
            "exception_type": [None],
        })

        results = self.engine.reconcile(data)
        memo = results["investigation_memo"].iloc[0]
        self.assertIn("INVESTIGATION MEMO", memo)
        self.assertIn("MERCH0001", memo)

    def test_recommendation_generation(self):
        """Test that recommendations are generated."""
        data = pd.DataFrame({
            "merchant_id": ["MERCH0001"],
            "settlement_date": ["2026-06-15"],
            "expected_settlement": [1000.00],
            "actual_settlement": [900.00],
            "total_gmv": [1200.00],
            "n_transactions": [10],
            "total_fees": [200.00],
            "refund_amount": [0.0],
            "chargeback_amount": [0.0],
            "exception_type": ["FEE_DEDUCTION_MISMATCH"],
        })

        results = self.engine.reconcile(data)
        rec = results["recommendation"].iloc[0]
        self.assertIn("fee", rec.lower())

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        results = self.engine.reconcile(pd.DataFrame())
        self.assertTrue(results.empty)


class TestAnalytics(unittest.TestCase):
    """Test analytics module."""

    def setUp(self):
        self.sample_results = pd.DataFrame({
            "merchant_id": ["MERCH0001"] * 5 + ["MERCH0002"] * 3,
            "settlement_date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03", 
                                               "2026-06-04", "2026-06-05",
                                               "2026-06-01", "2026-06-02", "2026-06-03"]),
            "expected_amount": [1000, 1200, 1100, 1300, 900, 2000, 2200, 2100],
            "actual_amount": [950, 1200, 1050, 1300, 850, 2000, 2150, 2100],
            "difference": [-50, 0, -50, 0, -50, 0, -50, 0],
            "is_exception": [True, False, True, False, True, False, True, False],
            "exception_type": ["FEE_DEDUCTION_MISMATCH", None, "FEE_DEDUCTION_MISMATCH", 
                                None, "FEE_DEDUCTION_MISMATCH", None, "REFUND_ADJUSTMENT", None],
            "severity": ["LOW", None, "LOW", None, "LOW", None, "MEDIUM", None],
        })

        self.sample_settlements = pd.DataFrame({
            "merchant_id": ["MERCH0001"] * 5 + ["MERCH0002"] * 3,
            "settlement_date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03", 
                                               "2026-06-04", "2026-06-05",
                                               "2026-06-01", "2026-06-02", "2026-06-03"]),
            "total_gmv": [1200, 1400, 1300, 1500, 1100, 2400, 2600, 2500],
        })

        self.analytics = ReconciliationAnalytics(self.sample_results, self.sample_settlements)

    def test_overall_metrics(self):
        metrics = self.analytics.get_overall_metrics()
        self.assertEqual(metrics["total_settlement_records"], 8)
        self.assertEqual(metrics["total_exceptions"], 4)
        self.assertEqual(metrics["exception_rate"], 50.0)

    def test_severity_breakdown(self):
        breakdown = self.analytics.get_severity_breakdown()
        self.assertEqual(len(breakdown), 2)  # LOW and MEDIUM

    def test_merchant_breakdown(self):
        breakdown = self.analytics.get_merchant_breakdown()
        self.assertEqual(len(breakdown), 2)
        self.assertEqual(breakdown.iloc[0]["merchant_id"], "MERCH0001")

    def test_pattern_detection(self):
        patterns = self.analytics.detect_patterns()
        # Should detect recurring FEE_DEDUCTION_MISMATCH for MERCH0001
        self.assertTrue(any(p["pattern"] == "RECURRING_EXCEPTION_TYPE" for p in patterns))


class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline."""

    def test_full_pipeline(self):
        """Test the complete pipeline end-to-end."""
        generator = SyntheticDataGenerator()
        data = generator.generate_all_data()

        engine = ReconciliationEngine()
        results = engine.reconcile(data["settlements"])

        analytics = ReconciliationAnalytics(results, data["settlements"])
        metrics = analytics.get_overall_metrics()

        self.assertGreater(metrics["total_settlement_records"], 0)
        self.assertIn("exception_rate", metrics)

        # Verify exceptions have memos
        exceptions = results[results["is_exception"] == True]
        if not exceptions.empty:
            self.assertTrue(all(exceptions["investigation_memo"].str.len() > 0))
            self.assertTrue(all(exceptions["recommendation"].str.len() > 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)

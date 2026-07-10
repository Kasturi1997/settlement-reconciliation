"""
Reconciliation Engine

Core module that compares expected vs actual settlements and identifies exceptions.
Generates investigation memos for each discrepancy found.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from config import CONFIG, EXCEPTION_REASONS, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW


@dataclass
class ReconciliationResult:
    """Result of a single reconciliation check."""
    merchant_id: str
    settlement_date: str
    expected_amount: float
    actual_amount: float
    difference: float
    difference_percent: float
    is_exception: bool
    exception_type: Optional[str]
    severity: str
    investigation_memo: str
    recommendation: str


class ReconciliationEngine:
    """
    Engine to reconcile expected settlements against actual payouts.

    The engine:
    1. Loads expected and actual settlement data
    2. Matches records by merchant_id + settlement_date
    3. Calculates differences with configurable tolerance
    4. Classifies exceptions by type and severity
    5. Generates investigation memos with root cause hypotheses
    """

    def __init__(self, config=CONFIG):
        self.config = config
        self.results: List[ReconciliationResult] = []
        self.exception_summary: Dict = {}

    def reconcile(self, settlements_df: pd.DataFrame) -> pd.DataFrame:
        """
        Main reconciliation method.

        Args:
            settlements_df: DataFrame with expected_settlement and actual_settlement columns

        Returns:
            DataFrame with reconciliation results and investigation memos
        """
        if settlements_df.empty:
            return pd.DataFrame()

        results = []

        for _, row in settlements_df.iterrows():
            result = self._reconcile_single(row)
            results.append(result)

        self.results = results
        results_df = pd.DataFrame([self._result_to_dict(r) for r in results])

        # Generate summary statistics
        self._generate_summary(results_df)

        return results_df

    def _reconcile_single(self, row: pd.Series) -> ReconciliationResult:
        """Reconcile a single settlement record."""
        expected = row["expected_settlement"]
        actual = row["actual_settlement"]
        difference = round(actual - expected, 2)

        # Avoid division by zero
        if expected != 0:
            difference_percent = round((difference / expected) * 100, 2)
        else:
            difference_percent = 0.0 if difference == 0 else 100.0

        # Determine if exception based on tolerance
        is_exception = self._is_exception(difference, difference_percent)

        # Get exception type (from synthetic injection or inferred)
        exception_type = row.get("exception_type", None)
        if pd.isna(exception_type):
            exception_type = None

        # If there's a difference but no injected type, infer from data patterns
        if is_exception and exception_type is None:
            exception_type = self._infer_exception_type(row, difference)

        # Determine severity
        severity = self._determine_severity(difference, difference_percent, exception_type)

        # Generate investigation memo
        memo = self._generate_investigation_memo(row, difference, difference_percent, 
                                                   exception_type, severity)

        # Generate recommendation
        recommendation = self._generate_recommendation(exception_type, severity, difference)

        return ReconciliationResult(
            merchant_id=row["merchant_id"],
            settlement_date=str(row["settlement_date"]),
            expected_amount=expected,
            actual_amount=actual,
            difference=difference,
            difference_percent=difference_percent,
            is_exception=is_exception,
            exception_type=exception_type,
            severity=severity,
            investigation_memo=memo,
            recommendation=recommendation
        )

    def _is_exception(self, difference: float, difference_percent: float) -> bool:
        """Check if difference exceeds tolerance thresholds."""
        abs_diff = abs(difference)
        abs_pct = abs(difference_percent)

        return (abs_diff > self.config.EXCEPTION_TOLERANCE_ABSOLUTE or 
                abs_pct > self.config.EXCEPTION_TOLERANCE_PERCENT)

    def _infer_exception_type(self, row: pd.Series, difference: float) -> str:
        """Infer exception type from data patterns when not explicitly injected."""

        # Check refund-related
        refund_amount = row.get("refund_amount", 0)
        if refund_amount > 0 and difference < 0:
            return "REFUND_ADJUSTMENT"

        # Check chargeback-related
        cb_amount = row.get("chargeback_amount", 0)
        if cb_amount > 0 and difference < 0:
            return "CHARGEBACK"

        # Check fee-related
        total_fees = row.get("total_fees", 0)
        if total_fees > 0 and abs(difference) < total_fees * 0.1:
            return "FEE_DEDUCTION_MISMATCH"

        # Check GST
        gst = row.get("gst_on_fees", 0)
        if gst > 0 and abs(difference) < gst * 0.2:
            return "GST_MISMATCH"

        # Large negative difference
        if difference < -100:
            return "MISSING_ADJUSTMENT"

        # Large positive difference
        if difference > 100:
            return "DUPLICATE_SETTLEMENT"

        # Default
        return "MISSING_ADJUSTMENT"

    def _determine_severity(self, difference: float, difference_percent: float, 
                           exception_type: Optional[str]) -> str:
        """Determine severity based on amount and type."""
        abs_diff = abs(difference)
        abs_pct = abs(difference_percent)

        # High severity criteria
        if abs_diff > 1000 or abs_pct > 10:
            return SEVERITY_HIGH

        # High severity exception types
        high_impact_types = ["CHARGEBACK", "DUPLICATE_SETTLEMENT", "FAILED_CAPTURE"]
        if exception_type in high_impact_types:
            return SEVERITY_HIGH

        # Medium severity
        if abs_diff > 100 or abs_pct > 5:
            return SEVERITY_MEDIUM

        # Low severity
        return SEVERITY_LOW

    def _generate_investigation_memo(self, row: pd.Series, difference: float,
                                     difference_percent: float, exception_type: Optional[str],
                                     severity: str) -> str:
        """Generate a detailed investigation memo for the exception."""

        merchant_id = row["merchant_id"]
        settlement_date = row["settlement_date"]
        expected = row["expected_settlement"]
        actual = row["actual_settlement"]

        memo_parts = []

        # Header
        memo_parts.append(f"=== INVESTIGATION MEMO ===")
        memo_parts.append(f"Merchant: {merchant_id} | Date: {settlement_date}")
        memo_parts.append(f"Expected: ${expected:,.2f} | Actual: ${actual:,.2f}")
        memo_parts.append(f"Difference: ${difference:,.2f} ({difference_percent:+.2f}%)")
        memo_parts.append(f"Severity: {severity}")
        memo_parts.append("")

        # Root cause analysis
        if exception_type and exception_type in EXCEPTION_REASONS:
            memo_parts.append(f"PRIMARY HYPOTHESIS: {exception_type}")
            memo_parts.append(f"Explanation: {EXCEPTION_REASONS[exception_type]}")
        else:
            memo_parts.append("PRIMARY HYPOTHESIS: UNCLASSIFIED")
            memo_parts.append("Explanation: Discrepancy does not match known patterns. Manual review required.")

        memo_parts.append("")

        # Supporting data points
        memo_parts.append("SUPPORTING DATA:")

        gmv = row.get("total_gmv", 0)
        n_txn = row.get("n_transactions", 0)
        fees = row.get("total_fees", 0)
        refunds = row.get("refund_amount", 0)
        chargebacks = row.get("chargeback_amount", 0)

        memo_parts.append(f"  - Total GMV: ${gmv:,.2f} across {n_txn} transactions")
        memo_parts.append(f"  - Total Fees: ${fees:,.2f}")
        memo_parts.append(f"  - Refunds: ${refunds:,.2f}")
        memo_parts.append(f"  - Chargebacks: ${chargebacks:,.2f}")

        # Directional analysis
        memo_parts.append("")
        if difference < 0:
            memo_parts.append("ANALYSIS: Actual settlement is LOWER than expected.")
            if refunds > 0:
                memo_parts.append(f"  -> Refunds of ${refunds:,.2f} may explain part of the shortfall.")
            if chargebacks > 0:
                memo_parts.append(f"  -> Chargebacks of ${chargebacks:,.2f} further reduce payout.")
            if fees > 0:
                memo_parts.append(f"  -> Fee calculations should be cross-checked against contract rates.")
        elif difference > 0:
            memo_parts.append("ANALYSIS: Actual settlement is HIGHER than expected.")
            memo_parts.append("  -> Possible duplicate payout, promotional credit, or fee reversal.")
            memo_parts.append("  -> Verify no duplicate settlement batch was processed.")
        else:
            memo_parts.append("ANALYSIS: Settlement matches expected amount.")

        memo_parts.append("")
        memo_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(memo_parts)

    def _generate_recommendation(self, exception_type: Optional[str], 
                                  severity: str, difference: float) -> str:
        """Generate actionable recommendation based on exception type."""

        recommendations = {
            "REFUND_ADJUSTMENT": "Verify refund timing against settlement cycle. Ensure refunds post-settlement are captured in next reconciliation batch.",
            "FEE_DEDUCTION_MISMATCH": "Pull fee contract for merchant and recalculate. Check for promotional fee waivers or tier changes.",
            "CHARGEBACK": "Review chargeback evidence. If representment possible, prepare documentation. Deduct chargeback fee from next settlement.",
            "FAILED_CAPTURE": "Confirm payment status in gateway. If auth expired, no funds were received. Update order status accordingly.",
            "SETTLEMENT_DELAY": "Check bank holiday calendar and weekend schedules. Verify if T+2 was affected. Follow up with bank for pending payout.",
            "GST_MISMATCH": "Reconcile GST ledger with fee breakdown. Verify tax rate applied matches jurisdiction requirements.",
            "DUPLICATE_SETTLEMENT": "URGENT: Initiate recovery process for duplicate payout. Notify merchant and adjust next settlement.",
            "MISSING_ADJUSTMENT": "Review adjustment log for manual credits/debits. Check promotional campaigns and penalty records.",
            "CURRENCY_CONVERSION": "Verify FX rate applied on settlement date vs order date. Check for hedging arrangements.",
            "RESERVE_HOLD": "Review risk reserve policy for merchant. Confirm hold percentage and release schedule.",
        }

        if exception_type in recommendations:
            base_rec = recommendations[exception_type]
        else:
            base_rec = "Conduct manual review of all transactions for this merchant on this date."

        if severity == SEVERITY_HIGH:
            return f"URGENT ACTION REQUIRED: {base_rec} Escalate to senior reconciliation analyst."
        elif severity == SEVERITY_MEDIUM:
            return f"ACTION REQUIRED: {base_rec} Resolve within 2 business days."
        else:
            return f"REVIEW: {base_rec} Monitor for recurrence."

    def _result_to_dict(self, result: ReconciliationResult) -> Dict:
        """Convert ReconciliationResult to dictionary."""
        return {
            "merchant_id": result.merchant_id,
            "settlement_date": result.settlement_date,
            "expected_amount": result.expected_amount,
            "actual_amount": result.actual_amount,
            "difference": result.difference,
            "difference_percent": result.difference_percent,
            "is_exception": result.is_exception,
            "exception_type": result.exception_type,
            "severity": result.severity,
            "investigation_memo": result.investigation_memo,
            "recommendation": result.recommendation,
        }

    def _generate_summary(self, results_df: pd.DataFrame):
        """Generate summary statistics from reconciliation results."""
        if results_df.empty:
            self.exception_summary = {
                "total_records": 0,
                "exceptions_found": 0,
                "exception_rate": 0.0,
                "total_discrepancy": 0.0,
                "by_severity": {},
                "by_type": {},
            }
            return

        exceptions = results_df[results_df["is_exception"] == True]

        self.exception_summary = {
            "total_records": len(results_df),
            "exceptions_found": len(exceptions),
            "exception_rate": round(len(exceptions) / len(results_df) * 100, 2),
            "total_discrepancy": round(exceptions["difference"].sum(), 2),
            "by_severity": exceptions["severity"].value_counts().to_dict(),
            "by_type": exceptions["exception_type"].value_counts().to_dict(),
        }

    def get_summary(self) -> Dict:
        """Get reconciliation summary statistics."""
        return self.exception_summary

    def export_memos(self, results_df: pd.DataFrame, output_dir: str = "reports") -> List[str]:
        """Export individual investigation memos as text files."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        exported = []
        exceptions = results_df[results_df["is_exception"] == True]

        for _, row in exceptions.iterrows():
            filename = f"memo_{row['merchant_id']}_{row['settlement_date']}.txt"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w") as f:
                f.write(row["investigation_memo"])

            exported.append(filepath)

        return exported


if __name__ == "__main__":
    # Test with sample data
    sample_data = pd.DataFrame({
        "merchant_id": ["MERCH0001", "MERCH0002"],
        "settlement_date": ["2026-06-15", "2026-06-15"],
        "expected_settlement": [1000.00, 2500.00],
        "actual_settlement": [950.00, 2500.00],
        "total_gmv": [1200.00, 3000.00],
        "n_transactions": [10, 25],
        "total_fees": [200.00, 500.00],
        "refund_amount": [0.0, 0.0],
        "chargeback_amount": [0.0, 0.0],
        "exception_type": [None, None],
    })

    engine = ReconciliationEngine()
    results = engine.reconcile(sample_data)
    print(results[["merchant_id", "difference", "is_exception", "exception_type", "severity"]])

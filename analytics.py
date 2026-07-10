"""
Analytics & Reporting Module

Provides summary statistics, trend analysis, and exception pattern detection
for settlement reconciliation data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class ReconciliationAnalytics:
    """Analytics engine for reconciliation data."""

    def __init__(self, results_df: pd.DataFrame, settlements_df: pd.DataFrame):
        self.results_df = results_df.copy()
        self.settlements_df = settlements_df.copy()

        # Convert date columns
        if "settlement_date" in self.results_df.columns:
            self.results_df["settlement_date"] = pd.to_datetime(self.results_df["settlement_date"])
        if "settlement_date" in self.settlements_df.columns:
            self.settlements_df["settlement_date"] = pd.to_datetime(self.settlements_df["settlement_date"])

    def get_overall_metrics(self) -> Dict:
        """Get high-level reconciliation metrics."""
        total_records = len(self.results_df)
        exceptions = self.results_df[self.results_df["is_exception"] == True]

        metrics = {
            "total_settlement_records": total_records,
            "total_merchants": self.results_df["merchant_id"].nunique(),
            "total_gmv": round(self.settlements_df["total_gmv"].sum(), 2),
            "total_expected_settlement": round(self.results_df["expected_amount"].sum(), 2),
            "total_actual_settlement": round(self.results_df["actual_amount"].sum(), 2),
            "total_exceptions": len(exceptions),
            "exception_rate": round(len(exceptions) / total_records * 100, 2) if total_records > 0 else 0,
            "total_discrepancy": round(exceptions["difference"].sum(), 2) if not exceptions.empty else 0,
            "avg_discrepancy": round(exceptions["difference"].abs().mean(), 2) if not exceptions.empty else 0,
            "max_positive_discrepancy": round(exceptions["difference"].max(), 2) if not exceptions.empty else 0,
            "max_negative_discrepancy": round(exceptions["difference"].min(), 2) if not exceptions.empty else 0,
        }
        return metrics

    def get_severity_breakdown(self) -> pd.DataFrame:
        """Get exception count and amount by severity."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return pd.DataFrame()

        breakdown = exceptions.groupby("severity").agg({
            "merchant_id": "count",
            "difference": ["sum", "mean", "min", "max"],
        }).reset_index()

        breakdown.columns = ["severity", "count", "total_discrepancy", "avg_discrepancy", "min_discrepancy", "max_discrepancy"]
        breakdown = breakdown.round(2)
        return breakdown

    def get_exception_type_breakdown(self) -> pd.DataFrame:
        """Get exception count and amount by type."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return pd.DataFrame()

        breakdown = exceptions.groupby("exception_type").agg({
            "merchant_id": "count",
            "difference": ["sum", "mean"],
        }).reset_index()

        breakdown.columns = ["exception_type", "count", "total_discrepancy", "avg_discrepancy"]
        breakdown = breakdown.sort_values("count", ascending=False).round(2)
        return breakdown

    def get_merchant_breakdown(self, top_n: int = 10) -> pd.DataFrame:
        """Get top merchants by exception count and amount."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return pd.DataFrame()

        merchant_stats = exceptions.groupby("merchant_id").agg({
            "difference": ["count", "sum", "mean"],
            "settlement_date": "nunique",
        }).reset_index()

        merchant_stats.columns = ["merchant_id", "exception_count", "total_discrepancy", "avg_discrepancy", "affected_days"]
        merchant_stats = merchant_stats.sort_values("total_discrepancy", ascending=False, key=abs).head(top_n)
        merchant_stats = merchant_stats.round(2)
        return merchant_stats

    def get_daily_trend(self) -> pd.DataFrame:
        """Get daily trend of exceptions and discrepancies."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return pd.DataFrame()

        daily = exceptions.groupby("settlement_date").agg({
            "merchant_id": "count",
            "difference": ["sum", "mean"],
        }).reset_index()

        daily.columns = ["settlement_date", "exception_count", "total_discrepancy", "avg_discrepancy"]
        daily = daily.sort_values("settlement_date").round(2)
        return daily

    def get_merchant_risk_score(self) -> pd.DataFrame:
        """Calculate risk score for each merchant based on exception history."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return pd.DataFrame()

        merchant_risk = exceptions.groupby("merchant_id").agg({
            "difference": ["count", "sum", "mean", "std"],
            "settlement_date": "nunique",
        }).reset_index()

        merchant_risk.columns = ["merchant_id", "exception_count", "total_discrepancy", "avg_discrepancy", "discrepancy_std", "affected_days"]

        # Calculate risk score (composite metric)
        merchant_risk["risk_score"] = (
            merchant_risk["exception_count"] * 10 +
            merchant_risk["affected_days"] * 5 +
            merchant_risk["total_discrepancy"].abs() * 0.1 +
            merchant_risk["discrepancy_std"].fillna(0) * 2
        ).round(2)

        merchant_risk = merchant_risk.sort_values("risk_score", ascending=False).round(2)
        return merchant_risk

    def detect_patterns(self) -> List[Dict]:
        """Detect recurring patterns in exceptions."""
        exceptions = self.results_df[self.results_df["is_exception"] == True]
        if exceptions.empty:
            return []

        patterns = []

        # Pattern 1: Same exception type recurring for same merchant
        type_by_merchant = exceptions.groupby(["merchant_id", "exception_type"]).size()
        recurring = type_by_merchant[type_by_merchant >= 3]
        for (merchant, exc_type), count in recurring.items():
            patterns.append({
                "pattern": "RECURRING_EXCEPTION_TYPE",
                "merchant_id": merchant,
                "exception_type": exc_type,
                "occurrences": int(count),
                "description": f"{exc_type} occurred {count} times for {merchant}. Suggests systemic issue.",
            })

        # Pattern 2: Consecutive days with exceptions
        for merchant in exceptions["merchant_id"].unique():
            merchant_ex = exceptions[exceptions["merchant_id"] == merchant].sort_values("settlement_date")
            if len(merchant_ex) < 2:
                continue

            dates = merchant_ex["settlement_date"].dt.date.tolist()
            consecutive_streaks = []
            current_streak = [dates[0]]

            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).days == 1:
                    current_streak.append(dates[i])
                else:
                    if len(current_streak) >= 3:
                        consecutive_streaks.append(current_streak.copy())
                    current_streak = [dates[i]]

            if len(current_streak) >= 3:
                consecutive_streaks.append(current_streak)

            for streak in consecutive_streaks:
                patterns.append({
                    "pattern": "CONSECUTIVE_EXCEPTIONS",
                    "merchant_id": merchant,
                    "exception_type": None,
                    "occurrences": len(streak),
                    "description": f"{merchant} had exceptions on {len(streak)} consecutive days ({streak[0]} to {streak[-1]}).",
                })

        # Pattern 3: Weekend/holiday settlement delays
        exceptions["day_of_week"] = exceptions["settlement_date"].dt.dayofweek
        weekend_delays = exceptions[
            (exceptions["exception_type"] == "SETTLEMENT_DELAY") & 
            (exceptions["day_of_week"].isin([5, 6]))
        ]
        if not weekend_delays.empty:
            patterns.append({
                "pattern": "WEEKEND_SETTLEMENT_DELAY",
                "merchant_id": None,
                "exception_type": "SETTLEMENT_DELAY",
                "occurrences": len(weekend_delays),
                "description": f"{len(weekend_delays)} settlement delays occurred on weekends. Review T+2 logic for non-business days.",
            })

        return patterns


if __name__ == "__main__":
    # Test with sample data
    sample_results = pd.DataFrame({
        "merchant_id": ["MERCH0001"] * 5 + ["MERCH0002"] * 3,
        "settlement_date": pd.date_range("2026-06-01", periods=5).tolist() + pd.date_range("2026-06-01", periods=3).tolist(),
        "expected_amount": [1000, 1200, 1100, 1300, 900, 2000, 2200, 2100],
        "actual_amount": [950, 1200, 1050, 1300, 850, 2000, 2150, 2100],
        "difference": [-50, 0, -50, 0, -50, 0, -50, 0],
        "is_exception": [True, False, True, False, True, False, True, False],
        "exception_type": ["FEE_DEDUCTION_MISMATCH", None, "FEE_DEDUCTION_MISMATCH", None, "FEE_DEDUCTION_MISMATCH", None, "REFUND_ADJUSTMENT", None],
        "severity": ["LOW", None, "LOW", None, "LOW", None, "MEDIUM", None],
    })

    sample_settlements = pd.DataFrame({
        "merchant_id": ["MERCH0001"] * 5 + ["MERCH0002"] * 3,
        "settlement_date": pd.date_range("2026-06-01", periods=5).tolist() + pd.date_range("2026-06-01", periods=3).tolist(),
        "total_gmv": [1200, 1400, 1300, 1500, 1100, 2400, 2600, 2500],
    })

    analytics = ReconciliationAnalytics(sample_results, sample_settlements)
    print("Overall Metrics:")
    print(analytics.get_overall_metrics())
    print("\nSeverity Breakdown:")
    print(analytics.get_severity_breakdown())
    print("\nPatterns:")
    for p in analytics.detect_patterns():
        print(f"  - {p['description']}")

"""
Settlement & Reconciliation Exception Agent - Main Pipeline

Orchestrates the full workflow:
1. Generate synthetic data
2. Calculate expected settlements
3. Reconcile against actual settlements
4. Generate investigation memos
5. Produce analytics and dashboards
6. Export reports

Usage:
    python src/main.py
"""

import os
import sys
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from data_generator import SyntheticDataGenerator
from reconciliation_engine import ReconciliationEngine
from analytics import ReconciliationAnalytics
from dashboard import ReconciliationDashboard


def run_pipeline(output_dir: str = "data", generate_dashboard: bool = True, 
                 export_memos: bool = True):
    """
    Run the complete reconciliation pipeline.

    Args:
        output_dir: Directory to save output files
        generate_dashboard: Whether to generate HTML dashboard
        export_memos: Whether to export individual investigation memos

    Returns:
        Dictionary with pipeline results and file paths
    """
    print("=" * 70)
    print("SETTLEMENT & RECONCILIATION EXCEPTION AGENT")
    print("=" * 70)
    print(f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {CONFIG.__dict__}")
    print("=" * 70)

    # Step 1: Generate synthetic data
    print("\n[STEP 1/6] Generating synthetic financial data...")
    generator = SyntheticDataGenerator()
    data = generator.generate_all_data()

    # Save raw data
    raw_dir = os.path.join(output_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    for name, df in data.items():
        filepath = os.path.join(raw_dir, f"{name}.csv")
        df.to_csv(filepath, index=False)
        print(f"  Saved: {filepath} ({len(df)} records)")

    # Step 2: Run reconciliation engine
    print("\n[STEP 2/6] Running reconciliation engine...")
    engine = ReconciliationEngine()
    settlements_df = data["settlements"]
    results_df = engine.reconcile(settlements_df)

    # Save reconciliation results
    processed_dir = os.path.join(output_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    results_path = os.path.join(processed_dir, "reconciliation_results.csv")
    results_df.to_csv(results_path, index=False)
    print(f"  Saved: {results_path} ({len(results_df)} records)")

    # Step 3: Generate analytics
    print("\n[STEP 3/6] Generating analytics...")
    analytics = ReconciliationAnalytics(results_df, settlements_df)

    metrics = analytics.get_overall_metrics()
    print(f"  Total Records: {metrics['total_settlement_records']}")
    print(f"  Exceptions Found: {metrics['total_exceptions']} ({metrics['exception_rate']}%)")
    print(f"  Total Discrepancy: ${metrics['total_discrepancy']:,.2f}")
    print(f"  Avg Discrepancy: ${metrics['avg_discrepancy']:,.2f}")

    # Save analytics summary
    summary_path = os.path.join(processed_dir, "analytics_summary.json")
    import json
    with open(summary_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Saved: {summary_path}")

    # Step 4: Export investigation memos
    if export_memos:
        print("\n[STEP 4/6] Exporting investigation memos...")
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        memo_files = engine.export_memos(results_df, output_dir=reports_dir)
        print(f"  Exported {len(memo_files)} investigation memos to {reports_dir}/")

    # Step 5: Generate dashboard
    if generate_dashboard:
        print("\n[STEP 5/6] Generating interactive dashboard...")
        dashboard = ReconciliationDashboard(results_df, settlements_df, analytics)
        dashboard_path = dashboard.generate_dashboard("dashboard/index.html")
        table_path = dashboard.generate_exception_table("dashboard/exceptions.html", top_n=100)
        print(f"  Dashboard: {dashboard_path}")
        print(f"  Exception Table: {table_path}")

    # Step 6: Generate summary report
    print("\n[STEP 6/6] Generating summary report...")
    generate_summary_report(results_df, settlements_df, analytics, "reports/summary_report.txt")

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  - Raw data: {raw_dir}/")
    print(f"  - Processed data: {processed_dir}/")
    print(f"  - Investigation memos: reports/")
    print(f"  - Dashboard: dashboard/index.html")
    print(f"  - Exception table: dashboard/exceptions.html")
    print(f"\nOpen dashboard/index.html in your browser to view results.")

    return {
        "results_df": results_df,
        "settlements_df": settlements_df,
        "analytics": analytics,
        "metrics": metrics,
    }


def generate_summary_report(results_df, settlements_df, analytics, output_path):
    """Generate a text summary report."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    metrics = analytics.get_overall_metrics()
    severity = analytics.get_severity_breakdown()
    exc_types = analytics.get_exception_type_breakdown()
    patterns = analytics.detect_patterns()

    report = f"""
{'='*70}
SETTLEMENT & RECONCILIATION EXCEPTION AGENT - SUMMARY REPORT
{'='*70}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY
{'-'*70}
Total Settlement Records:     {metrics['total_settlement_records']:,}
Total Merchants:              {metrics['total_merchants']}
Total GMV:                    ${metrics['total_gmv']:,.2f}
Total Expected Settlement:    ${metrics['total_expected_settlement']:,.2f}
Total Actual Settlement:      ${metrics['total_actual_settlement']:,.2f}

EXCEPTION SUMMARY
{'-'*70}
Exceptions Found:             {metrics['total_exceptions']:,}
Exception Rate:               {metrics['exception_rate']:.2f}%
Total Discrepancy:            ${metrics['total_discrepancy']:,.2f}
Average Discrepancy:          ${metrics['avg_discrepancy']:,.2f}
Max Positive Discrepancy:     ${metrics['max_positive_discrepancy']:,.2f}
Max Negative Discrepancy:     ${metrics['max_negative_discrepancy']:,.2f}

SEVERITY BREAKDOWN
{'-'*70}
"""
    if not severity.empty:
        for _, row in severity.iterrows():
            report += f"  {row['severity']:8s}: {row['count']:4.0f} records | Total: ${row['total_discrepancy']:,.2f} | Avg: ${row['avg_discrepancy']:,.2f}
"
    else:
        report += "  No exceptions found.
"

    report += f"""
EXCEPTION TYPE BREAKDOWN
{'-'*70}
"""
    if not exc_types.empty:
        for _, row in exc_types.iterrows():
            report += f"  {row['exception_type']:30s}: {row['count']:4.0f} records | Total: ${row['total_discrepancy']:,.2f}
"
    else:
        report += "  No exceptions found.
"

    report += f"""
DETECTED PATTERNS
{'-'*70}
"""
    if patterns:
        for i, pattern in enumerate(patterns, 1):
            report += f"  {i}. [{pattern['pattern']}] {pattern['description']}
"
    else:
        report += "  No recurring patterns detected.
"

    report += f"""
TOP 10 AFFECTED MERCHANTS
{'-'*70}
"""
    top_merchants = analytics.get_merchant_breakdown(top_n=10)
    if not top_merchants.empty:
        for _, row in top_merchants.iterrows():
            report += f"  {row['merchant_id']:12s}: {row['exception_count']:3.0f} exceptions | Total: ${row['total_discrepancy']:,.2f} | Avg: ${row['avg_discrepancy']:,.2f}
"
    else:
        report += "  No merchants with exceptions.
"

    report += f"""
{'='*70}
END OF REPORT
{'='*70}
"""

    with open(output_path, "w") as f:
        f.write(report)

    print(f"  Saved: {output_path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Settlement & Reconciliation Exception Agent"
    )
    parser.add_argument(
        "--output-dir", 
        default="data",
        help="Directory for output files (default: data)"
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip dashboard generation"
    )
    parser.add_argument(
        "--no-memos",
        action="store_true",
        help="Skip memo export"
    )

    args = parser.parse_args()

    run_pipeline(
        output_dir=args.output_dir,
        generate_dashboard=not args.no_dashboard,
        export_memos=not args.no_memos,
    )


if __name__ == "__main__":
    main()

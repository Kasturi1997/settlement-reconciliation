# Settlement & Reconciliation Exception Agent

A self-initiated project for detecting and investigating settlement reconciliation exceptions using synthetic financial data.

## Overview

This system generates realistic synthetic order, payment, refund, fee, GST, settlement, and payout data, then calculates expected settlement amounts for each merchant and compares them with actual simulated settlements to identify mismatches. When exceptions are found, the system generates detailed investigation memos explaining possible root causes.

## Features

- **Synthetic Data Generation**: Realistic e-commerce transaction data with controlled exception injection
- **Expected Settlement Calculation**: Platform fees, PG fees, GST, refunds, chargebacks
- **Automated Reconciliation**: Tolerance-based exception detection with severity classification
- **Investigation Memos**: Auto-generated root cause analysis and actionable recommendations
- **Interactive Dashboard**: Plotly-based HTML dashboard (no server required)
- **Pattern Detection**: Identifies recurring issues and merchant risk profiles
- **Comprehensive Testing**: Unit tests for all core components


## Dashboard Features

The interactive dashboard includes 9 visualizations:

1. **KPI Overview** - Total exceptions with delta indicator
2. **Severity Distribution** - Pie chart of HIGH/MEDIUM/LOW breakdown
3. **Exception Type Breakdown** - Bar chart by exception category
4. **Daily Exception Trend** - Time series of exception counts
5. **Merchant Risk Heatmap** - Discrepancy intensity by merchant and date
6. **Discrepancy Distribution** - Histogram of difference amounts
7. **Expected vs Actual** - Scatter plot with perfect-match reference line
8. **Exception Timeline** - Cumulative count over time
9. **Top Affected Merchants** - Horizontal bar chart by total discrepancy

## Testing

The test suite covers:
- Configuration validation
- Data generation correctness
- Reconciliation tolerance logic
- Severity classification
- Investigation memo generation
- Recommendation logic
- Empty dataframe handling
- Pattern detection
- Full pipeline integration


## Author

Built a project to demonstrate:
- Financial reconciliation automation
- Data engineering pipeline design
- Exception handling and root cause analysis
- Interactive dashboard development
- Software testing best practices


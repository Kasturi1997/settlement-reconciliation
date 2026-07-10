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

## Project Structure

```
settlement-reconciliation-exception-agent/
├── config.py                   # Central configuration and business rules
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore patterns
├── src/
│   ├── __init__.py
│   ├── data_generator.py       # Synthetic data generation
│   ├── reconciliation_engine.py # Core reconciliation logic
│   ├── analytics.py            # Analytics and reporting
│   ├── dashboard.py            # Interactive HTML dashboard
│   └── main.py                 # Pipeline orchestrator
├── notebooks/
│   └── exploratory_analysis.ipynb  # Jupyter notebook demo
├── tests/
│   ├── __init__.py
│   └── test_reconciliation.py  # Unit tests
├── data/                       # Generated data (created on run)
│   ├── raw/
│   └── processed/
├── dashboard/                  # HTML dashboards (created on run)
└── reports/                    # Investigation memos (created on run)
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd settlement-reconciliation-exception-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Run full pipeline - generates data, reconciles, creates dashboard
python src/main.py

# Or import and use programmatically
from src.main import run_pipeline
results = run_pipeline()
```

### Run Tests

```bash
pytest tests/test_reconciliation.py -v
```

### View Dashboard

After running the pipeline, open `dashboard/index.html` in any web browser:

```bash
# macOS
open dashboard/index.html

# Linux
xdg-open dashboard/index.html

# Windows
start dashboard/index.html
```

## Configuration

Edit `config.py` to adjust business rules:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PLATFORM_FEE_PERCENT` | 2.0% | Platform commission rate |
| `PAYMENT_GATEWAY_FEE_PERCENT` | 1.5% | Payment gateway fee rate |
| `FIXED_FEE_PER_TRANSACTION` | $0.30 | Per-transaction fixed fee |
| `GST_RATE` | 18.0% | GST on fees |
| `SETTLEMENT_DELAY_DAYS` | 2 | T+2 settlement cycle |
| `EXCEPTION_TOLERANCE_ABSOLUTE` | $0.01 | Absolute tolerance threshold |
| `EXCEPTION_TOLERANCE_PERCENT` | 0.5% | Percentage tolerance threshold |
| `MERCHANT_COUNT` | 15 | Number of synthetic merchants |

## Exception Types Handled

| Type | Description | Typical Cause |
|------|-------------|---------------|
| `REFUND_ADJUSTMENT` | Refund processed after settlement calculation | Post-settlement refund |
| `FEE_DEDUCTION_MISMATCH` | Platform/PG fees differ from expected | Rate change, promo waiver |
| `CHARGEBACK` | Customer-initiated dispute reversal | Fraud, service dispute |
| `FAILED_CAPTURE` | Authorized but not captured payment | Expired auth, gateway error |
| `SETTLEMENT_DELAY` | Payout delayed beyond T+2 | Bank holiday, risk hold |
| `GST_MISMATCH` | Tax calculation variance | Rate change, rounding |
| `DUPLICATE_SETTLEMENT` | Same transaction settled twice | Batch processing error |
| `MISSING_ADJUSTMENT` | Unaccounted manual credits/debits | Promo, penalty, reserve |
| `CURRENCY_CONVERSION` | FX rate fluctuation | Cross-border transaction |
| `RESERVE_HOLD` | Risk reserve held back | New merchant, high-risk txn |

## Sample Investigation Memo

```
=== INVESTIGATION MEMO ===
Merchant: MERCH0007 | Date: 2026-06-28
Expected: $12,450.00 | Actual: $0.00
Difference: -$12,450.00 (-100.00%)
Severity: HIGH

PRIMARY HYPOTHESIS: SETTLEMENT_DELAY
Explanation: Settlement delayed due to bank holiday, weekend, or risk hold.
Expected T+2 but actual payout occurred later.

SUPPORTING DATA:
  - Total GMV: $14,850.00 across 124 transactions
  - Total Fees: $2,400.00
  - Refunds: $0.00
  - Chargebacks: $0.00

ANALYSIS: Actual settlement is LOWER than expected.
  -> Fee calculations should be cross-checked against contract rates.

Generated: 2026-07-10 10:19:00
```

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

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Technology Stack

- **Python 3.10+**
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing
- **Plotly** - Interactive visualizations
- **Matplotlib/Seaborn** - Static charts for notebooks
- **Faker** - Synthetic data generation
- **Pytest** - Unit testing framework

## Author

Built as a self-initiated project to demonstrate:
- Financial reconciliation automation
- Data engineering pipeline design
- Exception handling and root cause analysis
- Interactive dashboard development
- Software testing best practices

## License

MIT License - feel free to use and modify for your own projects.

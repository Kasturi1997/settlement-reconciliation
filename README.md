# Settlement & Reconciliation Exception Agent

This is a self-initiated fintech analytics project that simulates merchant
settlement reconciliation using synthetic order, payment, refund, fee, GST,
settlement, and payout data.

The project calculates the expected settlement amount for each merchant, compares
it with the actual simulated settlement amount, flags exceptions, and generates
short investigation memos with likely reasons such as refund adjustment, fee
deduction, chargeback, failed capture, GST difference, or settlement delay.

## Business Problem

Payment companies, banks, and marketplaces process thousands of merchant
transactions every day. At settlement time, the amount paid to the merchant must
match what the business expects after deducting refunds, chargebacks, fees, and
GST.

Manual reconciliation is slow and error-prone. This project shows how a rule
based exception agent can automate the first level of reconciliation review.

## What The Project Demonstrates

- Synthetic data generation for fintech settlement workflows
- Expected settlement calculation using auditable business rules
- Merchant-level exception detection
- Root-cause style classification for operational investigation
- Auto-generated investigation memos
- Streamlit dashboard for recruiter review
- Static HTML dashboard that can be opened without running a server
- Unit tests for the reconciliation formula

## Folder Structure

```text
settlement-reconciliation-exception-agent/
|-- app.py
|-- run_pipeline.py
|-- requirements.txt
|-- data/
|   |-- raw/
|   |-- processed/
|-- dashboard/
|   |-- static_dashboard.html
|-- docs/
|   |-- business_rules.md
|-- src/
|   |-- generate_synthetic_data.py
|   |-- reconciliation_engine.py
|   |-- build_static_dashboard.py
|-- tests/
|   |-- test_reconciliation_engine.py
```

## Reconciliation Logic

```text
expected_settlement =
    captured_payments
  - successful_refunds
  - chargebacks
  - platform_fees
  - gateway_fees
  - GST_on_fees
```

```text
variance = actual_settlement - expected_settlement
```

An exception is raised when the absolute variance is more than INR 5.00.

## How To Run

Create a virtual environment and install the requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate the synthetic data and processed reconciliation outputs:

```bash
python run_pipeline.py
```

Run the dashboard:

```bash
streamlit run app.py
```

You can also open the offline dashboard directly:

```text
dashboard/static_dashboard.html
```

## Data Files

Raw synthetic files:

- `merchants.csv`
- `orders.csv`
- `payments.csv`
- `refunds.csv`
- `fees.csv`
- `gst.csv`
- `chargebacks.csv`
- `settlements.csv`
- `payouts.csv`

Processed files:

- `reconciliation_results.csv`
- `exceptions.csv`
- `merchant_summary.csv`

## Interview Talking Points

**Why did you build this?**  
To show how my credit, banking, finance, and analytics background can be applied
to fintech operations and GenAI-style workflow automation.

**Why use synthetic data?**  
Real payment and settlement data is confidential. Synthetic data lets me model
the business workflow without exposing customer or merchant information.

**Where can GenAI be added later?**  
The current memo generator is rule based for auditability. A future version can
use an LLM to draft richer investigation notes, summarize uploaded processor
files, or answer analyst questions over reconciliation data.

**What makes this useful for a business?**  
It reduces manual checking, prioritizes high-risk exceptions, and gives an
operations team a starting memo for investigation.

## Disclaimer

This is a portfolio project using fully synthetic data. It is not connected to
any real bank, payment processor, customer, or merchant.


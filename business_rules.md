# Business Rules

This project simulates a payment settlement reconciliation process for merchants.
All records are synthetic and created for portfolio demonstration.

## Settlement Formula

For every merchant and settlement date:

```text
expected_settlement_amount =
    captured_payment_amount
  - successful_refund_amount
  - chargeback_amount
  - platform_fee
  - gateway_fee
  - gst_on_fees
```

The engine compares the calculated expected amount with the actual simulated
settlement amount received from the payment processor.

```text
variance = actual_settlement_amount - expected_settlement_amount
```

An exception is raised when the absolute variance is greater than the tolerance
limit. The current tolerance is INR 5.00 to ignore small rounding differences.

## Exception Categories

| Category | What it means | Typical action |
| --- | --- | --- |
| Settlement Delay | The expected amount is valid but payout is pending or delayed | Check payout UTR, bank status, and processor SLA |
| Refund Adjustment | Processor deducted a refund that was not expected in the internal calculation | Match refund file, order ID, and refund posting date |
| Chargeback | Customer dispute or chargeback reduced the payout | Check chargeback reference and dispute documentation |
| Fee Deduction | Gateway/platform fee is higher than expected | Validate fee slab, GST, and pricing agreement |
| Failed Capture | Order was placed but payment capture did not complete | Match order status with payment capture status |
| GST / Tax Difference | GST charged on fees differs from the expected tax amount | Validate GST rate and invoice calculation |
| Unclassified Variance | Difference exists but no clear rule signal is available | Manual investigation required |

## Why This Matters In Banking And Fintech

Settlement reconciliation protects merchant trust, helps detect revenue leakage,
and supports audit readiness. A small mismatch can be caused by normal business
events such as refunds or fees, but it can also indicate incorrect pricing,
delayed settlement, payment failure, or operational control gaps.


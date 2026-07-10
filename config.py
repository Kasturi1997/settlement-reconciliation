"""
Configuration module for the Settlement Reconciliation Agent.
All tunable parameters and business rules are centralized here.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SettlementConfig:
    """Business configuration for settlement calculations."""

    # Fee structure
    PLATFORM_FEE_PERCENT: float = 2.0          # 2% platform fee
    PAYMENT_GATEWAY_FEE_PERCENT: float = 1.5   # 1.5% PG fee
    FIXED_FEE_PER_TRANSACTION: float = 0.30   # $0.30 per txn

    # Tax
    GST_RATE: float = 18.0                     # 18% GST on fees

    # Settlement timing
    SETTLEMENT_DELAY_DAYS: int = 2             # T+2 settlement

    # Exception thresholds
    EXCEPTION_TOLERANCE_ABSOLUTE: float = 0.01  # $0.01 tolerance
    EXCEPTION_TOLERANCE_PERCENT: float = 0.5    # 0.5% tolerance

    # Reconciliation window
    RECONCILIATION_WINDOW_DAYS: int = 30

    # Merchant config
    MERCHANT_COUNT: int = 15

    # Data generation config
    START_DATE: str = "2026-06-01"
    END_DATE: str = "2026-06-30"
    AVG_DAILY_ORDERS_PER_MERCHANT: int = 50

    # Exception injection rates (for synthetic data)
    REFUND_RATE: float = 0.08                  # 8% orders refunded
    CHARGEBACK_RATE: float = 0.02              # 2% chargebacks
    FAILED_CAPTURE_RATE: float = 0.03          # 3% failed captures
    SETTLEMENT_DELAY_RATE: float = 0.05        # 5% delayed settlements
    FEE_DISCREPANCY_RATE: float = 0.04         # 4% fee discrepancies


# Global config instance
CONFIG = SettlementConfig()

# Exception reason codes and descriptions
EXCEPTION_REASONS: Dict[str, str] = {
    "REFUND_ADJUSTMENT": "Refund processed after settlement calculation. Refund amount deducted from expected settlement but not reflected in actual payout.",
    "FEE_DEDUCTION_MISMATCH": "Platform or payment gateway fees applied differ from expected. Possible rate change, promotional fee waiver, or rounding difference.",
    "CHARGEBACK": "Customer initiated chargeback. Amount reversed from merchant settlement. Chargeback fee may also apply.",
    "FAILED_CAPTURE": "Payment authorized but not captured successfully. Order shows as paid but no funds received. Settlement excludes this amount.",
    "SETTLEMENT_DELAY": "Settlement delayed due to bank holiday, weekend, or risk hold. Expected T+2 but actual payout occurred later.",
    "GST_MISMATCH": "GST calculation on fees does not match expected. Possible tax rate change or rounding variance.",
    "DUPLICATE_SETTLEMENT": "Same transaction settled twice. Actual payout exceeds expected amount.",
    "MISSING_ADJUSTMENT": "Promotional adjustment, penalty, or manual credit/debit not accounted for in expected calculation.",
    "CURRENCY_CONVERSION": "Cross-border transaction with FX rate fluctuation between order date and settlement date.",
    "RESERVE_HOLD": "Risk reserve amount held back from settlement. Common for new merchants or high-risk transactions.",
}

# Severity levels
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

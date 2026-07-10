"""
Synthetic Data Generator for Settlement Reconciliation.

Generates realistic order, payment, refund, fee, GST, settlement, and payout data
with controlled exception injection for testing reconciliation logic.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from faker import Faker

from config import CONFIG, EXCEPTION_REASONS

fake = Faker()
Faker.seed(42)
random.seed(42)


class SyntheticDataGenerator:
    """Generates synthetic financial data for reconciliation testing."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.start_date = datetime.strptime(config.START_DATE, "%Y-%m-%d")
        self.end_date = datetime.strptime(config.END_DATE, "%Y-%m-%d")
        self.merchants = self._generate_merchants()

    def _generate_merchants(self) -> List[Dict]:
        """Generate merchant profiles."""
        merchants = []
        categories = ["Electronics", "Fashion", "Groceries", "Home & Garden", 
                     "Sports", "Books", "Health & Beauty", "Toys", "Automotive", "Food Delivery"]

        for i in range(self.config.MERCHANT_COUNT):
            merchants.append({
                "merchant_id": f"MERCH{str(i+1).zfill(4)}",
                "merchant_name": fake.company(),
                "category": random.choice(categories),
                "onboarding_date": fake.date_between(start_date="-2y", end_date="-3m"),
                "settlement_account": fake.iban(),
                "fee_tier": random.choice(["standard", "premium", "enterprise"]),
                "risk_score": random.randint(1, 100),
            })
        return merchants

    def generate_orders(self, n_orders: Optional[int] = None) -> pd.DataFrame:
        """Generate synthetic order data."""
        if n_orders is None:
            days = (self.end_date - self.start_date).days + 1
            n_orders = days * self.config.AVG_DAILY_ORDERS_PER_MERCHANT * self.config.MERCHANT_COUNT

        orders = []
        for _ in range(n_orders):
            merchant = random.choice(self.merchants)
            order_date = fake.date_between(start_date=self.config.START_DATE, 
                                          end_date=self.config.END_DATE)
            order_time = fake.time_object()

            # Order amount distribution (realistic e-commerce)
            amount = random.choice([
                random.uniform(10, 50),      # Small items
                random.uniform(50, 200),     # Medium items
                random.uniform(200, 1000),   # Large items
                random.uniform(1000, 5000),  # High value (rare)
            ])

            order = {
                "order_id": f"ORD{uuid.uuid4().hex[:12].upper()}",
                "merchant_id": merchant["merchant_id"],
                "merchant_name": merchant["merchant_name"],
                "category": merchant["category"],
                "order_date": order_date,
                "order_time": order_time.strftime("%H:%M:%S"),
                "order_datetime": datetime.combine(order_date, order_time),
                "order_amount": round(amount, 2),
                "currency": "USD",
                "customer_id": f"CUST{uuid.uuid4().hex[:8].upper()}",
                "payment_method": random.choice(["credit_card", "debit_card", "wallet", "bank_transfer"]),
                "status": random.choice(["completed", "completed", "completed", "completed", "pending", "cancelled"]),
                "fee_tier": merchant["fee_tier"],
            }
            orders.append(order)

        df = pd.DataFrame(orders)
        df = df.sort_values("order_datetime").reset_index(drop=True)
        return df

    def generate_payments(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        """Generate payment records linked to orders."""
        payments = []

        for _, order in orders_df.iterrows():
            if order["status"] == "cancelled":
                continue

            payment_status = "captured"
            capture_amount = order["order_amount"]

            # Inject failed captures
            if random.random() < self.config.FAILED_CAPTURE_RATE and order["status"] == "completed":
                payment_status = random.choice(["failed", "voided"])
                capture_amount = 0.0

            # Payment timestamp (usually within minutes of order)
            payment_datetime = order["order_datetime"] + timedelta(minutes=random.randint(1, 30))

            payment = {
                "payment_id": f"PAY{uuid.uuid4().hex[:12].upper()}",
                "order_id": order["order_id"],
                "merchant_id": order["merchant_id"],
                "payment_datetime": payment_datetime,
                "payment_amount": order["order_amount"],
                "capture_amount": capture_amount,
                "payment_status": payment_status,
                "payment_method": order["payment_method"],
                "gateway_reference": f"GW{uuid.uuid4().hex[:10].upper()}",
                "auth_code": f"AUTH{random.randint(100000, 999999)}",
            }
            payments.append(payment)

        df = pd.DataFrame(payments)
        if not df.empty:
            df = df.sort_values("payment_datetime").reset_index(drop=True)
        return df

    def generate_refunds(self, payments_df: pd.DataFrame) -> pd.DataFrame:
        """Generate refund records from successful payments."""
        refunds = []
        successful_payments = payments_df[payments_df["payment_status"] == "captured"].copy()

        # Sample payments for refunds
        n_refunds = int(len(successful_payments) * self.config.REFUND_RATE)
        refund_candidates = successful_payments.sample(n=min(n_refunds, len(successful_payments)), random_state=42)

        for _, payment in refund_candidates.iterrows():
            # Refund can be full or partial
            refund_type = random.choice(["full", "partial", "partial"])
            if refund_type == "full":
                refund_amount = payment["capture_amount"]
            else:
                refund_amount = round(payment["capture_amount"] * random.uniform(0.2, 0.8), 2)

            # Refund happens after payment, usually within 14 days
            refund_datetime = payment["payment_datetime"] + timedelta(days=random.randint(1, 14))

            refund = {
                "refund_id": f"REF{uuid.uuid4().hex[:12].upper()}",
                "payment_id": payment["payment_id"],
                "order_id": payment["order_id"],
                "merchant_id": payment["merchant_id"],
                "refund_datetime": refund_datetime,
                "refund_amount": refund_amount,
                "refund_type": refund_type,
                "reason": random.choice([
                    "customer_request", "defective_item", "wrong_item", 
                    "not_as_described", "duplicate_charge", "fraudulent"
                ]),
                "status": random.choice(["completed", "completed", "completed", "pending"]),
            }
            refunds.append(refund)

        df = pd.DataFrame(refunds)
        if not df.empty:
            df = df.sort_values("refund_datetime").reset_index(drop=True)
        return df

    def generate_chargebacks(self, payments_df: pd.DataFrame) -> pd.DataFrame:
        """Generate chargeback records."""
        chargebacks = []
        successful_payments = payments_df[payments_df["payment_status"] == "captured"].copy()

        n_chargebacks = int(len(successful_payments) * self.config.CHARGEBACK_RATE)
        if n_chargebacks == 0:
            return pd.DataFrame()

        cb_candidates = successful_payments.sample(n=min(n_chargebacks, len(successful_payments)), random_state=24)

        for _, payment in cb_candidates.iterrows():
            cb_datetime = payment["payment_datetime"] + timedelta(days=random.randint(15, 90))

            chargeback = {
                "chargeback_id": f"CB{uuid.uuid4().hex[:10].upper()}",
                "payment_id": payment["payment_id"],
                "order_id": payment["order_id"],
                "merchant_id": payment["merchant_id"],
                "chargeback_datetime": cb_datetime,
                "dispute_amount": payment["capture_amount"],
                "chargeback_fee": round(random.uniform(15.0, 50.0), 2),
                "reason_code": random.choice(["4837", "4849", "4853", "4854", "4855", "4860"]),
                "status": random.choice(["won", "lost", "lost", "lost"]),  # Mostly lost for realism
                "representment": random.choice([True, False, False]),
            }
            chargebacks.append(chargeback)

        df = pd.DataFrame(chargebacks)
        if not df.empty:
            df = df.sort_values("chargeback_datetime").reset_index(drop=True)
        return df

    def generate_fees_and_settlements(self, orders_df: pd.DataFrame, 
                                       payments_df: pd.DataFrame,
                                       refunds_df: pd.DataFrame,
                                       chargebacks_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate expected fees and settlements per merchant per day."""

        # Start with successful payments
        successful = payments_df[payments_df["payment_status"] == "captured"].copy()

        # Aggregate by merchant and date
        successful["settlement_date"] = successful["payment_datetime"].dt.date + timedelta(days=self.config.SETTLEMENT_DELAY_DAYS)

        daily_summary = []

        for (merchant_id, settlement_date), group in successful.groupby(["merchant_id", "settlement_date"]):
            total_gmv = group["capture_amount"].sum()
            n_transactions = len(group)

            # Calculate fees
            platform_fee = round(total_gmv * (self.config.PLATFORM_FEE_PERCENT / 100), 2)
            pg_fee = round(total_gmv * (self.config.PAYMENT_GATEWAY_FEE_PERCENT / 100), 2)
            fixed_fees = round(n_transactions * self.config.FIXED_FEE_PER_TRANSACTION, 2)
            total_fees = platform_fee + pg_fee + fixed_fees

            # GST on fees
            gst_on_fees = round(total_fees * (self.config.GST_RATE / 100), 2)

            # Refunds on this day (refunds reduce settlement)
            if not refunds_df.empty:
                day_refunds = refunds_df[
                    (refunds_df["merchant_id"] == merchant_id) & 
                    (refunds_df["refund_datetime"].dt.date == settlement_date) &
                    (refunds_df["status"] == "completed")
                ]
                refund_amount = day_refunds["refund_amount"].sum()
            else:
                refund_amount = 0.0

            # Chargebacks on this day
            if not chargebacks_df.empty:
                day_cb = chargebacks_df[
                    (chargebacks_df["merchant_id"] == merchant_id) & 
                    (chargebacks_df["chargeback_datetime"].dt.date == settlement_date) &
                    (chargebacks_df["status"] == "lost")
                ]
                chargeback_amount = day_cb["dispute_amount"].sum()
                chargeback_fees = day_cb["chargeback_fee"].sum()
            else:
                chargeback_amount = 0.0
                chargeback_fees = 0.0

            # Expected settlement calculation
            expected_settlement = (
                total_gmv 
                - refund_amount 
                - chargeback_amount 
                - total_fees 
                - gst_on_fees 
                - chargeback_fees
            )
            expected_settlement = round(expected_settlement, 2)

            summary = {
                "merchant_id": merchant_id,
                "settlement_date": settlement_date,
                "total_gmv": round(total_gmv, 2),
                "n_transactions": n_transactions,
                "platform_fee": platform_fee,
                "pg_fee": pg_fee,
                "fixed_fees": fixed_fees,
                "total_fees": total_fees,
                "gst_on_fees": gst_on_fees,
                "refund_amount": round(refund_amount, 2),
                "chargeback_amount": round(chargeback_amount, 2),
                "chargeback_fees": round(chargeback_fees, 2),
                "expected_settlement": expected_settlement,
            }
            daily_summary.append(summary)

        df = pd.DataFrame(daily_summary)
        if not df.empty:
            df = df.sort_values(["merchant_id", "settlement_date"]).reset_index(drop=True)
        return df

    def generate_actual_settlements(self, expected_df: pd.DataFrame) -> pd.DataFrame:
        """Generate actual settlement payouts with controlled exceptions."""
        actuals = expected_df.copy()

        # Inject various exceptions
        for idx in actuals.index:
            expected = actuals.loc[idx, "expected_settlement"]
            actual = expected
            exception_type = None

            rand = random.random()
            cumulative = 0.0

            # Fee discrepancy
            cumulative += self.config.FEE_DISCREPANCY_RATE
            if rand < cumulative and exception_type is None:
                discrepancy = round(expected * random.uniform(-0.02, 0.02), 2)
                actual = expected - discrepancy
                exception_type = "FEE_DEDUCTION_MISMATCH"

            # Settlement delay (actual is 0 because not yet settled, or shifted)
            cumulative += self.config.SETTLEMENT_DELAY_RATE
            if rand < cumulative and exception_type is None:
                # Sometimes actual is 0 (not yet paid), sometimes shifted amount
                if random.choice([True, False]):
                    actual = 0.0
                else:
                    actual = expected  # Will be paid next day, but we record it as exception for today
                exception_type = "SETTLEMENT_DELAY"

            # Missing adjustment (promo, penalty, reserve)
            cumulative += 0.03
            if rand < cumulative and exception_type is None:
                adjustment = round(random.uniform(-100, 100), 2)
                actual = expected + adjustment
                exception_type = "MISSING_ADJUSTMENT"

            # GST mismatch
            cumulative += 0.02
            if rand < cumulative and exception_type is None:
                gst_error = round(actuals.loc[idx, "gst_on_fees"] * random.uniform(-0.1, 0.1), 2)
                actual = expected + gst_error
                exception_type = "GST_MISMATCH"

            # Duplicate settlement
            cumulative += 0.01
            if rand < cumulative and exception_type is None:
                actual = expected * 2
                exception_type = "DUPLICATE_SETTLEMENT"

            # Small rounding errors (not exceptions, just noise)
            if exception_type is None:
                actual = expected + round(random.uniform(-0.05, 0.05), 2)

            actuals.loc[idx, "actual_settlement"] = round(actual, 2)
            actuals.loc[idx, "exception_type"] = exception_type
            actuals.loc[idx, "difference"] = round(actual - expected, 2)

        return actuals

    def generate_all_data(self) -> Dict[str, pd.DataFrame]:
        """Generate complete synthetic dataset."""
        print("Generating orders...")
        orders = self.generate_orders()

        print("Generating payments...")
        payments = self.generate_payments(orders)

        print("Generating refunds...")
        refunds = self.generate_refunds(payments)

        print("Generating chargebacks...")
        chargebacks = self.generate_chargebacks(payments)

        print("Calculating expected settlements...")
        expected = self.generate_fees_and_settlements(orders, payments, refunds, chargebacks)

        print("Generating actual settlements with exceptions...")
        actuals = self.generate_actual_settlements(expected)

        return {
            "orders": orders,
            "payments": payments,
            "refunds": refunds,
            "chargebacks": chargebacks,
            "settlements": actuals,
            "merchants": pd.DataFrame(self.merchants),
        }


if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    data = generator.generate_all_data()

    for name, df in data.items():
        print(f"\n{name}: {len(df)} records")
        if not df.empty:
            print(df.head(2).to_string())

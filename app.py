from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def format_inr(value: float) -> str:
    return f"INR {float(value):,.2f}"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = pd.read_csv(PROCESSED_DIR / "reconciliation_results.csv")
    exceptions = pd.read_csv(PROCESSED_DIR / "exceptions.csv")
    summary = pd.read_csv(PROCESSED_DIR / "merchant_summary.csv")
    return results, exceptions, summary


st.set_page_config(
    page_title="Settlement Reconciliation Exception Agent",
    page_icon=":material/account_balance:",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 3rem; }
      [data-testid="stMetricValue"] { font-size: 1.6rem; }
      div[data-testid="stDataFrame"] { border: 1px solid #d9e1e7; border-radius: 8px; }
      h1, h2, h3 { letter-spacing: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

required_files = [
    PROCESSED_DIR / "reconciliation_results.csv",
    PROCESSED_DIR / "exceptions.csv",
    PROCESSED_DIR / "merchant_summary.csv",
]

st.title("Settlement Reconciliation Exception Agent")
st.caption("Synthetic merchant settlement control dashboard for finance, banking, and fintech analytics portfolios.")

if not all(path.exists() for path in required_files):
    st.warning("Processed data is missing. Run `python run_pipeline.py` from the project root first.")
    st.stop()

results_df, exceptions_df, summary_df = load_data()

merchant_options = ["All Merchants"] + sorted(results_df["merchant_name"].dropna().unique().tolist())
exception_options = ["All Types"] + sorted(exceptions_df["exception_type"].dropna().unique().tolist())
priority_options = ["All Priorities"] + sorted(exceptions_df["risk_priority"].dropna().unique().tolist())

with st.sidebar:
    st.header("Filters")
    selected_merchant = st.selectbox("Merchant", merchant_options)
    selected_exception = st.selectbox("Exception Type", exception_options)
    selected_priority = st.selectbox("Risk Priority", priority_options)
    show_matched = st.toggle("Include matched settlements", value=False)

filtered = results_df.copy()
if selected_merchant != "All Merchants":
    filtered = filtered[filtered["merchant_name"] == selected_merchant]
if selected_exception != "All Types":
    filtered = filtered[filtered["exception_type"] == selected_exception]
if selected_priority != "All Priorities":
    filtered = filtered[filtered["risk_priority"] == selected_priority]
if not show_matched:
    filtered = filtered[filtered["exception_flag"]]

total_expected = filtered["expected_settlement_amount"].sum()
total_actual = filtered["actual_settlement_amount"].sum()
net_variance = filtered["variance_amount"].sum()
exception_count = int(filtered["exception_flag"].sum())
high_priority_count = int((filtered["risk_priority"] == "High").sum())

metric_cols = st.columns(5)
metric_cols[0].metric("Expected Settlement", format_inr(total_expected))
metric_cols[1].metric("Actual Settlement", format_inr(total_actual))
metric_cols[2].metric("Net Variance", format_inr(net_variance))
metric_cols[3].metric("Exceptions", exception_count)
metric_cols[4].metric("High Priority", high_priority_count)

left, right = st.columns([1.1, 1])

with left:
    st.subheader("Exception Mix")
    if filtered.empty:
        st.info("No rows match the selected filters.")
    else:
        mix = filtered[filtered["exception_flag"]]["exception_type"].value_counts().rename_axis("exception_type")
        if mix.empty:
            st.info("No exceptions in the selected view.")
        else:
            st.bar_chart(mix)

with right:
    st.subheader("Merchant Variance")
    merchant_variance = (
        filtered.groupby("merchant_name", as_index=False)["variance_amount"]
        .sum()
        .sort_values("variance_amount")
        .set_index("merchant_name")
    )
    if merchant_variance.empty:
        st.info("No merchant variance to show.")
    else:
        st.bar_chart(merchant_variance)

st.subheader("Settlement Exception Queue")
display_columns = [
    "merchant_name",
    "settlement_date",
    "exception_type",
    "risk_priority",
    "expected_settlement_amount",
    "actual_settlement_amount",
    "variance_amount",
    "settlement_status",
    "payout_status",
]
st.dataframe(
    filtered[display_columns].sort_values("absolute_variance", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Investigation Memos")
memo_rows = filtered[filtered["exception_flag"]].sort_values("absolute_variance", ascending=False).head(10)
if memo_rows.empty:
    st.success("No exception memos in the selected view.")
else:
    for _, row in memo_rows.iterrows():
        with st.expander(f"{row['risk_priority']} | {row['merchant_name']} | {row['exception_type']}"):
            st.write(row["investigation_memo"])
            st.write(
                {
                    "settlement_date": row["settlement_date"],
                    "processor_adjustment_code": row["processor_adjustment_code"],
                    "bank_reference": row["bank_reference"],
                }
            )

st.subheader("Merchant Summary")
st.dataframe(summary_df, use_container_width=True, hide_index=True)

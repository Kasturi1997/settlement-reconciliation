from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


def _format_inr(value: float) -> str:
    return f"INR {float(value):,.0f}"


def _format_rate(value: float) -> str:
    return f"{float(value) * 100:.1f}%"


def _bar_rows(series: pd.Series) -> str:
    if series.empty:
        return "<p class='muted'>No exceptions found.</p>"
    max_value = max(float(series.max()), 1.0)
    rows = []
    for label, value in series.items():
        width = max((float(value) / max_value) * 100, 4)
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(str(label))}</div>"
            "<div class='bar-track'>"
            f"<div class='bar-fill' style='width:{width:.1f}%'></div>"
            "</div>"
            f"<div class='bar-value'>{int(value)}</div>"
            "</div>"
        )
    return "\n".join(rows)


def _exception_table(exceptions: pd.DataFrame) -> str:
    if exceptions.empty:
        return "<p class='muted'>All settlements matched within tolerance.</p>"

    columns = [
        "merchant_name",
        "settlement_date",
        "exception_type",
        "risk_priority",
        "expected_settlement_amount",
        "actual_settlement_amount",
        "variance_amount",
    ]
    header = "".join(f"<th>{escape(column.replace('_', ' ').title())}</th>" for column in columns)
    rows = []
    for _, row in exceptions.head(12).iterrows():
        cells = []
        for column in columns:
            value = row[column]
            if column.endswith("_amount"):
                value = _format_inr(float(value))
            cells.append(f"<td>{escape(str(value))}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _memo_cards(exceptions: pd.DataFrame) -> str:
    cards = []
    for _, row in exceptions.head(6).iterrows():
        cards.append(
            "<article class='memo-card'>"
            f"<div class='memo-top'><span>{escape(row['exception_type'])}</span>"
            f"<strong>{escape(row['risk_priority'])}</strong></div>"
            f"<h3>{escape(row['merchant_name'])} | {escape(str(row['settlement_date']))}</h3>"
            f"<p>{escape(row['investigation_memo'])}</p>"
            "</article>"
        )
    return "\n".join(cards)


def _merchant_rows(summary: pd.DataFrame) -> str:
    rows = []
    for _, row in summary.iterrows():
        variance_class = "negative" if row["total_variance_amount"] < 0 else "positive"
        rows.append(
            "<tr>"
            f"<td>{escape(row['merchant_name'])}</td>"
            f"<td>{escape(row['category'])}</td>"
            f"<td>{int(row['settlement_days'])}</td>"
            f"<td>{int(row['exception_count'])}</td>"
            f"<td>{_format_rate(row['exception_rate'])}</td>"
            f"<td class='{variance_class}'>{_format_inr(row['total_variance_amount'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_static_dashboard(processed_dir: Path, dashboard_path: Path) -> None:
    results = pd.read_csv(processed_dir / "reconciliation_results.csv")
    exceptions = pd.read_csv(processed_dir / "exceptions.csv")
    summary = pd.read_csv(processed_dir / "merchant_summary.csv")

    total_expected = results["expected_settlement_amount"].sum()
    total_actual = results["actual_settlement_amount"].sum()
    net_variance = results["variance_amount"].sum()
    exception_count = int(results["exception_flag"].sum())
    settlement_rows = len(results)
    high_priority_count = int((exceptions["risk_priority"] == "High").sum()) if not exceptions.empty else 0
    exception_rate = exception_count / settlement_rows if settlement_rows else 0

    by_type = exceptions["exception_type"].value_counts() if not exceptions.empty else pd.Series(dtype=int)
    by_priority = exceptions["risk_priority"].value_counts() if not exceptions.empty else pd.Series(dtype=int)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Settlement Reconciliation Exception Agent</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #66737f;
      --line: #d9e1e7;
      --paper: #f6f8fa;
      --panel: #ffffff;
      --teal: #006d77;
      --teal-soft: #d8f3f0;
      --gold: #b7791f;
      --red: #b42318;
      --green: #13795b;
      --blue: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
      line-height: 1.5;
    }}
    header {{
      background: #0f2f35;
      color: #fff;
      padding: 38px 5vw 32px;
      border-bottom: 6px solid #f2b84b;
    }}
    header p {{
      color: #d8ecef;
      max-width: 900px;
      margin: 8px 0 0;
      font-size: 17px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(30px, 5vw, 56px);
      line-height: 1.05;
      letter-spacing: 0;
    }}
    h2 {{ margin: 0 0 16px; font-size: 22px; }}
    h3 {{ margin: 8px 0 8px; font-size: 16px; }}
    main {{
      width: min(1180px, 92vw);
      margin: 28px auto 60px;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .metric, .panel, .memo-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(15, 47, 53, 0.06);
    }}
    .metric {{ padding: 16px; min-height: 118px; }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .metric strong {{
      display: block;
      margin-top: 8px;
      font-size: clamp(20px, 2vw, 30px);
      letter-spacing: 0;
    }}
    .metric small {{ color: var(--muted); }}
    .layout {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{ padding: 20px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 150px 1fr 34px;
      align-items: center;
      gap: 10px;
      margin: 12px 0;
    }}
    .bar-label {{ font-size: 13px; color: var(--ink); }}
    .bar-track {{
      background: #e9eef2;
      height: 12px;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{ height: 100%; background: var(--teal); border-radius: 999px; }}
    .bar-value {{ text-align: right; font-weight: 700; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 10px 8px;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      background: #fbfcfd;
    }}
    .memo-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .memo-card {{ padding: 16px; }}
    .memo-card p {{ margin: 0; color: #34434f; }}
    .memo-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      color: var(--teal);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .memo-top strong {{
      color: var(--red);
      background: #fff0ed;
      border: 1px solid #ffd1ca;
      padding: 3px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .negative {{ color: var(--red); font-weight: 700; }}
    .positive {{ color: var(--green); font-weight: 700; }}
    .muted {{ color: var(--muted); }}
    .section {{ margin-top: 20px; }}
    footer {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 28px;
    }}
    @media (max-width: 920px) {{
      .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .layout, .memo-grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 112px 1fr 30px; }}
      table {{ font-size: 12px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Settlement Reconciliation Exception Agent</h1>
    <p>Merchant settlement control dashboard built on synthetic order, payment, refund, fee, GST, settlement, and payout data.</p>
  </header>
  <main>
    <section class="metric-grid">
      <div class="metric"><span>Expected Settlement</span><strong>{_format_inr(total_expected)}</strong><small>Calculated from internal data</small></div>
      <div class="metric"><span>Actual Settlement</span><strong>{_format_inr(total_actual)}</strong><small>Simulated processor payout</small></div>
      <div class="metric"><span>Net Variance</span><strong>{_format_inr(net_variance)}</strong><small>Actual minus expected</small></div>
      <div class="metric"><span>Exceptions</span><strong>{exception_count}</strong><small>{_format_rate(exception_rate)} of settlement rows</small></div>
      <div class="metric"><span>High Priority</span><strong>{high_priority_count}</strong><small>Needs immediate review</small></div>
    </section>

    <section class="layout">
      <div class="panel">
        <h2>Exceptions By Type</h2>
        {_bar_rows(by_type)}
      </div>
      <div class="panel">
        <h2>Exceptions By Priority</h2>
        {_bar_rows(by_priority)}
      </div>
    </section>

    <section class="panel section">
      <h2>Top Exceptions</h2>
      {_exception_table(exceptions)}
    </section>

    <section class="section">
      <h2>Investigation Memos</h2>
      <div class="memo-grid">
        {_memo_cards(exceptions)}
      </div>
    </section>

    <section class="panel section">
      <h2>Merchant Summary</h2>
      <table>
        <thead>
          <tr>
            <th>Merchant</th>
            <th>Category</th>
            <th>Settlement Days</th>
            <th>Exceptions</th>
            <th>Exception Rate</th>
            <th>Total Variance</th>
          </tr>
        </thead>
        <tbody>
          {_merchant_rows(summary)}
        </tbody>
      </table>
    </section>
    <footer>
      Synthetic data only. Generated for a finance, banking, analytics, and GenAI portfolio project.
    </footer>
  </main>
</body>
</html>
"""
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(html, encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    build_static_dashboard(
        processed_dir=project_root / "data" / "processed",
        dashboard_path=project_root / "dashboard" / "static_dashboard.html",
    )


if __name__ == "__main__":
    main()

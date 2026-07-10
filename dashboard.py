"""
Interactive Reconciliation Dashboard

Generates a standalone HTML dashboard with Plotly visualizations.
Can be opened directly in a browser without a server.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
import os

from config import CONFIG


class ReconciliationDashboard:
    """Generate interactive HTML dashboard for reconciliation results."""

    def __init__(self, results_df: pd.DataFrame, settlements_df: pd.DataFrame, 
                 analytics_engine=None):
        self.results_df = results_df.copy()
        self.settlements_df = settlements_df.copy()
        self.analytics = analytics_engine

        # Ensure date columns are datetime
        if "settlement_date" in self.results_df.columns:
            self.results_df["settlement_date"] = pd.to_datetime(self.results_df["settlement_date"])
        if "settlement_date" in self.settlements_df.columns:
            self.settlements_df["settlement_date"] = pd.to_datetime(self.settlements_df["settlement_date"])

    def generate_dashboard(self, output_path: str = "dashboard/index.html"):
        """Generate complete HTML dashboard."""

        # Prepare data
        exceptions = self.results_df[self.results_df["is_exception"] == True].copy()
        non_exceptions = self.results_df[self.results_df["is_exception"] == False].copy()

        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=(
                "KPI Overview", "Severity Distribution", "Exception Type Breakdown",
                "Daily Exception Trend", "Merchant Risk Heatmap", "Discrepancy Distribution",
                "Expected vs Actual Settlement", "Exception Timeline", "Top 10 Affected Merchants"
            ),
            specs=[
                [{"type": "indicator"}, {"type": "pie"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "heatmap"}, {"type": "histogram"}],
                [{"type": "scatter"}, {"type": "scatter"}, {"type": "bar"}],
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.08,
        )

        # Row 1, Col 1: KPI Indicators
        total_gmv = self.settlements_df["total_gmv"].sum() if not self.settlements_df.empty else 0
        total_exceptions = len(exceptions)
        exception_rate = (total_exceptions / len(self.results_df) * 100) if len(self.results_df) > 0 else 0
        total_discrepancy = exceptions["difference"].sum() if not exceptions.empty else 0

        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=total_exceptions,
                title={"text": "Total Exceptions", "font": {"size": 14, "color": "#e2e8f0"}},
                number={"font": {"size": 36, "color": "#ef4444"}},
                delta={"reference": len(self.results_df) * 0.1, "relative": True, "valueformat": ".1%"},
                domain={"row": 0, "column": 0},
            ),
            row=1, col=1
        )

        # Row 1, Col 2: Severity Pie Chart
        if not exceptions.empty:
            severity_counts = exceptions["severity"].value_counts()
            colors_severity = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
            fig.add_trace(
                go.Pie(
                    labels=severity_counts.index.tolist(),
                    values=severity_counts.values.tolist(),
                    hole=0.4,
                    marker_colors=[colors_severity.get(s, "#64748b") for s in severity_counts.index],
                    textinfo="label+percent",
                    textfont={"size": 11, "color": "#e2e8f0"},
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                ),
                row=1, col=2
            )

        # Row 1, Col 3: Exception Type Bar Chart
        if not exceptions.empty:
            type_counts = exceptions["exception_type"].value_counts().head(8)
            colors_type = px.colors.qualitative.Bold
            fig.add_trace(
                go.Bar(
                    x=type_counts.index.tolist(),
                    y=type_counts.values.tolist(),
                    marker_color=colors_type[:len(type_counts)],
                    text=type_counts.values.tolist(),
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
                ),
                row=1, col=3
            )

        # Row 2, Col 1: Daily Exception Trend
        if not exceptions.empty:
            daily = exceptions.groupby("settlement_date").agg({
                "merchant_id": "count",
                "difference": "sum"
            }).reset_index()
            daily.columns = ["date", "count", "total_discrepancy"]

            fig.add_trace(
                go.Scatter(
                    x=daily["date"].astype(str).tolist(),
                    y=daily["count"].tolist(),
                    mode="lines+markers",
                    name="Exception Count",
                    line={"color": "#f59e0b", "width": 2},
                    marker={"size": 6, "color": "#f59e0b"},
                    hovertemplate="Date: %{x}<br>Exceptions: %{y}<extra></extra>",
                ),
                row=2, col=1
            )

        # Row 2, Col 2: Merchant Risk Heatmap
        if not exceptions.empty:
            merchant_daily = exceptions.groupby(["merchant_id", "settlement_date"]).agg({
                "difference": "sum"
            }).reset_index()

            # Pivot for heatmap (sample top merchants)
            top_merchants = exceptions["merchant_id"].value_counts().head(10).index.tolist()
            merchant_daily_filtered = merchant_daily[merchant_daily["merchant_id"].isin(top_merchants)]

            if not merchant_daily_filtered.empty:
                pivot = merchant_daily_filtered.pivot_table(
                    index="merchant_id", 
                    columns="settlement_date", 
                    values="difference", 
                    fill_value=0
                )

                fig.add_trace(
                    go.Heatmap(
                        z=pivot.values.tolist(),
                        x=[str(d)[:10] for d in pivot.columns.tolist()],
                        y=pivot.index.tolist(),
                        colorscale="RdYlGn_r",
                        hovertemplate="Merchant: %{y}<br>Date: %{x}<br>Discrepancy: $%{z:.2f}<extra></extra>",
                        colorbar={"title": "Discrepancy ($)", "titleside": "right"},
                    ),
                    row=2, col=2
                )

        # Row 2, Col 3: Discrepancy Distribution Histogram
        if not exceptions.empty:
            fig.add_trace(
                go.Histogram(
                    x=exceptions["difference"].tolist(),
                    nbinsx=30,
                    marker_color="#3b82f6",
                    opacity=0.7,
                    hovertemplate="Discrepancy: $%{x:.2f}<br>Count: %{y}<extra></extra>",
                ),
                row=2, col=3
            )

        # Row 3, Col 1: Expected vs Actual Scatter
        sample_size = min(500, len(self.results_df))
        sample_df = self.results_df.sample(n=sample_size, random_state=42) if len(self.results_df) > sample_size else self.results_df

        fig.add_trace(
            go.Scatter(
                x=sample_df["expected_amount"].tolist(),
                y=sample_df["actual_amount"].tolist(),
                mode="markers",
                marker={
                    "color": ["#ef4444" if exc else "#22c55e" for exc in sample_df["is_exception"].tolist()],
                    "size": 6,
                    "opacity": 0.6,
                },
                hovertemplate="Expected: $%{x:.2f}<br>Actual: $%{y:.2f}<extra></extra>",
            ),
            row=3, col=1
        )

        # Add diagonal reference line
        max_val = max(sample_df["expected_amount"].max(), sample_df["actual_amount"].max())
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line={"color": "#64748b", "dash": "dash", "width": 1},
                showlegend=False,
                hoverinfo="skip",
            ),
            row=3, col=1
        )

        # Row 3, Col 2: Exception Timeline (Cumulative)
        if not exceptions.empty:
            daily_cum = exceptions.groupby("settlement_date").size().cumsum().reset_index()
            daily_cum.columns = ["date", "cumulative_exceptions"]

            fig.add_trace(
                go.Scatter(
                    x=daily_cum["date"].astype(str).tolist(),
                    y=daily_cum["cumulative_exceptions"].tolist(),
                    mode="lines",
                    fill="tozeroy",
                    line={"color": "#8b5cf6", "width": 2},
                    fillcolor="rgba(139, 92, 246, 0.2)",
                    hovertemplate="Date: %{x}<br>Cumulative: %{y}<extra></extra>",
                ),
                row=3, col=2
            )

        # Row 3, Col 3: Top 10 Affected Merchants
        if not exceptions.empty:
            merchant_totals = exceptions.groupby("merchant_id").agg({
                "difference": ["sum", "count"]
            }).reset_index()
            merchant_totals.columns = ["merchant_id", "total_discrepancy", "exception_count"]
            merchant_totals = merchant_totals.sort_values("total_discrepancy", key=abs, ascending=False).head(10)

            colors = ["#ef4444" if d < 0 else "#22c55e" for d in merchant_totals["total_discrepancy"].tolist()]

            fig.add_trace(
                go.Bar(
                    y=merchant_totals["merchant_id"].tolist(),
                    x=merchant_totals["total_discrepancy"].tolist(),
                    orientation="h",
                    marker_color=colors,
                    text=[f"${v:,.0f}" for v in merchant_totals["total_discrepancy"].tolist()],
                    textposition="auto",
                    hovertemplate="<b>%{y}</b><br>Total Discrepancy: $%{x:,.2f}<br>Count: %{customdata}<extra></extra>",
                    customdata=merchant_totals["exception_count"].tolist(),
                ),
                row=3, col=3
            )

        # Update layout
        fig.update_layout(
            title={
                "text": "<b>Settlement & Reconciliation Exception Dashboard</b><br><sup>Real-time monitoring of settlement discrepancies across merchant portfolio</sup>",
                "font": {"size": 20, "color": "#e2e8f0"},
                "x": 0.5,
                "xanchor": "center",
            },
            paper_bgcolor="#0f172a",
            plot_bgcolor="#1e293b",
            font={"color": "#e2e8f0", "family": "system-ui, sans-serif"},
            showlegend=False,
            height=1200,
            margin={"t": 100, "b": 50, "l": 50, "r": 50},
        )

        # Update axes
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#334155", tickfont={"size": 9})
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#334155", tickfont={"size": 9})

        # Update subplot titles
        for annotation in fig["layout"]["annotations"]:
            annotation["font"] = {"size": 13, "color": "#e2e8f0", "family": "system-ui, sans-serif"}

        # Save as HTML
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settlement Reconciliation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            background-color: #0f172a; 
            font-family: system-ui, -apple-system, sans-serif;
            color: #e2e8f0;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 20px 40px;
            border-bottom: 1px solid #334155;
        }}
        .header h1 {{ font-size: 24px; font-weight: 600; margin-bottom: 4px; }}
        .header p {{ color: #94a3b8; font-size: 14px; }}
        .kpi-bar {{
            display: flex;
            gap: 20px;
            padding: 20px 40px;
            background: #1e293b;
            border-bottom: 1px solid #334155;
            flex-wrap: wrap;
        }}
        .kpi-card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px 24px;
            min-width: 180px;
            flex: 1;
        }}
        .kpi-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
        .kpi-value {{ font-size: 24px; font-weight: 700; }}
        .kpi-value.positive {{ color: #22c55e; }}
        .kpi-value.negative {{ color: #ef4444; }}
        .kpi-value.warning {{ color: #f59e0b; }}
        .kpi-value.info {{ color: #3b82f6; }}
        .kpi-sub {{ font-size: 11px; color: #64748b; margin-top: 2px; }}
        .dashboard-container {{ padding: 20px 40px; }}
        .chart-container {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #475569;
            font-size: 12px;
            border-top: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Settlement & Reconciliation Exception Agent</h1>
        <p>Interactive Dashboard | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="kpi-bar">
        <div class="kpi-card">
            <div class="kpi-label">Total GMV</div>
            <div class="kpi-value positive">${total_gmv:,.0f}</div>
            <div class="kpi-sub">Across {self.results_df["merchant_id"].nunique()} merchants</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Exception Rate</div>
            <div class="kpi-value warning">{exception_rate:.1f}%</div>
            <div class="kpi-sub">{total_exceptions} of {len(self.results_df)} records</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Total Discrepancy</div>
            <div class="kpi-value {'negative' if total_discrepancy < 0 else 'positive'}">${total_discrepancy:,.2f}</div>
            <div class="kpi-sub">Net {'shortfall' if total_discrepancy < 0 else 'surplus'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Avg Discrepancy</div>
            <div class="kpi-value info">${exceptions["difference"].abs().mean() if not exceptions.empty else 0:,.2f}</div>
            <div class="kpi-sub">Per exception record</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Merchants Affected</div>
            <div class="kpi-value warning">{exceptions["merchant_id"].nunique() if not exceptions.empty else 0}/{self.results_df["merchant_id"].nunique()}</div>
            <div class="kpi-sub">{exceptions["merchant_id"].nunique() / self.results_df["merchant_id"].nunique() * 100 if not exceptions.empty and self.results_df["merchant_id"].nunique() > 0 else 0:.0f}% exposure</div>
        </div>
    </div>

    <div class="dashboard-container">
        <div class="chart-container" id="main-chart"></div>
    </div>

    <div class="footer">
        Settlement & Reconciliation Exception Agent v1.0.0 | Built with Plotly | Synthetic Data Demo
    </div>

    <script>
        var plotly_data = {fig.to_json()};
        Plotly.newPlot('main-chart', plotly_data.data, plotly_data.layout, {{responsive: true}});
    </script>
</body>
</html>
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Dashboard saved to: {output_path}")
        return output_path

    def generate_exception_table(self, output_path: str = "dashboard/exceptions.html", top_n: int = 50):
        """Generate a detailed exception table view."""

        exceptions = self.results_df[self.results_df["is_exception"] == True].copy()
        exceptions = exceptions.sort_values("difference", key=abs, ascending=False).head(top_n)

        # Truncate memos for table view
        exceptions["memo_short"] = exceptions["investigation_memo"].str[:200] + "..."
        exceptions["recommendation_short"] = exceptions["recommendation"].str[:150] + "..."

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exception Details - Settlement Reconciliation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            background-color: #0f172a; 
            font-family: system-ui, -apple-system, sans-serif;
            color: #e2e8f0;
            padding: 30px;
        }}
        h1 {{ margin-bottom: 8px; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 24px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #334155;
        }}
        th {{
            background: #334155;
            padding: 14px 16px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
            font-weight: 600;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
            font-size: 13px;
            vertical-align: top;
        }}
        tr:hover {{ background: #1e293b; }}
        .severity-high {{ color: #ef4444; font-weight: 600; }}
        .severity-medium {{ color: #f59e0b; font-weight: 600; }}
        .severity-low {{ color: #22c55e; font-weight: 600; }}
        .diff-negative {{ color: #ef4444; }}
        .diff-positive {{ color: #22c55e; }}
        .memo {{ max-width: 300px; color: #94a3b8; font-size: 12px; line-height: 1.5; }}
        .recommendation {{ max-width: 250px; color: #94a3b8; font-size: 12px; line-height: 1.5; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #475569;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>Exception Details</h1>
    <p class="subtitle">Top {top_n} exceptions requiring investigation | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <table>
        <thead>
            <tr>
                <th>Merchant</th>
                <th>Date</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Difference</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Investigation Memo</th>
                <th>Recommendation</th>
            </tr>
        </thead>
        <tbody>
"""

        for _, row in exceptions.iterrows():
            diff_class = "diff-negative" if row["difference"] < 0 else "diff-positive"
            severity_class = f"severity-{row['severity'].lower()}"

            html_content += f"""
            <tr>
                <td><b>{row['merchant_id']}</b></td>
                <td>{row['settlement_date']}</td>
                <td>${row['expected_amount']:,.2f}</td>
                <td>${row['actual_amount']:,.2f}</td>
                <td class="{diff_class}">${row['difference']:+,.2f} ({row['difference_percent']:+.1f}%)</td>
                <td>{row['exception_type']}</td>
                <td class="{severity_class}">{row['severity']}</td>
                <td class="memo">{row['memo_short']}</td>
                <td class="recommendation">{row['recommendation_short']}</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>
    <div class="footer">
        Settlement & Reconciliation Exception Agent v1.0.0 | Full investigation memos available in /reports/
    </div>
</body>
</html>
"""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Exception table saved to: {output_path}")
        return output_path


if __name__ == "__main__":
    # Demo with sample data
    sample_results = pd.DataFrame({
        "merchant_id": ["MERCH0001", "MERCH0002", "MERCH0001", "MERCH0003"],
        "settlement_date": pd.to_datetime(["2026-06-15", "2026-06-15", "2026-06-16", "2026-06-17"]),
        "expected_amount": [1000, 2500, 1200, 800],
        "actual_amount": [950, 2500, 1150, 750],
        "difference": [-50, 0, -50, -50],
        "difference_percent": [-5.0, 0, -4.17, -6.25],
        "is_exception": [True, False, True, True],
        "exception_type": ["FEE_DEDUCTION_MISMATCH", None, "FEE_DEDUCTION_MISMATCH", "REFUND_ADJUSTMENT"],
        "severity": ["LOW", None, "LOW", "LOW"],
        "investigation_memo": ["Test memo 1", "", "Test memo 2", "Test memo 3"],
        "recommendation": ["Rec 1", "", "Rec 2", "Rec 3"],
    })

    sample_settlements = pd.DataFrame({
        "merchant_id": ["MERCH0001", "MERCH0002", "MERCH0001", "MERCH0003"],
        "settlement_date": pd.to_datetime(["2026-06-15", "2026-06-15", "2026-06-16", "2026-06-17"]),
        "total_gmv": [1200, 3000, 1400, 1000],
    })

    dashboard = ReconciliationDashboard(sample_results, sample_settlements)
    dashboard.generate_dashboard("dashboard/test.html")

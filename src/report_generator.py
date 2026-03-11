import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import ticker
from matplotlib.figure import Figure

from src.config import AppConfig
from src.logger import LogManager

logger = LogManager.get_logger("ReportGenerator")

COLORS = {
    "light": "#4CAF50",
    "medium": "#FF9800",
    "critical": "#F44336",
    "judicial": "#9C27B0",
}

LABELS = {
    "light": "Light (1-7d)",
    "medium": "Medium (8-15d)",
    "critical": "Critical (16-30d)",
    "judicial": "Judicial (>30d)",
}


class ReportGenerator:
    """Generates comprehensive HTML reports of the billing cycle."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.reports_dir = Path(config.data.reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="muted")

    def generate_html_report(
        self,
        df: pd.DataFrame,
        statistics: Dict[str, Any],
        sending_results: Optional[List[Any]] = None,
        filename: Optional[str] = None,
    ) -> str:
        """Generates a full HTML report and returns the file path."""
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"billing_report_{ts}.html"

        path = self.reports_dir / filename

        pie_chart = self._pie_chart(statistics)
        bar_chart = self._bar_chart(statistics)
        debt_chart = self._debt_by_category_chart(statistics)

        html = self._build_html(
            df=df,
            stats=statistics,
            sending_results=sending_results or [],
            charts={
                "pie": pie_chart,
                "bar": bar_chart,
                "debt": debt_chart,
            },
        )

        path.write_text(html, encoding="utf-8")
        logger.info(f"Report generated: {path}")
        return str(path)

    def _figure_to_base64(self, fig: Figure) -> str:
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_b64

    def _pie_chart(self, stats: Dict[str, Any]) -> str:
        cats = stats.get("by_category", {})
        labels = [v.get("label", k) for k, v in cats.items()]
        sizes = [v["count"] for v in cats.values()]
        colors = [COLORS.get(k, "#999") for k in cats]

        sizes_nz = [
            (label, size, color)
            for label, size, color in zip(labels, sizes, colors)
            if size > 0
        ]
        if not sizes_nz:
            return ""

        labels, sizes, colors = zip(*sizes_nz)

        fig, ax = plt.subplots(figsize=(5, 4))
        pie_result = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.82,
        )
        autotexts = pie_result[2] if len(pie_result) > 2 else []
        for at in autotexts:
            at.set_fontsize(9)
            at.set_color("white")
            at.set_fontweight("bold")

        ax.set_title(
            "Distribution of Delinquency", fontsize=12, fontweight="bold", pad=10
        )
        return self._figure_to_base64(fig)

    def _bar_chart(self, stats: Dict[str, Any]) -> str:
        cats = stats.get("by_category", {})
        labels = [v.get("label", k) for k, v in cats.items()]
        counts = [v["count"] for v in cats.values()]
        colors = [COLORS.get(k, "#999") for k in cats]

        fig, ax = plt.subplots(figsize=(6, 3.5))
        bars = ax.bar(labels, counts, color=colors, edgecolor="white", linewidth=0.8)

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(count),
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )

        ax.set_ylabel("Client Count")
        ax.set_title("Clients by Category", fontsize=12, fontweight="bold")
        ax.set_ylim(0, max(counts) * 1.25 if counts else 1)
        plt.xticks(rotation=15, ha="right", fontsize=9)
        plt.tight_layout()
        return self._figure_to_base64(fig)

    def _debt_by_category_chart(self, stats: Dict[str, Any]) -> str:
        cats = stats.get("by_category", {})
        labels = [v.get("label", k) for k, v in cats.items()]
        debts = [v["total_debt"] for v in cats.values()]
        colors = [COLORS.get(k, "#999") for k in cats]

        fig, ax = plt.subplots(figsize=(6, 3.5))
        bars = ax.barh(labels, debts, color=colors, edgecolor="white")

        for bar, val in zip(bars, debts):
            ax.text(
                bar.get_width() + max(debts) * 0.01 if debts else 0,
                bar.get_y() + bar.get_height() / 2,
                f"R$ {val:,.0f}",
                va="center",
                fontsize=9,
            )

        ax.set_xlabel("Value (R$)")
        ax.set_title("Debt by Category", fontsize=12, fontweight="bold")
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))
        plt.tight_layout()
        return self._figure_to_base64(fig)

    def _build_html(
        self,
        df: pd.DataFrame,
        stats: Dict[str, Any],
        sending_results: List[Any],
        charts: Dict[str, str],
    ) -> str:
        date_time = datetime.now().strftime("%d/%m/%Y at %H:%M")
        total_clients = stats.get("total_clients", 0)
        total_debt = stats.get("total_debt", 0)

        total_sent = len(sending_results)
        sent_ok = sum(
            1
            for r in sending_results
            if (r.get("success") if isinstance(r, dict) else r.success)
        )
        rate = round(sent_ok / total_sent * 100, 1) if total_sent > 0 else 0
        cards_html = ""
        for cat, data in stats.get("by_category", {}).items():
            color = COLORS.get(cat, "#999")
            label = data.get("label", cat)
            cards_html += f"""
            <div class="card" style="border-left: 4px solid {color};">
              <div class="card-label" style="color:{color};">{label}</div>
              <div class="card-value">{data["count"]}</div>
              <div class="card-sub">R$ {data["total_debt"]:,.2f}</div>
            </div>"""

        table_rows = ""

        def img_tag(b64):
            return (
                f'<img src="data:image/png;base64,{b64}" style="max-width:100%;border-radius:6px;">'
                if b64
                else ""
            )

        if not df.empty:
            for _, row in df.iterrows():
                cat_value = row.get("category", "")
                cat = "" if cat_value is None else str(cat_value)
                color = COLORS.get(cat, "#999")
                client_id_value = row.get("client_id", "")
                name_value = row.get("name", "")
                company_value = row.get("company", "")
                value_value = row.get("value", 0.0)
                days_value = row.get("days_overdue", 0)

                client_id = "" if client_id_value is None else str(client_id_value)
                name = "" if name_value is None else str(name_value)
                company = "" if company_value is None else str(company_value)
                try:
                    value = float(value_value) if value_value is not None else 0.0
                except (TypeError, ValueError):
                    value = 0.0
                try:
                    days = int(days_value) if days_value is not None else 0
                except (TypeError, ValueError):
                    days = 0

                table_rows += f"""
                <tr>
                  <td>{client_id}</td>
                  <td>{name}</td>
                  <td>{company}</td>
                  <td>R$ {value:,.2f}</td>
                  <td>
                    <span class="badge" style="background-color:{color}20; color:{color}; border:1px solid {color};">
                      {days} days
                    </span>
                  </td>
                  <td>{cat.capitalize() if cat else ""}</td>
                </tr>"""

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Billing Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f5f7fa; margin: 0; padding: 20px; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; color: #2c3e50; font-size: 24px; }}
                .header .meta {{ text-align: right; color: #7f8c8d; font-size: 14px; }}
                
                .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .kpi {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #e9ecef; }}
                .kpi .label {{ font-size: 13px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }}
                .kpi .value {{ font-size: 28px; font-weight: bold; color: #2c3e50; }}
                .kpi .sub {{ font-size: 12px; color: #95a5a6; margin-top: 5px; }}

                .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 30px; margin-bottom: 40px; }}
                .chart-box {{ background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 15px; text-align: center; }}
                
                .category-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
                .card {{ background: #fff; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); border: 1px solid #eee; }}
                .card-label {{ font-weight: bold; font-size: 14px; margin-bottom: 5px; }}
                .card-value {{ font-size: 20px; font-weight: bold; color: #333; }}
                .card-sub {{ font-size: 12px; color: #7f8c8d; }}

                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                th {{ text-align: left; padding: 12px; background: #f8f9fa; border-bottom: 2px solid #e9ecef; color: #7f8c8d; font-weight: 600; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                tr:hover {{ background-color: #f8f9fa; }}
                .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; display: inline-block; }}
                
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #95a5a6; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>Billing Report</h1>
                        <div style="margin-top:5px; color:#7f8c8d;">{self.config.company.name}</div>
                    </div>
                    <div class="meta">
                        Generated on: <strong>{date_time}</strong><br>
                        Period: Current Cycle
                    </div>
                </div>

                <!-- Global KPIs -->
                <div class="kpi-grid">
                    <div class="kpi">
                        <div class="label">Total Clients</div>
                        <div class="value">{total_clients}</div>
                    </div>
                    <div class="kpi">
                        <div class="label">Total Debt</div>
                        <div class="value" style="color:#e74c3c;">R$ {total_debt:,.2f}</div>
                    </div>
                    <div class="kpi">
                        <div class="label">Emails Sent</div>
                        <div class="value">{sent_ok}/{total_sent}</div>
                        <div class="sub">Success Rate: {rate}%</div>
                    </div>
                </div>

                <!-- Category Cards -->
                <h3>Summary by Category</h3>
                <div class="category-cards">
                    {cards_html}
                </div>

                <!-- Charts -->
                <div class="charts-grid">
                    <div class="chart-box">
                        {img_tag(charts.get("pie"))}
                    </div>
                    <div class="chart-box">
                        {img_tag(charts.get("bar"))}
                    </div>
                    <div class="chart-box">
                        {img_tag(charts.get("debt"))}
                    </div>
                </div>

                <!-- Detailed Table -->
                <h3>Delinquent Clients (Top 50)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Company</th>
                            <th>Value</th>
                            <th>Delay</th>
                            <th>Category</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                
                <div class="footer">
                    Automated System | Generated by Python ReportGenerator
                </div>
            </div>
        </body>
        </html>
        """
        return html_template

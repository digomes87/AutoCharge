from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from src.config import AppConfig


@dataclass
class EmailMessage:
    recipient: str
    recipient_name: str
    subject: str
    html_body: str
    text_body: str
    category: str
    client_id: str
    has_attachment: bool = False
    attachment_path: Optional[str] = None


class EmailTemplates:
    """Generates personalized emails by delinquency category."""

    def __init__(self, config: AppConfig):
        self.company = config.company

    def generate_email(self, client: Dict[str, Any], category: str) -> EmailMessage:
        """Email factory: dispatches to the correct template."""
        generators: Dict[str, Callable[[Dict[str, Any]], EmailMessage]] = {
            "light": self._template_light,
            "medium": self._template_medium,
            "critical": self._template_critical,
            "judicial": self._template_judicial,
        }
        generator = generators.get(category)
        if not generator:
            raise ValueError(f"Unknown category: {category}")
        return generator(client)

    # ─────────────────────────────────────────────
    # TEMPLATES
    # ─────────────────────────────────────────────

    def _template_light(self, c: Dict[str, Any]) -> EmailMessage:
        subject = f"Payment Reminder - {self.company.name}"
        value_fmt = f"R$ {float(c['value']):,.2f}"

        html_body = self._html_wrapper(
            category_color="#4CAF50",
            category_label="FRIENDLY REMINDER",
            client=c,
            value_fmt=value_fmt,
            body=f"""
            <p>Hello, <strong>{c["name"]}</strong>!</p>
            <p>We hope everything is well with you and <strong>{c["company"]}</strong>.</p>
            <p>We are writing to let you know that we identified an open invoice regarding your
               plan <strong>{c["plan"]}</strong>, which is <strong>{c["days_overdue"]} days overdue</strong>.</p>
            <p>Sometimes this happens due to forgetfulness or unforeseen events - no problem! Just
               regularize it by the end of this week to avoid additional charges.</p>
            <table class="valor-box">
              <tr><td>Amount Due:</td><td><strong>{value_fmt}</strong></td></tr>
              <tr><td>Days Overdue:</td><td><strong>{c["days_overdue"]} days</strong></td></tr>
            </table>
            <p>If you have already made the payment, please disregard this notice.</p>
            <p>If you have any questions, we are at your disposal!</p>
            """,
        )

        text_body = f"""Hello, {c["name"]}!

We identified an open invoice regarding your plan {c["plan"]}.
Value: {value_fmt} | Overdue: {c["days_overdue"]} days

Please regularize your situation to avoid charges.
If you have already paid, disregard this notice.

Support: {self.company.support_email} | {self.company.phone}
{self.company.name}"""

        return EmailMessage(
            recipient=c["email"],
            recipient_name=c["name"],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            category="light",
            client_id=str(c["client_id"]),
        )

    def _template_medium(self, c: Dict[str, Any]) -> EmailMessage:
        subject = f"Payment Overdue Notice - {self.company.name}"
        value_fmt = f"R$ {float(c['value']):,.2f}"

        html_body = self._html_wrapper(
            category_color="#FF9800",
            category_label="SECOND NOTICE",
            client=c,
            value_fmt=value_fmt,
            body=f"""
            <p>Dear <strong>{c["name"]}</strong>,</p>
            <p>We are contacting you regarding the outstanding payment for <strong>{c["company"]}</strong>,
               plan <strong>{c["plan"]}</strong>, with <strong>{c["days_overdue"]} days of delay</strong>.</p>
            <p>We previously sent a reminder, but we have not identified the regularization yet.
               We request that you arrange payment within <strong>5 business days</strong> to avoid
               the application of contractual fines and interest.</p>
            <table class="valor-box">
              <tr><td>Principal Amount:</td><td><strong>{value_fmt}</strong></td></tr>
              <tr><td>Days Overdue:</td><td><strong>{c["days_overdue"]} days</strong></td></tr>
              <tr><td>Status:</td><td><strong>Second Notice</strong></td></tr>
            </table>
            <p>To negotiate or pay in installments, contact our finance department:</p>
            <p>{self.company.support_email} | {self.company.phone}</p>
            <p>If payment has already been made, please forward the receipt to this email.</p>
            """,
        )

        text_body = f"""Dear {c["name"]},

SECOND NOTICE - Payment overdue for {c["days_overdue"]} days.

Company: {c["company"]} | Plan: {c["plan"]}
Value: {value_fmt}

Regularize within 5 business days to avoid fines and interest.
To negotiate: {self.company.support_email} | {self.company.phone}

{self.company.name}"""

        return EmailMessage(
            recipient=c["email"],
            recipient_name=c["name"],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            category="medium",
            client_id=str(c["client_id"]),
        )

    def _template_critical(self, c: Dict[str, Any]) -> EmailMessage:
        subject = f"URGENT: Critical Financial Pendency - {self.company.name}"
        value_fmt = f"R$ {float(c['value']):,.2f}"

        html_body = self._html_wrapper(
            category_color="#F44336",
            category_label="CRITICAL NOTICE",
            client=c,
            value_fmt=value_fmt,
            body=f"""
            <p>Dear <strong>{c["name"]}</strong>,</p>
            <p>This is an <strong>urgent</strong> communication regarding the delinquency of
               <strong>{c["company"]}</strong> with {self.company.name}.</p>
            <p>After multiple notices without response, your account is
               <strong>{c["days_overdue"]} days overdue</strong>, a situation that may result in:</p>
            <ul>
              <li>Immediate service suspension ({c["plan"]})</li>
              <li>Addition of fine (2%) + interest (1% p.m.)</li>
              <li>Negative credit reporting</li>
            </ul>
            <table class="valor-box" style="border-color:#F44336;">
              <tr><td>Amount Due:</td><td><strong style="color:#F44336;">{value_fmt}</strong></td></tr>
              <tr><td>Days Overdue:</td><td><strong style="color:#F44336;">{c["days_overdue"]} days</strong></td></tr>
              <tr><td>Status:</td><td><strong style="color:#F44336;">CRITICAL - Immediate action required</strong></td></tr>
            </table>
            <p><strong>Deadline for regularization: 48 hours.</strong></p>
            <p>For urgent negotiation or installment plan, contact our finance department
               <strong>immediately</strong>:<br>
               {self.company.support_email} | {self.company.phone}</p>
            """,
        )

        text_body = f"""CRITICAL NOTICE - {c["name"]}

Delay of {c["days_overdue"]} days detected - {c["company"]} / Plan {c["plan"]}
Value: {value_fmt}

Deadline: 48 hours for regularization.
Risk: Service suspension + credit reporting.

URGENT Contact: {self.company.support_email} | {self.company.phone}

{self.company.name}"""

        return EmailMessage(
            recipient=c["email"],
            recipient_name=c["name"],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            category="critical",
            client_id=str(c["client_id"]),
            has_attachment=False,
        )

    def _template_judicial(self, c: Dict[str, Any]) -> EmailMessage:
        """Internal template - sent to legal team, not to client."""
        subject = f"[LEGAL] Client for judicial collection - ID {c['client_id']}"
        value_fmt = f"R$ {float(c['value']):,.2f}"
        today_date = datetime.now().strftime("%d/%m/%Y")

        html_body = self._html_wrapper(
            category_color="#9C27B0",
            category_label="LEGAL REFERRAL",
            client=c,
            value_fmt=value_fmt,
            body=f"""
            <p><strong>Report Date:</strong> {today_date}</p>
            <p>The client below has exceeded 30 days of delinquency and should be
               forwarded for judicial / extrajudicial collection.</p>
            <table class="valor-box" style="border-color:#9C27B0;">
              <tr><td>Client ID:</td><td><strong>{c["client_id"]}</strong></td></tr>
              <tr><td>Name:</td><td><strong>{c["name"]}</strong></td></tr>
              <tr><td>Company:</td><td><strong>{c["company"]}</strong></td></tr>
              <tr><td>Phone:</td><td><strong>{c["phone"]}</strong></td></tr>
              <tr><td>Email:</td><td><strong>{c["email"]}</strong></td></tr>
              <tr><td>Plan:</td><td><strong>{c["plan"]}</strong></td></tr>
              <tr><td>Amount Due:</td><td><strong style="color:#9C27B0;">{value_fmt}</strong></td></tr>
              <tr><td>Days Overdue:</td><td><strong style="color:#9C27B0;">{c["days_overdue"]} days</strong></td></tr>
              <tr><td>Last Payment:</td><td><strong>{c["last_payment"]}</strong></td></tr>
            </table>
            <p><em>Automatically forwarded by the Billing System.</em></p>
            """,
        )

        text_body = f"""[LEGAL] Client for collection - {today_date}

ID: {c["client_id"]} | {c["name"]} | {c["company"]}
Phone: {c["phone"]} | Email: {c["email"]}
Plan: {c["plan"]} | Value: {value_fmt}
Delay: {c["days_overdue"]} days | Last Payment: {c["last_payment"]}

Forwarded by the Automated Billing System."""

        return EmailMessage(
            recipient=self.company.support_email,
            recipient_name="Legal Team",
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            category="judicial",
            client_id=str(c["client_id"]),
        )

    # ─────────────────────────────────────────────
    # HTML WRAPPER
    # ─────────────────────────────────────────────

    def _html_wrapper(
        self,
        category_color: str,
        category_label: str,
        client: Dict[str, Any],
        value_fmt: str,
        body: str,
    ) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f5f5f5; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff;
                border-radius:8px; overflow:hidden;
                box-shadow:0 2px 10px rgba(0,0,0,.1); }}
  .header {{ background:{category_color}; color:#fff; padding:20px 30px; }}
  .header h1 {{ margin:0; font-size:20px; }}
  .header p {{ margin:4px 0 0; opacity:.9; font-size:13px; }}
  .badge {{ display:inline-block; background:rgba(255,255,255,.25);
            padding:3px 10px; border-radius:12px; font-size:12px;
            font-weight:bold; margin-bottom:8px; }}
  .body {{ padding:30px; color:#333; line-height:1.6; }}
  .body p {{ margin:0 0 14px; }}
  .body ul {{ margin:0 0 14px 20px; }}
  .body li {{ margin-bottom:6px; }}
  .valor-box {{ width:100%; border-collapse:collapse;
                border:2px solid {category_color};
                border-radius:6px; margin:16px 0;
                background:#fafafa; }}
  .valor-box td {{ padding:10px 16px; font-size:14px; border-bottom:1px solid #eee; }}
  .valor-box tr:last-child td {{ border-bottom:none; }}
  .footer {{ background:#f9f9f9; border-top:1px solid #eee;
             padding:16px 30px; font-size:12px; color:#888; text-align:center; }}
  .footer a {{ color:{category_color}; text-decoration:none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">{category_label}</div>
    <h1>{self.company.name}</h1>
    <p>Finance Department</p>
  </div>
  <div class="body">
    {body}
  </div>
  <div class="footer">
    <p>
      {self.company.name} &nbsp;|&nbsp;
      <a href="mailto:{self.company.support_email}">{self.company.support_email}</a> &nbsp;|&nbsp;
      {self.company.phone}
    </p>
    <p><a href="http://{self.company.website}">{self.company.website}</a></p>
    <p style="font-size:10px;color:#bbb;">
      This is an automated email. To unsubscribe, please contact our support.
    </p>
  </div>
</div>
</body>
</html>"""

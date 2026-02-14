"""Notification system for alerting users about new studies via email and SMS."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .scraper import Study

logger = logging.getLogger(__name__)


def _build_study_summary(studies: list[Study]) -> str:
    """Build a plain-text summary of new studies."""
    lines = [f"Found {len(studies)} new SPP Impact Study posting(s):\n"]
    for i, study in enumerate(studies, 1):
        lines.append(f"{i}. {study.name}")
        lines.append(f"   Category: {study.year_type_label}")
        lines.append(f"   Link: {study.url}")
        if study.details:
            for key, val in study.details.items():
                if not key.endswith("_url") and val:
                    lines.append(f"   {key}: {val}")
        lines.append("")
    lines.append("---")
    lines.append("SPP OpsPortal: https://opsportal.spp.org/Studies/Gen")
    return "\n".join(lines)


def _build_study_html(studies: list[Study]) -> str:
    """Build an HTML summary of new studies."""
    rows = []
    for study in studies:
        detail_cells = ""
        if study.details:
            for key, val in study.details.items():
                if not key.endswith("_url") and val:
                    detail_cells += f"<br><small><b>{key}:</b> {val}</small>"

        rows.append(
            f"""<tr>
            <td style="padding:8px;border:1px solid #ddd;">
                <a href="{study.url}">{study.name}</a>
            </td>
            <td style="padding:8px;border:1px solid #ddd;">{study.year_type_label}</td>
            <td style="padding:8px;border:1px solid #ddd;">
                <a href="{study.url}">View</a>{detail_cells}
            </td>
        </tr>"""
        )

    return f"""<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
<h2 style="color:#003366;">New SPP Impact Studies Available</h2>
<p>{len(studies)} new study posting(s) detected on the
<a href="https://opsportal.spp.org/Studies/Gen">SPP OpsPortal</a>.</p>
<table style="border-collapse:collapse;width:100%;">
    <tr style="background:#003366;color:white;">
        <th style="padding:8px;border:1px solid #ddd;">Study Name</th>
        <th style="padding:8px;border:1px solid #ddd;">Category</th>
        <th style="padding:8px;border:1px solid #ddd;">Details</th>
    </tr>
    {"".join(rows)}
</table>
<p style="color:#666;font-size:12px;margin-top:20px;">
    This alert was sent by the SPP Impact Study Monitor.<br>
    Visit <a href="https://opsportal.spp.org/Studies/Gen">SPP OpsPortal</a>
    for full details.
</p>
</body></html>"""


class EmailNotifier:
    """Send email notifications about new studies via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls

    def send(self, recipients: list[str], studies: list[Study]) -> bool:
        """Send an email alert about new studies.

        Args:
            recipients: List of email addresses.
            studies: List of new studies to include in the alert.

        Returns:
            True if email was sent successfully.
        """
        if not recipients:
            logger.warning("No email recipients configured, skipping email notification")
            return False

        if not studies:
            logger.info("No new studies to report, skipping email")
            return True

        subject = f"[SPP Alert] {len(studies)} New Impact Study Posting(s)"
        text_body = _build_study_summary(studies)
        html_body = _build_study_html(studies)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            server.login(self.username, self.password)
            server.sendmail(self.from_address, recipients, msg.as_string())
            server.quit()
            logger.info("Email sent to %d recipient(s)", len(recipients))
            return True
        except smtplib.SMTPException as e:
            logger.error("Failed to send email: %s", e)
            return False


class SMSNotifier:
    """Send SMS/text notifications about new studies via Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self._client: Optional[object] = None

    def _get_client(self):
        """Lazy-load the Twilio client."""
        if self._client is None:
            try:
                from twilio.rest import Client

                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                logger.error(
                    "twilio package is not installed. "
                    "Install it with: pip install twilio"
                )
                raise
        return self._client

    def send(self, phone_numbers: list[str], studies: list[Study]) -> bool:
        """Send SMS alerts about new studies.

        Args:
            phone_numbers: List of phone numbers in E.164 format (e.g., +1234567890).
            studies: List of new studies to alert about.

        Returns:
            True if all messages were sent successfully.
        """
        if not phone_numbers:
            logger.warning("No phone numbers configured, skipping SMS notification")
            return False

        if not studies:
            logger.info("No new studies to report, skipping SMS")
            return True

        # SMS has character limits, so keep it brief
        if len(studies) == 1:
            body = (
                f"SPP Alert: New impact study posted - {studies[0].name}. "
                f"Category: {studies[0].year_type_label}. "
                f"View: {studies[0].url}"
            )
        else:
            study_names = ", ".join(s.name for s in studies[:3])
            extra = f" (+{len(studies) - 3} more)" if len(studies) > 3 else ""
            body = (
                f"SPP Alert: {len(studies)} new impact studies posted: "
                f"{study_names}{extra}. "
                f"View all: https://opsportal.spp.org/Studies/Gen"
            )

        # Truncate to SMS limit
        if len(body) > 1600:
            body = body[:1597] + "..."

        client = self._get_client()
        all_sent = True

        for number in phone_numbers:
            try:
                message = client.messages.create(
                    body=body,
                    from_=self.from_number,
                    to=number,
                )
                logger.info("SMS sent to %s (SID: %s)", number, message.sid)
            except Exception as e:
                logger.error("Failed to send SMS to %s: %s", number, e)
                all_sent = False

        return all_sent

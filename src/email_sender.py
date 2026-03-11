import json
import smtplib
import ssl
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import AppConfig
from src.email_templates import EmailMessage
from src.logger import LogManager

logger = LogManager.get_logger("EmailSender")


@dataclass
class SendingResult:
    client_id: str
    recipient: str
    category: str
    success: bool
    timestamp: str = ""
    error: Optional[str] = None
    attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmailSender:
    """Sends emails via SMTP with retry support and rate limiting."""

    def __init__(self, config: AppConfig, password: str):
        self.config = config.email
        self.company_config = config.company
        self.test_mode = config.test_mode
        self.test_email = config.test_email
        self.password = password
        self.history: List[SendingResult] = []
        self._connection: Optional[smtplib.SMTP] = None

    def connect(self) -> None:
        """Establishes SMTP connection."""
        cfg = self.config
        try:
            context = ssl.create_default_context()
            self._connection = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
            self._connection.ehlo()
            if cfg.use_tls:
                self._connection.starttls(context=context)
                self._connection.ehlo()
            self._connection.login(cfg.sender_email, self.password)
            logger.info(f"Connected to SMTP: {cfg.smtp_host}:{cfg.smtp_port}")
        except Exception as e:
            logger.error(f"SMTP connection failure: {e}")
            raise

    def disconnect(self) -> None:
        """Closes the SMTP connection."""
        if self._connection:
            try:
                self._connection.quit()
                logger.info("SMTP connection closed.")
            except Exception:
                pass
            self._connection = None

    def send(self, message: EmailMessage) -> SendingResult:
        """Sends an email with automatic retry."""
        max_attempts = self.config.max_retries
        delay = self.config.rate_limit_seconds
        real_recipient = self.test_email if self.test_mode else message.recipient
        error_msg = None

        for attempt in range(1, max_attempts + 1):
            try:
                if self._connection is None:
                    self.connect()

                msg = self._build_mime(message, real_recipient)
                connection = self._connection
                if connection is None:
                    raise RuntimeError("SMTP connection not estabilish")
                connection.sendmail(
                    self.config.sender_email, real_recipient, msg.as_string()
                )

                timestamp = datetime.now().isoformat()
                result = SendingResult(
                    client_id=message.client_id,
                    recipient=message.recipient,
                    category=message.category,
                    success=True,
                    timestamp=timestamp,
                    attempts=attempt,
                )

                log_msg = f"Email sent to {real_recipient} | {message.category}"
                if self.test_mode:
                    log_msg = f"[TEST] {log_msg} (original: {message.recipient})"
                logger.info(log_msg)

                self.history.append(result)
                time.sleep(delay)
                return result

            except smtplib.SMTPRecipientsRefused as e:
                error_msg = f"Email refused: {e}"
                logger.warning(f"{error_msg} (client {message.client_id})")
                break  # Do not retry for refused recipients

            except (smtplib.SMTPServerDisconnected, smtplib.SMTPSenderRefused) as e:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}")
                if attempt < max_attempts:
                    logger.info("Reconnecting...")
                    self.disconnect()
                    try:
                        self.connect()
                    except Exception:
                        pass
                    time.sleep(delay * attempt)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error sending (attempt {attempt}): {error_msg}")
                if attempt < max_attempts:
                    time.sleep(delay * attempt)

        # Failed after all attempts
        result = SendingResult(
            client_id=message.client_id,
            recipient=message.recipient,
            category=message.category,
            success=False,
            timestamp=datetime.now().isoformat(),
            error=error_msg if error_msg else "Failed after max attempts",
            attempts=max_attempts,
        )
        self.history.append(result)
        return result

    def send_batch(self, messages: List[EmailMessage]) -> List[SendingResult]:
        """Sends a list of messages and returns the results."""
        if not messages:
            logger.info("No messages to send.")
            return []

        logger.info(f"Starting batch send of {len(messages)} emails...")
        results = []

        try:
            self.connect()
            for i, msg in enumerate(messages, 1):
                logger.info(f"  [{i}/{len(messages)}] Sending to {msg.recipient}...")
                result = self.send(msg)
                results.append(result)
        except Exception as e:
            logger.error(f"Batch sending interrupted: {e}")
        finally:
            self.disconnect()

        sent_count = sum(1 for r in results if r.success)
        failures = len(results) - sent_count
        logger.info(f"Result: {sent_count} sent | {failures} failures")
        return results

    def _build_mime(self, message: EmailMessage, real_recipient: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
        msg["To"] = real_recipient
        msg["Subject"] = message.subject

        if self.test_mode:
            msg["Subject"] = f"[TEST] {message.subject}"

        msg.attach(MIMEText(message.text_body, "plain", "utf-8"))
        msg.attach(MIMEText(message.html_body, "html", "utf-8"))

        if message.has_attachment and message.attachment_path:
            self._add_attachment(msg, message.attachment_path)

        return msg

    def _add_attachment(self, msg: MIMEMultipart, path: str) -> None:
        """Adds file as email attachment."""
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"Attachment not found: {path}")
            return

        try:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", f'attachment; filename="{path_obj.name}"'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to attach file {path}: {e}")

    def save_log(self, path: str) -> None:
        """Saves sending history to JSON."""
        data = [r.to_dict() for r in self.history]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Sending log saved: {path}")
        except Exception as e:
            logger.error(f"Failed to save log: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.history)
        success = sum(1 for r in self.history if r.success)
        return {
            "total": total,
            "success": success,
            "failure": total - success,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
        }

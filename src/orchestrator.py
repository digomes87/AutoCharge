import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import AppConfig
from src.data_processor import DataProcessor
from src.email_sender import EmailSender, SendingResult
from src.email_templates import EmailTemplates
from src.interfaces import (
    DataProcessorProtocol,
    EmailSenderProtocol,
    EmailTemplatesProtocol,
    ReportGeneratorProtocol,
)
from src.logger import LogManager
from src.report_generator import ReportGenerator

logger = LogManager.get_logger("Orchestrator")


class Orchestrator:
    """Orchestrates the full automated billing flow."""

    def __init__(
        self,
        config_path: str = "config.json",
        email_password: str = "",
        processor: Optional[DataProcessorProtocol] = None,
        templates: Optional[EmailTemplatesProtocol] = None,
        report_gen: Optional[ReportGeneratorProtocol] = None,
        sender: Optional[EmailSenderProtocol] = None,
    ):
        self.config = AppConfig.load(config_path)
        self.email_password = email_password or os.getenv("EMAIL_PASSWORD", "")

        LogManager.setup(self.config.data.logs_dir)

        self.processor = processor or DataProcessor(self.config)
        self.templates = templates or EmailTemplates(self.config)
        self.report_gen = report_gen or ReportGenerator(self.config)
        self.sender = sender  # Will be initialized in run() if None and needed, or used if provided

    def run(
        self, send_emails: bool = True, generate_report: bool = True
    ) -> Dict[str, Any]:
        """Executes the full billing cycle."""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("STARTING AUTOMATED BILLING SYSTEM")
        logger.info(f"   Company: {self.config.company.name}")
        logger.info(f"   Test Mode: {self.config.test_mode}")
        logger.info("=" * 60)

        logger.info("\nSTEP 1: Data Processing")
        df = self.processor.load_data()
        logger.info(self.processor.summary())

        logger.info("\nSTEP 2: Message Generation")
        email_categories = ["light", "medium", "critical"]
        messages = []

        for category in email_categories:
            clients = self.processor.get_clients_by_category(category)
            logger.info(f"  [{category.upper():8}] {len(clients)} messages prepared")
            for _, client in clients.iterrows():
                try:
                    msg = self.templates.generate_email(client.to_dict(), category)
                    messages.append(msg)
                except Exception as e:
                    logger.error(
                        f"  Error generating message for {client['client_id']}: {e}"
                    )

        judicial_clients = self.processor.get_judicial_clients()
        if not judicial_clients.empty:
            logger.info(
                f"  [JUDICIAL ] {len(judicial_clients)} clients for legal referral"
            )
            for _, client in judicial_clients.iterrows():
                try:
                    msg = self.templates.generate_email(client.to_dict(), "judicial")
                    messages.append(msg)
                except Exception as e:
                    logger.error(
                        f"  Error generating judicial message for {client['client_id']}: {e}"
                    )

        logger.info(f"  Total: {len(messages)} messages generated")

        sending_results: List[SendingResult] = []
        if send_emails:
            logger.info("\nSTEP 3: Email Delivery")
            if not self.sender:
                if not self.email_password:
                    logger.warning(
                        "Email password not configured. "
                        "Set EMAIL_PASSWORD environment variable or pass it to the constructor."
                    )
                else:
                    self.sender = EmailSender(self.config, self.email_password)

            if self.sender:
                try:
                    sending_results = self.sender.send_batch(messages)

                    total = len(sending_results)
                    success = sum(1 for r in sending_results if r.success)
                    rate = round(success / total * 100, 1) if total > 0 else 0

                    logger.info(f"  Delivery completed: {success}/{total} ({rate}%)")

                except Exception as e:
                    logger.error(f"  Email delivery failed: {e}")
        else:
            logger.info("\nSTEP 3: Email Delivery (SKIPPED)")

        report_path = None
        if generate_report:
            logger.info("\nSTEP 4: Report Generation")
            try:
                results_dict = [r.to_dict() for r in sending_results]

                report_path = self.report_gen.generate_html_report(
                    df=df,
                    statistics=self.processor.statistics.to_dict(),
                    sending_results=results_dict,
                )
                logger.info(f"  Report available at: {report_path}")
            except Exception as e:
                logger.error(f"  Failed to generate report: {e}")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "=" * 60)
        logger.info("EXECUTION COMPLETED")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"   Clients processed: {self.processor.statistics.total_clients}")
        logger.info(f"   Messages generated: {len(messages)}")
        if sending_results:
            success_count = sum(1 for r in sending_results if r.success)
            logger.info(f"   Emails sent: {success_count}/{len(sending_results)}")
        if report_path:
            logger.info(f"   Report: {report_path}")
        logger.info("=" * 60)

        return {
            "total_clients": self.processor.statistics.total_clients,
            "messages_generated": len(messages),
            "sending_results": sending_results,
            "report_path": report_path,
            "duration_seconds": round(duration, 1),
            "statistics": self.processor.statistics.to_dict(),
        }

    def report_only(self) -> Optional[str]:
        """Generates only the report without sending emails."""
        result = self.run(send_emails=False, generate_report=True)
        return result.get("report_path")


def start_scheduler(config_path: str = "config.json"):
    """Starts the APScheduler for automatic executions."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        return

    config = AppConfig.load(config_path)

    execution_time = config.schedule.execution_time
    hour, minute = execution_time.split(":")
    timezone = config.schedule.timezone

    scheduler = BlockingScheduler(timezone=timezone)

    def job():
        logger.info(f"Scheduled execution started at {datetime.now()}")
        orch = Orchestrator(config_path)
        orch.run()

    scheduler.add_job(job, "cron", hour=hour, minute=minute, id="billing_job")

    logger.info(f"Scheduler started. Next run at {execution_time} ({timezone})")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

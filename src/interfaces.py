from typing import Any, Dict, List, Optional, Protocol

import pandas as pd

from src.data_processor import BillingStatistics
from src.email_sender import SendingResult
from src.email_templates import EmailMessage


class DataProcessorProtocol(Protocol):
    """Protocol for data processing modules."""

    statistics: BillingStatistics

    def load_data(self, file_path: Optional[str] = None) -> pd.DataFrame: ...
    def get_clients_by_category(self, category: str) -> pd.DataFrame: ...
    def get_judicial_clients(self) -> pd.DataFrame: ...
    def summary(self) -> str: ...


class EmailTemplatesProtocol(Protocol):
    """Protocol for email template generation."""

    def generate_email(self, client: Dict[str, Any], category: str) -> EmailMessage: ...


class EmailSenderProtocol(Protocol):
    """Protocol for email sending services."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def send(self, message: EmailMessage) -> SendingResult: ...
    def send_batch(self, messages: List[EmailMessage]) -> List[SendingResult]: ...


class ReportGeneratorProtocol(Protocol):
    """Protocol for report generation."""

    def generate_html_report(
        self,
        df: pd.DataFrame,
        statistics: Dict[str, Any],
        sending_results: Optional[List[Any]] = None,
        filename: Optional[str] = None,
    ) -> str: ...

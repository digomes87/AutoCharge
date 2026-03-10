from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config import AppConfig
from logger import Logger

logger = Logger.get_logger("DataProcessor")


@dataclass
class BillingStatistics:
    total_clients: int = 0
    total_debt: float = 0.0
    by_category: Dict[str, Any] = field(default_factory=dict)
    invalid_emails: List[str] = field(default_factory=list)
    clients_without_email: List[str] = field(default_factory=list)
    processing_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataProcessor:
    """Processes and classifies delinquente client data"""

    REQUIRED_COLUMNS = [
        "client_id",
        "name",
        "email",
        "company",
        "plan",
        "value",
        "days_overdue",
        "last_payment",
        "phone",
    ]

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.categories = config.categories
        self.df: Optional[pd.DataFrame] = None
        self.statistics = BillingStatistics()

    def load_data(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """Loads and validates the client csv file"""
        if file_path is None:
            file_path = self.config.data.clients_file

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Loading data from: {file_path}")

        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                self.df = pd.read_csv(path, encoding=encoding)
                logger.info(f"File loaded with encoding {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if self.df is None:
            raise ValueError(
                "Could not read the CSV file with any supported for encoding"
            )

        self._translate_columns()
        self._validate_columns()
        self._clean_data()
        self._classify_clients()
        self._calculate_statistics()

        return self.df

    def _translate_columns(self) -> None:
        """Translate cloumn names from pt to eng if necessary"""
        if self.df is None:
            return

        mapping = {
            "id_cliene": "client_id",
            "nome": "name",
            "empresa": "company",
            "plano": "plan",
            "valor": "value",
            "dias_atraso": "days_overdue",
            "ultimo_pagamento": "last_payment",
            "telefone": "phone",
        }

        self.df.rename(
            columns={k: v for k, v in mapping.items() if k in self.df.columns},
            inplace=True,
        )

    def _validate_columns(self) -> None:
        """checks if all required columns are present"""
        if self.df is None:
            return

        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in self.df.columns
        ]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        logger.info("Column validation OK")

    def _clean_data(self) -> None:
        """Cleans and normalizes the data"""
        if self.df is None:
            pass

    def _classify_clients(self) -> None:
        pass

    def _calculate_statistics(self) -> None:
        pass

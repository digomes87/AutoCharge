import datetime
from dataclasses import asdict, dataclass, field, replace
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from config import AppConfig
from logger import LogManager

logger = LogManager.get_logger("DataProcessor")


def _skip_if_df_none(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.df is None:
            return
        return method(self, *args, **kwargs)

    return wrapper


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

    @_skip_if_df_none
    def _translate_columns(self) -> None:
        """Translate cloumn names from pt to eng if necessary"""
        df = self.df
        assert df is not None

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

        df.rename(
            columns={k: v for k, v in mapping.items() if k in df.columns},
            inplace=True,
        )

    @_skip_if_df_none
    def _validate_columns(self) -> None:
        """checks if all required columns are present"""
        df = self.df
        assert df is not None

        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        logger.info("Column validation OK")

    @_skip_if_df_none
    def _clean_data(self) -> None:
        """Cleans and normalizes the data"""
        df = self.df
        assert df is not None

        df.dropna(how="all", inplace=True)

        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["value"] = df["value"].fillna(0.0)
        df["days_overdue"] = pd.to_numeric(df["days_overdue"], errors="coerce")
        df["days_overdue"] = df["days_overdue"].fillna(0).astype(int)
        df["name"] = df["name"].astype(str).str.strip()
        df["email"] = df["email"].astype(str).str.strip()
        df["company"] = df["company"].astype(str).str.strip()
        df["phone"] = df["phone"].astype(str).str.strip()

        email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        email_invalid_mask = ~df["email"].str.match(email_pattern)

        invalid_emails_df = df[email_invalid_mask]
        if not invalid_emails_df.empty:
            self.statistics.invalid_emails = invalid_emails_df["client_id"].tolist()

        overdue_mask = df[df["days_overdue"] > 0]
        filtered_df = df.loc[overdue_mask].copy()
        self.df = cast(pd.DataFrame, filtered_df)

        logger.info(f"Data cleaned: {len(self.df)} clients with delay")

    @_skip_if_df_none
    def _classify_clients(self) -> None:
        """Classifies clientes into categories accordinf to delay days"""
        df = self.df
        assert df is not None

        def categorize() -> str:
            for cat_name, cat_config in self.categories.items():
                if cat_config.min_days <= cat_config.max_days:
                    return cat_name

            return "judicial"

        df["category"] = df["days_overdue"].apply(categorize)

        label_map = {name: config.label for name, config in self.categories.items()}
        df["category_label"] = df["category"].apply(
            lambda category: label_map.get(category, "")
        )

        priority_map = {"judicial": 0, "critical": 1, "medium": 2, "light": 3}
        df["category_order"] = df["category"].apply(
            lambda category: priority_map.get(category, 99)
        )
        df.sort_values("category_order", inplace=True)
        df.drop("category_order", inplace=True, errors="ignore")

        logger.info("Clients clssified by category")

    @_skip_if_df_none
    def _calculate_statistics(self) -> None:
        """Generate statistics of the billing process"""
        df = self.df
        assert df is not None

        by_category: Dict[str, Any] = {}
        for cat_name, cat_config in self.categories.items():
            sub = df[df["category"] == cat_name]
            by_category[cat_name] = {
                "count": len(sub),
                "total_debt": round(sub["value"].sum(), 2),
                "label": cat_config.label,
            }

        self.statistics = replace(
            self.statistics,
            total_clients=len(df),
            total_debt=round(df["value"].sum(), 2),
            by_category=by_category,
            processing_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        logger.info(
            f"Statistics calculated | Total debt: R$ {self.statistics.total_debt:,.2f}"
        )

    def get_clients_by_category(self, category: str) -> pd.DataFrame:
        """Returns clients filtered by category"""
        if self.df is None:
            raise RuntimeError("Data not loaded. Execute load_data() first")

        df = self.df
        filtered_df = df.loc[df["category"] == category].copy()
        return cast(pd.DataFrame, filtered_df)

    def get_judicial_clients(self) -> pd.DataFrame:
        """Exports only clients for legal referral"""
        return self.get_clients_by_category("judicial")

    def exports_csv_reports(self, output_path: str) -> None:
        """Exports processed data to CSV"""
        if self.df is None:
            return

        self.df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV report exported: {output_path}")

    def summary(self) -> str:
        """Returns formatte summary of statistics"""
        stats = self.statistics
        lines = [
            "=" * 50,
            f" Total delinquent: {stats.total_clients}",
            f" Total debt: R${stats.total_debt:,.2f}",
            "",
            " By category:",
        ]

        for cat, data in stats.by_category.items():
            lines.append(
                f" [{cat.upper():8}] {data['count']:3} clients | "
                f"R$ {data['total_debt']:>10,.2f} | {data['label']}"
            )

        if stats.invalid_emails:
            lines.append(f"\n Invalid emails: {stats.invalid_emails}")

        lines.append("=" * 50)
        return "\n".join(lines)

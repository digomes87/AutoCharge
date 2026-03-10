import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class CompanyConfig:
    name: str
    support_email: str
    phone: str
    website: str


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    use_tls: bool
    sender_email: str
    sender_name: str
    rate_limit_seconds: int
    max_retries: int


@dataclass
class DataConfig:
    clients_file: str
    logs_dir: str
    reports_dir: str


@dataclass
class CategoryConfig:
    min_days: int
    max_days: int
    label: str


@dataclass
class ScheduleConfig:
    execution_time: str
    weekdays: List[str]
    timezone: str


@dataclass
class AppConfig:
    company: CompanyConfig
    email: EmailConfig
    data: DataConfig
    categories: Dict[str, CategoryConfig]
    schedule: ScheduleConfig
    test_mode: bool
    test_email: str

    @classmethod
    def load(cls, config_path: str = "config.json") -> "AppConfig":
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            company=CompanyConfig(
                name=data["company"]["name"],
                support_email=data["company"]["support_email"],
                phone=data["company"]["phone"],
                website=data["company"]["website"],
            ),
            email=EmailConfig(
                smtp_host=data["email"]["smtp_host"],
                smtp_port=data["email"]["smtp_port"],
                use_tls=data["email"]["use_tls"],
                sender_email=data["email"]["sender_email"],
                sender_name=data["email"]["sender_name"],
                rate_limit_seconds=data["email"]["rate_limit_seconds"],
                max_retries=data["email"]["max_retries"],
            ),
            data=DataConfig(
                clients_file=data["data"]["clients_file"],
                logs_dir=data["data"]["logs_dir"],
                reports_dir=data["data"]["reports_dir"],
            ),
            categories={
                k: CategoryConfig(
                    min_days=v["min"], max_days=v["max"], label=v["label"]
                )
                for k, v in data["categories"].items()
            },
            schedule=ScheduleConfig(
                execution_time=data["schedule"]["execution_time"],
                weekdays=data["schedule"]["weekdays"],
                timezone=data["schedule"]["timezone"],
            ),
            test_mode=data.get("test_mode", True),
            test_email=data.get("test_email", ""),
        )

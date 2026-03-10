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
                name=data["empresa"]["nome"],
                support_email=data["empresa"]["email_suporte"],
                phone=data["empresa"]["telefone"],
                website=data["empresa"]["site"],
            ),
            email=EmailConfig(
                smtp_host=data["email"]["smtp_host"],
                smtp_port=data["email"]["smtp_port"],
                use_tls=data["email"]["usar_tls"],
                sender_email=data["email"]["email_remetente"],
                sender_name=data["email"]["nome_remetente"],
                rate_limit_seconds=data["email"]["rate_limit_segundos"],
                max_retries=data["email"]["max_tentativas"],
            ),
            data=DataConfig(
                clients_file=data["dados"]["arquivo_clientes"],
                logs_dir=data["dados"]["diretorio_logs"],
                reports_dir=data["dados"]["diretorio_relatorios"],
            ),
            categories={
                k: CategoryConfig(
                    min_days=v["min"], max_days=v["max"], label=v["label"]
                )
                for k, v in data["categorias"].items()
            },
            schedule=ScheduleConfig(
                execution_time=data["agendamento"]["horario_execucao"],
                weekdays=data["agendamento"]["dias_semana"],
                timezone=data["agendamento"]["timezone"],
            ),
            test_mode=data.get("modo_teste", True),
            test_email=data.get("email_teste", ""),
        )

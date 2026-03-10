import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class CompanyConfig:
    name: str
    support_email: str

import logging
from datetime import datetime
from pathlib import Path


class LogManager:
    """Manages application logging configuration."""

    @staticmethod
    def setup(log_dir: str = "logs") -> logging.Logger:
        """Configures the application logger."""
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = Path(log_dir) / f"billing_{timestamp}.log"

        logger = logging.getLogger("BillingSystem")
        logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        if logger.handlers:
            logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Returns a logger with the given name."""
        return logging.getLogger(f"BillingSystem.{name}")


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    return LogManager.setup(log_dir)


def get_logger(name: str) -> logging.Logger:
    return LogManager.get_logger(name)

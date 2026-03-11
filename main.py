import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.orchestrator import Orchestrator, start_scheduler


def main():
    parser = argparse.ArgumentParser(
        description="Automated Billing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                        Full cycle (test mode)
  python3 main.py --mode report          Generate HTML report only
  python3 main.py --no-email             Process without sending emails
  python3 main.py --mode schedule        Start automatic scheduler
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["run", "report", "schedule"],
        default="run",
        help="Operation mode (default: run)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Execute without sending emails (process and generate report only)",
    )

    args = parser.parse_args()

    if args.mode == "schedule":
        start_scheduler(args.config)
        return

    password = os.getenv("EMAIL_PASSWORD", "")
    orchestrator = Orchestrator(config_path=args.config, email_password=password)

    if args.mode == "report" or args.no_email:
        result = orchestrator.run(send_emails=False, generate_report=True)
    else:
        result = orchestrator.run(send_emails=True, generate_report=True)

    if result.get("report_path"):
        print(f"\nReport available at: {result['report_path']}")


if __name__ == "__main__":
    main()

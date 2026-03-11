# Automated Billing System

Python system for complete automation of the billing process for delinquent clients: classification by criticality, personalized email sending, and generation of management reports in HTML.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
# Option A - Environment variable (recommended)
export EMAIL_PASSWORD="your_app_password_here"

# Option B - .env file in root
echo "EMAIL_PASSWORD=your_app_password_here" > .env

# 3. Edit config.json with your company and SMTP data

# 4. Run (test mode - does not send real emails)
python3 main.py

# 5. Generate HTML report only
python3 main.py --mode report
```

---

## Project Structure

```
sistema_cobrancas/
├── src/
│   ├── data_processor.py    # Reading, validation, and classification of clients
│   ├── email_templates.py   # HTML templates by delay category
│   ├── email_sender.py      # SMTP sending with retry and rate limiting
│   ├── report_generator.py  # HTML report with charts
│   └── orchestrator.py      # Orchestrator + scheduler (APScheduler)
├── data/
│   └── clientes.csv         # Delinquent clients spreadsheet (input)
├── logs/                    # Execution and sending logs
├── reports/                 # Generated HTML reports
├── config.json              # System configuration
├── requirements.txt
├── main.py                  # Entry point
└── README.md
```

---

## Configuration (config.json)

```json
{
  "company": {
    "name": "My Company SA",
    "support_email": "finance@mycompany.com",
    "phone": "(11) 3000-0000",
    "website": "www.mycompany.com"
  },
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": true,
    "sender_email": "finance@mycompany.com",
    "sender_name": "Finance - My Company SA",
    "rate_limit_seconds": 2,
    "max_retries": 3
  },
  "test_mode": true,
  "test_email": "dev@company.com"
}
```

### Supported SMTP Providers

| Provider        | Host                | Port    |
| --------------- | ------------------- | ------- |
| Gmail           | smtp.gmail.com      | 587     |
| Outlook/Hotmail | smtp.office365.com  | 587     |
| Yahoo           | smtp.mail.yahoo.com | 587     |
| Own SMTP        | your.server.com     | 587/465 |

> **Gmail:** Use an [App Password](https://myaccount.google.com/apppasswords) (not your account password).

---

## Input Data (data/clientes.csv)

Required columns (headers can be in Portuguese or English):

| Column         | Type   | Description               |
| -------------- | ------ | ------------------------- |
| `client_id`    | string | Unique identifier         |
| `name`         | string | Full name                 |
| `email`        | string | Client email              |
| `company`      | string | Client company            |
| `plan`         | string | Contracted plan           |
| `value`        | float  | Overdue amount (Currency) |
| `days_overdue` | int    | Days of delinquency       |
| `last_payment` | date   | Date of last payment      |
| `phone`        | string | Contact phone             |

---

## Billing Categories

| Category     | Days Overdue | Action                                     |
| ------------ | ------------ | ------------------------------------------ |
| **Light**    | 1 - 7 days   | Friendly reminder email                    |
| **Medium**   | 8 - 15 days  | Second professional notice                 |
| **Critical** | 16 - 30 days | Urgent warning + 48h deadline              |
| **Judicial** | > 30 days    | Report for legal team (no email to client) |

---

## Execution Modes

```bash
# Full cycle (process + send emails + report)
python3 main.py --mode run

# Report only (without sending emails)
python3 main.py --mode report

# Full cycle without sending emails
python3 main.py --no-email

# Automatic scheduling (daily, weekdays, time in config.json)
python3 main.py --mode schedule

# Custom config
python3 main.py --config /path/to/other_config.json
```

---

## Automatic Scheduling

The system uses **APScheduler** for automatic execution. Configure in `config.json`:

```json
"schedule": {
  "execution_time": "08:00",
  "weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "timezone": "America/Sao_Paulo"
}
```

### Windows Task Scheduler (alternative)

1. Open Windows Task Scheduler
2. Create a new basic task
3. Set trigger: Daily, 08:00
4. Action: `python.exe C:\path\to\sistema_cobrancas\main.py`

---

## HTML Report

The report generated in `reports/` includes:

- KPIs: total delinquents, total value, sending rate
- Pie chart: distribution by category
- Bar chart: clients by category
- Horizontal chart: debt by category
- Complete table of delinquents
- Detailed log of each sending (success/failure)

---

## Security

- **Never** commit passwords in code or `config.json`
- Use environment variables: `export EMAIL_PASSWORD="..."`
- Or `.env` file (add to `.gitignore`)
- The `password` field does not exist in `config.json` intentionally

---

## Dependencies

```
pandas          # CSV data manipulation
matplotlib      # Report charts
seaborn         # Chart styling
apscheduler     # Automatic scheduling
python-dotenv   # .env loading
openpyxl        # .xlsx support (optional)
```

---

## Next Steps

- [ ] Web interface with Flask/FastAPI
- [ ] SQLite/PostgreSQL database for history
- [ ] WhatsApp integration (Twilio)
- [ ] Real-time dashboard
- [ ] PDF invoice sending as attachment
- [ ] REST API for ERP integration
- [ ] Email blacklist for opt-out

---

## Support

Questions or problems? Check logs in `logs/billing_*.log`.

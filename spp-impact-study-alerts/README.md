# SPP Impact Study Alert Monitor

Monitors the [SPP OpsPortal](https://opsportal.spp.org/Studies/Gen) for new Generator Interconnection impact study postings and sends alerts via **email** and/or **SMS text message**.

## How It Works

1. Scrapes the SPP OpsPortal study listing pages for current studies
2. Compares against previously seen studies stored in a local JSON file
3. Sends email (SMTP) and/or SMS (Twilio) notifications for any new postings
4. Can run locally as a cron job, or automatically via GitHub Actions

## Quick Start

### 1. Install dependencies

```bash
cd spp-impact-study-alerts
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your settings:

- **`monitor.year_type_ids`** — Which study categories to watch. Run `python main.py --discover` to see available IDs. Leave empty to monitor all.
- **`notifications.email_recipients`** — Email addresses to alert.
- **`notifications.sms_recipients`** — Phone numbers (E.164 format, e.g. `+12125551234`).
- **`smtp.*`** — Your SMTP server settings (Gmail, SendGrid, etc.).
- **`twilio.*`** — Your Twilio API credentials (for SMS).

### 3. Run

```bash
# Discover available study year types
python main.py --discover

# Do a dry run (check for studies, don't send alerts)
python main.py --dry-run

# Run for real (check + send alerts)
python main.py
```

## Configuration

All secret values can be set via **environment variables** instead of (or to override) the YAML config:

| Env Variable | Description |
|---|---|
| `SMTP_HOST` | SMTP server host (default: `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP server port (default: `587`) |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password / app password |
| `SMTP_FROM_ADDRESS` | Sender email address |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_FROM_NUMBER` | Twilio phone number (e.g. `+15017122661`) |
| `ALERT_EMAIL_RECIPIENTS` | Comma-separated email addresses |
| `ALERT_SMS_RECIPIENTS` | Comma-separated phone numbers |
| `SPP_YEAR_TYPE_IDS` | Comma-separated yearTypeId integers to monitor |

## Gmail Setup

To use Gmail as your SMTP provider:

1. Enable 2-Factor Authentication on your Google account
2. Generate an **App Password** at https://myaccount.google.com/apppasswords
3. Use your Gmail address as `SMTP_USERNAME` and the app password as `SMTP_PASSWORD`

## Twilio Setup (for SMS)

1. Sign up at https://www.twilio.com
2. Get your Account SID, Auth Token, and a phone number from the Twilio console
3. Set them in config or env variables

## Automated Monitoring with GitHub Actions

The included workflow (`.github/workflows/check-studies.yml`) runs every 6 hours automatically.

### Setup

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add the following **Repository Secrets** (only the ones you need):
   - `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`
   - `SMTP_HOST`, `SMTP_PORT` (if not using Gmail defaults)
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
   - `ALERT_EMAIL_RECIPIENTS` (comma-separated emails)
   - `ALERT_SMS_RECIPIENTS` (comma-separated phone numbers)
   - `SPP_YEAR_TYPE_IDS` (comma-separated IDs, e.g. `243,146`)

3. The workflow uses GitHub Actions cache to persist the seen-studies database between runs.

### Manual Trigger

You can also trigger a check manually from the GitHub Actions tab → "Check SPP Impact Studies" → "Run workflow". There is an option for dry-run mode.

## Running as a Local Cron Job

Add to your crontab (`crontab -e`) to check every 6 hours:

```cron
0 */6 * * * cd /path/to/spp-impact-study-alerts && /path/to/python main.py >> /var/log/spp-monitor.log 2>&1
```

## CLI Reference

```
python main.py                     # Check and send alerts
python main.py --dry-run           # Check without sending alerts
python main.py --discover          # List available study categories
python main.py --reset             # Clear seen-studies history
python main.py --config prod.yaml  # Use a different config file
python main.py --log-level DEBUG   # Verbose logging
```

## Project Structure

```
spp-impact-study-alerts/
├── main.py                    # CLI entry point
├── config.example.yaml        # Example configuration (copy to config.yaml)
├── requirements.txt           # Python dependencies
├── .gitignore
├── spp_monitor/
│   ├── __init__.py
│   ├── scraper.py             # SPP OpsPortal web scraper
│   ├── storage.py             # Tracks previously seen studies
│   ├── notifier.py            # Email and SMS notification senders
│   └── config.py              # Configuration loading (YAML + env vars)
└── .github/
    └── workflows/
        └── check-studies.yml  # GitHub Actions scheduled workflow
```

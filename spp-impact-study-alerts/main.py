#!/usr/bin/env python3
"""SPP Impact Study Monitor - Main entry point.

Checks the SPP OpsPortal for new generator interconnection impact studies
and sends alerts via email and/or SMS when new postings are detected.

Usage:
    python main.py                     # Run a check using config.yaml
    python main.py --config my.yaml    # Use a custom config file
    python main.py --discover          # List available study year types
    python main.py --reset             # Clear seen studies and start fresh
    python main.py --dry-run           # Check for new studies without sending alerts
"""

import argparse
import logging
import sys
from pathlib import Path

from spp_monitor.config import load_config
from spp_monitor.notifier import EmailNotifier, SMSNotifier
from spp_monitor.scraper import SPPScraper
from spp_monitor.storage import StudyStorage


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_discover(config):
    """Discover and list available study year types."""
    scraper = SPPScraper(
        request_delay=config.request_delay,
        max_retries=config.max_retries,
    )
    year_types = scraper.discover_year_types()
    if not year_types:
        print("No study year types found. The portal may be unavailable.")
        return 1

    print(f"\nFound {len(year_types)} study year type(s):\n")
    print(f"{'ID':<10} {'Label'}")
    print("-" * 60)
    for ytid, label in sorted(year_types.items()):
        print(f"{ytid:<10} {label}")
    print(
        "\nAdd desired IDs to your config.yaml under monitor.year_type_ids"
    )
    return 0


def cmd_reset(config):
    """Clear all seen studies."""
    storage = StudyStorage(Path(config.storage_path))
    count = storage.seen_count
    storage.clear()
    print(f"Cleared {count} seen studies. Next run will treat all studies as new.")
    return 0


def cmd_check(config, dry_run: bool = False):
    """Main check: scrape for new studies and send alerts."""
    logger = logging.getLogger("spp_monitor")

    # Initialize components
    scraper = SPPScraper(
        year_type_ids=config.year_type_ids or None,
        request_delay=config.request_delay,
        max_retries=config.max_retries,
    )
    storage = StudyStorage(Path(config.storage_path))

    # Fetch current studies
    print("Checking SPP OpsPortal for studies...")
    all_studies = scraper.fetch_all_studies()

    if not all_studies:
        print("No studies found. The portal may be unavailable or the page structure changed.")
        storage.update_last_check()
        return 1

    print(f"Found {len(all_studies)} total study entries")

    # Find new studies
    new_studies = storage.find_new_studies(all_studies)

    if not new_studies:
        print("No new studies since last check.")
        storage.update_last_check()
        return 0

    print(f"\n{'='*60}")
    print(f"  {len(new_studies)} NEW STUDY POSTING(S) DETECTED")
    print(f"{'='*60}\n")

    for i, study in enumerate(new_studies, 1):
        print(f"  {i}. {study.name}")
        print(f"     Category: {study.year_type_label}")
        print(f"     URL: {study.url}")
        if study.details:
            for key, val in study.details.items():
                if not key.endswith("_url") and val:
                    print(f"     {key}: {val}")
        print()

    if dry_run:
        print("[DRY RUN] Skipping notifications and not marking studies as seen.")
        return 0

    # Send notifications
    success = True

    # Email alerts
    if config.email_recipients and config.smtp.username:
        print(f"Sending email to {len(config.email_recipients)} recipient(s)...")
        email_notifier = EmailNotifier(
            smtp_host=config.smtp.host,
            smtp_port=config.smtp.port,
            username=config.smtp.username,
            password=config.smtp.password,
            from_address=config.smtp.from_address,
            use_tls=config.smtp.use_tls,
        )
        if not email_notifier.send(config.email_recipients, new_studies):
            logger.error("Email notification failed")
            success = False
        else:
            print("Email sent successfully.")
    elif config.email_recipients:
        print("Email recipients configured but SMTP credentials missing. Skipping email.")

    # SMS alerts
    if config.sms_recipients and config.twilio.account_sid:
        print(f"Sending SMS to {len(config.sms_recipients)} recipient(s)...")
        sms_notifier = SMSNotifier(
            account_sid=config.twilio.account_sid,
            auth_token=config.twilio.auth_token,
            from_number=config.twilio.from_number,
        )
        if not sms_notifier.send(config.sms_recipients, new_studies):
            logger.error("SMS notification failed")
            success = False
        else:
            print("SMS sent successfully.")
    elif config.sms_recipients:
        print("SMS recipients configured but Twilio credentials missing. Skipping SMS.")

    # Mark studies as seen (even if notifications failed, to avoid repeated alerts)
    storage.mark_seen(new_studies)
    print(f"\nMarked {len(new_studies)} studies as seen. Total tracked: {storage.seen_count}")

    return 0 if success else 2


def main():
    parser = argparse.ArgumentParser(
        description="SPP Impact Study Monitor - Get alerted when new studies are posted",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          Check for new studies and send alerts
  python main.py --dry-run                Check without sending alerts
  python main.py --discover               List available study year types
  python main.py --config prod.yaml       Use a custom config file
  python main.py --reset                  Clear history and start fresh

Environment variables (override config.yaml):
  SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_ADDRESS
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
  ALERT_EMAIL_RECIPIENTS    (comma-separated)
  ALERT_SMS_RECIPIENTS      (comma-separated)
  SPP_YEAR_TYPE_IDS         (comma-separated integers)
        """,
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--discover", "-d",
        action="store_true",
        help="Discover and list available study year types",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all seen studies and start fresh",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for new studies but don't send notifications or mark as seen",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Override log level from config",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    log_level = args.log_level or config.log_level
    setup_logging(log_level)

    if args.discover:
        return cmd_discover(config)
    elif args.reset:
        return cmd_reset(config)
    else:
        return cmd_check(config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

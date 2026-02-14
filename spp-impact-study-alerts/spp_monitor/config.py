"""Configuration management for SPP Impact Study Monitor."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SMTPConfig:
    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = ""
    use_tls: bool = True


@dataclass
class TwilioConfig:
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""


@dataclass
class AppConfig:
    """Main application configuration."""

    # Study monitoring
    year_type_ids: list[int] = field(default_factory=list)
    request_delay: float = 2.0
    max_retries: int = 3

    # Notification recipients
    email_recipients: list[str] = field(default_factory=list)
    sms_recipients: list[str] = field(default_factory=list)

    # Service configs
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    twilio: TwilioConfig = field(default_factory=TwilioConfig)

    # Storage
    storage_path: str = "data/seen_studies.json"

    # Logging
    log_level: str = "INFO"


def _env_override(yaml_val: str, env_var: str) -> str:
    """Use environment variable if set, otherwise use YAML value."""
    return os.environ.get(env_var, yaml_val or "")


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file and environment variables.

    Environment variables take precedence over YAML values for secrets.

    Args:
        config_path: Path to YAML config file. If None, uses config.yaml in cwd.

    Returns:
        Populated AppConfig instance.
    """
    config = AppConfig()

    # Load YAML file if it exists
    path = Path(config_path) if config_path else Path("config.yaml")
    if path.exists():
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Study monitoring settings
        monitor = data.get("monitor", {})
        config.year_type_ids = monitor.get("year_type_ids", [])
        config.request_delay = monitor.get("request_delay", 2.0)
        config.max_retries = monitor.get("max_retries", 3)

        # Recipients
        notifications = data.get("notifications", {})
        config.email_recipients = notifications.get("email_recipients", [])
        config.sms_recipients = notifications.get("sms_recipients", [])

        # SMTP
        smtp_data = data.get("smtp", {})
        config.smtp.host = smtp_data.get("host", "smtp.gmail.com")
        config.smtp.port = smtp_data.get("port", 587)
        config.smtp.username = smtp_data.get("username", "")
        config.smtp.password = smtp_data.get("password", "")
        config.smtp.from_address = smtp_data.get("from_address", "")
        config.smtp.use_tls = smtp_data.get("use_tls", True)

        # Twilio
        twilio_data = data.get("twilio", {})
        config.twilio.account_sid = twilio_data.get("account_sid", "")
        config.twilio.auth_token = twilio_data.get("auth_token", "")
        config.twilio.from_number = twilio_data.get("from_number", "")

        # Storage
        config.storage_path = data.get("storage", {}).get(
            "path", "data/seen_studies.json"
        )

        # Logging
        config.log_level = data.get("log_level", "INFO")

    # Environment variable overrides (for secrets -- these take precedence)
    config.smtp.username = _env_override(config.smtp.username, "SMTP_USERNAME")
    config.smtp.password = _env_override(config.smtp.password, "SMTP_PASSWORD")
    config.smtp.from_address = _env_override(config.smtp.from_address, "SMTP_FROM_ADDRESS")
    config.smtp.host = _env_override(config.smtp.host, "SMTP_HOST") or config.smtp.host
    smtp_port_env = os.environ.get("SMTP_PORT")
    if smtp_port_env:
        config.smtp.port = int(smtp_port_env)

    config.twilio.account_sid = _env_override(
        config.twilio.account_sid, "TWILIO_ACCOUNT_SID"
    )
    config.twilio.auth_token = _env_override(
        config.twilio.auth_token, "TWILIO_AUTH_TOKEN"
    )
    config.twilio.from_number = _env_override(
        config.twilio.from_number, "TWILIO_FROM_NUMBER"
    )

    # Email/SMS recipients can also come from env (comma-separated)
    env_emails = os.environ.get("ALERT_EMAIL_RECIPIENTS")
    if env_emails:
        config.email_recipients = [e.strip() for e in env_emails.split(",") if e.strip()]

    env_phones = os.environ.get("ALERT_SMS_RECIPIENTS")
    if env_phones:
        config.sms_recipients = [p.strip() for p in env_phones.split(",") if p.strip()]

    # Year type IDs from env (comma-separated)
    env_ytids = os.environ.get("SPP_YEAR_TYPE_IDS")
    if env_ytids:
        config.year_type_ids = [int(x.strip()) for x in env_ytids.split(",") if x.strip()]

    return config

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic — required; app will not start without this
    anthropic_api_key: str
    scoring_model: str = "claude-sonnet-4-6"
    digest_model: str = "claude-opus-4-6"

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "content-aggregator/0.1"

    # Twitter/X
    twitter_bearer_token: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Newsletter IMAP
    newsletter_imap_host: str = ""
    newsletter_imap_port: int = 993
    newsletter_imap_user: str = ""
    newsletter_imap_password: str = ""

    # Email digest (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    digest_from_email: str = "digest@example.com"
    digest_to_email: str = ""

    # Slack
    slack_webhook_url: str = ""

    # App
    database_url: str = "sqlite+aiosqlite:///./aggregator.db"
    log_level: str = "INFO"

    def validate_for_source_types(self, types: set[str]) -> None:
        """Raise ValueError with a clear message if secrets for the given source types are missing."""
        errors: list[str] = []
        if "reddit" in types and not (self.reddit_client_id and self.reddit_client_secret):
            errors.append("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET required for Reddit sources")
        if "twitter" in types and not self.twitter_bearer_token:
            errors.append("TWITTER_BEARER_TOKEN required for Twitter/X sources")
        if "youtube" in types and not self.youtube_api_key:
            errors.append("YOUTUBE_API_KEY required for YouTube sources")
        if "newsletter" in types and not (
            self.newsletter_imap_host
            and self.newsletter_imap_user
            and self.newsletter_imap_password
        ):
            errors.append(
                "NEWSLETTER_IMAP_HOST, NEWSLETTER_IMAP_USER, and NEWSLETTER_IMAP_PASSWORD "
                "required for newsletter sources"
            )
        if errors:
            raise ValueError(
                "Missing required secrets:\n" + "\n".join(f"  • {e}" for e in errors)
            )

    def validate_for_email_digest(self) -> None:
        """Raise ValueError if SMTP settings are incomplete."""
        if not (self.smtp_host and self.smtp_user and self.smtp_password and self.digest_to_email):
            raise ValueError(
                "Missing required secrets for email digest:\n"
                "  • SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and DIGEST_TO_EMAIL must all be set"
            )

    def validate_for_slack_digest(self) -> None:
        """Raise ValueError if Slack webhook is not configured."""
        if not self.slack_webhook_url:
            raise ValueError(
                "Missing required secret for Slack digest:\n"
                "  • SLACK_WEBHOOK_URL must be set"
            )


settings = Settings()

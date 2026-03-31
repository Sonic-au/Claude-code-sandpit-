from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
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


settings = Settings()

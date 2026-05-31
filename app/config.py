import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "homelab")
    db_user: str = os.getenv("DB_USER", "ingestion_api")
    db_password: str = os.getenv("DB_PASSWORD", "")

    pushover_user_key: str = os.getenv("PUSHOVER_USER_KEY", "")
    pushover_api_token: str = os.getenv("PUSHOVER_API_TOKEN", "")
    pushover_device: str = os.getenv("PUSHOVER_DEVICE", "iphoneRSI")

    hostname: str = os.getenv("HOSTNAME", "cygnus")
    service_name: str = os.getenv("SERVICE_NAME", "data-ingestion-api")

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def get_tokens(self) -> dict[str, str]:
        """Return mapping of token value → app name from APP_TOKEN_* env vars."""
        tokens: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("APP_TOKEN_") and value:
                app_name = key[len("APP_TOKEN_"):].lower()
                tokens[value] = app_name
        return tokens


settings = Settings()

from pydantic import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_path: str | None = None
    default_timeframe: str = "M15"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

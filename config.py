import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    BOT_TOKEN: str = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ_sample"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'bot.db'}"
    CHANNEL_URL: str = "https://t.me/your_kz_channel"
    ADMIN_IDS: str = "507618077"
    ADMIN_PASSWORD: str = "KzEdu#Admin_9842$X!"
    PORT: int = int(os.getenv("PORT", "8080"))
    
    LOCALES_PATH: Path = BASE_DIR / "data" / "locales.json"
    OFFERS_PATH: Path = BASE_DIR / "data" / "offers.json"
    QUIZ_PATH: Path = BASE_DIR / "data" / "quiz.json"

    model_config = SettingsConfigDict(
        env_file=[BASE_DIR / ".env", BASE_DIR / ".env.example"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def formatted_database_url(self) -> str:
        """
        Автоматически адаптирует строку подключения Supabase к асинхронному драйверу asyncpg.
        postgres:// или postgresql:// -> postgresql+asyncpg://
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def formatted_channel_url(self) -> str:
        url = self.CHANNEL_URL.strip()
        if url.startswith("@"):
            return f"https://t.me/{url[1:]}"
        elif not url.startswith("http://") and not url.startswith("https://"):
            return f"https://t.me/{url}"
        return url

    @property
    def admin_id_list(self) -> list[int]:
        """Возвращает список ID администраторов"""
        ids = []
        for part in self.ADMIN_IDS.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

settings = Settings()

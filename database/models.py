from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    """
    Таблица пользователей для аналитики трафика и последующих рассылок (дожима).
    """
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, doc="Telegram User ID")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, doc="Telegram @username")
    language: Mapped[str] = mapped_column(String(10), default="ru", doc="Выбранный язык интерфейса (ru/kz)")
    
    # Трекинг арбитражных действий
    last_clicked_offer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, doc="ID последнего просмотренного оффера")
    test_result: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, doc="Определенный архетип по тесту (it/design/marketing/english)")
    test_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Дата прохождения теста")
    
    # Даты активности
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, doc="Дата первой регистрации в боте")
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Дата последней активности")

    def __repr__(self) -> str:
        return f"<User id={self.user_id} lang={self.language} offer={self.last_clicked_offer_id}>"

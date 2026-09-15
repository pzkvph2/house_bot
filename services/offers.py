import json
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from config import settings

class Offer(BaseModel):
    id: str
    is_active: bool = True
    priority: int = 100
    title: dict[str, str] = Field(default_factory=dict)
    description: dict[str, str] = Field(default_factory=dict)
    url_template: str

    def get_title(self, lang: str = "ru") -> str:
        return self.title.get(lang) or self.title.get("ru", self.id)

    def get_description(self, lang: str = "ru") -> str:
        return self.description.get(lang) or self.description.get("ru", "")

    def get_tracking_url(self, user_id: int) -> str:
        """Подставляет Telegram User ID в subID партнерской ссылки для точной аналитики конверсий"""
        return self.url_template.format(user_id=user_id, offer_id=self.id)


class OfferService:
    def __init__(self, offers_path: Path):
        self.offers_path = offers_path

    def load_offers(self) -> List[Offer]:
        """Загрузка офферов из JSON-файла без перезапуска бота"""
        if not self.offers_path.exists():
            return []
        try:
            with open(self.offers_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            offers = [Offer(**item) for item in raw_data]
            # Сортировка по приоритету
            offers.sort(key=lambda x: x.priority)
            return offers
        except Exception as e:
            print(f"[ERROR] Failed to load offers: {e}")
            return []

    def get_active_offers(self) -> List[Offer]:
        """Возвращает только включенные (активные) офферы"""
        return [offer for offer in self.load_offers() if offer.is_active]

    def get_offer_by_id(self, offer_id: str) -> Optional[Offer]:
        for offer in self.load_offers():
            if offer.id == offer_id:
                return offer
        return None

offer_service = OfferService(settings.OFFERS_PATH)

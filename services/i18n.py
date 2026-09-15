import json
from pathlib import Path
from config import settings

class I18nService:
    def __init__(self, locales_path: Path):
        self.locales_path = locales_path
        self._cache: dict = {}
        self.reload()

    def reload(self) -> None:
        """Перезагрузка текстов из JSON (для редактирования на лету без перезапуска кода)"""
        if self.locales_path.exists():
            with open(self.locales_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        else:
            self._cache = {}

    def get(self, key: str, lang: str = "ru", **kwargs) -> str:
        """Получить локализованный текст по ключу с форматированием параметров"""
        # Всегда перечитываем или берем из кэша (для продакшена с частыми правками можно включить reload при необходимости)
        self.reload()
        
        lang_data = self._cache.get(lang) or self._cache.get("ru", {})
        text = lang_data.get(key, f"[{key}]")
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

i18n = I18nService(settings.LOCALES_PATH)

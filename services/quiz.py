import json
from pathlib import Path
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from config import settings

class QuizOption(BaseModel):
    letter: str = ""
    btn: Dict[str, str] = Field(default_factory=dict)
    text: Dict[str, str] = Field(default_factory=dict)
    category: str  # it / marketing / design / english

    def get_btn_text(self, lang: str = "ru") -> str:
        """Короткий текст для инлайн-кнопки (гарантированно не урезается на смартфонах)"""
        val = self.btn.get(lang) or self.btn.get("ru")
        if val:
            return val
        # Фолбэк на букву, если короткого текста нет
        return f"[{self.letter}]" if self.letter else "•"

    def get_full_text(self, lang: str = "ru") -> str:
        """Полный текст варианта ответа (печатается в сообщении без ограничений)"""
        return self.text.get(lang) or self.text.get("ru", "")

class QuizQuestion(BaseModel):
    id: int
    text: Dict[str, str]
    options: List[QuizOption]

    def get_text(self, lang: str = "ru") -> str:
        return self.text.get(lang) or self.text.get("ru", "")

class ArchetypeProfile(BaseModel):
    title: Dict[str, str]
    description: Dict[str, str]
    recommended_offer_id: str

    def get_title(self, lang: str = "ru") -> str:
        return self.title.get(lang) or self.title.get("ru", "")

    def get_description(self, lang: str = "ru") -> str:
        return self.description.get(lang) or self.description.get("ru", "")

class QuizService:
    def __init__(self, quiz_path: Path):
        self.quiz_path = quiz_path
        self._cache: Optional[dict] = None

    def _load(self) -> dict:
        if not self.quiz_path.exists():
            return {"questions": [], "profiles": {}}
        try:
            with open(self.quiz_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load quiz: {e}")
            return {"questions": [], "profiles": {}}

    def get_questions(self) -> List[QuizQuestion]:
        data = self._load()
        return [QuizQuestion(**q) for q in data.get("questions", [])]

    def get_question_by_index(self, index: int) -> Optional[QuizQuestion]:
        questions = self.get_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def get_total_questions(self) -> int:
        return len(self.get_questions())

    def get_profile(self, category: str) -> Optional[ArchetypeProfile]:
        data = self._load()
        profiles = data.get("profiles", {})
        raw_profile = profiles.get(category)
        if raw_profile:
            return ArchetypeProfile(**raw_profile)
        return None

    def calculate_result(self, answers: List[str]) -> str:
        """
        Подсчитывает баллы по категориям и возвращает доминирующее направление.
        В случае равенства баллов отдает приоритет IT или Marketing.
        """
        scores: Dict[str, int] = {"it": 0, "marketing": 0, "design": 0, "english": 0}
        for category in answers:
            if category in scores:
                scores[category] += 1

        priority_order = ["it", "marketing", "design", "english"]
        best_category = max(priority_order, key=lambda cat: (scores.get(cat, 0), -priority_order.index(cat)))
        return best_category

quiz_service = QuizService(settings.QUIZ_PATH)

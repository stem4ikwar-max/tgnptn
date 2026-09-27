"""
Конфигурация бота.

Все чувствительные данные (токен, ключи API) берутся ТОЛЬКО из переменных
окружения (.env). Хранить токен прямо в коде небезопасно — если он попадёт
в чужие руки (git-репозиторий, чат, скриншот), бота можно будет угнать.
"""

import os
from dataclasses import dataclass, field
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Не задана переменная окружения {name}. "
            f"Проверь файл .env (см. .env.example)."
        )
    return value


def _draft_link(username: str, text: str) -> str:
    """
    Ссылка на личку с уже готовым (незаотправленным) черновиком сообщения.
    Пользователю остаётся только нажать «Отправить» в Telegram.
    """
    return f"https://t.me/{username}?text={quote(text)}"


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: _get_required("BOT_TOKEN"))
    admin_id: int = field(default_factory=lambda: int(_get_required("ADMIN_ID")))
    admin_username: str = os.getenv("ADMIN_USERNAME", "rufivo")

    # ИИ (Google Gemini API — бесплатный тариф, ключ на aistudio.google.com/apikey)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Прочее
    db_path: str = os.getenv("DB_PATH", "bot_database.db")
    cover_photo: str = os.getenv("COVER_PHOTO", "photo.jpg")
    contact_url: str = f"https://t.me/{os.getenv('ADMIN_USERNAME', 'rufivo')}"
    users_per_page: int = 5
    history_messages_limit: int = 15


config = Config()

# ---------- Тексты разделов ----------

WHO_AM_I_TEXT = (
    "🙋‍♂️ Кто я такой:\n\n"
    "Я — rufivo 🔥\n"
    "Стратег и предприниматель\n\n"
    "Есть идеи или вопросы? Жми «💬 Задать вопрос» — отвечу лично "
    "или через своего ассистента 😊🚀"
)

ASK_QUESTION_INTRO = (
    "💬 Режим диалога включён!\n\n"
    "Напиши свой вопрос — отвечу настолько быстро, насколько смогу 😊✨"
)

SUPPORT_MENU_TEXT = (
    "💎 Поддержать проект:\n\n"
    "Выбери удобный способ ниже — откроется личка с уже готовым сообщением, "
    "останется только отправить 🙌"
)

# Готовые черновики сообщений — открываются в личке сразу с текстом.
CONTACT_DRAFT_TEXT = (
    "Привет! 👋 Хочу задать вопрос / обсудить кое-что 😊"
)

SUPPORT_DRAFTS = {
    "support_stars": (
        "Привет! ⭐ Хочу поддержать тебя через Telegram Stars. "
        "Подскажи, пожалуйста, как это лучше сделать?"
    ),
    "support_uah": (
        "Привет! 💛 Хочу поддержать тебя, например на 100 грн. "
        "Скинь, пожалуйста, реквизиты карты 🙏"
    ),
    "support_crypto": (
        "Привет! ₿ Хочу поддержать тебя криптовалютой. "
        "Скинь, пожалуйста, адрес кошелька 🙏"
    ),
}

CONTACT_URL_WITH_DRAFT = _draft_link(config.admin_username, CONTACT_DRAFT_TEXT)
SUPPORT_URLS = {
    key: _draft_link(config.admin_username, text) for key, text in SUPPORT_DRAFTS.items()
}

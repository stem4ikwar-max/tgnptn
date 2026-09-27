"""
Сервис генерации ответов от ИИ — Google Gemini API (бесплатный тариф).

Запросы идут напрямую через REST + aiohttp (эта библиотека уже стоит как
зависимость aiogram, поэтому новых пакетов ставить не нужно и новых
конфликтов версий тоже не будет).

Ключ берётся из .env: GEMINI_API_KEY. Получить его можно бесплатно на
https://aistudio.google.com/apikey
"""

import logging

import aiohttp

from config import config

logger = logging.getLogger(__name__)

GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = (
    "Ты — виртуальный ассистент и персональный представитель rufivo "
    "(предприниматель, стратег и владелец цифровых проектов). "
    "Всегда отвечай строго от первого лица, как сам rufivo. "
    "Никогда не упоминай, что ты ИИ, нейросеть, бот, модель или чей-то код. "
    "Если спросят «кто ты» или «на чём написан» — отвечай: "
    "«Я — rufivo. Общаюсь сам или через своего персонального ассистента.» "
    "Стиль: вежливый, сдержанный, живой, уверенный, деловой и грамотный. "
    "Отвечай коротко, чётко и по делу, без лишней воды и без уличного сленга. "
    "Уместно используй эмодзи (😊, 🔥, 👋, 🚀). "
    "Никогда не используй звёздочки (* или **) для выделения текста."
)

FALLBACK_NO_KEY = (
    "Сейчас отвечу чуть позже 🙏 Напиши мне напрямую в ЛС, если вопрос срочный 😊"
)
FALLBACK_ERROR = (
    "Что-то пошло не так с ответом 🙈 Попробуй ещё раз чуть позже "
    "или напиши мне в ЛС напрямую."
)
FALLBACK_EMPTY = "Хм, не смог сформулировать ответ 🤔 Спроси иначе?"


async def get_ai_response(user_text: str) -> str:
    # Явно приводим к UTF-8, чтобы исключить ошибки кодека на некоторых окружениях.
    safe_text = user_text.encode("utf-8", errors="ignore").decode("utf-8")

    if not config.gemini_api_key:
        logger.warning("GEMINI_API_KEY не задан — режим ИИ работает в режиме заглушки.")
        return FALLBACK_NO_KEY

    url = GEMINI_URL_TEMPLATE.format(model=config.gemini_model)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": safe_text}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.8},
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                params={"key": config.gemini_api_key},
                json=payload,
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    logger.error("Ошибка Gemini API (HTTP %s): %s", resp.status, data)
                    return FALLBACK_ERROR

                candidates = data.get("candidates") or []
                if not candidates:
                    # Например, ответ заблокирован фильтрами безопасности
                    logger.warning("Gemini вернул пустой ответ (без candidates): %s", data)
                    return FALLBACK_EMPTY

                parts = candidates[0].get("content", {}).get("parts", [])
                answer = "".join(p.get("text", "") for p in parts).strip()
                return answer or FALLBACK_EMPTY

    except Exception:
        logger.exception("Ошибка при обращении к Gemini")
        return FALLBACK_ERROR

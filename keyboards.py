"""Инлайн-клавиатуры бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import CONTACT_URL_WITH_DRAFT, SUPPORT_URLS, config


def main_menu_kb() -> InlineKeyboardMarkup:
    # Сетка 2×2: два ряда по две кнопки.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🙋‍♂️ Кто я", callback_data="who_am_i"),
                InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask_question"),
            ],
            [
                InlineKeyboardButton(text="✉️ Связаться лично", url=CONTACT_URL_WITH_DRAFT),
                InlineKeyboardButton(text="💎 Поддержать", callback_data="support_menu"),
            ],
        ]
    )


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
        ]
    )


def ask_question_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать @" + config.admin_username + " лично", url=CONTACT_URL_WITH_DRAFT)],
            [InlineKeyboardButton(text="🔙 Завершить диалог", callback_data="back_main")],
        ]
    )


def support_menu_kb() -> InlineKeyboardMarkup:
    # Каждая кнопка сразу открывает личку с готовым черновиком сообщения —
    # без промежуточного экрана "напиши мне в ЛС".
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", url=SUPPORT_URLS["support_stars"])],
            [InlineKeyboardButton(text="🇺🇦 UAH / Гривны", url=SUPPORT_URLS["support_uah"])],
            [InlineKeyboardButton(text="₿ Крипта", url=SUPPORT_URLS["support_crypto"])],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
        ]
    )


# ---------- Админ-панель ----------

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users:0")],
            [InlineKeyboardButton(text="🗒 Последние логи", callback_data="adm_logs")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В админ-меню", callback_data="adm_home")],
        ]
    )


def users_page_kb(users, page: int, total: int, page_size: int) -> InlineKeyboardMarkup:
    rows = []
    for user in users:
        label = f"{user.first_name or '—'} (@{user.username or 'no_username'})"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"adm_user:{user.user_id}:{page}")]
        )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_users:{page - 1}"))
    total_pages = max(1, (total + page_size - 1) // page_size)
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if (page + 1) * page_size < total:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_users:{page + 1}"))
    rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="🔙 В админ-меню", callback_data="adm_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_history_back_kb(page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К списку", callback_data=f"adm_users:{page}")],
        ]
    )

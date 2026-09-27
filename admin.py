"""Админ-панель, доступна только пользователю с ADMIN_ID."""

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from config import config
from keyboards import admin_back_kb, admin_main_kb, user_history_back_kb, users_page_kb

logger = logging.getLogger(__name__)
router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id == config.admin_id


async def safe_answer(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return  # обычным пользователям панель не показываем и не палим её существование
    await message.answer("🛠 Админ-панель", reply_markup=admin_main_kb())


@router.callback_query(F.data == "adm_home")
async def cb_adm_home(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await safe_answer(callback)
    await callback.message.edit_text("🛠 Админ-панель", reply_markup=admin_main_kb())
    await safe_answer(callback)


@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await safe_answer(callback)

    users_count, messages_count = await db.get_stats()
    text = (
        "📊 Статистика бота:\n\n"
        f"👥 Пользователей в базе: {users_count}\n"
        f"🗒 Всего сообщений/логов: {messages_count}"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await safe_answer(callback)


@router.callback_query(F.data.startswith("adm_users:"))
async def cb_adm_users(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await safe_answer(callback)

    page = int(callback.data.split(":")[1])
    users, total = await db.get_users_page(page, config.users_per_page)

    if total == 0:
        await callback.message.edit_text("Пока в базе нет пользователей.", reply_markup=admin_back_kb())
        return await safe_answer(callback)

    text = f"👥 Пользователи (всего: {total})\nВыбери, чтобы посмотреть историю диалога:"
    await callback.message.edit_text(
        text, reply_markup=users_page_kb(users, page, total, config.users_per_page)
    )
    await safe_answer(callback)


@router.callback_query(F.data.startswith("adm_user:"))
async def cb_adm_user_history(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await safe_answer(callback)

    _, user_id_str, page_str = callback.data.split(":")
    user_id, page = int(user_id_str), int(page_str)

    history = await db.get_user_history(user_id, config.history_messages_limit)
    if not history:
        text = f"История пользователя {user_id} пуста."
    else:
        lines = [f"🗂 Последние {len(history)} сообщений (user_id: {user_id}):\n"]
        for msg in history:
            who = "👤" if msg.role == "user" else "🤖"
            ts = msg.created_at.replace("T", " ")[:19]
            lines.append(f"{who} [{ts}] {msg.text}")
        text = "\n".join(lines)

    # Telegram ограничивает длину сообщения — подрежем на всякий случай
    if len(text) > 4000:
        text = text[-4000:]

    await callback.message.edit_text(text, reply_markup=user_history_back_kb(page))
    await safe_answer(callback)


@router.callback_query(F.data == "adm_logs")
async def cb_adm_logs(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return await safe_answer(callback)

    rows = await db.get_recent_activity(limit=30)
    if not rows:
        text = "Логов пока нет."
    else:
        lines = ["🗒 Последние сообщения всех пользователей:\n"]
        for user_id, username, text_, created_at in rows:
            ts = created_at.replace("T", " ")[:19]
            uname = f"@{username}" if username else str(user_id)
            snippet = text_ if len(text_) <= 80 else text_[:80] + "…"
            lines.append(f"[{ts}] {uname}: {snippet}")
        text = "\n".join(lines)

    if len(text) > 4000:
        text = text[:4000]

    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await safe_answer(callback)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast <текст рассылки>")
        return

    # Явно приводим к UTF-8, как и остальные тексты в системе
    safe_text = text.encode("utf-8", errors="ignore").decode("utf-8")

    user_ids = await db.get_all_user_ids()
    sent, failed = 0, 0

    status_msg = await message.answer(f"🚀 Начинаю рассылку на {len(user_ids)} пользователей…")

    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, safe_text)
            sent += 1
        except TelegramForbiddenError:
            failed += 1  # пользователь заблокировал бота
        except TelegramBadRequest:
            failed += 1
        except Exception:
            logger.exception("Ошибка при рассылке пользователю %s", user_id)
            failed += 1
        await asyncio.sleep(0.05)  # мягкий троттлинг, чтобы не упереться в лимиты Telegram

    await status_msg.edit_text(f"✅ Рассылка завершена.\nДоставлено: {sent}\nНе доставлено: {failed}")

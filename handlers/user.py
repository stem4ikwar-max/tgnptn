"""Пользовательские хендлеры: главное меню и все его разделы."""

import logging
import os

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

import database as db
from ai_service import get_ai_response
from config import (
    ASK_QUESTION_INTRO,
    SUPPORT_MENU_TEXT,
    WHO_AM_I_TEXT,
    config,
)
from keyboards import (
    ask_question_kb,
    main_menu_kb,
    support_menu_kb,
)
from states import DialogStates

logger = logging.getLogger(__name__)
router = Router(name="user")

MAIN_CAPTION = "👋 Привет! Это личный бот rufivo 🚀\nВыбери, что тебя интересует 👇"


async def safe_answer(callback: CallbackQuery) -> None:
    """callback.answer(), обёрнутый от ошибки 'query is too old'."""
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )

    if os.path.exists(config.cover_photo):
        await message.answer_photo(
            photo=FSInputFile(config.cover_photo),
            caption=MAIN_CAPTION,
            reply_markup=main_menu_kb(),
        )
    else:
        logger.warning("Файл обложки %s не найден, отправляю текстовое меню", config.cover_photo)
        await message.answer(MAIN_CAPTION, reply_markup=main_menu_kb())


async def _render_section(callback: CallbackQuery, text: str, keyboard) -> None:
    """
    Переключение раздела с сохранением фото-обложки: редактируем caption
    у фото, а не пересоздаём сообщение. Если по какой-то причине
    отредактировать не получилось — отправляем НОВОЕ сообщение С ТЕМ ЖЕ
    ФОТО (а не голый текст), чтобы обложка никогда не пропадала.
    """
    had_photo = bool(callback.message.photo)
    try:
        if had_photo:
            await callback.message.edit_caption(caption=text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text=text, reply_markup=keyboard)
        return
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        logger.warning("Не удалось отредактировать сообщение (%s), отправляю новое", e)
    except Exception:
        logger.exception("Непредвиденная ошибка при рендере раздела")

    # Фолбэк: если исходное сообщение было с фото — новое тоже должно быть с фото.
    if had_photo and os.path.exists(config.cover_photo):
        await callback.message.answer_photo(
            photo=FSInputFile(config.cover_photo),
            caption=text,
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _render_section(callback, MAIN_CAPTION, main_menu_kb())
    await safe_answer(callback)


@router.callback_query(F.data == "who_am_i")
async def cb_who_am_i(callback: CallbackQuery, state: FSMContext) -> None:
    # На всякий случай выходим из режима диалога с ИИ, если он был активен —
    # иначе следующий текст пользователя мог бы неожиданно уйти в ИИ.
    await state.clear()
    await _render_section(callback, WHO_AM_I_TEXT, main_menu_kb())
    await safe_answer(callback)


@router.callback_query(F.data == "ask_question")
async def cb_ask_question(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DialogStates.ai_chat)
    await _render_section(callback, ASK_QUESTION_INTRO, ask_question_kb())
    await safe_answer(callback)


@router.callback_query(F.data == "support_menu")
async def cb_support_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _render_section(callback, SUPPORT_MENU_TEXT, support_menu_kb())
    await safe_answer(callback)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await safe_answer(callback)


@router.message(DialogStates.ai_chat, F.text)
async def handle_ai_dialog(message: Message) -> None:
    """Пока пользователь в режиме 'Задать вопрос' — все текстовые сообщения идут в ИИ."""
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )

    user_text = message.text.encode("utf-8", errors="ignore").decode("utf-8")
    await db.log_message(message.from_user.id, "user", user_text)

    await message.bot.send_chat_action(message.chat.id, "typing")
    answer = await get_ai_response(user_text)

    await db.log_message(message.from_user.id, "bot", answer)
    await message.answer(answer, reply_markup=ask_question_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer("Просто нажми /start и выбери нужный раздел в меню 😊")

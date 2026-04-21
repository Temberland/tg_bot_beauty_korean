from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_kb
from db.repository import UserRepo

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    repo = UserRepo(session)
    await repo.get_or_create(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        "👋 Добро пожаловать в <b>K-Beauty Shop</b>!\n\n"
        "Лучшая корейская косметика с доставкой по России. "
        "Выберите раздел в меню ниже:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    await call.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

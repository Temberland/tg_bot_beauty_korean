from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🛍 Каталог"),
        KeyboardButton(text="🛒 Корзина"),
    )
    builder.row(
        KeyboardButton(text="📦 Мои заказы"),
        KeyboardButton(text="🎁 Акции"),
    )
    builder.row(
        KeyboardButton(text="💬 Поддержка"),
    )
    return builder.as_markup(resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def phone_kb() -> ReplyKeyboardMarkup:
    """Запрос контакта — Telegram автоматически подставляет номер."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Отправить мой номер", request_contact=True))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def remove_kb() -> ReplyKeyboardMarkup:
    """Убирает reply-клавиатуру."""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

FAQ = {
    "faq:delivery": (
        "🚚 <b>Доставка</b>",
        "Доставляем по всей России через СДЭК, Boxberry и Почту России.\n"
        "Срок доставки: 3–14 рабочих дней в зависимости от региона.\n"
        "Бесплатная доставка при заказе от 3 000 ₽.",
    ),
    "faq:payment": (
        "💳 <b>Оплата</b>",
        "Принимаем оплату онлайн через ЮKassa (Сбер, Тинькофф, карты)\n"
        "или наличными/картой при получении.",
    ),
    "faq:returns": (
        "🔄 <b>Возврат</b>",
        "Принимаем возврат в течение 14 дней при сохранении упаковки.\n"
        "Косметика надлежащего качества возврату не подлежит по закону.",
    ),
    "faq:original": (
        "✅ <b>Оригинальность</b>",
        "Все товары — оригинальные, приобретаются напрямую у корейских поставщиков.\n"
        "Сертификаты качества есть на все позиции.",
    ),
}


def support_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Доставка", callback_data="faq:delivery")
    builder.button(text="💳 Оплата", callback_data="faq:payment")
    builder.button(text="🔄 Возврат", callback_data="faq:returns")
    builder.button(text="✅ Оригинальность", callback_data="faq:original")
    builder.button(text="💬 Написать оператору", url="https://t.me/param_p1")
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


@router.message(Command("support"))
@router.callback_query(lambda c: c.data == "support")
async def show_support(event: Message | CallbackQuery):
    text = "💬 <b>Поддержка</b>\n\nВыберите тему или напишите оператору:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=support_kb(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=support_kb(), parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("faq:"))
async def show_faq(call: CallbackQuery):
    key = call.data
    if key not in FAQ:
        return
    title, answer = FAQ[key]
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="support")
    await call.message.edit_text(
        f"{title}\n\n{answer}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

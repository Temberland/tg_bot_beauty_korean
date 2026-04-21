from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import orders_list_kb, main_menu_kb
from db.repository import OrderRepo

router = Router()

STATUS_EMOJI = {
    "new": "🆕",
    "processing": "⚙️",
    "shipped": "📦",
    "delivered": "✅",
    "cancelled": "❌",
}


@router.message(Command("orders"))
@router.callback_query(lambda c: c.data == "orders")
async def show_orders(event: Message | CallbackQuery, session: AsyncSession):
    user_id = event.from_user.id
    orders = await OrderRepo(session).get_user_orders(user_id)

    if not orders:
        text = "📦 У вас пока нет заказов"
        kb = main_menu_kb()
    else:
        text = "📦 <b>Ваши заказы:</b>"
        kb = orders_list_kb(orders)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("order_detail:"))
async def show_order_detail(call: CallbackQuery, session: AsyncSession):
    order_id = int(call.data.split(":")[1])
    orders = await OrderRepo(session).get_user_orders(call.from_user.id)
    order = next((o for o in orders if o.id == order_id), None)

    if not order:
        await call.answer("Заказ не найден")
        return

    emoji = STATUS_EMOJI.get(order.status.value, "📦")
    lines = [
        f"📋 <b>Заказ №{order.id}</b>",
        f"Статус: {emoji} {order.status.value}",
        f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}",
        "",
        "<b>Товары:</b>",
    ]
    for item in order.items:
        lines.append(f"• {item.product.name} x{item.quantity} — {item.price_at_purchase * item.quantity} ₽")

    lines.append(f"\n💰 <b>Итого: {order.total_price} ₽</b>")
    if order.tracking_number:
        lines.append(f"🔍 Трек-номер: <code>{order.tracking_number}</code>")

    from aiogram.types import InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="orders")
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

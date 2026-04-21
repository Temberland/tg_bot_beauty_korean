from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.is_admin import IsAdmin
from bot.keyboards.inline import admin_menu_kb, order_status_kb
from bot.states.order import AdminAddProduct
from db.models import Order, OrderStatus, Product
from db.repository import OrderRepo

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer("⚙️ <b>Панель администратора</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(lambda c: c.data == "admin:orders")
async def admin_orders(call: CallbackQuery, session: AsyncSession):
    q = select(Order).where(Order.status == OrderStatus.new).order_by(Order.created_at.desc())
    result = await session.execute(q)
    orders = result.scalars().all()

    if not orders:
        await call.message.edit_text("✅ Новых заказов нет", reply_markup=admin_menu_kb())
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=f"№{order.id} | {order.full_name} | {order.total_price} ₽",
            callback_data=f"admin:order:{order.id}",
        )
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(1)

    await call.message.edit_text(
        f"🆕 <b>Новые заказы ({len(orders)}):</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:order:"))
async def admin_order_detail(call: CallbackQuery, session: AsyncSession):
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if not order:
        await call.answer("Заказ не найден")
        return

    text = (
        f"📋 <b>Заказ №{order.id}</b>\n"
        f"👤 {order.full_name}\n"
        f"📱 {order.phone}\n"
        f"📍 {order.address}\n"
        f"🚚 {order.delivery_method.value}\n"
        f"💳 {order.payment_method.value}\n"
        f"💰 {order.total_price} ₽\n\n"
        f"Изменить статус:"
    )
    await call.message.edit_text(text, reply_markup=order_status_kb(order_id), parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("set_status:"))
async def set_order_status(call: CallbackQuery, session: AsyncSession):
    _, order_id, status_value = call.data.split(":")
    repo = OrderRepo(session)
    await repo.update_status(int(order_id), OrderStatus(status_value))

    # Уведомляем покупателя
    order = await session.get(Order, int(order_id))
    try:
        await call.bot.send_message(
            order.user_id,
            f"📦 Статус заказа <b>№{order_id}</b> обновлён: <b>{status_value}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.answer(f"Статус обновлён: {status_value}")
    await call.message.edit_reply_markup(reply_markup=admin_menu_kb())


@router.callback_query(lambda c: c.data == "admin:stats")
async def admin_stats(call: CallbackQuery, session: AsyncSession):
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar()
    total_revenue = (await session.execute(select(func.sum(Order.total_price)))).scalar() or 0

    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"Всего заказов: {total_orders}\n"
        f"Выручка: {total_revenue:.2f} ₽",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )

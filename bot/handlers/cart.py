from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    cart_kb, delivery_kb, payment_kb, order_confirm_kb, main_menu_kb,
)
from bot.states.order import OrderForm
from db.models import DeliveryMethod, PaymentMethod
from db.repository import CartRepo, OrderRepo

router = Router()

DELIVERY_LABELS = {
    "courier": "🚚 Курьер",
    "pickup": "📦 Пункт выдачи",
    "post": "📮 Почта России",
}
PAYMENT_LABELS = {
    "online": "💳 Онлайн",
    "on_delivery": "💵 При получении",
}


@router.message(Command("cart"))
@router.callback_query(lambda c: c.data == "cart")
async def show_cart(event: Message | CallbackQuery, session: AsyncSession):
    user_id = event.from_user.id
    repo = CartRepo(session)
    items = await repo.get_items(user_id)
    total = await repo.get_total(user_id)

    if not items:
        text = "🛒 Ваша корзина пуста"
    else:
        lines = ["🛒 <b>Ваша корзина:</b>\n"]
        for item in items:
            price = item.product.effective_price
            lines.append(f"• {item.product.name} x{item.quantity} = {price * item.quantity} ₽")
        lines.append(f"\n<b>Итого: {total} ₽</b>")
        text = "\n".join(lines)

    kb = cart_kb(items)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("add_cart:"))
async def add_to_cart(call: CallbackQuery, session: AsyncSession):
    product_id = int(call.data.split(":")[1])
    repo = CartRepo(session)
    await repo.add_or_increment(call.from_user.id, product_id)
    await call.answer("✅ Добавлено в корзину!")


@router.callback_query(lambda c: c.data.startswith("remove_cart:"))
async def remove_from_cart(call: CallbackQuery, session: AsyncSession):
    item_id = int(call.data.split(":")[1])
    cart_repo = CartRepo(session)
    await cart_repo.remove_item(item_id)
    # Обновляем корзину
    items = await cart_repo.get_items(call.from_user.id)
    total = await cart_repo.get_total(call.from_user.id)
    if not items:
        text = "🛒 Ваша корзина пуста"
    else:
        lines = ["🛒 <b>Ваша корзина:</b>\n"]
        for item in items:
            price = item.product.effective_price
            lines.append(f"• {item.product.name} x{item.quantity} = {price * item.quantity} ₽")
        lines.append(f"\n<b>Итого: {total} ₽</b>")
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=cart_kb(items), parse_mode="HTML")


@router.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart(call: CallbackQuery, session: AsyncSession):
    await CartRepo(session).clear(call.from_user.id)
    await call.message.edit_text("🗑 Корзина очищена", reply_markup=main_menu_kb())


# ── Оформление заказа (FSM) ──────────────────

@router.callback_query(lambda c: c.data == "checkout")
async def checkout_start(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    items = await CartRepo(session).get_items(call.from_user.id)
    if not items:
        await call.answer("Корзина пуста!")
        return
    await state.set_state(OrderForm.full_name)
    await call.message.answer("📝 Введите ваше <b>ФИО</b>:", parse_mode="HTML")


@router.message(OrderForm.full_name)
async def order_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(OrderForm.phone)
    await message.answer("📱 Введите ваш <b>номер телефона</b>:", parse_mode="HTML")


@router.message(OrderForm.phone)
async def order_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OrderForm.address)
    await message.answer("📍 Введите <b>адрес доставки</b>:", parse_mode="HTML")


@router.message(OrderForm.address)
async def order_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.delivery_method)
    await message.answer("🚚 Выберите <b>способ доставки</b>:", reply_markup=delivery_kb(), parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("delivery:"), OrderForm.delivery_method)
async def order_delivery(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(delivery_method=method)
    await state.set_state(OrderForm.payment_method)
    await call.message.edit_text(
        "💳 Выберите <b>способ оплаты</b>:",
        reply_markup=payment_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("payment:"), OrderForm.payment_method)
async def order_payment(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    method = call.data.split(":")[1]
    await state.update_data(payment_method=method)

    data = await state.get_data()
    cart_repo = CartRepo(session)
    total = await cart_repo.get_total(call.from_user.id)

    summary = (
        f"📋 <b>Подтвердите заказ:</b>\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"📍 Адрес: {data['address']}\n"
        f"🚚 Доставка: {DELIVERY_LABELS[data['delivery_method']]}\n"
        f"💳 Оплата: {PAYMENT_LABELS[data['payment_method']]}\n"
        f"\n💰 <b>Итого: {total} ₽</b>"
    )
    await state.set_state(OrderForm.confirm)
    await call.message.edit_text(summary, reply_markup=order_confirm_kb(), parse_mode="HTML")


@router.callback_query(lambda c: c.data == "order_confirm", OrderForm.confirm)
async def order_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cart_repo = CartRepo(session)
    order_repo = OrderRepo(session)

    items = await cart_repo.get_items(call.from_user.id)
    order = await order_repo.create_from_cart(
        user_id=call.from_user.id,
        cart_items=items,
        full_name=data["full_name"],
        phone=data["phone"],
        address=data["address"],
        delivery_method=DeliveryMethod(data["delivery_method"]),
        payment_method=PaymentMethod(data["payment_method"]),
    )
    await cart_repo.clear(call.from_user.id)
    await state.clear()

    await call.message.edit_text(
        f"✅ <b>Заказ №{order.id} оформлен!</b>\n\n"
        f"Мы свяжемся с вами для подтверждения.\n"
        f"Отслеживайте статус в разделе «Мои заказы».",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

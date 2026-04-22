import json
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.is_admin import IsAdmin
from bot.keyboards.inline import (
    admin_menu_kb, order_status_kb, admin_products_kb,
    admin_edit_product_kb, admin_categories_kb, admin_brands_kb,
    admin_reviews_kb, admin_review_action_kb, admin_promos_kb,
)
from bot.states.order import (
    AdminAddProduct, AdminEditProduct, AdminEditCategory,
    AdminEditBrand, AdminSetDiscount,
)
from db.models import Brand, Category, Order, OrderItem, OrderStatus, Product, Review
from db.repository import OrderRepo

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

# fsm_router — без фильтра IsAdmin, для кнопок «Пропустить» внутри FSM
fsm_router = Router()


# ── Главная панель ───────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer(
        "⚙️ <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
3

@router.callback_query(lambda c: c.data == "admin:menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "⚙️ <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "admin:cancel")
async def admin_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "⚙️ <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


def _cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin:cancel")
    return builder.as_markup()


# ════════════════════════════════════════════
# ЗАКАЗЫ
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:orders")
async def admin_orders(call: CallbackQuery, session: AsyncSession):
    q = select(Order).where(Order.status == OrderStatus.new).order_by(Order.created_at.desc())
    orders = (await session.execute(q)).scalars().all()

    if not orders:
        await call.message.edit_text("✅ Новых заказов нет", reply_markup=admin_menu_kb())
        return

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
    await OrderRepo(session).update_status(int(order_id), OrderStatus(status_value))
    order = await session.get(Order, int(order_id))
    try:
        await call.bot.send_message(
            order.user_id,
            f"📦 Статус заказа <b>№{order_id}</b> обновлён: <b>{status_value}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await call.answer(f"Статус: {status_value}")
    await call.message.edit_reply_markup(reply_markup=admin_menu_kb())


# ════════════════════════════════════════════
# ДОБАВЛЕНИЕ ТОВАРА
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:add_product")
async def admin_add_product_start(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    categories = (await session.execute(select(Category))).scalars().all()
    if not categories:
        await call.message.edit_text(
            "⚠️ Нет категорий. Введите название первой категории:",
            reply_markup=_cancel_kb(),
        )
        await state.set_state(AdminAddProduct.category)
        await state.update_data(creating_category=True)
        return

    brands = (await session.execute(select(Brand))).scalars().all()
    if not brands:
        await call.message.edit_text(
            "⚠️ Нет брендов. Введите название первого бренда:",
            reply_markup=_cancel_kb(),
        )
        await state.set_state(AdminAddProduct.brand)
        await state.update_data(creating_brand=True)
        return

    await state.set_state(AdminAddProduct.name)
    await call.message.edit_text(
        "➕ <b>Добавление товара</b>\n\nШаг 1/7 — Введите <b>название</b>:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AdminAddProduct.name)
async def ap_name(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(name=message.text)
    categories = (await session.execute(select(Category))).scalars().all()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"apcat:{cat.id}")
    builder.button(text="➕ Новая категория", callback_data="apcat:new")
    builder.button(text="❌ Отмена", callback_data="admin:cancel")
    builder.adjust(2)
    await message.answer("Шаг 2/7 — Выберите <b>категорию</b>:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.category)


@router.callback_query(lambda c: c.data.startswith("apcat:"), AdminAddProduct.category)
async def ap_category_cb(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    value = call.data.split(":")[1]
    if value == "new":
        await call.message.edit_text("Введите название <b>новой категории</b>:", parse_mode="HTML", reply_markup=_cancel_kb())
        return
    await state.update_data(category_id=int(value))
    await _ask_brand(call.message, state, session)


@router.message(AdminAddProduct.category)
async def ap_category_text(message: Message, state: FSMContext, session: AsyncSession):
    slug = message.text.lower().replace(" ", "-")
    cat = Category(name=message.text, slug=slug)
    session.add(cat)
    await session.flush()
    await state.update_data(category_id=cat.id)
    await message.answer(f"✅ Категория «{message.text}» создана.")
    await _ask_brand(message, state, session)


async def _ask_brand(message: Message, state: FSMContext, session: AsyncSession):
    brands = (await session.execute(select(Brand))).scalars().all()
    builder = InlineKeyboardBuilder()
    for b in brands:
        builder.button(text=b.name, callback_data=f"apbrand:{b.id}")
    builder.button(text="➕ Новый бренд", callback_data="apbrand:new")
    builder.button(text="❌ Отмена", callback_data="admin:cancel")
    builder.adjust(2)
    await message.answer("Шаг 3/7 — Выберите <b>бренд</b>:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.brand)


@router.callback_query(lambda c: c.data.startswith("apbrand:"), AdminAddProduct.brand)
async def ap_brand_cb(call: CallbackQuery, state: FSMContext):
    value = call.data.split(":")[1]
    if value == "new":
        await call.message.edit_text("Введите название <b>нового бренда</b>:", parse_mode="HTML", reply_markup=_cancel_kb())
        return
    await state.update_data(brand_id=int(value))
    await call.message.edit_text("Шаг 4/7 — Введите <b>цену</b> (например: 1490.00):", reply_markup=_cancel_kb(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.price)


@router.message(AdminAddProduct.brand)
async def ap_brand_text(message: Message, state: FSMContext, session: AsyncSession):
    brand = Brand(name=message.text)
    session.add(brand)
    await session.flush()
    await state.update_data(brand_id=brand.id)
    await message.answer(f"✅ Бренд «{message.text}» создан.\n\nШаг 4/7 — Введите <b>цену</b>:", reply_markup=_cancel_kb(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.price)


@router.message(AdminAddProduct.price)
async def ap_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("⚠️ Введите число, например: 1490.00")
        return
    await state.update_data(price=price)
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="ap:skip_desc")
    builder.button(text="❌ Отмена", callback_data="admin:cancel")
    builder.adjust(1)
    await message.answer("Шаг 5/7 — Введите <b>описание</b> или пропустите:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.description)


@router.message(AdminAddProduct.description)
async def ap_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await _ask_stock(message, state)


@fsm_router.callback_query(lambda c: c.data == "ap:skip_desc", AdminAddProduct.description)
async def ap_skip_desc(call: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await _ask_stock(call.message, state)


async def _ask_stock(message: Message, state: FSMContext):
    await message.answer("Шаг 6/7 — Введите <b>количество на складе</b>:", reply_markup=_cancel_kb(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.stock)


@router.message(AdminAddProduct.stock)
async def ap_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
    except ValueError:
        await message.answer("⚠️ Введите целое число, например: 50")
        return
    await state.update_data(stock=stock)
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="ap:skip_photo")
    builder.button(text="❌ Отмена", callback_data="admin:cancel")
    builder.adjust(1)
    await message.answer("Шаг 7/7 — Отправьте <b>фото</b> товара или пропустите:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(AdminAddProduct.photo)


@router.message(AdminAddProduct.photo, F.photo)
async def ap_photo(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(photo_ids=json.dumps([message.photo[-1].file_id]))
    await _save_product(message, state, session)


@fsm_router.callback_query(lambda c: c.data == "ap:skip_photo", AdminAddProduct.photo)
async def ap_skip_photo(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.update_data(photo_ids=None)
    await _save_product(call.message, state, session)


async def _save_product(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    product = Product(
        name=data["name"],
        description=data.get("description"),
        price=data["price"],
        stock=data["stock"],
        category_id=data["category_id"],
        brand_id=data["brand_id"],
        photo_ids=data.get("photo_ids"),
        is_active=True,
    )
    session.add(product)
    await session.flush()
    await state.clear()
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n📦 {product.name}\n💰 {product.price} ₽\n🗂 Остаток: {product.stock} шт.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


# ════════════════════════════════════════════
# РЕДАКТИРОВАНИЕ ТОВАРА
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:edit_product")
async def admin_edit_product_list(call: CallbackQuery, session: AsyncSession):
    products = (await session.execute(select(Product).where(Product.is_active == True))).scalars().all()
    if not products:
        await call.answer("Нет активных товаров")
        return
    await call.message.edit_text(
        "✏️ <b>Выберите товар для редактирования:</b>",
        reply_markup=admin_products_kb(products),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:edit:"))
async def admin_edit_product(call: CallbackQuery, session: AsyncSession):
    product_id = int(call.data.split(":")[2])
    p = await session.get(Product, product_id)
    if not p:
        await call.answer("Товар не найден")
        return
    text = (
        f"✏️ <b>{p.name}</b>\n"
        f"💰 Цена: {p.price} ₽"
        + (f" → скидка {p.discount_price} ₽" if p.discount_price else "") + "\n"
        f"📦 Остаток: {p.stock} шт.\n"
        f"✨ Новинка: {'да' if p.is_new else 'нет'}\n"
        f"🔥 Хит: {'да' if p.is_bestseller else 'нет'}\n"
        f"👁 Активен: {'да' if p.is_active else 'нет'}\n\n"
        f"Что редактируем?"
    )
    await call.message.edit_text(text, reply_markup=admin_edit_product_kb(product_id), parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("apedit:"))
async def admin_edit_field(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    parts = call.data.split(":")
    field = parts[1]
    product_id = int(parts[2])

    # Переключатели — без ввода текста
    if field == "toggle_new":
        p = await session.get(Product, product_id)
        p.is_new = not p.is_new
        await call.answer(f"Новинка: {'да' if p.is_new else 'нет'}")
        await call.message.edit_reply_markup(reply_markup=admin_edit_product_kb(product_id))
        return

    if field == "toggle_best":
        p = await session.get(Product, product_id)
        p.is_bestseller = not p.is_bestseller
        await call.answer(f"Хит продаж: {'да' if p.is_bestseller else 'нет'}")
        await call.message.edit_reply_markup(reply_markup=admin_edit_product_kb(product_id))
        return

    if field == "toggle_active":
        p = await session.get(Product, product_id)
        p.is_active = not p.is_active
        await call.answer(f"Активен: {'да' if p.is_active else 'нет'}")
        await call.message.edit_reply_markup(reply_markup=admin_edit_product_kb(product_id))
        return

    prompts = {
        "name": "Введите новое <b>название</b>:",
        "price": "Введите новую <b>цену</b> (например: 1490.00):",
        "discount": "Введите <b>цену со скидкой</b> или 0 чтобы убрать скидку:",
        "stock": "Введите новый <b>остаток на складе</b>:",
        "description": "Введите новое <b>описание</b>:",
        "photo": "Отправьте новое <b>фото</b> товара:",
    }
    await state.set_state(AdminEditProduct.waiting_value)
    await state.update_data(edit_field=field, edit_product_id=product_id)
    await call.message.edit_text(
        prompts.get(field, "Введите новое значение:"),
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AdminEditProduct.waiting_value, F.photo)
async def admin_edit_photo(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    p = await session.get(Product, data["edit_product_id"])
    p.photo_ids = json.dumps([message.photo[-1].file_id])
    await state.clear()
    await message.answer("✅ Фото обновлено.", reply_markup=admin_menu_kb())


@router.message(AdminEditProduct.waiting_value)
async def admin_edit_save(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    field = data["edit_field"]
    product_id = data["edit_product_id"]
    p = await session.get(Product, product_id)

    try:
        if field == "name":
            p.name = message.text
        elif field == "price":
            p.price = float(message.text.replace(",", "."))
        elif field == "discount":
            val = float(message.text.replace(",", "."))
            p.discount_price = None if val == 0 else val
        elif field == "stock":
            p.stock = int(message.text)
        elif field == "description":
            p.description = message.text
    except ValueError:
        await message.answer("⚠️ Некорректное значение, попробуйте ещё раз.")
        return

    await state.clear()
    await message.answer(f"✅ Поле обновлено.", reply_markup=admin_edit_product_kb(product_id))


# ════════════════════════════════════════════
# КАТЕГОРИИ
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:categories")
async def admin_categories(call: CallbackQuery, session: AsyncSession):
    cats = (await session.execute(select(Category))).scalars().all()
    await call.message.edit_text(
        "🗂 <b>Категории:</b>",
        reply_markup=admin_categories_kb(cats),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "admin:cat:add")
async def admin_cat_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminEditCategory.waiting_name)
    await call.message.edit_text("Введите название <b>новой категории</b>:", reply_markup=_cancel_kb(), parse_mode="HTML")


@router.message(AdminEditCategory.waiting_name)
async def admin_cat_save(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cat_id = data.get("edit_cat_id")
    if cat_id:
        cat = await session.get(Category, cat_id)
        cat.name = message.text
        cat.slug = message.text.lower().replace(" ", "-")
        text = f"✅ Категория переименована в «{message.text}»."
    else:
        cat = Category(name=message.text, slug=message.text.lower().replace(" ", "-"))
        session.add(cat)
        text = f"✅ Категория «{message.text}» добавлена."
    await session.flush()
    await state.clear()
    cats = (await session.execute(select(Category))).scalars().all()
    await message.answer(text, reply_markup=admin_categories_kb(cats))


@router.callback_query(lambda c: c.data.startswith("admin:cat:edit:"))
async def admin_cat_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    cat_id = int(call.data.split(":")[3])
    cat = await session.get(Category, cat_id)
    await state.set_state(AdminEditCategory.waiting_name)
    await state.update_data(edit_cat_id=cat_id)
    await call.message.edit_text(
        f"Введите новое название для категории <b>«{cat.name}»</b>:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:cat:del:"))
async def admin_cat_delete(call: CallbackQuery, session: AsyncSession):
    cat_id = int(call.data.split(":")[3])
    cat = await session.get(Category, cat_id)
    name = cat.name
    await session.delete(cat)
    cats = (await session.execute(select(Category))).scalars().all()
    await call.answer(f"Категория «{name}» удалена")
    await call.message.edit_reply_markup(reply_markup=admin_categories_kb(cats))


# ════════════════════════════════════════════
# БРЕНДЫ
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:brands")
async def admin_brands(call: CallbackQuery, session: AsyncSession):
    brands = (await session.execute(select(Brand))).scalars().all()
    await call.message.edit_text(
        "🏷 <b>Бренды:</b>",
        reply_markup=admin_brands_kb(brands),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "admin:brand:add")
async def admin_brand_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminEditBrand.waiting_name)
    await call.message.edit_text("Введите название <b>нового бренда</b>:", reply_markup=_cancel_kb(), parse_mode="HTML")


@router.message(AdminEditBrand.waiting_name)
async def admin_brand_save(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    brand_id = data.get("edit_brand_id")
    if brand_id:
        brand = await session.get(Brand, brand_id)
        brand.name = message.text
        text = f"✅ Бренд переименован в «{message.text}»."
    else:
        brand = Brand(name=message.text)
        session.add(brand)
        text = f"✅ Бренд «{message.text}» добавлен."
    await session.flush()
    await state.clear()
    brands = (await session.execute(select(Brand))).scalars().all()
    await message.answer(text, reply_markup=admin_brands_kb(brands))


@router.callback_query(lambda c: c.data.startswith("admin:brand:edit:"))
async def admin_brand_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    brand_id = int(call.data.split(":")[3])
    brand = await session.get(Brand, brand_id)
    await state.set_state(AdminEditBrand.waiting_name)
    await state.update_data(edit_brand_id=brand_id)
    await call.message.edit_text(
        f"Введите новое название для бренда <b>«{brand.name}»</b>:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:brand:del:"))
async def admin_brand_delete(call: CallbackQuery, session: AsyncSession):
    brand_id = int(call.data.split(":")[3])
    brand = await session.get(Brand, brand_id)
    name = brand.name
    await session.delete(brand)
    brands = (await session.execute(select(Brand))).scalars().all()
    await call.answer(f"Бренд «{name}» удалён")
    await call.message.edit_reply_markup(reply_markup=admin_brands_kb(brands))


# ════════════════════════════════════════════
# МОДЕРАЦИЯ ОТЗЫВОВ
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:reviews")
async def admin_reviews(call: CallbackQuery, session: AsyncSession):
    reviews = (
        await session.execute(select(Review).where(Review.is_approved == False))
    ).scalars().all()
    if not reviews:
        await call.message.edit_text("✅ Нет отзывов на модерации", reply_markup=admin_menu_kb())
        return
    await call.message.edit_text(
        f"⭐ <b>Отзывы на модерации ({len(reviews)}):</b>",
        reply_markup=admin_reviews_kb(reviews),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:review:view:"))
async def admin_review_view(call: CallbackQuery, session: AsyncSession):
    review_id = int(call.data.split(":")[3])
    r = await session.get(Review, review_id)
    if not r:
        await call.answer("Отзыв не найден")
        return
    text = (
        f"⭐ <b>Отзыв #{r.id}</b>\n"
        f"Рейтинг: {'⭐' * r.rating}\n"
        f"Товар ID: {r.product_id}\n"
        f"Пользователь ID: {r.user_id}\n\n"
        f"{r.text or 'Без текста'}"
    )
    await call.message.edit_text(text, reply_markup=admin_review_action_kb(review_id), parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("admin:review:approve:"))
async def admin_review_approve(call: CallbackQuery, session: AsyncSession):
    review_id = int(call.data.split(":")[3])
    r = await session.get(Review, review_id)
    r.is_approved = True
    await call.answer("✅ Отзыв одобрен")
    reviews = (await session.execute(select(Review).where(Review.is_approved == False))).scalars().all()
    await call.message.edit_text(
        f"⭐ <b>Отзывы на модерации ({len(reviews)}):</b>",
        reply_markup=admin_reviews_kb(reviews),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:review:delete:"))
async def admin_review_delete(call: CallbackQuery, session: AsyncSession):
    review_id = int(call.data.split(":")[3])
    r = await session.get(Review, review_id)
    await session.delete(r)
    await call.answer("🗑 Отзыв удалён")
    reviews = (await session.execute(select(Review).where(Review.is_approved == False))).scalars().all()
    await call.message.edit_text(
        f"⭐ <b>Отзывы на модерации ({len(reviews)}):</b>",
        reply_markup=admin_reviews_kb(reviews),
        parse_mode="HTML",
    )


# ════════════════════════════════════════════
# АКЦИИ И СКИДКИ
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:promos")
async def admin_promos(call: CallbackQuery, session: AsyncSession):
    products = (await session.execute(select(Product).where(Product.is_active == True))).scalars().all()
    await call.message.edit_text(
        "🎁 <b>Акции и скидки</b>\n\nВыберите товар для установки скидки:",
        reply_markup=admin_promos_kb(products),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("admin:promo:set:"))
async def admin_promo_set(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    product_id = int(call.data.split(":")[3])
    p = await session.get(Product, product_id)
    await state.set_state(AdminSetDiscount.waiting_price)
    await state.update_data(promo_product_id=product_id)
    current = f"Текущая скидочная цена: {p.discount_price} ₽\n\n" if p.discount_price else ""
    await call.message.edit_text(
        f"🔖 <b>{p.name}</b>\n"
        f"Цена: {p.price} ₽\n"
        f"{current}"
        f"Введите <b>цену со скидкой</b> или <b>0</b> чтобы убрать скидку:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AdminSetDiscount.waiting_price)
async def admin_promo_save(message: Message, state: FSMContext, session: AsyncSession):
    try:
        val = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("⚠️ Введите число, например: 990.00 или 0")
        return

    data = await state.get_data()
    p = await session.get(Product, data["promo_product_id"])
    p.discount_price = None if val == 0 else val
    await state.clear()

    if val == 0:
        await message.answer(f"✅ Скидка на «{p.name}» убрана.", reply_markup=admin_menu_kb())
    else:
        await message.answer(
            f"✅ Скидка установлена!\n\n"
            f"📦 {p.name}\n"
            f"💰 {p.price} ₽ → 🔖 {p.discount_price} ₽",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )


# ════════════════════════════════════════════
# СТАТИСТИКА
# ════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "admin:stats")
async def admin_stats(call: CallbackQuery, session: AsyncSession):
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    total_revenue = (await session.execute(select(func.sum(Order.total_price)))).scalar() or 0

    # За последние 30 дней
    month_ago = datetime.now() - timedelta(days=30)
    month_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= month_ago)
    )).scalar() or 0
    month_revenue = (await session.execute(
        select(func.sum(Order.total_price)).where(Order.created_at >= month_ago)
    )).scalar() or 0

    # Топ-3 товара по количеству продаж
    top_q = (
        select(Product.name, func.sum(OrderItem.quantity).label("total"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(3)
    )
    top_products = (await session.execute(top_q)).all()

    top_text = "\n".join(f"  {i+1}. {row.name} — {row.total} шт." for i, row in enumerate(top_products)) or "  Нет данных"

    # Заказы по статусам
    statuses_q = select(Order.status, func.count(Order.id)).group_by(Order.status)
    statuses = (await session.execute(statuses_q)).all()
    status_text = "\n".join(f"  {s.value}: {cnt}" for s, cnt in statuses) or "  Нет данных"

    text = (
        f"📊 <b>Статистика магазина</b>\n\n"
        f"<b>За всё время:</b>\n"
        f"  Заказов: {total_orders}\n"
        f"  Выручка: {total_revenue:.2f} ₽\n\n"
        f"<b>За последние 30 дней:</b>\n"
        f"  Заказов: {month_orders}\n"
        f"  Выручка: {month_revenue:.2f} ₽\n\n"
        f"<b>Топ-3 товара:</b>\n{top_text}\n\n"
        f"<b>Заказы по статусам:</b>\n{status_text}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

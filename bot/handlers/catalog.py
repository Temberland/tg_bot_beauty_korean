from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import categories_kb, products_list_kb, product_kb
from db.repository import CartRepo, ProductRepo

router = Router()


def product_text(p) -> str:
    lines = [f"<b>{p.name}</b>"]
    if p.brand:
        lines.append(f"Бренд: {p.brand.name}")
    if p.volume:
        lines.append(f"Объём: {p.volume}")
    if p.description:
        lines.append(f"\n{p.description}")
    if p.composition:
        lines.append(f"\n<i>Состав:</i> {p.composition[:300]}...")

    if p.discount_price:
        lines.append(f"\nЦена: <s>{p.price} ₽</s>  <b>{p.discount_price} ₽</b> 🔥")
    else:
        lines.append(f"\nЦена: <b>{p.price} ₽</b>")

    stock_label = "✅ В наличии" if p.stock > 0 else "❌ Нет в наличии"
    lines.append(stock_label)
    return "\n".join(lines)


@router.message(Command("catalog"))
@router.callback_query(lambda c: c.data == "catalog")
async def show_catalog(event: Message | CallbackQuery, session: AsyncSession):
    repo = ProductRepo(session)
    categories = await repo.get_categories()
    text = "🛍 <b>Каталог</b>\n\nВыберите категорию:"
    kb = categories_kb(categories)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("cat:"))
async def show_category(call: CallbackQuery, session: AsyncSession):
    cat_id = int(call.data.split(":")[1])
    repo = ProductRepo(session)
    products = await repo.get_by_category(cat_id, page=0)
    if not products:
        await call.answer("В этой категории пока нет товаров")
        return
    await call.message.edit_text(
        f"Найдено товаров: {len(products)}",
        reply_markup=products_list_kb(products, page=0, cat_id=cat_id),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data.startswith("cat_page:"))
async def show_category_page(call: CallbackQuery, session: AsyncSession):
    _, cat_id, page = call.data.split(":")
    cat_id, page = int(cat_id), int(page)
    repo = ProductRepo(session)
    products = await repo.get_by_category(cat_id, page=page)
    await call.message.edit_reply_markup(
        reply_markup=products_list_kb(products, page=page, cat_id=cat_id)
    )


@router.callback_query(lambda c: c.data.startswith("product:"))
async def show_product(call: CallbackQuery, session: AsyncSession):
    product_id = int(call.data.split(":")[1])
    prod_repo = ProductRepo(session)
    cart_repo = CartRepo(session)

    product = await prod_repo.get_by_id(product_id)
    if not product:
        await call.answer("Товар не найден")
        return

    cart_items = await cart_repo.get_items(call.from_user.id)
    in_cart = any(i.product_id == product_id for i in cart_items)

    text = product_text(product)
    kb = product_kb(product, in_cart=in_cart)

    photo_ids = []
    if product.photo_ids:
        import json
        photo_ids = json.loads(product.photo_ids)

    if photo_ids:
        await call.message.answer_photo(
            photo=photo_ids[0],
            caption=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
        await call.message.delete()
    else:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("filter:"))
async def filter_products(call: CallbackQuery, session: AsyncSession):
    filter_type = call.data.split(":")[1]
    repo = ProductRepo(session)
    if filter_type == "new":
        products = await repo.get_new()
        title = "✨ Новинки"
    else:
        products = await repo.get_bestsellers()
        title = "🔥 Хиты продаж"

    if not products:
        await call.answer("Пока здесь пусто")
        return

    lines = [f"<b>{title}</b>\n"]
    for p in products:
        price = p.discount_price or p.price
        lines.append(f"• {p.name} — {price} ₽")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=products_list_kb(products, page=0, cat_id=0),
        parse_mode="HTML",
    )

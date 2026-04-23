import json

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.keyboards.inline import (
    categories_kb, products_list_kb, product_kb, reviews_kb, brands_filter_kb,
)
from bot.states.order import ReviewForm
from db.models import Product, Review
from db.repository import CartRepo, ProductRepo, ReviewRepo

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
    lines.append("✅ В наличии" if p.stock > 0 else "❌ Нет в наличии")
    return "\n".join(lines)


async def safe_edit_message(call: CallbackQuery, text: str, reply_markup=None, parse_mode: str = "HTML"):
    # Если текущее сообщение содержит фото/медиа — удаляем его и отправляем новое текстовое.
    if call.message.photo or call.message.video or call.message.document:
        await call.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        try:
            await call.message.delete()
        except Exception:
            pass
        return

    try:
        await call.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return
    except Exception:
        pass

    await call.message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    try:
        await call.message.delete()
    except Exception:
        pass


def _sort_label(sort: str | None) -> str:
    if sort == "price_asc":
        return " · цена ↑"
    if sort == "price_desc":
        return " · цена ↓"
    return ""


@router.message(Command("catalog"))
@router.callback_query(lambda c: c.data == "catalog")
async def show_catalog(event: Message | CallbackQuery, session: AsyncSession):
    repo = ProductRepo(session)
    categories = await repo.get_categories()
    text = "🛍 <b>Каталог</b>\n\nВыберите категорию:"
    kb = categories_kb(categories)

    if isinstance(event, CallbackQuery):
        await safe_edit_message(event, text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Вход в категорию (без фильтров) ─────────────────────────
@router.callback_query(lambda c: c.data.startswith("cat:"))
async def show_category(call: CallbackQuery, session: AsyncSession):
    cat_id = int(call.data.split(":")[1])
    repo = ProductRepo(session)
    products = await repo.get_by_category(cat_id, page=0)

    if not products:
        await call.answer("В этой категории пока нет товаров")
        return

    await safe_edit_message(
        call,
        f"Найдено товаров: {len(products)}",
        reply_markup=products_list_kb(products, page=0, cat_id=cat_id),
        parse_mode="HTML",
    )
    await call.answer()


# ── Применить фильтр (сортировка или бренд) ─────────────────
# callback: cat_sort:{cat_id}:{sort}:{brand_id}
# sort: price_asc | price_desc | none
# brand_id: 0 = без фильтра
@router.callback_query(lambda c: c.data.startswith("cat_sort:"))
async def apply_sort(call: CallbackQuery, session: AsyncSession):
    _, cat_id_s, sort_s, brand_id_s = call.data.split(":")
    cat_id = int(cat_id_s)
    sort = sort_s if sort_s != "none" else None
    brand_id = int(brand_id_s) if int(brand_id_s) != 0 else None

    repo = ProductRepo(session)
    products = await repo.get_by_category(cat_id, page=0, sort=sort, brand_id=brand_id)

    if not products:
        await call.answer("Товаров по этому фильтру не найдено")
        return

    label = _sort_label(sort)
    await safe_edit_message(
        call,
        f"Найдено товаров: {len(products)}{label}",
        reply_markup=products_list_kb(products, page=0, cat_id=cat_id, sort=sort, brand_id=brand_id),
        parse_mode="HTML",
    )
    await call.answer()


# ── Меню выбора бренда ───────────────────────────────────────
# callback: cat_brand_menu:{cat_id}:{sort}
@router.callback_query(lambda c: c.data.startswith("cat_brand_menu:"))
async def show_brand_menu(call: CallbackQuery, session: AsyncSession):
    _, cat_id_s, sort_s = call.data.split(":")
    cat_id = int(cat_id_s)
    sort = sort_s if sort_s != "none" else None

    repo = ProductRepo(session)
    brands = await repo.get_brands_by_category(cat_id)

    if not brands:
        await call.answer("Бренды не найдены")
        return

    await safe_edit_message(
        call,
        "🏷 <b>Выберите бренд:</b>",
        reply_markup=brands_filter_kb(brands, cat_id=cat_id, sort=sort),
        parse_mode="HTML",
    )
    await call.answer()


# ── Пагинация с учётом фильтров ──────────────────────────────
# callback: cat_page:{cat_id}:{page}:{sort}:{brand_id}
@router.callback_query(lambda c: c.data.startswith("cat_page:"))
async def show_category_page(call: CallbackQuery, session: AsyncSession):
    parts = call.data.split(":")
    cat_id = int(parts[1])
    page = int(parts[2])
    sort_s = parts[3] if len(parts) > 3 else "none"
    brand_id_s = parts[4] if len(parts) > 4 else "0"
    sort = sort_s if sort_s != "none" else None
    brand_id = int(brand_id_s) if int(brand_id_s) != 0 else None

    repo = ProductRepo(session)
    products = await repo.get_by_category(cat_id, page=page, sort=sort, brand_id=brand_id)

    label = _sort_label(sort)
    await safe_edit_message(
        call,
        f"Найдено товаров: {len(products)}{label}",
        reply_markup=products_list_kb(products, page=page, cat_id=cat_id, sort=sort, brand_id=brand_id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("product:"))
async def show_product(call: CallbackQuery, session: AsyncSession):
    product_id = int(call.data.split(":")[1])

    result = await session.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.brand), selectinload(Product.category))
    )
    product = result.scalar_one_or_none()

    if not product:
        await call.answer("Товар не найден")
        return

    cart_repo = CartRepo(session)
    cart_items = await cart_repo.get_items(call.from_user.id)
    in_cart = any(i.product_id == product_id for i in cart_items)

    review_repo = ReviewRepo(session)
    reviews = await review_repo.get_approved_by_product(product_id)
    review_count = len(reviews)
    avg_rating = round(sum(r.rating for r in reviews) / review_count, 1) if reviews else None

    text = product_text(product)
    if avg_rating:
        text += f"\n\n⭐ Рейтинг: {avg_rating} ({review_count} отз.)"

    kb = product_kb(product, in_cart=in_cart, review_count=review_count)

    photo_ids = []
    if product.photo_ids:
        photo_ids = json.loads(product.photo_ids)

    if photo_ids:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer_photo(
            photo=photo_ids[0],
            caption=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await safe_edit_message(call, text, reply_markup=kb, parse_mode="HTML")

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("reviews:"))
async def show_reviews(call: CallbackQuery, session: AsyncSession):
    product_id = int(call.data.split(":")[1])
    product = await session.get(Product, product_id)
    if not product:
        await call.answer("Товар не найден")
        return

    review_repo = ReviewRepo(session)
    reviews = await review_repo.get_approved_by_product(product_id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Оставить отзыв", callback_data=f"write_review:{product_id}")
    builder.button(text="◀️ Назад", callback_data=f"product:{product_id}")
    builder.adjust(1)

    if not reviews:
        text = f"⭐ <b>Отзывы о {product.name}</b>\n\nОтзывов пока нет. Будьте первым!"
    else:
        lines = [f"⭐ <b>Отзывы о {product.name}</b>\n"]
        for r in reviews:
            stars = "⭐" * r.rating
            text_part = f"\n{r.text}" if r.text else ""
            lines.append(f"{stars}{text_part}")
            lines.append("─" * 20)
        text = "\n".join(lines)

    await safe_edit_message(call, text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("write_review:"))
async def write_review_start(call: CallbackQuery, state: FSMContext):
    product_id = call.data.split(":")[1]
    await state.update_data(review_product_id=int(product_id))
    await state.set_state(ReviewForm.rating)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐1", callback_data=f"rate:{product_id}:1")
    builder.button(text="⭐2", callback_data=f"rate:{product_id}:2")
    builder.button(text="⭐3", callback_data=f"rate:{product_id}:3")
    builder.button(text="⭐4", callback_data=f"rate:{product_id}:4")
    builder.button(text="⭐5", callback_data=f"rate:{product_id}:5")
    builder.button(text="◀️ Отмена", callback_data=f"reviews:{product_id}")
    builder.adjust(5, 1)

    await safe_edit_message(
        call,
        "✍️ <b>Оцените товар:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("rate:"))
async def rate_product(call: CallbackQuery, state: FSMContext):
    _, product_id_str, rating_str = call.data.split(":")
    product_id = int(product_id_str)
    rating = int(rating_str)
    await state.update_data(review_product_id=product_id, review_rating=rating)
    await state.set_state(ReviewForm.text)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="review_skip_text")
    builder.button(text="◀️ Отмена", callback_data=f"reviews:{product_id}")
    builder.adjust(1)

    text = f"{'⭐' * rating} Отлично! Напишите текст отзыва или нажмите «Пропустить»:"
    await safe_edit_message(call, text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.message(ReviewForm.text)
async def review_text(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await ReviewRepo(session).add(
        user_id=message.from_user.id,
        product_id=data["review_product_id"],
        rating=data["review_rating"],
        text=message.text.strip(),
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к товару", callback_data=f"product:{data['review_product_id']}")

    await message.answer(
        f"✅ Ваша оценка {'⭐' * data['review_rating']} и отзыв приняты!\nОн будет опубликован после проверки.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(lambda c: c.data == "review_skip_text", ReviewForm.text)
async def review_skip_text(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()

    await ReviewRepo(session).add(
        user_id=call.from_user.id,
        product_id=data["review_product_id"],
        rating=data["review_rating"],
        text=None,
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к товару", callback_data=f"product:{data['review_product_id']}")

    text = (
        f"✅ Ваша оценка {'⭐' * data['review_rating']} принята и будет опубликована после проверки."
    )
    await safe_edit_message(call, text, reply_markup=builder.as_markup())
    await call.answer()


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

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.button(text=f"{p.name}", callback_data=f"product:{p.id}")
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="catalog"))
    builder.adjust(1)

    await safe_edit_message(
        call,
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await call.answer()

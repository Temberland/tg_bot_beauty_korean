from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Category, Brand, Product, CartItem, Order, OrderStatus, Review


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог", callback_data="catalog")
    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="📦 Мои заказы", callback_data="orders")
    builder.button(text="🎁 Акции", callback_data="promo")
    builder.button(text="💬 Поддержка", callback_data="support")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"cat:{cat.id}")
    builder.button(text="🔍 Новинки", callback_data="filter:new")
    builder.button(text="🔥 Хиты продаж", callback_data="filter:bestseller")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


def product_kb(product: Product, in_cart: bool = False, review_count: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if product.stock > 0:
        label = "✅ В корзине" if in_cart else "🛒 В корзину"
        builder.button(text=label, callback_data=f"add_cart:{product.id}")
    rev_label = f"⭐ Отзывы ({review_count})" if review_count else "⭐ Отзывы"
    builder.button(text=rev_label, callback_data=f"reviews:{product.id}")
    builder.button(text="◀️ Назад", callback_data=f"cat:{product.category_id}")
    builder.adjust(1)
    return builder.as_markup()


def reviews_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Оставить отзыв", callback_data=f"write_review:{product_id}")
    builder.button(text="◀️ Назад", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def products_list_kb(
    products: list[Product],
    page: int,
    cat_id: int,
    sort: str | None = None,
    brand_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Список товаров с активными фильтрами.
    sort: None | 'price_asc' | 'price_desc'
    brand_id: None | int
    """
    builder = InlineKeyboardBuilder()

    # --- Кнопки фильтров ---
    # Фильтр по цене
    if sort == "price_asc":
        price_btn = InlineKeyboardButton(
            text="💰 Цена ↑ ✓",
            callback_data=f"cat_sort:{cat_id}:price_desc:{brand_id or 0}",
        )
    elif sort == "price_desc":
        price_btn = InlineKeyboardButton(
            text="💰 Цена ↓ ✓",
            callback_data=f"cat_sort:{cat_id}:price_asc:{brand_id or 0}",
        )
    else:
        price_btn = InlineKeyboardButton(
            text="💰 По цене",
            callback_data=f"cat_sort:{cat_id}:price_asc:{brand_id or 0}",
        )

    # Фильтр по бренду
    if brand_id:
        brand_btn = InlineKeyboardButton(
            text="🏷 Бренд ✓",
            callback_data=f"cat_brand_menu:{cat_id}:{sort or 'none'}",
        )
    else:
        brand_btn = InlineKeyboardButton(
            text="🏷 По бренду",
            callback_data=f"cat_brand_menu:{cat_id}:{sort or 'none'}",
        )

    builder.row(price_btn, brand_btn)

    # --- Список товаров ---
    for p in products:
        price = p.discount_price or p.price
        builder.button(text=f"{p.name} — {price} ₽", callback_data=f"product:{p.id}")

    # --- Пагинация ---
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"cat_page:{cat_id}:{page - 1}:{sort or 'none'}:{brand_id or 0}",
        ))
    if len(products) == 6:
        nav.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"cat_page:{cat_id}:{page + 1}:{sort or 'none'}:{brand_id or 0}",
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="catalog"))
    builder.adjust(1)
    return builder.as_markup()


def brands_filter_kb(
    brands: list[Brand],
    cat_id: int,
    sort: str | None,
    active_brand_id: int | None = None,
) -> InlineKeyboardMarkup:
    """Список брендов для фильтрации в категории."""
    builder = InlineKeyboardBuilder()
    sort_str = sort or "none"
    for brand in brands:
        mark = " ✓" if brand.id == active_brand_id else ""
        builder.button(
            text=f"{brand.name}{mark}",
            callback_data=f"cat_sort:{cat_id}:{sort_str}:{brand.id}",
        )
    # Кнопка "Все бренды" (сброс фильтра по бренду)
    builder.button(
        text="❌ Сбросить бренд",
        callback_data=f"cat_sort:{cat_id}:{sort_str}:0",
    )
    builder.button(
        text="◀️ Назад",
        callback_data=f"cat_sort:{cat_id}:{sort_str}:{active_brand_id or 0}",
    )
    builder.adjust(1)
    return builder.as_markup()


def cart_kb(items: list[CartItem]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=f"❌ {item.product.name} x{item.quantity}",
            callback_data=f"remove_cart:{item.id}",
        )
    if items:
        builder.button(text="✅ Оформить заказ", callback_data="checkout")
        builder.button(text="🗑 Очистить корзину", callback_data="clear_cart")
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def delivery_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚚 Курьер", callback_data="delivery:courier")
    builder.button(text="📦 Пункт выдачи", callback_data="delivery:pickup")
    builder.button(text="📮 Почта России", callback_data="delivery:post")
    builder.button(text="◀️ Назад", callback_data="checkout_back:address")
    builder.adjust(1)
    return builder.as_markup()


def payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Онлайн", callback_data="payment:online")
    builder.button(text="💵 При получении", callback_data="payment:on_delivery")
    builder.button(text="◀️ Назад", callback_data="checkout_back:delivery")
    builder.adjust(1)
    return builder.as_markup()


def order_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="order_confirm")
    builder.button(text="❌ Отмена", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


def orders_list_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=f"№{order.id} — {order.status.value} — {order.total_price} ₽",
            callback_data=f"order_detail:{order.id}",
        )
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


# ── Admin keyboards ──────────────────────────────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Заказы", callback_data="admin:orders")
    builder.button(text="➕ Добавить товар", callback_data="admin:add_product")
    builder.button(text="✏️ Редактировать товар", callback_data="admin:edit_product")
    builder.button(text="🗂 Категории", callback_data="admin:categories")
    builder.button(text="🏷 Бренды", callback_data="admin:brands")
    builder.button(text="🎁 Акции и скидки", callback_data="admin:promos")
    builder.button(text="⭐ Отзывы", callback_data="admin:reviews")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.adjust(2)
    return builder.as_markup()


def admin_orders_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Новые", callback_data="admin:orders:new")
    builder.button(text="📋 Все", callback_data="admin:orders:all")
    builder.button(text="✅ Завершённые", callback_data="admin:orders:done")
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(3, 1)
    return builder.as_markup()


def admin_orders_list_kb(orders: list[Order], back_cb: str = "admin:orders") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=f"№{order.id} | {order.full_name} | {order.total_price} ₽",
            callback_data=f"admin:order:{order.id}",
        )
    builder.button(text="◀️ Назад", callback_data=back_cb)
    builder.adjust(1)
    return builder.as_markup()


def order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for status in OrderStatus:
        builder.button(text=status.value, callback_data=f"set_status:{order_id}:{status.value}")
    builder.button(text="◀️ Назад", callback_data="admin:orders")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def admin_products_kb(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.button(text=f"{p.name} — {p.price} ₽", callback_data=f"admin:edit:{p.id}")
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_edit_product_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Название", callback_data=f"apedit:name:{product_id}")
    builder.button(text="💰 Цена", callback_data=f"apedit:price:{product_id}")
    builder.button(text="🔖 Скидка", callback_data=f"apedit:discount:{product_id}")
    builder.button(text="📦 Остаток", callback_data=f"apedit:stock:{product_id}")
    builder.button(text="📄 Описание", callback_data=f"apedit:description:{product_id}")
    builder.button(text="🖼 Фото", callback_data=f"apedit:photo:{product_id}")
    builder.button(text="✨ Новинка", callback_data=f"apedit:toggle_new:{product_id}")
    builder.button(text="🔥 Хит продаж", callback_data=f"apedit:toggle_best:{product_id}")
    builder.button(text="🚫 Скрыть/показать", callback_data=f"apedit:toggle_active:{product_id}")
    builder.button(text="🗑 Удалить товар", callback_data=f"admin:product:del:{product_id}")
    builder.button(text="◀️ Назад", callback_data="admin:edit_product")
    builder.adjust(2)
    return builder.as_markup()


def admin_categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"✏️ {cat.name}", callback_data=f"admin:cat:edit:{cat.id}")
        builder.button(text="🗑", callback_data=f"admin:cat:del:{cat.id}")
    builder.button(text="➕ Добавить", callback_data="admin:cat:add")
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(2)
    return builder.as_markup()


def admin_brands_kb(brands: list[Brand]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for brand in brands:
        builder.button(text=f"✏️ {brand.name}", callback_data=f"admin:brand:edit:{brand.id}")
        builder.button(text="🗑", callback_data=f"admin:brand:del:{brand.id}")
    builder.button(text="➕ Добавить", callback_data="admin:brand:add")
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(2)
    return builder.as_markup()


def admin_reviews_products_kb(rows) -> InlineKeyboardMarkup:
    """rows — list[(Product, count)]"""
    builder = InlineKeyboardBuilder()
    for product, cnt in rows:
        builder.button(
            text=f"📦 {product.name} ({cnt} новых)",
            callback_data=f"admin:reviews:product:{product.id}",
        )
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_reviews_kb(reviews: list[Review]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in reviews:
        status = "✅" if r.is_approved else "⏳"
        builder.button(
            text=f"{status} ⭐{r.rating} — {r.text[:20] if r.text else 'без текста'}",
            callback_data=f"admin:review:view:{r.id}",
        )
    builder.button(text="◀️ Назад", callback_data="admin:reviews")
    builder.adjust(1)
    return builder.as_markup()


def admin_review_action_kb(review_id: int, product_id: int, is_approved: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_approved:
        builder.button(text="✅ Одобрить", callback_data=f"admin:review:approve:{review_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin:review:delete:{review_id}:{product_id}")
    builder.button(text="◀️ Назад", callback_data=f"admin:reviews:product:{product_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def admin_promos_kb(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        disc = f" 🔖{p.discount_price}₽" if p.discount_price else ""
        builder.button(text=f"{p.name}{disc}", callback_data=f"admin:promo:set:{p.id}")
    builder.button(text="◀️ Назад", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()

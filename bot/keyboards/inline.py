from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Category, Product, CartItem, Order, OrderStatus


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


def product_kb(product: Product, in_cart: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if product.stock > 0:
        label = "✅ В корзине" if in_cart else "🛒 В корзину"
        builder.button(text=label, callback_data=f"add_cart:{product.id}")
    builder.button(text="⭐ Отзывы", callback_data=f"reviews:{product.id}")
    builder.button(text="◀️ Назад", callback_data=f"cat:{product.category_id}")
    builder.adjust(1)
    return builder.as_markup()


def products_list_kb(products: list[Product], page: int, cat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        price = p.discount_price or p.price
        label = f"{p.name} — {price} ₽"
        builder.button(text=label, callback_data=f"product:{p.id}")
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cat_page:{cat_id}:{page - 1}"))
    if len(products) == 6:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cat_page:{cat_id}:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="catalog"))
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
    builder.adjust(1)
    return builder.as_markup()


def payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Онлайн", callback_data="payment:online")
    builder.button(text="💵 При получении", callback_data="payment:on_delivery")
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


# ── Admin keyboards ──────────────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Новые заказы", callback_data="admin:orders")
    builder.button(text="➕ Добавить товар", callback_data="admin:add_product")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="⭐ Модерация отзывов", callback_data="admin:reviews")
    builder.adjust(2)
    return builder.as_markup()


def order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for status in OrderStatus:
        builder.button(
            text=status.value,
            callback_data=f"set_status:{order_id}:{status.value}",
        )
    builder.adjust(2)
    return builder.as_markup()

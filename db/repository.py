from decimal import Decimal

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    Brand, CartItem, Category, Order, OrderItem,
    OrderStatus, Product, Review, User,
)


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, tg_id: int, username: str | None, full_name: str | None) -> User:
        user = await self.session.get(User, tg_id)
        if not user:
            user = User(id=tg_id, username=username, full_name=full_name)
            self.session.add(user)
            await self.session.flush()
        return user

    async def is_admin(self, tg_id: int) -> bool:
        user = await self.session.get(User, tg_id)
        return bool(user and user.is_admin)


class ProductRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_categories(self) -> list[Category]:
        result = await self.session.execute(select(Category))
        return result.scalars().all()

    async def get_brands(self) -> list[Brand]:
        result = await self.session.execute(select(Brand))
        return result.scalars().all()

    async def get_by_category(self, category_id: int, page: int = 0, per_page: int = 6) -> list[Product]:
        q = (
            select(Product)
            .where(Product.category_id == category_id, Product.is_active == True)
            .offset(page * per_page)
            .limit(per_page)
        )
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get_new(self, limit: int = 10) -> list[Product]:
        q = select(Product).where(Product.is_new == True, Product.is_active == True).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_bestsellers(self, limit: int = 10) -> list[Product]:
        q = select(Product).where(Product.is_bestseller == True, Product.is_active == True).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def search(self, query: str) -> list[Product]:
        q = select(Product).where(
            Product.name.ilike(f"%{query}%"),
            Product.is_active == True,
        )
        result = await self.session.execute(q)
        return result.scalars().all()


class CartRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_items(self, user_id: int) -> list[CartItem]:
        q = (
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .options(selectinload(CartItem.product))
        )
        result = await self.session.execute(q)
        return result.scalars().all()

    async def add_or_increment(self, user_id: int, product_id: int) -> None:
        q = select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        item = (await self.session.execute(q)).scalar_one_or_none()
        if item:
            item.quantity += 1
        else:
            self.session.add(CartItem(user_id=user_id, product_id=product_id))
        await self.session.flush()

    async def remove_item(self, item_id: int) -> None:
        await self.session.execute(delete(CartItem).where(CartItem.id == item_id))

    async def clear(self, user_id: int) -> None:
        await self.session.execute(delete(CartItem).where(CartItem.user_id == user_id))

    async def get_total(self, user_id: int) -> Decimal:
        items = await self.get_items(user_id)
        return sum(item.product.effective_price * item.quantity for item in items)


class OrderRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_from_cart(
        self,
        user_id: int,
        cart_items: list[CartItem],
        full_name: str,
        phone: str,
        address: str,
        delivery_method,
        payment_method,
    ) -> Order:
        total = sum(i.product.effective_price * i.quantity for i in cart_items)
        order = Order(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            address=address,
            delivery_method=delivery_method,
            payment_method=payment_method,
            total_price=total,
        )
        self.session.add(order)
        await self.session.flush()

        for item in cart_items:
            self.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_purchase=item.product.effective_price,
            ))
        return order

    async def get_user_orders(self, user_id: int) -> list[Order]:
        q = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(q)
        return result.scalars().all()

    async def update_status(self, order_id: int, status: OrderStatus) -> None:
        await self.session.execute(
            update(Order).where(Order.id == order_id).values(status=status)
        )

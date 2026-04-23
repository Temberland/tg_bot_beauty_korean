from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    delivery_method = State()
    payment_method = State()
    confirm = State()


class ReviewForm(StatesGroup):
    rating = State()
    text = State()


class AdminAddProduct(StatesGroup):
    name = State()
    category = State()
    brand = State()
    price = State()
    description = State()
    stock = State()
    photo = State()


class AdminEditProduct(StatesGroup):
    waiting_value = State()


class AdminEditCategory(StatesGroup):
    waiting_name = State()


class AdminEditBrand(StatesGroup):
    waiting_name = State()


class AdminSetDiscount(StatesGroup):
    waiting_price = State()

from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    delivery_method = State()
    payment_method = State()
    confirm = State()


class AdminAddProduct(StatesGroup):
    name = State()
    category = State()
    brand = State()
    price = State()
    description = State()
    photo = State()
    stock = State()

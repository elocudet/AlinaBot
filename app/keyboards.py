from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from app.products import PRODUCTS


def _price(payload: str) -> str:
    return f"{PRODUCTS[payload]['price'] // 100}р"


PANEL_BUTTON = 'Панель управления'


def main(is_owner: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text='Подробнее: За пределом. Синдром хорошей девочки')],
        [KeyboardButton(text='Подробнее: Программа по выходу из созависимости «Полюб(в)и»')],
        [KeyboardButton(text='Подробнее: Психологический журнал a.soznanie')],
        [KeyboardButton(text='Обратиться в поддержку')]
    ]
    if is_owner:
        keyboard.append([KeyboardButton(text=PANEL_BUTTON)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder='Выберите пункт меню...'
    )

good_girl = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплата {_price('good_girl_payment')}", callback_data='good_girl')]
    ]
)

polubvi = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплата {_price('polubvi_payment')}", callback_data="polubvi")]
    ]
)

read = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплата {_price('read_payment')}", callback_data='read')]
    ]
)

good_girl1 = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить", callback_data='good_girl1')]
    ]
)

polubvi1 = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить", callback_data='polubvi1')]
    ]
)

read1 = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить", callback_data='read1')]
    ]
)

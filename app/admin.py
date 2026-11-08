"""Панель управления для админов из owners.txt: добавить/удалить пользователя по ID."""

from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import app.db as db
from app.keyboards import PANEL_BUTTON
from app.owners import is_owner
from app.products import PRODUCTS

router = Router()

# Ждём от админа ID: admin_id -> (что делаем, продукт). Сбрасывается при перезапуске бота.
PENDING: dict[int, tuple[str, str]] = {}

HINT = "Нужен числовой ID (например 123456789), а не имя. Узнать ID можно у @userinfobot."


def _short_date(kick_date: str | None) -> str:
    return datetime.fromisoformat(kick_date).astimezone(db.MSK).strftime("%d.%m.%Y")


def _find(product_key: str) -> dict:
    for item in PRODUCTS.values():
        if item["product"] == product_key:
            return item
    raise KeyError(product_key)


async def _deny(event) -> bool:
    """True, если это не админ. Отвечает пользователю и возвращает True."""
    if is_owner(event.from_user):
        if event.from_user.username:
            db.remember_owner(event.from_user.username, event.from_user.id)
        return False
    if isinstance(event, CallbackQuery):
        await event.answer("Только для админов", show_alert=True)
    return True


def _plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def panel_kb() -> InlineKeyboardMarkup:
    rows = []
    for item in PRODUCTS.values():
        total, active = db.payment_stats(item["product"])
        suffix = f" · активных {active}" if item["days"] else f" · купили {total}"
        rows.append([InlineKeyboardButton(text=item["short"] + suffix, callback_data=f"adm:p:{item['product']}")])
    rows.append([InlineKeyboardButton(text="🧾 Выручка", callback_data="adm:rev")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_text(item: dict) -> str:
    total, active = db.payment_stats(item["product"])
    lines = [item["title"], f"Всего записей: {total}"]
    if item["days"]:
        lines.append(f"Активных подписок: {active}")
    return "\n".join(lines)


def product_kb(item: dict) -> InlineKeyboardMarkup:
    product = item["product"]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить по ID", callback_data=f"adm:a:{product}")],
            [InlineKeyboardButton(text="👥 Список / удалить", callback_data=f"adm:l:{product}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:panel")],
        ]
    )


def list_view(item: dict) -> tuple[str, InlineKeyboardMarkup]:
    product = item["product"]
    rows = db.list_payments(product)
    buttons = []
    for row in rows:
        name = (row["user_name"] or "без имени")[:18]
        label = f"❌ {name} {row['user_id']}"
        if row["kick_date"]:
            label += f" · до {_short_date(row['kick_date'])}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"adm:d:{product}:{row['user_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm:p:{product}")])
    text = item["title"] + "\n\n"
    text += "Нажмите на пользователя, чтобы удалить его из базы." if rows else "Пока никого нет."
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


def revenue_view() -> str:
    by_product = db.revenue_by_product()
    total = sum(amount for _, amount in by_product.values())
    lines = [f"Выручка: {db.money(total)}", ""]
    for item in PRODUCTS.values():
        count, amount = by_product.get(item["product"], (0, 0))
        lines.append(
            f"{item['short']} — {db.money(amount)} ({count} {_plural(count, 'оплата', 'оплаты', 'оплат')})"
        )
    lines += [
        "",
        "Считаются только оплаты через бота. Ручная выдача доступа из панели не в счёт.",
        "За продажи до обновления записано по одной оплате на человека, даже если продлевали.",
    ]
    return "\n".join(lines)


@router.message(F.text == PANEL_BUTTON)
async def panel(message: Message):
    if await _deny(message):
        return
    PENDING.pop(message.from_user.id, None)
    await message.answer("Панель управления", reply_markup=panel_kb())


@router.callback_query(F.data == "adm:panel")
async def panel_cb(callback: CallbackQuery):
    if await _deny(callback):
        return
    await callback.answer()
    await callback.message.edit_text("Панель управления", reply_markup=panel_kb())


@router.callback_query(F.data == "adm:rev")
async def revenue_cb(callback: CallbackQuery):
    if await _deny(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        revenue_view(),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:panel")]]
        ),
    )


@router.callback_query(F.data.startswith("adm:p:"))
async def product_cb(callback: CallbackQuery):
    if await _deny(callback):
        return
    await callback.answer()
    item = _find(callback.data.split(":")[2])
    await callback.message.edit_text(product_text(item), reply_markup=product_kb(item))


@router.callback_query(F.data.startswith("adm:l:"))
async def list_cb(callback: CallbackQuery):
    if await _deny(callback):
        return
    await callback.answer()
    text, markup = list_view(_find(callback.data.split(":")[2]))
    await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith("adm:a:"))
async def add_cb(callback: CallbackQuery):
    if await _deny(callback):
        return
    await callback.answer()
    item = _find(callback.data.split(":")[2])
    PENDING[callback.from_user.id] = ("add", item["product"])
    await callback.message.answer(f"{HINT}\n\nКому выдать доступ: «{item['title']}»?")


@router.callback_query(F.data.startswith("adm:d:"))
async def delete_cb(callback: CallbackQuery, bot: Bot):
    if await _deny(callback):
        return
    await callback.answer()
    _, _, product, raw_id = callback.data.split(":")
    item = _find(product)
    user_id = int(raw_id)
    db.delete_payment(user_id, product)
    note = f"Запись {user_id} удалена."
    if item["days"]:
        # Подписка: смысл удаления — закрыть доступ, поэтому исключаем из канала.
        try:
            await bot.ban_chat_member(item["chat_id"], user_id)
            await bot.unban_chat_member(item["chat_id"], user_id)
            note += " Из канала исключён."
        except Exception as e:
            note += f" Но исключить из канала не удалось: {e}"
    text, markup = list_view(item)
    await callback.message.edit_text(f"{note}\n\n{text}", reply_markup=markup)


@router.message(F.text)
async def add_input(message: Message, bot: Bot):
    # Ловит только то, что не разобрали роутеры выше (кнопки меню, /start, оплата).
    if await _deny(message):
        return
    pending = PENDING.pop(message.from_user.id, None)
    if not pending:
        return
    action, product = pending
    if action != "add":
        return
    text = message.text.strip().lstrip("@")
    if not text.isdigit():
        await message.answer(HINT)
        return

    user_id = int(text)
    item = _find(product)
    existing = db.get_payment(user_id, product)
    kick_date = None
    if item["days"]:
        kick_date, _ = db.extend_subscription(user_id, product, item["days"])
    db.save_payment(user_id, existing["user_name"] if existing else "", product, kick_date)

    if kick_date:
        note = f"Доступ выдан: {item['title']}\nID {user_id}, до {db.kick_date_text(kick_date.isoformat())}"
    else:
        note = f"Доступ выдан: {item['title']}\nID {user_id}, бессрочно"
    try:
        link = await bot.create_chat_invite_link(chat_id=item["chat_id"], member_limit=1, expire_date=None)
        note += f"\n\nСсылка (перешлите её человеку):\n{link.invite_link}"
    except Exception as e:
        note += f"\n\nСсылку создать не удалось: {e}"
    # shortcut: ссылка живёт до первого вступления и приходит админу, а не пользователю —
    # так работает и для тех, кто ни разу не писал боту. Если понадобится автоотправка, писать в личку.
    await message.answer(note, reply_markup=product_kb(item))

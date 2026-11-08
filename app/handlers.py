from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message, CallbackQuery
import app.keyboards as kb
from aiogram.filters import CommandStart
import TOKEN
import app.db as db
from app.products import PRODUCTS, TEST_MODE
from app.owners import is_owner
from datetime import datetime, timezone

router = Router()

Asoznanie = FSInputFile('Asoznanie.jpg')
Zapredelom = FSInputFile('Zapredelom.jpg')
Polubvi = FSInputFile('Polubvi.jpg')
Read = FSInputFile('New.jpg')

@router.message(CommandStart())
async def cmd_start(message: Message):
    if is_owner(message.from_user):
        db.remember_owner(message.from_user.username, message.from_user.id)
    await message.answer_photo(
        photo=Asoznanie,
        caption=(
            'Добро пожаловать в бот психолога '
            '<a href="https://t.me/asoznaniie">asoznanie</a>.\n\n'
            "Здесь вы можете познакомиться с моими проектами и приобрести к ним доступ 🤍\n\n"
            "Нажмите «подробнее», чтобы узнать больше о каждом из проектов.\n\n"
            "По всем вопросам пишите в поддержку: https://t.me/asoznaniee"
        ),
        parse_mode="HTML",
        reply_markup=kb.main(is_owner(message.from_user))
    )

@router.message(F.text == 'Подробнее: За пределом. Синдром хорошей девочки')
async def good_girl(message: Message):
    await message.answer_photo(
        photo=Zapredelom,
        caption=(
            "Проект «За пределом. Синдром хорошей девочки»\n\n"
            "Для женщин, которые хотят:\n\n"
            "• научиться выстраивать здоровые личные границы\n"
            "• избавиться от стремления соответствовать чужим ожиданиям\n"
            "• разобраться в причинах синдрома хорошести\n"
            "• перестать быть удобной для всех, кроме себя\n\n"
            "Цель проекта — помочь женщинам почувствовать внутреннюю опору и принять себя такими, какие есть.\n\n"
            "Все материалы в тг-канале.\n"
            "25 подкастов по теме и еще больше терапевтических практик.\n"
            "Доступ к материалам после единоразовой оплаты навсегда.\n\n"
            "Больше о проекте: asoznanie.ru/zapredelom\n\n"
            "Для оплаты жми на кнопку ⤵️"
        ),
        reply_markup=kb.good_girl
    )

@router.message(F.text == 'Подробнее: Программа по выходу из созависимости «Полюб(в)и»')
async def polubvi(message: Message):
    await message.answer_photo(
        photo=Polubvi,
        caption=(
            "Терапевтическая программа по выходу из созависимости «Полюб(в)и»\n\n"
            "Для тех, кто:\n\n"
            "• хочет улучшить качество своих отношений\n"
            "• хочет говорить «нет» без чувства вины\n"
            "• хочет противостоять манипуляциям\n"
            "• понять причины созависимости и сложностей в отношениях\n"
            "• хочет наладить контакт с собой, повысить самооценку и выйти из слияния с партнёром\n\n"
            "Структура программы:\n\n"
            "8 подробных лекций\n"
            "8 презентаций\n"
            "Практики\n"
            "Терапевтические письма с разбором ваших ситуаций\n\n"
            "Формат участия:\n\n"
            "Материалы в тг-канале после оплаты, доступ навсегда.\n\n"
            "Подробнее о программе: asoznanie.ru/polubvi\n\n"
            "Для оплаты жми на кнопку ⤵️"
        ),
        reply_markup=kb.polubvi
    )

def split_caption(text: str, limit: int = 1024) -> tuple[str, str]:
    """Telegram не принимает подпись к фото длиннее 1024 символов — остаток уходит отдельным сообщением."""
    if len(text) <= limit:
        return text, ""
    head = text[:limit].rsplit("\n\n", 1)[0]
    return head, text[len(head):].lstrip("\n")


@router.message(F.text == 'Подробнее: Психологический журнал a.soznanie')
async def liter_project(message: Message):
    caption_text = (
        "Психологический журнал a.soznanie\n\n"
        "Авторский проект о психологии, философии и человеческом опыте.\n\n"
        "Пространство, где мы будем разбираться в сложном, задавать неудобные вопросы и искать ответы за пределами привычных сценариев.\n\n"
        "Мне важно создать подробную проверенную базу по актуальным темам сегодняшнего дня, чтобы вы могли обращаться за помощью в удобное для вас время, в доступном формате.\n\n"
        "Что будет в канале:\n"
        "• мои авторские эссе\n"
        "• подкасты с разбором каждой темы\n"
        "• практики самопомощи\n"
        "• разборы фильмов\n"
        "• научные исследования (в том числе переведенные мной с английского)\n"
        "• книги\n\n"
        f"Стоимость участия — {db.money(PRODUCTS['read_payment']['price'])} в месяц. Никакого автопродления подписки. Бот напоминает о продлении за несколько дней до окончания.\n\n"
        "Важно: после оплаты подписки вы получаете доступ ко всем новым материалам проекта. Старые материалы до оформления подписки не видны.\n\n"
        "Посты выходят 2-3 раза в неделю. Вы можете обращаться к ним в любое время, пока ваша подписка активна."
    )
    if db.has_active_subscription(message.from_user.id, "read"):
        caption_text += (
            "\n\nПри повторной оплате подписка продлевается на месяц — "
            "дни до окончания не сгорают."
        )
    head, tail = split_caption(caption_text)
    await message.answer_photo(
        photo=Read,
        caption=head,
        reply_markup=None if tail else kb.read
    )
    if tail:
        await message.answer(tail, reply_markup=kb.read)

@router.message(F.text == 'Обратиться в поддержку')
async def help(message: Message):
    await message.answer(
        'Узнать подробнее или задать вопрос можно здесь: https://t.me/asoznaniee'
    )

async def _edit_caption(message: Message, text: str, markup) -> None:
    """Меняет текст под кнопкой: у фото это подпись, у обычного сообщения — сам текст.

    Нужно потому, что длинное описание журнала уходит вторым, текстовым сообщением.
    """
    if message.caption is not None:
        await message.edit_caption(caption=text, reply_markup=markup)
    else:
        await message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == "good_girl")
async def good_girl1(callback: CallbackQuery):
    await callback.answer()
    await _edit_caption(callback.message, "Нажми для оплаты:", kb.good_girl1)

@router.callback_query(F.data == "polubvi")
async def polubvi_callback(callback: CallbackQuery):
    await callback.answer()
    await _edit_caption(callback.message, "Нажми для оплаты:", kb.polubvi1)

@router.callback_query(F.data == "read")
async def read_callback(callback: CallbackQuery):
    await callback.answer()
    await _edit_caption(callback.message, "Нажми для оплаты:", kb.read1)

async def send_invoice(callback: CallbackQuery, payload: str, bot: Bot):
    item = PRODUCTS[payload]
    payment = db.get_payment(callback.from_user.id, item["product"])

    # Бессрочный доступ второй раз не продаём; подписку можно продлить в любой момент.
    if payment and not item["days"]:
        await callback.answer(text="Доступ уже оплачен.", show_alert=True)
        return

    if TEST_MODE:
        await callback.answer()
        print(f"[TEST] доступ выдан без оплаты: {callback.from_user.id} ({item['product']})")
        await grant_access(bot, callback.from_user, item, callback.message.answer)
        return

    description = item["description"]
    if payment and payment["kick_date"]:
        description = (
            f"Продление подписки. Сейчас доступ действует до {db.kick_date_text(payment['kick_date'])}."
        )

    try:
        await callback.message.answer_invoice(
            title=item["title"],
            description=description,
            provider_token=TOKEN.PAY_TOKEN,
            currency="RUB",
            prices=[LabeledPrice(label=item["label"], amount=item["price"])],
            payload=payload
        )
    except TelegramBadRequest as e:
        # Например, сумма ниже минимума Telegram для рубля (~88 ₽): CURRENCY_TOTAL_AMOUNT_INVALID.
        print(f"Не удалось выставить счёт {item['product']} на {item['price']} коп.: {e}")
        await callback.answer(
            "Не удалось выставить счёт. Напишите мне: @asoznaniee", show_alert=True
        )


def access_text(item: dict, invite_link: str) -> str:
    text = (
        "Оплата прошла, спасибо!\n\n"
        "Вот ваша ссылка на закрытый канал:\n\n"
        f"{invite_link}\n\n"
        "Перейдите по ней и нажмите «Вступить». "
        "Если ссылка вдруг не сработает — напишите мне: @asoznaniee"
    )
    if item["days"]:
        text += "\n\nЗа пару дней до окончания подписки бот напомнит о продлении."
    return text


def _access_line(item: dict, row) -> str:
    price = db.money(item["price"])
    until = f"до {db.kick_date_text(row['kick_date'])}" if row["kick_date"] else "бессрочно"
    return f"• {item['short']} — {price}, {until}"


async def notify_owners(bot: Bot, user, item: dict) -> None:
    """Пишет админам из owners.txt, кто и что купил (кто именно -- только те, кто уже заходил в бота)."""
    by_product = {entry["product"]: entry for entry in PRODUCTS.values()}
    access = "\n".join(
        _access_line(by_product[row["product"]], row)
        for row in db.user_payments(user.id)
        if row["product"] in by_product
    ) or "Других проектов нет."
    payment = db.get_payment(user.id, item["product"])
    until = f"до {db.kick_date_text(payment['kick_date'])}" if payment and payment["kick_date"] else "бессрочно"
    text = (
        "Новая оплата\n\n"
        f"{user.full_name or 'Без имени'} "
        f"({('@' + user.username) if user.username else 'без юзернейма'})\n"
        f"ID: {user.id}\n"
        f"Проект: {item['title']}\n"
        f"Сумма: {db.money(item['price'])}\n"
        f"Доступ: {until}\n"
        f"Когда: {db.kick_date_text(datetime.now(timezone.utc).isoformat())}\n\n"
        "Все доступы пользователя:\n"
        f"{access}"
    )
    for owner_id in db.owner_ids():
        try:
            await bot.send_message(owner_id, text)
        except Exception as e:
            print(f"Не удалось уведомить админа {owner_id}: {e}")


async def grant_access(bot: Bot, user, item: dict, send):
    """Записывает оплату и присылает ссылку. Общая точка для реальной и тестовой оплаты."""
    if item["days"]:
        kick_date, was_active = db.extend_subscription(user.id, item["product"], item["days"])
        db.save_payment(user.id, user.full_name, item["product"], kick_date)
        if was_active:
            await send(
                "Оплата прошла, спасибо!\n\n"
                f"Подписка продлена до {db.kick_date_text(kick_date.isoformat())}.\n\n"
                "За пару дней до окончания подписки бот напомнит о продлении."
            )
            return
    else:
        db.save_payment(user.id, user.full_name, item["product"], None)

    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=item["chat_id"],
            member_limit=1,
            expire_date=None
        )
    except Exception as e:
        # Доступ уже записан в БД, поэтому повторная оплата не нужна.
        print(f"Ошибка создания ссылки для {user.id} ({item['product']}): {e}")
        await send(
            "Оплата прошла, спасибо! Но ссылку не удалось создать. Напишите мне: @asoznaniee"
        )
        return

    await send(access_text(item, invite_link.invite_link))


@router.callback_query(F.data == "good_girl1")
async def good_girl_payment(callback: CallbackQuery, bot: Bot):
    await send_invoice(callback, "good_girl_payment", bot)

@router.callback_query(F.data == "polubvi1")
async def polubvi_payment(callback: CallbackQuery, bot: Bot):
    await send_invoice(callback, "polubvi_payment", bot)

@router.callback_query(F.data == "read1")
async def read_payment(callback: CallbackQuery, bot: Bot):
    await send_invoice(callback, "read_payment", bot)

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    item = PRODUCTS.get(pre_checkout_q.invoice_payload)
    ok = (
        item is not None
        and pre_checkout_q.total_amount == item["price"]
        and pre_checkout_q.currency == "RUB"
    )
    await bot.answer_pre_checkout_query(
        pre_checkout_q.id,
        ok=ok,
        error_message=None if ok else "Не удалось проверить платёж. Напишите мне: @asoznaniee",
    )

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    user = message.from_user
    payment = message.successful_payment
    item = PRODUCTS.get(payment.invoice_payload)

    if item is None:
        await message.answer("Оплата прошла, но не удалось определить назначение платежа.")
        return

    if payment.total_amount != item["price"] or payment.currency != "RUB":
        await message.answer(
            "Оплата прошла, но сумма не совпадает с ожидаемой. Напишите мне: @asoznaniee"
        )
        return

    await grant_access(bot, user, item, message.answer)
    try:
        db.record_purchase(user.id, item["product"], payment.total_amount)
        await notify_owners(bot, user, item)
    except Exception as e:
        # Доступ человек уже получил — сбой учёта/уведомления не должен ломать оплату.
        print(f"Не удалось учесть оплату или уведомить админов: {e}")

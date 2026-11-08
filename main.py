import asyncio
import traceback
import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from app.handlers import router
from app.admin import router as admin_router
import app.db as db
from app.products import PRODUCTS
from datetime import datetime, timezone

bot = Bot(token=TOKEN.TOKEN)

READ_CHAT_ID = PRODUCTS["read_payment"]["chat_id"]


async def notify_owners_error(error: BaseException):
    """Сообщает админам, с какой ошибкой упал бот. Нужен новый Bot: старый уже закрыт."""
    text = "Бот остановился из-за ошибки:\n\n" + "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    ).strip()
    if len(text) > 4000:  # лимит Telegram, хвост трейсбека важнее середины
        text = text[:800] + "\n...\n" + text[-3100:]
    notifier = Bot(token=TOKEN.TOKEN)
    try:
        for owner_id in db.owner_ids():
            try:
                await notifier.send_message(owner_id, text)
            except Exception as e:
                print(f"Не удалось уведомить админа {owner_id}: {e}")
    finally:
        await notifier.session.close()

async def send_renewal_reminders(now: datetime):
    for user in db.subscriptions_to_remind("read", now):
        try:
            await bot.send_message(
                user["user_id"],
                f"Подписка на «{PRODUCTS['read_payment']['title']}» заканчивается "
                f"{db.kick_date_text(user['kick_date'])}.\n\n"
                "Чтобы продлить — отправьте /start и выберите проект.",
            )
        except Exception as e:
            # Пользователь заблокировал бота: напоминание повторять бессмысленно.
            print(f"Не удалось напомнить о продлении {user['user_id']}: {e}")
        db.mark_reminded(user["user_id"], "read")

async def check_subscriptions():
    while True:
        try:
            await check_subscriptions_once()
        except Exception as e:
            # Одна сломанная итерация не должна убивать фоновую задачу навсегда.
            print(f"Ошибка в проверке подписок: {e}")
        await asyncio.sleep(60)


async def check_subscriptions_once():
    now = datetime.now(timezone.utc)
    await send_renewal_reminders(now)
    for user in db.expired_subscriptions("read", now):
        user_id = user["user_id"]
        user_name = user["user_name"] or "Пользователь"
        try:
            await bot.ban_chat_member(chat_id=READ_CHAT_ID, user_id=user_id)
            await bot.unban_chat_member(chat_id=READ_CHAT_ID, user_id=user_id)
            db.delete_payment(user_id, "read")
            print(f"Подписка {user_name} (id: {user_id}) истекла {user['kick_date']}, пользователь исключён")
            try:
                await bot.send_message(
                    user_id,
                    f"Подписка на «{PRODUCTS['read_payment']['title']}» закончилась, "
                    "доступ к каналу закрыт.\n\n"
                    "Если хотите вернуться — отправьте /start и выберите журнал.",
                )
            except Exception as e:
                # Пользователь заблокировал бота: доступ уже закрыт, сообщение не доставить.
                print(f"Не удалось сообщить об окончании подписки {user_id}: {e}")
        except TelegramBadRequest as e:
            # Пользователь не найден/не в канале: повтор не поможет, снимаем запись.
            db.delete_payment(user_id, "read")
            print(f"Не удалось исключить {user_name} (id: {user_id}), запись удалена: {e}")
        except Exception as e:
            # Запись не удаляем: попробуем ещё раз на следующей итерации.
            print(f"Ошибка при исключении {user_name} (id: {user_id}): {e}")

async def main():
    db.init_db()
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(admin_router)

    asyncio.create_task(check_subscriptions())

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен.')
    except Exception as e:
        # Сначала уведомляем админов, только потом завершаем работу.
        traceback.print_exc()
        print("Отправляю ошибку админам...")
        try:
            asyncio.run(notify_owners_error(e))
        except Exception as nested:
            print(f"Не удалось отправить уведомление: {nested}")
        raise SystemExit(1)

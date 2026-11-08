import os


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Не задана переменная окружения {name}. Пример — в .env.example"
        )
    return value


TOKEN = _required("BOT_TOKEN")
PAY_TOKEN = _required("PAYMENT_TOKEN")

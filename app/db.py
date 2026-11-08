"""Хранилище оплат в SQLite. Одна таблица: (user_id, product) -> доступ."""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("BOT_DB", BASE_DIR / "bot.db"))
PAYMENTS_DIR = BASE_DIR / "payments"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS payments (
    user_id    INTEGER NOT NULL,
    product    TEXT    NOT NULL,
    user_name  TEXT    NOT NULL DEFAULT '',
    kick_date  TEXT,              -- ISO UTC, NULL = доступ бессрочный
    created_at TEXT    NOT NULL,
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, product)
);

-- Все успешные оплаты (для выручки): продления добавляют строку, а не перезаписывают её.
CREATE TABLE IF NOT EXISTS purchases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product    TEXT    NOT NULL,
    amount     INTEGER NOT NULL,  -- копейки
    created_at TEXT    NOT NULL
);

-- id админов из owners.txt, чтобы им можно было прислать уведомление.
CREATE TABLE IF NOT EXISTS owners (
    user_id  INTEGER PRIMARY KEY,
    username TEXT NOT NULL
);
"""

# Файлы старого формата, которые переносим в БД один раз при первом запуске.
_LEGACY_JSON = {
    "good_girl": "good_girl_users.json",
    "polubvi": "polubvi_users.json",
    "read": "read_users.json",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    # shortcut: sqlite3 синхронный, но запросы здесь микросекундные — на таком
    # объёме блокировка event loop незаметна. Перейти на aiosqlite, если появится нагрузка.
    with closing(_connect()) as conn, conn:
        return conn.execute(sql, params).fetchall()


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.executescript(_SCHEMA)
        # БД с прошлой версии схемы: добавляем колонку напоминаний.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(payments)")}
        if "reminder_sent" not in columns:
            conn.execute("ALTER TABLE payments ADD COLUMN reminder_sent INTEGER NOT NULL DEFAULT 0")
    _migrate_legacy_json()
    _backfill_purchases()


def _backfill_purchases() -> None:
    """Один раз переносит текущие записи в таблицу оплат, чтобы выручка не начиналась с нуля."""
    if _query("SELECT 1 FROM purchases LIMIT 1"):
        return
    from app.products import PRODUCTS

    prices = {item["product"]: item["price"] for item in PRODUCTS.values()}
    rows = _query("SELECT user_id, product, created_at FROM payments")
    for row in rows:
        if row["product"] in prices:
            _query(
                "INSERT INTO purchases (user_id, product, amount, created_at) VALUES (?, ?, ?, ?)",
                (row["user_id"], row["product"], prices[row["product"]], row["created_at"]),
            )
    if rows:
        print(f"Выручка: перенесено {len(rows)} старых оплат")


def _migrate_legacy_json() -> None:
    """Импортирует старые payments/*.json в БД и переименовывает их, чтобы не импортировать повторно."""
    for product, filename in _LEGACY_JSON.items():
        path = PAYMENTS_DIR / filename
        if not path.exists():
            continue
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Не удалось перенести {path}: {exc}")
            continue

        for entry in entries:
            user_id = entry.get("user_id")
            if not user_id:
                continue
            kick_date = _parse_legacy_date(entry.get("kick_date"))
            save_payment(user_id, entry.get("user_name") or "", product, kick_date)

        path.rename(path.with_suffix(".json.migrated"))
        print(f"Перенесено в БД: {len(entries)} записей из {path.name}")


def _parse_legacy_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Старый код писал локальное время, а сравнивал его с UTC — считаем старые даты UTC.
        return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"Неверный формат даты в старых данных: {value}")
        return None


def get_payment(user_id: int, product: str) -> sqlite3.Row | None:
    rows = _query(
        "SELECT user_id, product, user_name, kick_date, reminder_sent FROM payments WHERE user_id = ? AND product = ?",
        (user_id, product),
    )
    return rows[0] if rows else None


def save_payment(
    user_id: int,
    user_name: str,
    product: str,
    kick_date: datetime | None = None,
) -> None:
    _query(
        """
        INSERT INTO payments (user_id, product, user_name, kick_date, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, product) DO UPDATE SET
            user_name = excluded.user_name,
            kick_date = excluded.kick_date,
            reminder_sent = 0
        """,
        (
            user_id,
            product,
            user_name,
            kick_date.astimezone(timezone.utc).isoformat() if kick_date else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def extend_subscription(
    user_id: int,
    product: str,
    days: int,
    now: datetime | None = None,
) -> tuple[datetime, bool]:
    """Считает новый срок подписки. Продление прибавляется к текущей дате окончания.

    Возвращает (новая дата окончания, была ли подписка активна).
    """
    now = now or datetime.now(timezone.utc)
    row = get_payment(user_id, product)
    base, was_active = now, False
    if row and row["kick_date"]:
        current = datetime.fromisoformat(row["kick_date"])
        if current > now:
            base, was_active = current, True
    return base + timedelta(days=days), was_active


def delete_payment(user_id: int, product: str) -> None:
    _query("DELETE FROM payments WHERE user_id = ? AND product = ?", (user_id, product))


def payment_stats(product: str, now: datetime | None = None) -> tuple[int, int]:
    """(всего записей, действующих сейчас)."""
    now = now or datetime.now(timezone.utc)
    rows = _query("SELECT kick_date FROM payments WHERE product = ?", (product,))
    active = sum(1 for row in rows if row["kick_date"] and datetime.fromisoformat(row["kick_date"]) > now)
    return len(rows), active


def list_payments(product: str, limit: int = 20) -> list[sqlite3.Row]:
    return _query(
        "SELECT user_id, user_name, kick_date FROM payments WHERE product = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (product, limit),
    )


def expired_subscriptions(product: str, now: datetime) -> list[sqlite3.Row]:
    """Записи с истёкшей подпиской. Истёкшие удаляются только после успешного кика."""
    rows = _query(
        "SELECT user_id, product, user_name, kick_date FROM payments WHERE product = ? AND kick_date IS NOT NULL",
        (product,),
    )
    return [row for row in rows if datetime.fromisoformat(row["kick_date"]) <= now]


MSK = timezone(timedelta(hours=3))  # Москва без перехода на летнее время


def kick_date_text(kick_date: str | None) -> str:
    """Дата окончания подписки в виде, понятном пользователю (московское время)."""
    if not kick_date:
        return "бессрочно"
    return datetime.fromisoformat(kick_date).astimezone(MSK).strftime("%d.%m.%Y %H:%M МСК")


def money(kopecks: int) -> str:
    """Копейки -> '2 500 ₽'."""
    return f"{kopecks // 100:,}".replace(",", " ") + " ₽"


def has_active_subscription(user_id: int, product: str, now: datetime | None = None) -> bool:
    row = get_payment(user_id, product)
    if not row or not row["kick_date"]:
        return False
    return datetime.fromisoformat(row["kick_date"]) > (now or datetime.now(timezone.utc))


def subscriptions_to_remind(
    product: str,
    now: datetime,
    within: timedelta = timedelta(days=2),
) -> list[sqlite3.Row]:
    """Активные подписки, до конца которых осталось меньше `within`, без отправленного напоминания."""
    rows = _query(
        "SELECT user_id, product, user_name, kick_date FROM payments "
        "WHERE product = ? AND kick_date IS NOT NULL AND reminder_sent = 0",
        (product,),
    )
    return [row for row in rows if now < datetime.fromisoformat(row["kick_date"]) <= now + within]


def mark_reminded(user_id: int, product: str) -> None:
    _query(
        "UPDATE payments SET reminder_sent = 1 WHERE user_id = ? AND product = ?",
        (user_id, product),
    )


def record_purchase(user_id: int, product: str, amount: int) -> None:
    """Журнал успешных оплат. Пишется только за реальные платежи, ручная выдача доступа не считается."""
    _query(
        "INSERT INTO purchases (user_id, product, amount, created_at) VALUES (?, ?, ?, ?)",
        (user_id, product, amount, datetime.now(timezone.utc).isoformat()),
    )


def revenue_by_product() -> dict[str, tuple[int, int]]:
    """product -> (количество оплат, сумма в копейках)."""
    rows = _query("SELECT product, COUNT(*) AS count, SUM(amount) AS total FROM purchases GROUP BY product")
    return {row["product"]: (row["count"], row["total"]) for row in rows}


def user_payments(user_id: int) -> list[sqlite3.Row]:
    """Все доступы пользователя: product, kick_date, created_at."""
    return _query(
        "SELECT product, kick_date, created_at FROM payments WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    )


def remember_owner(username: str | None, user_id: int) -> None:
    """Запоминает id админа из owners.txt, чтобы присылать ему уведомления об оплатах."""
    if username:
        _query("INSERT OR REPLACE INTO owners (user_id, username) VALUES (?, ?)", (user_id, username.lower()))


def owner_ids() -> list[int]:
    """ID админов, которые есть в owners.txt и хоть раз заходили в бота."""
    from app.owners import owners

    names = owners()
    if not names:
        return []
    return [row["user_id"] for row in _query("SELECT user_id, username FROM owners") if row["username"] in names]

from pathlib import Path

OWNERS_FILE = Path(__file__).resolve().parent.parent / "owners.txt"


def owners() -> set[str]:
    """Юзернеймы администраторов из owners.txt (без @, регистр не важен)."""
    if not OWNERS_FILE.exists():
        return set()
    names = set()
    for line in OWNERS_FILE.read_text(encoding="utf-8").splitlines():
        name = line.strip().lstrip("@").lower()
        if name and not name.startswith("#"):
            names.add(name)
    return names


def is_owner(user) -> bool:
    # Файл читается на каждый вызов, чтобы можно было править список без перезапуска бота.
    return bool(user and user.username and user.username.lower() in owners())

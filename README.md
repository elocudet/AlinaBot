# Установка бота на Ubuntu-сервер

Пошагово: от пустого сервера до работающего бота с автозапуском.

---

## Что в папке

| Файл | Зачем |
|---|---|
| `main.py` | точка входа |
| `app/` | код: обработчики, клавиатуры, база, товары, админка |
| `TOKEN.py` | читает токены из переменных окружения |
| `.env.example` | образец файла с токенами (сам `.env` в Git не попадает) |
| `owners.txt` | юзернеймы админов (по одному в строке) |
| `bot.db` | база: подписчики, оплаты, выручка. **Уже с текущими клиентами** |
| `*.jpg` | картинки проектов. Лежат рядом с `main.py`, переименовывать нельзя |
| `requirements.txt` | зависимости (aiogram) |
| `zakaz.service` | автозапуск через systemd |
| `backup.sh` | ежедневная копия базы |

`start.bat` и `nohup.out` сюда не входят — они не нужны на Linux.

---

## 1. Подготовка сервера

Нужен Ubuntu 22.04 или новее, Python **3.10+** (в 22.04 как раз 3.10).

```bash
ssh root@ВАШ_IP

apt update
apt install -y python3 python3-venv python3-pip
python3 --version        # должно быть 3.10 или выше

mkdir -p /root/Zakaz
```

## 2. Загрузить файлы

С Windows (PowerShell), из папки, где лежит `Deploy`:

```powershell
scp -r "C:\Users\elise\Desktop\Deploy\*" root@ВАШ_IP:/root/Zakaz/
```

Можно и через WinSCP — просто перетащить содержимое `Deploy` в `/root/Zakaz`.

Проверка на сервере:

```bash
cd /root/Zakaz && ls
# app  Asoznanie.jpg  backup.sh  bot.db  main.py  New.jpg
# owners.txt  Polubvi.jpg  requirements.txt  TOKEN.py  zakaz.service  Zapredelom.jpg
```

Файлы `.env` и `bot.db` в Git не лежат: первый содержит ключи, вторая — данные клиентов. Их создаём на сервере вручную (разделы 4 и 7).

## 3. Установить зависимости

```bash
cd /root/Zakaz
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 4. Проверить настройки

**Токены — через переменные окружения.** Создайте файл `/root/Zakaz/.env` по образцу `.env.example`:

```bash
cp /root/Zakaz/.env.example /root/Zakaz/.env
nano /root/Zakaz/.env
```

```ini
BOT_TOKEN=токен_бота_от_BotFather
PAYMENT_TOKEN=токен_платёжного_провайдера
```

`systemd` подхватывает этот файл сам (строка `EnvironmentFile=` в `zakaz.service`). При ручном запуске без systemd токены нужно задать в оболочке:

```bash
export BOT_TOKEN=... PAYMENT_TOKEN=...
.venv/bin/python main.py
```

Файл `.env` в Git не попадает — ключи в репозиторий не коммитим.

**`owners.txt`** — юзернеймы админов, у кого будет кнопка «Панель управления» и кто получает уведомления о покупках:

```bash
nano /root/Zakaz/owners.txt
```
Пишется без `@`, по одному в строке, регистр не важен. Сейчас там `elocudet`.

**`app/products.py`** — цены и режим оплаты:

```bash
nano /root/Zakaz/app/products.py
```
`TEST_MODE = False` — бот берёт настоящие деньги. `True` — выдаёт доступ без оплаты (для проверок). Сейчас стоит `False`.

**Права бота в каналах.** Бот должен быть администратором в каждом закрытом канале с правами:
- «Приглашать пользователей» — чтобы создавать ссылки на вход;
- «Блокировать участников» — чтобы исключать по окончании подписки.

## 5. Первый запуск вручную

```bash
cd /root/Zakaz
.venv/bin/python main.py
```

Откройте бота в Telegram, нажмите `/start`. Появился ответ с картинкой — всё работает. Остановите `Ctrl+C`.

Если в консоли ошибка — смотрите раздел «Если что-то не работает» в конце.

## 6. Автозапуск (systemd)

```bash
cp /root/Zakaz/zakaz.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now zakaz
systemctl status zakaz --no-pager
```

Должно быть `active (running)`. Бот сам поднимется после перезагрузки сервера и после падения.

Полезные команды:

```bash
systemctl restart zakaz     # перезапустить (после правок кода)
systemctl stop zakaz        # остановить
journalctl -u zakaz -f      # смотреть, что происходит, в реальном времени
journalctl -u zakaz -n 100  # последние 100 строк лога
```

## 7. Бэкап базы

Вся база — один файл `bot.db`. Включите ежедневную копию:

```bash
chmod +x /root/Zakaz/backup.sh
crontab -e
```

Добавьте строку (копия каждый день в 3:00, хранятся 14 последних):

```
0 3 * * * /root/Zakaz/backup.sh >> /root/Zakaz/backups.log 2>&1
```

Копии кладутся в `/root/Zakaz/backups/`. Забрать к себе:

```powershell
scp root@ВАШ_IP:/root/Zakaz/backups/bot-2026-11-01.db .
```

Восстановление:

```bash
systemctl stop zakaz
cp /root/Zakaz/backups/bot-2026-11-01.db /root/Zakaz/bot.db
systemctl start zakaz
```

---

## Обновление кода

```powershell
# с Windows: только код, без базы
scp -r "C:\Users\elise\Desktop\Deploy\app" root@ВАШ_IP:/root/Zakaz/
scp "C:\Users\elise\Desktop\Deploy\main.py" root@ВАШ_IP:/root/Zakaz/
```

```bash
systemctl restart zakaz
```

**Не копируйте `bot.db` при обновлении** — затрёте базу на сервере свежей локальной копией и потеряете новые оплаты.

Если менялся `requirements.txt`:

```bash
cd /root/Zakaz && .venv/bin/pip install -r requirements.txt
systemctl restart zakaz
```

---

## Как это работает

- **Бессрочные проекты** («За пределом», «Полюб(в)и») — после оплаты человек получает одноразовую ссылку в канал, повторно купить не даст.
- **Журнал** — подписка на 30 дней. За 2 дня бот напоминает, в день окончания исключает из канала и пишет об этом. При повторной оплате дни не сгорают: новый срок прибавляется к текущему.
- **Панель управления** (у админов из `owners.txt`): добавить/удалить человека, продлить подписку, посмотреть выручку.
- **Уведомления о покупках** приходят админам в личку. Чтобы они заработали, админ должен хотя бы раз написать боту `/start` — по юзернейму Telegram не даёт узнать ID, бот запоминает его при первом обращении.
- Время в базе хранится в UTC, а показывается пользователю в московском (МСК) — от часового пояса сервера ничего не зависит.

---

## Если что-то не работает

**`Conflict: terminated by other getUpdates request`**
Бот уже запущен где-то ещё — на Windows или второй копией на сервере. Остановите лишнюю: на Windows закройте окно `start.bat`, на сервере `systemctl stop zakaz`.

**`Bad Request: chat not found` или `not enough rights to create chat invite link`**
Бот не админ в канале, либо неверный `chat_id` в `app/products.py`. Добавьте бота админом канала с правом приглашать и блокировать.

**Кнопка «Оплатить» молчит или пишет «Не удалось выставить счёт»**
Telegram отклонил счёт. В логе будет причина. Частые: `CURRENCY_TOTAL_AMOUNT_INVALID` (сумма ниже ~88 ₽ — сейчас минимальная цена 620 ₽, так что не про нас), отключённый у провайдера приём платежей, неверный `PAYMENT_TOKEN`.

**`[TEST] доступ выдан без оплаты` в логе**
В `app/products.py` стоит `TEST_MODE = True`. Поменяйте на `False` и перезапустите.

**Бот не отвечает вообще**
```bash
systemctl status zakaz --no-pager
journalctl -u zakaz -n 50
```
Если `status` показывает `failed` — в логе будет трейсбек. Обычно это неверный токен в `.env` или нет файла-картинки.

**Не приходят уведомления о покупках**
Админ из `owners.txt` ни разу не написал боту `/start`, либо в файле опечатка в юзернейме.

**Хочу начать с чистой базы**
```bash
systemctl stop zakaz
rm /root/Zakaz/bot.db
systemctl start zakaz
```
Бот создаст пустую базу сам. **Все подписчики и история оплат пропадут.**

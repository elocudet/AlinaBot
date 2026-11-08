#!/bin/bash
# Ежедневная копия базы бота. Ставится в cron, вручную запускать не обязательно.
#   0 3 * * * /root/Zakaz/backup.sh >> /root/Zakaz/backups.log 2>&1
set -e
cd "$(dirname "$0")"

mkdir -p backups
.venv/bin/python -c "import sqlite3; s=sqlite3.connect('bot.db'); d=sqlite3.connect('backups/bot-$(date +%F).db'); s.backup(d); d.close(); s.close()"

# Держим 14 последних копий, остальные удаляем
ls -1t backups/bot-*.db | tail -n +15 | xargs -r rm --

echo "$(date '+%F %T') backup ok: backups/bot-$(date +%F).db"

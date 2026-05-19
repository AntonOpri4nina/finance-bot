#!/bin/bash
# ────────────────────────────────────────────────────────────
#  Скрипт деплоя Finance Bot на Ubuntu 24.04 (AEZA VPS)
#  Запускать от root: bash deploy.sh
# ────────────────────────────────────────────────────────────

set -e  # Остановить скрипт при любой ошибке

BOT_DIR="/opt/finance-bot"
BOT_USER="botuser"
SERVICE_NAME="finance-bot"

echo "=== [1/7] Обновляем систему ==="
apt update && apt upgrade -y

echo "=== [2/7] Устанавливаем Python 3.11 и зависимости ==="
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git

echo "=== [3/7] Создаём системного пользователя для бота ==="
id -u $BOT_USER &>/dev/null || useradd -r -s /bin/false -d $BOT_DIR $BOT_USER

echo "=== [4/7] Создаём рабочую директорию ==="
mkdir -p $BOT_DIR/images
cp -r . $BOT_DIR/
chown -R $BOT_USER:$BOT_USER $BOT_DIR

echo "=== [5/7] Создаём виртуальное окружение и ставим зависимости ==="
cd $BOT_DIR
python3.11 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "=== [6/7] Копируем systemd-сервис ==="
cp finance-bot.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo ""
echo "=== [7/7] ГОТОВО! ==="
echo ""
echo "Следующие шаги:"
echo "  1. Создайте файл .env:"
echo "     cp $BOT_DIR/.env.example $BOT_DIR/.env"
echo "     nano $BOT_DIR/.env"
echo ""
echo "  2. Запустите бота:"
echo "     systemctl start $SERVICE_NAME"
echo ""
echo "  3. Проверьте статус:"
echo "     systemctl status $SERVICE_NAME"
echo ""
echo "  4. Смотреть логи в реальном времени:"
echo "     journalctl -u $SERVICE_NAME -f"

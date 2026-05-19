#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Finance Bot - Автоматическое развертывание на Ubuntu    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Проверка прав администратора
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Этот скрипт должен быть запущен от суперпользователя (sudo)${NC}"
   exit 1
fi

# Обновление системы
echo -e "${YELLOW}📦 Шаг 1/6: Обновление системы...${NC}"
apt update
apt install -y curl wget git build-essential libssl-dev libffi-dev python3-dev

# Установка Python 3.11
echo -e "${YELLOW}🐍 Шаг 2/6: Установка Python 3.11...${NC}"
apt install -y python3.11 python3.11-venv python3-pip

# Проверка Python
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11 не установлен${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3.11 установлен${NC}"

# Создание пользователя для бота
echo -e "${YELLOW}👤 Шаг 3/6: Создание пользователя finance-bot...${NC}"
if id "finance-bot" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Пользователь finance-bot уже существует${NC}"
else
    useradd -m -s /bin/bash -d /home/finance-bot finance-bot
    echo -e "${GREEN}✅ Пользователь finance-bot создан${NC}"
fi

# Клонирование репозитория
echo -e "${YELLOW}📥 Шаг 4/6: Клонирование репозитория...${NC}"
cd /home/finance-bot
if [ -d "finance-bot" ]; then
    cd finance-bot
    git pull
    echo -e "${GREEN}✅ Репозиторий обновлен${NC}"
else
    git clone https://github.com/AntonOpri4nina/finance-bot.git
    cd finance-bot
    echo -e "${GREEN}✅ Репозиторий клонирован${NC}"
fi

# Установка зависимостей
echo -e "${YELLOW}📚 Шаг 5/6: Установка зависимостей Python...${NC}"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo -e "${GREEN}✅ Зависимости установлены${NC}"

# Установка прав доступа
chown -R finance-bot:finance-bot /home/finance-bot
chmod +x /home/finance-bot/finance-bot/bot.py

# Настройка systemd сервиса
echo -e "${YELLOW}⚙️  Шаг 6/6: Настройка systemd сервиса...${NC}"
cp /home/finance-bot/finance-bot/finance-bot.service /etc/systemd/system/
systemctl daemon-reload

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               ✅ УСТАНОВКА ЗАВЕРШЕНА!                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}📝 НЕОБХОДИМЫЕ ДЕЙСТВИЯ:${NC}\n"

echo -e "${BLUE}1️⃣  Отредактируй файл конфигурации:${NC}"
echo -e "   ${GREEN}nano /home/finance-bot/finance-bot/.env${NC}\n"

echo -e "   Вставь свой API_TOKEN от @BotFather:\n"
echo -e "   ${GREEN}API_TOKEN=твой_токен_здесь${NC}\n"

echo -e "${BLUE}2️⃣  Сохрани файл (Ctrl+O, Enter, Ctrl+X)${NC}\n"

echo -e "${BLUE}3️⃣  Запусти бот:${NC}"
echo -e "   ${GREEN}sudo systemctl start finance-bot${NC}\n"

echo -e "${BLUE}4️⃣  Проверь статус:${NC}"
echo -e "   ${GREEN}sudo systemctl status finance-bot${NC}\n"

echo -e "${BLUE}5️⃣  Просмотри логи:${NC}"
echo -e "   ${GREEN}sudo journalctl -u finance-bot -f${NC}\n"

echo -e "${YELLOW}📋 ПОЛЕЗНЫЕ КОМАНДЫ:${NC}\n"
echo -e "   ${GREEN}sudo systemctl restart finance-bot${NC}  - Перезагрузить бот"
echo -e "   ${GREEN}sudo systemctl stop finance-bot${NC}     - Остановить бот"
echo -e "   ${GREEN}sudo systemctl enable finance-bot${NC}   - Включить автозапуск\n"

echo -e "${BLUE}📂 Директория бота:${NC}"
echo -e "   ${GREEN}/home/finance-bot/finance-bot/${NC}\n"

echo -e "${BLUE}📊 База данных:${NC}"
echo -e "   ${GREEN}/home/finance-bot/finance-bot/stats.db${NC}\n"

echo -e "${GREEN}🎉 Установка успешно завершена!${NC}\n"

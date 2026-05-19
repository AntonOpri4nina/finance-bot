# Finance Bot - Telegram бот для подбора финансовых предложений

Telegram-бот для подбора финансовых предложений (МФО, ПТС, недвижимость).

## 🚀 Развертывание на Ubuntu 24.04 (AEZA)

### Способ 1: Автоматическое развертывание (рекомендуется)

```bash
sudo bash deploy.sh
```

Скрипт автоматически:
- Обновит систему
- Установит Python 3.11
- Создаст пользователя бота
- Клонирует репозиторий
- Установит зависимости
- Настроит systemd сервис
- Создаст файл .env

### Способ 2: Ручное развертывание

#### 1. Подготовка сервера

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

#### 2. Создание пользователя

```bash
sudo useradd -r -s /bin/bash -d /home/finance-bot finance-bot
sudo mkdir -p /home/finance-bot
sudo chown finance-bot:finance-bot /home/finance-bot
```

#### 3. Клонирование репозитория

```bash
cd /home/finance-bot
sudo -u finance-bot git clone https://github.com/AntonOpri4nina/finance-bot.git
cd finance-bot
```

#### 4. Создание виртуального окружения

```bash
sudo -u finance-bot python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Конфигурация .env

```bash
cp .env.example .env
sudo nano .env
```

Заполните необходимые переменные:
```env
API_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
```

Получить токен: [@BotFather](https://t.me/BotFather)

#### 6. Установка systemd сервиса

```bash
sudo cp finance-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable finance-bot
```

#### 7. Запуск бота

```bash
sudo systemctl start finance-bot
```

## 📋 Управление ботом

### Основные команды

```bash
# Запустить бота
sudo systemctl start finance-bot

# Остановить бота
sudo systemctl stop finance-bot

# Перезагрузить бота (после изменения .env)
sudo systemctl restart finance-bot

# Проверить статус
sudo systemctl status finance-bot

# Смотреть логи в реальном времени
sudo journalctl -u finance-bot -f

# Смотреть последние 100 строк логов
sudo journalctl -u finance-bot -n 100

# Смотреть логи за последний час
sudo journalctl -u finance-bot --since="1 hour ago"
```

## 🔧 Структура проекта

```
finance-bot/
├── bot.py                 # Основной код бота (Polling режим)
├── db.py                  # Работа с БД SQLite
├── requirements.txt       # Python зависимости
├── .env.example          # Пример конфигурации
├── finance-bot.service   # Systemd сервис
├── deploy.sh             # Скрипт развертывания
├── README.md             # Этот файл
├── stats.db              # База данных (создается автоматически)
├── stats_log.csv         # Логи статистики
└── images/               # Папка для изображений
```

## 📊 Функциональность

- **Займы без залога** - МФО предложения до 150k
- **Займы под ПТС** - до 5млн с низкими ставками
- **Займы под н��движимость** - до 50млн
- **Статистика** - Отслеживание конверсий и пользователей
- **Напоминания** - Автоматические напоминания через 1, 3, 10 дней
- **Команды администратора** - /sourcestats, /userstats, /getstats, /getdb

## 🔐 Переменные окружения

Создайте файл `.env`:

```env
# Токен Telegram бота (обязательно!)
API_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
```

## 🛠️ Технология

- **Python 3.11+**
- **aiogram 3.14** - Telegram Bot API
- **SQLite** - База данных
- **asyncio** - Асинхронное программирование
- **python-dotenv** - Управление переменными окружения

## 📝 Логирование

Логи сохраняются через systemd journal:

```bash
# Все логи бота
sudo journalctl -u finance-bot

# Логи в реальном времени (с фильтром)
sudo journalctl -u finance-bot -f

# Экспорт логов в файл
sudo journalctl -u finance-bot > /tmp/bot_logs.txt
```

## 🚨 Решение проблем

### Бот не запускается

```bash
# Проверить статус
sudo systemctl status finance-bot

# Смотреть ошибки
sudo journalctl -u finance-bot -n 50
```

### Проблема: "ModuleNotFoundError"

```bash
# Переустановить зависимости
cd /home/finance-bot/finance-bot
source venv/bin/activate
pip install -r requirements.txt
```

### Проблема: "API_TOKEN не найден"

```bash
# Проверить .env файл
cat /home/finance-bot/finance-bot/.env

# Отредактировать
sudo nano /home/finance-bot/finance-bot/.env

# Перезагрузить бота
sudo systemctl restart finance-bot
```

### Бот зависает или не отвечает

```bash
# Перезагрузить
sudo systemctl restart finance-bot

# Или убить процесс и перезапустить
sudo systemctl kill finance-bot
sudo systemctl start finance-bot
```

## 📞 Контакты администратора

- ID: 1006600764, 130155491
- Команды: `/help`, `/sourcestats`, `/userstats ID`

## 📄 Лицензия

MIT

## 🔄 Обновление бота

```bash
cd /home/finance-bot/finance-bot
sudo -u finance-bot git pull origin main

# Если были изменения в requirements.txt
source venv/bin/activate
pip install -r requirements.txt

# Перезагрузить бота
sudo systemctl restart finance-bot
```

## ℹ️ Режим работы

Бот работает в режиме **Long Polling** (без вебхуков):
- ✅ Не требует белого IP
- ✅ Не требует SSL сертификата
- ✅ Более стабилен на обычных хостингах
- ✅ Простая конфигурация
- ✅ Идеален для AEZA и других приватных хостингов

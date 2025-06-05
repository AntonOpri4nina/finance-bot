# Finance Bot

Telegram-бот для подбора финансовых предложений.

## Быстрый старт

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/yourusername/finance-bot.git
   cd finance-bot
   ```
2. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```
3. Создайте файл `.env` на основе `.env.example` и укажите свои значения:
   ```
   API_TOKEN=ваш_токен_бота
   WEBHOOK_URL=https://your-app-name.onrender.com
   ```
4. Запустите бота локально:
   ```
   python bot.py
   ```

## Деплой на Render
- Добавьте переменные окружения API_TOKEN и WEBHOOK_URL в настройках Render.
- Убедитесь, что в render.yaml прописан healthCheckPath: `/webhook`.
- Для стабильной работы используйте мониторинг через UptimeRobot.

## Структура проекта
- `bot.py` — основной код бота
- `db.py` — работа с базой данных и напоминаниями
- `requirements.txt` — зависимости
- `render.yaml` — конфиг Render
- `images/` — изображения для сообщений (если используются)

## Лицензия
MIT 
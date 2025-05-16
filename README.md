# Finance Telegram Bot

## Запуск локально

1. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```

2. Создайте файл `.env` и добавьте ваш токен:
   ```
   API_TOKEN=ваш_токен_бота
   ```

3. Запустите бота:
   ```
   python bot.py
   ```

## Деплой на Render

1. Создайте аккаунт на [Render](https://render.com).
2. Создайте новый Web Service, выбрав ваш репозиторий.
3. Укажите команду запуска: `python bot.py`.
4. Добавьте переменную окружения `API_TOKEN` со значением вашего токена.
5. Нажмите "Create Web Service".

## Зависимости

- aiogram
- python-dotenv
- pytz 
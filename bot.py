import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from dotenv import load_dotenv
import os
import asyncio
import aiohttp
from datetime import datetime

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv('API_TOKEN')

if not API_TOKEN:
    logger.error("API_TOKEN не найден в .env файле!")
    exit(1)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # задаём в Render переменную окружения WEBHOOK_URL

logger.info("Starting bot initialization...")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Флаг для отслеживания состояния бота
bot_is_running = False

async def check_webhook_health():
    """Проверяет состояние вебхука и переустанавливает его при необходимости"""
    global bot_is_running
    while True:
        try:
            if not bot_is_running:
                logger.warning("Бот не работает, пытаемся перезапустить...")
                await setup_webhook()
            else:
                # Проверяем состояние вебхука
                webhook_info = await bot.get_webhook_info()
                if not webhook_info.url or webhook_info.url != WEBHOOK_URL + WEBHOOK_PATH:
                    logger.warning(f"Вебхук не установлен или неверный URL: {webhook_info.url}")
                    await setup_webhook()
            
            await asyncio.sleep(300)  # Проверка каждые 5 минут
        except Exception as e:
            logger.error(f"Ошибка при проверке состояния вебхука: {e}")
            await asyncio.sleep(60)  # При ошибке ждем минуту перед следующей попыткой

async def setup_webhook():
    """Устанавливает вебхук"""
    global bot_is_running
    try:
        if WEBHOOK_URL:
            webhook_url = WEBHOOK_URL + WEBHOOK_PATH
            await bot.set_webhook(webhook_url)
            logger.info(f"Webhook установлен: {webhook_url}")
            bot_is_running = True
        else:
            logger.error("WEBHOOK_URL не задан! Укажите переменную окружения WEBHOOK_URL.")
            bot_is_running = False
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        bot_is_running = False

logger.info("Bot initialized successfully")

# Клавиатуры
def get_start_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🚀 Поехали!", callback_data="start_menu"))
    return keyboard

def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💸 МФО до 150к", callback_data="mfo_150k"))
    keyboard.add(InlineKeyboardButton("🚗 Под ПТС до 5млн", callback_data="pts_5m"))
    keyboard.add(InlineKeyboardButton("🏠 Под залог до 50млн", callback_data="pledge_50m"))
    keyboard.add(InlineKeyboardButton("❓ Помощь", callback_data="help"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_start"))
    return keyboard

def get_mfo_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⚡️ ЭкспрессДеньги 0%", callback_data="mfo_express"))
    keyboard.add(InlineKeyboardButton("⚡️ Срочноденьги 0%", callback_data="mfo_urgent"))
    keyboard.add(InlineKeyboardButton("⚡️ А Деньги 7 дней 0%", callback_data="mfo_amoney"))
    keyboard.add(InlineKeyboardButton("⚡️ РокетМэн 0,6%", callback_data="mfo_rocket"))
    keyboard.add(InlineKeyboardButton("⚡️ Небус от 0,48%", callback_data="mfo_nebus"))
    keyboard.add(InlineKeyboardButton("⚡️ Доброзайм от 0%", callback_data="mfo_dobro"))
    keyboard.add(InlineKeyboardButton("⚡️ ФИНМОЛЛ от 0,59%", callback_data="mfo_finmoll"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    return keyboard

def get_loan_keyboard(mfo_name: str):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Получить займ", callback_data=f"get_loan_{mfo_name}"))
    keyboard.add(InlineKeyboardButton("◀️ Назад к списку МФО", callback_data="mfo_150k"))
    return keyboard

def get_pts_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Получить кредит", callback_data="get_pts_loan"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    return keyboard

def get_pledge_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Получить кредит", callback_data="get_pledge_loan"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    return keyboard

# Хендлеры
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = message.from_user
    full_name = user.full_name or f"{user.first_name or ''} {user.last_name or ''}".strip()
    welcome_message = (
        f"👋 Привет, {full_name}! На связи ФинАгрегаторБот!\n\n"
        "Я помогу вам подобрать выгодные финансовые решения в кратчайшие сроки: "
        "займы от МФО без залога, займы под залог авто или недвижимости.\n\n"
        "А также иные денежные инструменты на все случаи жизни вы сможете найти здесь!\n\n"
        "Начинаем?"
    )
    await message.answer(welcome_message, reply_markup=get_start_menu())
    logger.info(f"User {user.id} started the bot")

@dp.callback_query_handler(lambda c: True)
async def callback_handler(callback_query: types.CallbackQuery):
    data = callback_query.data
    logger.info(f"Received callback_data: {data}")
    mfo_info = {
        'express': ("ЭкспрессДеньги", "0%", "30 000 ₽", "7 дней"),
        'urgent': ("Срочноденьги", "0%", "30 000 ₽", "7 дней"),
        'amoney': ("А Деньги", "0%", "30 000 ₽", "7 дней"),
        'rocket': ("РокетМэн", "0,6%", "30 000 ₽", "7 дней"),
        'nebus': ("Небус", "от 0,48%", "30 000 ₽", "7 дней"),
        'dobro': ("Доброзайм", "от 0%", "30 000 ₽", "7 дней"),
        'finmoll': ("ФИНМОЛЛ", "от 0,59%", "30 000 ₽", "7 дней")
    }
    mfo_links = {
        'express': 'https://clck.ru/3M6gGy',
        'urgent': 'https://trk.ppdu.ru/click/XTQAqAhA?erid=2SDnjc7jaxR',
        'amoney': 'https://trk.ppdu.ru/click/Z2nIYcGH?erid=LjN8KSUm6',
        'rocket': 'https://trk.ppdu.ru/click/Zm2xFzSS?erid=2SDnjcXCda4',
        'nebus': 'https://trk.ppdu.ru/click/jOAljKvs?erid=2SDnjck7R1e',
        'dobro': 'https://trk.ppdu.ru/click/zub20YhE?erid=LjN8JvgqW',
        'finmoll': 'https://trk.ppdu.ru/click/wQwFZLCW?erid=2SDnjd4YnrC',
    }
    try:
        if data == 'start_menu':
            await callback_query.message.edit_text(
                "Выбери финпродукт, который тебя интересует:",
                reply_markup=get_main_menu()
            )
        elif data == 'mfo_150k':
            await callback_query.message.edit_text(
                "💫 Вы выбрали займ от микрофинансовой организации.\n\n"
                "У нас есть быстрые займы под низкий процент! 🚀\n\n"
                "Выберите подходящую МФО:",
                reply_markup=get_mfo_menu()
            )
        elif data.startswith('mfo_'):
            mfo_name = data[len('mfo_'):]
            if mfo_name in mfo_info:
                if mfo_name == 'express':
                    await callback_query.message.edit_text(
                        "💸 <b>ЭкспрессДеньги</b>\n\n"
                        "🥇 Первый и 🏅 шестой займ — <b>без процентов</b>!\n"
                        "🎁 Постоянные клиенты получают <b>бонусы</b> и привилегии!\n"
                        "💰 Кешбэк за выполнение заданий: выполняйте простые задания и получайте возврат!\n\n"
                        "<b>Условия:</b>\n"
                        "👤 Гражданам РФ от 18 до 70 лет\n"
                        "💵 Сумма: от 1 000 до 100 000 ₽ (шаг 1 000 ₽)\n"
                        "📆 Срок: до 52 недель\n\n"
                        "⚡️ Решение моментально! В случае доп. проверки — до 10-15 минут.\n\n"
                        "<b>Тарифы:</b>\n"
                        "🆕 Стандартный (новый клиент): от 1 000 до 30 000 ₽ — с 1 по 29 день <b>0%</b>, с 30 дня — 0,6%/день\n"
                        "📈 Долгосрочный: от 31 000 до 100 000 ₽ — с 10 по 24 неделю <b>0,6%/день</b>\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'urgent':
                    await callback_query.message.edit_text(
                        "💸 <b>Срочноденьги</b>\n\n"
                        "🎉 <b>Ваш кредит — первый заём бесплатно!</b>\n\n"
                        "<b>Описание:</b>\n"
                        "💵 Сумма займа: от 2 000 до 30 000 ₽\n"
                        "📆 Срок займа: до 30 дней\n"
                        "🥇 Первый заём бесплатно (до 7 дней)\n\n"
                        "<b>Преимущества:</b>\n"
                        "💰 Выгодные условия\n"
                        "🪪 Только паспорт для оформления\n"
                        "⚡️ До 8 минут — и деньги уже на карте!\n\n"
                        "<b>Требования к заёмщику:</b>\n"
                        "🔞 Возраст: 18–65 лет\n"
                        "🇷🇺 Гражданство РФ, паспорт РФ\n"
                        "🏠 Регистрация на территории РФ\n\n"
                        "🌍 Все регионы РФ, кроме: Крым, Дагестан, Карачаево-Черкессия, Севастополь, Чечня, ДНР, ЛНР.\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'amoney':
                    await callback_query.message.edit_text(
                        "💳 <b>Кредитный лимит от 'А Деньги'</b>\n\n"
                        "⚡️ Новый вид заёмных средств: быстрота одобрения как у онлайн-займов и удобство кредитки!\n\n"
                        "📝 Подайте заявку, получите лимит и превратите свою дебетовую карту в кредитку!\n"
                        "💸 Снимайте наличные, берите любые суммы в рамках лимита, возвращайте частями и пользуйтесь снова!\n\n"
                        "<b>Условия простые:</b>\n"
                        "🎁 Для новых клиентов первые 7 дней — бесплатно!\n"
                        "💸 Далее — всего 8 руб./день за каждую 1 000 ₽, которую перевели себе на карту.\n"
                        "📅 Тарификация ежедневная: не пользуетесь — не платите!\n"
                        "🟢 Всегда под рукой запас средств на любые случаи.\n\n"
                        "<b>Как получить лимит?</b>\n"
                        "🪪 Паспорт + дебетовая карта + короткая анкета за 5 минут.\n\n"
                        "<b>Условия кредитного лимита:</b>\n"
                        "💵 Сумма: до 30 000 ₽\n"
                        "📆 Срок лимита: до 30 дней с автопродлением\n"
                        "❌ Без поручителей, справок и залога\n\n"
                        "<b>Требования к клиенту:</b>\n"
                        "🔞 Возраст: 18–75 лет включительно\n"
                        "🇷🇺 Гражданство РФ\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'rocket':
                    await callback_query.message.edit_text(
                        "🚀 <b>РокетМЭН</b>\n\n"
                        "💵 Размер займа: от 3 000 до 30 000 ₽\n"
                        "📆 Срок займа: от 5 до 30 дней\n"
                        "💸 Процентная ставка: 0.8% в день\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'nebus':
                    await callback_query.message.edit_text(
                        "🌐 <b>Небус</b>\n\n"
                        "<b>Требования к заемщику:</b>\n"
                        "🔞 Возраст: от 18 до 88 лет\n"
                        "🪪 Паспорт РФ\n\n"
                        "<b>Условия получения займов:</b>\n"
                        "💵 Сумма: от 7 000 до 100 000 ₽\n"
                        "📆 Срок: от 7 до 365 дней\n"
                        "💸 Ставка: от 0,48% до 0,8% в день\n\n"
                        "⏱️ Срок рассмотрения: 15 минут\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'dobro':
                    await callback_query.message.edit_text(
                        "🤝 <b>Доброзайм</b>\n\n"
                        "🏢 Работает на территории РФ с 2011 года. Компания хорошо относится к своим клиентам, выдавая деньги в долг в разных ситуациях.\n\n"
                        "<b>Сумма займа:</b> от 1 000 до 100 000 ₽\n"
                        "<b>Срок займа:</b> от 4 до 364 дней\n"
                        "<b>Ставка:</b> от 0% до 1% в день\n"
                        "(под 0% новый и постоянный клиент может получить только на 7 дней)\n\n"
                        "<b>Требования к заемщику:</b>\n"
                        "🪪 Только паспорт РФ\n"
                        "🔞 Возраст: от 19 до 90 лет\n"
                        "❌ Без справок, поручителей и залога\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
                elif mfo_name == 'finmoll':
                    await callback_query.message.edit_text(
                        "🏦 <b>ФИНМОЛЛ</b>\n\n"
                        "🌟 Наша миссия — предоставляем лучшие финансовые возможности для хороших людей. Быстро, удобно и доступно в шаге от Вас.\n\n"
                        "<b>Сумма займа:</b>\n"
                        "🆕 Для нового клиента: от 30 000 до 60 000 ₽\n"
                        "🔁 Для повторного клиента: от 30 000 до 200 000 ₽\n\n"
                        "<b>Срок займа:</b> до 52 недель (до 364 дней)\n"
                        "💳 Платежи: еженедельно\n"
                        "💸 Процентная ставка: от 215% до 250% годовых\n"
                        "💰 Полная стоимость займа: от 199,073% до 250%\n"
                        "❌ Без залога и поручительства\n\n"
                        "<b>Требования к заёмщику:</b>\n"
                        "🇷🇺 Гражданство РФ\n"
                        "🔞 Возраст: 18–70 лет (первичные), 18–75 лет (повторные)\n"
                        "💼 Постоянный источник дохода\n"
                        "🪪 Оформление по паспорту\n",
                        reply_markup=get_loan_keyboard(mfo_name),
                        parse_mode='HTML'
                    )
        elif data.startswith('get_loan_'):
            mfo_name = data.split('_')[2]
            link = mfo_links.get(mfo_name)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text='✅ ЗАБРАТЬ ДЕНЬГИ НА КАРТУ', url=link))
            keyboard.add(InlineKeyboardButton(text='◀️ Назад к списку МФО', callback_data='mfo_150k'))
            await callback_query.message.edit_text(
                text='Здесь будет картинка',
                reply_markup=keyboard
            )
        elif data == 'back_to_main':
            await callback_query.message.edit_text(
                "Выбери финпродукт, который тебя интересует:",
                reply_markup=get_main_menu()
            )
        elif data == 'pts_5m':
            await callback_query.message.edit_text(
                "🚗 Кредит под ПТС до 5 000 000 ₽\n\n"
                "✨ Низкая процентная ставка\n"
                "📅 Срок до 5 лет\n"
                "🔑 Автомобиль остается у вас\n"
                "💵 Выплаты от 15 000 ₽/мес\n\n"
                "Для получения кредита нажмите кнопку ниже:",
                reply_markup=get_pts_keyboard()
            )
        elif data == 'pledge_50m':
            await callback_query.message.edit_text(
                "🏠 Кредит под залог недвижимости до 50 000 000 ₽\n\n"
                "✨ Крупная сумма\n"
                "📅 Срок до 20 лет\n"
                "💫 Низкая процентная ставка\n"
                "💵 Выплаты от 50 000 ₽/мес\n\n"
                "Для получения кредита нажмите кнопку ниже:",
                reply_markup=get_pledge_keyboard()
            )
        elif data == 'help':
            await callback_query.message.edit_text(
                "❓ Помощь\n\n"
                "📝 Как получить финансирование:\n\n"
                "1️⃣ Выберите подходящий продукт\n"
                "2️⃣ Заполните анкету\n"
                "3️⃣ Загрузите необходимые документы\n"
                "4️⃣ Получите решение\n"
                "5️⃣ Подпишите договор\n\n"
                "💬 По всем вопросам обращайтесь в поддержку: @support",
                reply_markup=get_main_menu()
            )
        elif data == 'back_to_start':
            await callback_query.message.edit_text(
                "👋 Привет! На связи ФинАгрегаторБот!\n\n"
                "Я помогу вам подобрать выгодные финансовые решения в кратчайшие сроки: "
                "займы от МФО без залога, займы под залог авто или недвижимости.\n\n"
                "А также иные денежные инструменты на все случаи жизни вы сможете найти здесь!\n\n"
                "Начинаем?",
                reply_markup=get_start_menu()
            )
        elif data == 'get_pts_loan':
            await callback_query.message.edit_text(
                "📝 Для получения кредита под ПТС:\n\n"
                "1. Нажмите на кнопку ниже\n"
                "2. Заполните анкету\n"
                "3. Загрузите документы на автомобиль\n"
                "4. Получите решение\n\n"
                "⚡️ Среднее время рассмотрения: 1-2 часа",
                reply_markup=get_pts_keyboard()
            )
        elif data == 'get_pledge_loan':
            await callback_query.message.edit_text(
                "📝 Для получения кредита под залог недвижимости:\n\n"
                "1. Нажмите на кнопку ниже\n"
                "2. Заполните анкету\n"
                "3. Загрузите документы на недвижимость\n"
                "4. Получите решение\n\n"
                "⚡️ Среднее время рассмотрения: 1-3 дня",
                reply_markup=get_pledge_keyboard()
            )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await callback_query.message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз или начните сначала с помощью команды /start")

async def on_startup(dp):
    """Действия при запуске бота"""
    await setup_webhook()
    # Запускаем проверку состояния вебхука в фоновом режиме
    asyncio.create_task(check_webhook_health())

async def on_shutdown(dp):
    """Действия при остановке бота"""
    global bot_is_running
    bot_is_running = False
    await bot.delete_webhook()
    logger.info("Webhook удален")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host='0.0.0.0',
        port=port
    )

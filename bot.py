import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage  # ✅ aiogram 3.x
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils import executor
# executor больше не нужен, используем встроенную async функцию
import os
import asyncio
import aiohttp
from datetime import datetime
from db import (
    create_table, add_stat_row, get_source_stats, get_user_stats,
    add_user_first_interaction, get_users_for_reminder, mark_reminder_sent,
    add_pending_event, get_unprocessed_pending_events, mark_pending_event_processed
)
import sqlite3

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

create_table()

ADMIN_IDS = [1006600764, 130155491]  # Список Telegram user_id админов

# Информация о МФО
mfo_info = {
    'express': ("ЭкспрессДеньги", "0%", "30 000 ₽", "7 дней"),
    'urgent': ("Срочноденьги", "0%", "30 000 ₽", "7 дней"),
    'amoney': ("А Деньги", "0%", "30 000 ₽", "7 дней"),
    'rocket': ("РокетМэн", "0,6%", "30 000 ₽", "7 дней"),
    'nebus': ("Небус", "от 0,48%", "30 000 ₽", "7 дней"),
    'dobro': ("Доброзайм", "от 0%", "30 000 ₽", "7 дней"),
    'finmoll': ("ФИНМОЛЛ", "от 0,59%", "30 000 ₽", "7 дней")
}

# Ссылки на МФО
mfo_links = {
    'express': 'https://clck.ru/3M6gGy',
    'urgent': 'https://trk.ppdu.ru/click/XTQAqAhA?erid=2SDnjc7jaxR',
    'amoney': 'https://trk.ppdu.ru/click/Z2nIYcGH?erid=LjN8KSUm6',
    'rocket': 'https://trk.ppdu.ru/click/Zm2xFzSS?erid=2SDnjcXCda4',
    'nebus': 'https://trk.ppdu.ru/click/jOAljKvs?erid=2SDnjck7R1e',
    'dobro': 'https://trk.ppdu.ru/click/zub20YhE?erid=LjN8JvgqW',
    'finmoll': 'https://trk.ppdu.ru/click/wQwFZLCW?erid=2SDnjd4YnrC',
}

async def setup_webhook():
    """Устанавливает вебхук"""
    global bot_is_running
    try:
        if WEBHOOK_URL:
            webhook_url = WEBHOOK_URL + WEBHOOK_PATH
            await bot.set_webhook(
                webhook_url,
                max_connections=100,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            logger.info(f"Webhook установлен: {webhook_url}")
            bot_is_running = True
        else:
            logger.error("WEBHOOK_URL не задан! Укажите переменную окружения WEBHOOK_URL.")
            bot_is_running = False
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
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
                else:
                    # Если вебхук работает нормально, просто логируем
                    logger.info("Webhook status check: OK")
            
            await asyncio.sleep(300)  # Проверка каждые 5 минут
        except Exception as e:
            logger.error(f"Ошибка при проверке состояния вебхука: {e}")
            await asyncio.sleep(60)  # При ошибке ждем минуту перед следующей попыткой

logger.info("Bot initialized successfully")

# Клавиатуры
def get_start_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🚀 Перейти в меню", callback_data="start_menu"))
    return keyboard

def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💸 Без залога до 150к", callback_data="mfo_150k"))
    keyboard.add(InlineKeyboardButton("🚗 Под ПТС до 5млн", callback_data="pts_5m"))
    keyboard.add(InlineKeyboardButton("🏠 Под недвижимость до 50м", callback_data="pledge_50m"))
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
    keyboard.add(InlineKeyboardButton("⚡️ Драйв от 2% в мес.", callback_data="pts_drive"))
    keyboard.add(InlineKeyboardButton("⚡️ Креди от 3% в мес.", callback_data="pts_kredi"))
    keyboard.add(InlineKeyboardButton("⚡️ КэшДрайв от 1,7% в мес.", callback_data="pts_cashdrive"))
    keyboard.add(InlineKeyboardButton("⚡️ Совком от 1,5% в мес.", callback_data="pts_sovcom"))
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
    try:
        user = message.from_user
        full_name = user.full_name or f"{user.first_name or ''} {user.last_name or ''}".strip()
        args = message.get_args()
        source = args if args else 'direct'
        add_user_first_interaction(user.id)
        welcome_message = (
            f"Привет, {full_name}. Вы находитесь в Финансовом Агрегаторе.\n\n"
            "Мы собрали для вас лучшие финансовые решения с наиболее выгодными условиями, чтобы помочь вам в важных моментах. В нашем ассортименте:\n\n"
            "🔍 Займы от МФО без залога — быстро и удобно.\n"
            "🔍 Займы под залог авто или недвижимости — надежные решения для получения необходимой суммы.\n"
            "🔍 И другие финансовые инструменты с оптимальными условиями, чтобы каждый нашел подходящий вариант.\n\n"
            "Изучите доступные предложения и выберите то, что соответствует вашим потребностям. Мы здесь, чтобы помочь вам сделать правильный выбор!"
        )
        msg = await message.answer(welcome_message, reply_markup=get_start_menu())
        logger.info(f"Start message sent to user {user.id} from source: {source}")
        await dp.storage.set_data(user=user.id, data={'start_message_sent': True, 'last_bot_message_id': msg.message_id})
        add_stat_row(user.id, user.full_name, user.username, 'start', source)
    except Exception as e:
        logger.error(f"Error in start command handler: {e}")
        # Сохраняем событие, если не удалось ответить
        try:
            add_pending_event(message.from_user.id, 'start', '')
        except Exception as db_e:
            logger.error(f"Error saving pending start event: {db_e}")

@dp.callback_query_handler(lambda c: True)
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    logger.info(f"Received callback_data: {data}")
    logger.info(f"Processing callback for user {callback_query.from_user.id}")
    try:
        # Получаем id предыдущего сообщения, если есть
        data_state = await state.get_data()
        last_bot_message_id = data_state.get('last_bot_message_id')
        logger.info(f"Last message ID: {last_bot_message_id}")
        
        if data == 'pts_5m':
            logger.info("Processing pts_5m callback")
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'pts_5m')
            # Отправляем новое сообщение с меню ПТС
            logger.info("Sending PTS menu message")
            msg = await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text="🚀 Займы под залог ПТС – с минимальными переплатами от лицензированных кредиторов!\n\n"
                     "Получите деньги быстро и безопасно, сохранив возможность пользоваться своим авто. Мы сотрудничаем только с проверенными компаниями, предлагающими честные условия по залогу транспортных средств.\n\n"
                     "🔹 Авто остается у вас\n"
                     "🔹 Минимальные требования к документам\n"
                     "🔹 Решение за 15 минут\n\n"
                     "Выбирайте надежного кредитора из нашего тщательно отобранного списка и решайте финансовые вопросы без риска!",
                reply_markup=get_pts_keyboard()
            )
            logger.info(f"Sent PTS menu message with ID: {msg.message_id}")
            await state.update_data(last_bot_message_id=msg.message_id)
            
            # Удаляем предыдущее сообщение только после успешной отправки нового
            if last_bot_message_id:
                try:
                    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=last_bot_message_id)
                    logger.info(f"Deleted previous message {last_bot_message_id}")
                except Exception as e:
                    logger.error(f'Ошибка при удалении предыдущего сообщения: {e}')
            
            # Удаляем текущее сообщение с кнопками
            try:
                await callback_query.message.delete()
                logger.info("Deleted current message with buttons")
            except Exception as e:
                logger.error(f'Ошибка при удалении текущего сообщения: {e}')
        else:
            # Удаляем предыдущее сообщение, если оно есть
            if last_bot_message_id:
                try:
                    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=last_bot_message_id)
                    logger.info(f"Deleted previous message {last_bot_message_id}")
                except Exception as e:
                    if "Message to delete not found" in str(e):
                        logger.info("Previous message was already deleted")
                    else:
                        logger.error(f'Ошибка при удалении предыдущего сообщения: {e}')
            
            # Удаляем текущее сообщение с кнопками
            try:
                await callback_query.message.delete()
                logger.info("Deleted current message with buttons")
            except Exception as e:
                if "Message to delete not found" in str(e):
                    logger.info("Current message was already deleted")
                else:
                    logger.error(f'Ошибка при удалении текущего сообщения: {e}')

            if data == 'start_menu':
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="Выбери финпродукт, который тебя интересует:",
                    reply_markup=get_main_menu()
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            elif data == 'mfo_150k':
                add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'mfo_150k')
                # Отправляем новое сообщение с меню МФО
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="💫 Быстрые займы с нулевыми процентами от лицензированных МФО! 🚀\n\n"
                         "Получите займ без переплат, выбрав проверенную организацию из нашего тщательно отобранного списка. Мы обеспечим вас всей необходимой информацией для безопасного и выгодного оформления займа. Доверяйте только надежным компаниям и начните улучшать свое финансовое положение уже сегодня!",
                    reply_markup=get_mfo_menu()
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            elif data.startswith('mfo_'):
                mfo_name = data[len('mfo_'):]
                if mfo_name in mfo_info:
                    if mfo_name == 'express':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="💸 <b>ЭкспрессДеньги</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'urgent':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="💸 <b>Срочноденьги</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'amoney':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="💳 <b>Кредитный лимит от 'А Деньги'</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'rocket':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="🚀 <b>РокетМЭН</b>\n\n"
                                 "💵 Размер займа: от 3 000 до 30 000 ₽\n"
                                 "📆 Срок займа: от 5 до 30 дней\n"
                                 "💸 Процентная ставка: 0.8% в день\n",
                            reply_markup=get_loan_keyboard(mfo_name),
                            parse_mode='HTML'
                        )
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'nebus':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="🌐 <b>Небус</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'dobro':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="🤝 <b>Доброзайм</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
                    elif mfo_name == 'finmoll':
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text="🏦 <b>ФИНМОЛЛ</b>\n\n"
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
                        await state.update_data(last_bot_message_id=msg.message_id)
            elif data.startswith('pts_'):
                mfo_name = data
                if mfo_name in ["pts_drive", "pts_kredi", "pts_cashdrive", "pts_sovcom"]:
                    loan_keyboard = InlineKeyboardMarkup()
                    loan_keyboard.add(InlineKeyboardButton("📝 Получить займ", callback_data=f"get_loan_{mfo_name}"))
                    loan_keyboard.add(InlineKeyboardButton("◀️ Назад к списку кредиторов", callback_data="pts_5m"))
                    if mfo_name == "pts_drive":
                        text = (
                            "💳 <b>Драйв</b> — онлайн на банковскую карту.\n\n"
                            "🚗 <b>Обеспечение:</b>\n"
                            "В качестве залога принимаются легковые и грузовые автомобили, спецтехника, водный транспорт, мототехника, автобусы. Передаваемое в залог ТС остается у Вас.\n\n"
                            "📋 <b>Требования к транспортному средству:</b>\n"
                            "• Рыночная стоимость ТС более 75 000 руб.\n"
                            "• Регистрация ТС в РФ\n"
                            "• VIN номер без дефектов\n"
                            "• ТС не находится в угоне\n"
                            "• ТС находится в собственности или с согласия на залог 3-го лица\n"
                            "• Иномарки не старше 2005 года, отечественные 2010 года\n\n"
                            "💰 <b>Процентная ставка:</b> от 2 до 7,4% в месяц\n"
                            "⏳ <b>Срок:</b> 61 — 1094 дн.\n"
                            "✅ Досрочное погашение без комиссий: Да\n"
                            "🔄 Продление срока займа: Да"
                        )
                    elif mfo_name == "pts_kredi":
                        text = (
                            "🏦 <b>Креди</b> — онлайн-займы под залог легковых автомобилей и коммерческого транспорта.\n\n"
                            "📑 Мы состоим в реестре Центрального Банка РФ и заключаем договоры в соответствии с законодательством.\n"
                            "🚗 Автомобиль остается в вашей собственности.\n\n"
                            "📝 <b>Для одобрения потребуется:</b> Паспорт гражданина РФ\n"
                            "📄 <b>Для заключения договора и выдачи денег:</b> ПТС, СТС\n\n"
                            "⏱️ Время рассмотрения заявки: 30 минут\n"
                            "💵 Сумма: от 50 000 до 500 000 рублей\n"
                            "⏳ Срок займа: от 3 мес до 4 лет, с шагом 1 мес.\n\n"
                            "🚘 <b>Легковые автомобили категории В:</b>\n"
                            "• Отечественные — не старше 7 лет\n"
                            "• Иномарки — не старше 20 лет\n\n"
                            "🚚 <b>Коммерческий транспорт и грузовые авто:</b>\n"
                            "• Отечественные — не старше 10 лет\n"
                            "• Иномарки — не старше 15 лет\n\n"
                            "💳 <b>Способы получения займа:</b> На банковскую карту, СБП"
                        )
                    elif mfo_name == "pts_cashdrive":
                        text = (
                            "💸 <b>КэшДрайв</b>\n\n"
                            "👤 <b>Требования к заёмщику:</b>\n"
                            "• Гражданство РФ\n"
                            "• Возраст от 21 до 70 лет\n\n"
                            "💰 <b>Условия займа:</b>\n"
                            "• Сумма от 5 000 до 250 000 рублей\n"
                            "• Срок от 1 до 24 месяцев\n"
                            "• Ставка от 20% годовых\n\n"
                            "💳 <b>Способы получения:</b> Онлайн на банковскую карту"
                        )
                    elif mfo_name == "pts_sovcom":
                        text = (
                            "🏦 <b>Совком</b>\n\n"
                            "ℹ️ <b>Информация о продукте:</b>\n"
                            "• ПСК от 14,883 до 14,901%\n"
                            "• Процентная ставка: 14,9% годовых\n"
                            "• Сумма: от 150 000 до 15 000 000 руб.\n"
                            "• Срок: от 12 до 60 месяцев\n\n"
                            "🌟 <b>Преимущества:</b>\n"
                            "• Онлайн заявка\n"
                            "• Получение кредита день в день\n"
                            "• Кредит на карту или курьером\n"
                            "• Автомобиль остается у вас\n\n"
                            "🏷️ <b>Требования к ТС:</b>\n"
                            "• Не старше 24 лет включительно\n"
                            "• Технически исправное\n"
                            "• Не должно находиться в залоге, участвовать в программе автокредитования\n\n"
                            "📄 <b>Документы для заемщика:</b>\n"
                            "• Паспорт гражданина РФ\n"
                            "• Один из документов: СНИЛС, водительское удостоверение\n"
                            "• Свидетельство о регистрации ТС\n"
                            "• Паспорт ТС\n"
                            "• Страховой полис ОСАГО\n"
                            "• Согласие супруга(-и)"
                        )
                    msg = await bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text=text,
                        reply_markup=loan_keyboard,
                        parse_mode='HTML'
                    )
                    await state.update_data(last_bot_message_id=msg.message_id)
            elif data.startswith('get_loan_'):
                mfo_name = data.replace('get_loan_', '')  # Получаем полное имя оператора
                logger.info(f"Processing get_loan_ callback for {mfo_name}")
                # Для ПТС-операторов показываем картинку, кнопку с внешней ссылкой и кнопку "Назад к списку кредиторов"
                if mfo_name in ["pts_drive", "pts_kredi", "pts_cashdrive", "pts_sovcom"]:
                    try:
                        logger.info(f"Processing PTS operator: {mfo_name}")
                        pts_links = {
                            "pts_drive": "https://slds.pro/az72w",
                            "pts_kredi": "https://slds.pro/vcdj7",
                            "pts_cashdrive": "https://slds.pro/hxhbv",
                            "pts_sovcom": "https://trk.ppdu.ru/click/ELxQqqRu?erid=Kra23xE7N"
                        }
                        url = pts_links.get(mfo_name)
                        if not url:
                            logger.error(f"URL not found for {mfo_name}")
                            return

                        logger.info(f"Creating keyboard for {mfo_name} with URL: {url}")
                        action_keyboard = InlineKeyboardMarkup()
                        action_keyboard.add(InlineKeyboardButton("✅ ПОЛУЧИТЬ ДЕНЬГИ ЗА ПОЛЧАСА!", url=url))
                        action_keyboard.add(InlineKeyboardButton("◀️ Назад к списку кредиторов", callback_data="pts_5m"))

                        image_extensions = ['jpg', 'jpeg', 'png']
                        image_path = None
                        for ext in image_extensions:
                            path = f'images/{mfo_name}.{ext}'
                            if os.path.exists(path):
                                image_path = path
                                logger.info(f"Found image at {path}")
                                break

                        try:
                            if image_path:
                                logger.info(f"Sending photo for {mfo_name}")
                                with open(image_path, 'rb') as photo:
                                    msg = await bot.send_photo(
                                        chat_id=callback_query.message.chat.id,
                                        photo=photo,
                                        caption=f'Получите займ в {mfo_name.replace("pts_", "").capitalize()}',
                                        reply_markup=action_keyboard
                                    )
                            else:
                                logger.info(f"No image found for {mfo_name}, sending text message")
                                msg = await bot.send_message(
                                    chat_id=callback_query.message.chat.id,
                                    text=f'Получите займ в {mfo_name.replace("pts_", "").capitalize()}',
                                    reply_markup=action_keyboard
                                )
                            logger.info(f"Message sent successfully for {mfo_name}")
                            await state.update_data(last_bot_message_id=msg.message_id)
                        except Exception as e:
                            logger.error(f"Error sending message/photo for {mfo_name}: {e}")
                            # Пробуем отправить хотя бы текстовое сообщение
                            try:
                                logger.info(f"Attempting to send fallback message for {mfo_name}")
                                msg = await bot.send_message(
                                    chat_id=callback_query.message.chat.id,
                                    text=f'Получите займ в {mfo_name.replace("pts_", "").capitalize()}',
                                    reply_markup=action_keyboard
                                )
                                await state.update_data(last_bot_message_id=msg.message_id)
                            except Exception as e:
                                logger.error(f"Error sending fallback message for {mfo_name}: {e}")
                    except Exception as e:
                        logger.error(f"Error processing PTS operator {mfo_name}: {e}")
                else:
                    # Старое поведение для МФО
                    link = mfo_links.get(mfo_name)
                    image_extensions = ['jpg', 'jpeg', 'png']
                    image_path = None
                    for ext in image_extensions:
                        path = f'images/{mfo_name}.{ext}'
                        if os.path.exists(path):
                            image_path = path
                            break
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(text='✅ ЗАБРАТЬ ДЕНЬГИ НА КАРТУ', url=link))
                    keyboard.add(InlineKeyboardButton(text='◀️ Назад к списку МФО', callback_data='mfo_150k'))
                    if image_path:
                        with open(image_path, 'rb') as photo:
                            msg = await bot.send_photo(
                                chat_id=callback_query.message.chat.id,
                                photo=photo,
                                caption=f'Получите займ в {mfo_info[mfo_name][0]}',
                                reply_markup=keyboard
                            )
                    else:
                        msg = await bot.send_message(
                            chat_id=callback_query.message.chat.id,
                            text=f'Получите займ в {mfo_info[mfo_name][0]}',
                            reply_markup=keyboard
                        )
                    await state.update_data(last_bot_message_id=msg.message_id)
            elif data == 'back_to_main':
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="Выбери финпродукт, который тебя интересует:",
                    reply_markup=get_main_menu()
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            elif data == 'pledge_50m':
                add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'pledge_50m')
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("Оформить займ", url="https://t.me/Odobrenie41Bot"))
                keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="🚀 Займы под залог недвижимости – выгодные условия от частного инвестора!\n\n"
                         "Получите деньги быстро и без лишних сложностей, сохранив право пользоваться своей недвижимостью. Мы предлагаем индивидуальные условия кредитования с минимальной переплатой и гибким графиком погашения.\n\n"
                         "🔹 Квартира, дом или коммерческая недвижимость в залоге – вы остаетесь собственником\n"
                         "🔹 Минимум документов – решение в кратчайшие сроки\n"
                         "🔹 Сделка без банков – быстро, конфиденциально, без бюрократии\n\n"
                         "Решите финансовые вопросы с надежным частным инвестором – оставьте заявку и получите деньги уже сегодня!",
                    reply_markup=keyboard
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            elif data == 'help':
                await callback_query.message.answer(
                    "ℹ️ Я бот для оформления займов под залог недвижимости. Вот что я могу для вас сделать:\n\n"
                    "🔹 Оформить заявку – подберу лучшие условия от частных инвесторов\n"
                    "🔹 Рассчитать сумму – помогу оценить вашу недвижимость и возможный займ\n"
                    "🔹 Ответить на вопросы – расскажу о требованиях, сроках и документах\n"
                    "🔹 Связать с инвестором – организую быструю и безопасную сделку\n\n"
                    "📌 Чтобы начать, выберите нужную опцию в меню или напишите свой вопрос.\n"
                    "📌Техподдержка и помощь с заявками: <a href='https://t.me/Odobrenie41Bot'>@support_finagr</a>",
                    parse_mode='HTML'
                )
            elif data == 'back_to_start':
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=f"Привет, {callback_query.from_user.full_name}. Вы находитесь в Финансовом Агрегаторе.\n\n"
                         "Мы собрали для вас лучшие финансовые решения с наиболее выгодными условиями, чтобы помочь вам в важных моментах. В нашем ассортименте:\n\n"
                         "🔍 Займы от МФО без залога — быстро и удобно.\n"
                         "🔍 Займы под залог авто или недвижимости — надежные решения для получения необходимой суммы.\n"
                         "🔍 И другие финансовые инструменты с оптимальными условиями, чтобы каждый нашел подходящий вариант.\n\n"
                         "Изучите доступные предложения и выберите то, что соответствует вашим потребностям. Мы здесь, чтобы помочь вам сделать правильный выбор!",
                    reply_markup=get_start_menu()
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            elif data == 'get_pledge_loan':
                msg = await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="📝 Для получения кредита под залог недвижимости:\n\n"
                         "1. Нажмите на кнопку ниже\n"
                         "2. Заполните анкету\n"
                         "3. Загрузите документы на недвижимость\n"
                         "4. Получите решение\n\n"
                         "⚡️ Среднее время рассмотрения: 1-3 дня",
                    reply_markup=get_pledge_keyboard()
                )
                await state.update_data(last_bot_message_id=msg.message_id)
            await callback_query.answer()
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        # Сохраняем событие, если не удалось ответить
        try:
            add_pending_event(callback_query.from_user.id, 'callback', data)
        except Exception as db_e:
            logger.error(f"Error saving pending callback event: {db_e}")

@dp.message_handler(commands=['help'])
async def help_command_handler(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        help_text = (
            "🔧 <b>Команды администратора:</b>\n\n"
            "/sourcestats - Статистика по источникам трафика\n"
            "/userstats ID - Статистика по конкретному пользователю\n"
            "/getstats - Получить файл статистики\n"
            "/getdb - Получить файл базы данных\n\n"
            "📊 <b>Статистика включает:</b>\n"
            "• Количество переходов\n"
            "• Уникальных пользователей\n"
            "• Конверсии\n"
            "• Процент конверсии"
        )
    else:
        help_text = (
            "ℹ️ Я бот для оформления займов под залог недвижимости. Вот что я могу для вас сделать:\n\n"
            "🔹 Оформить заявку – подберу лучшие условия от частных инвесторов\n"
            "🔹 Рассчитать сумму – помогу оценить вашу недвижимость и возможный займ\n"
            "🔹 Ответить на вопросы – расскажу о требованиях, сроках и документах\n"
            "🔹 Связать с инвестором – организую быструю и безопасную сделку\n\n"
            "📌 Чтобы начать, выберите нужную опцию в меню или напишите свой вопрос.\n"
            "📌Техподдержка и помощь с заявками: <a href='https://t.me/Odobrenie41Bot'>@support_finagr</a>"
        )
    
    await message.answer(help_text, parse_mode='HTML')

@dp.message_handler(commands=['getstats'])
async def send_stats_file(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        try:
            with open('stats_log.csv', 'rb') as f:
                await message.answer_document(types.InputFile(f, filename='stats_log.csv'))
        except Exception as e:
            await message.reply(f'Ошибка при отправке файла: {e}')
    else:
        await message.reply('Нет доступа')

@dp.message_handler(commands=['getdb'])
async def send_db_file(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        try:
            with open('stats.db', 'rb') as f:
                await message.answer_document(types.InputFile(f, filename='stats.db'))
        except Exception as e:
            await message.reply(f'Ошибка при отправке файла: {e}')
    else:
        await message.reply('Нет доступа')

@dp.message_handler(commands=['sourcestats'])
async def send_source_stats(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        try:
            stats = get_source_stats()
            
            if not stats:
                await message.reply("Статистика по источникам пока пуста.")
                return
                
            # Формируем сообщение со статистикой
            stats_message = "📊 <b>Статистика по источникам трафика:</b>\n\n"
            
            for row in stats:
                source = row['source']
                total = row['total_users']
                unique = row['unique_users']
                conversions = row['conversions']
                conversion_rate = (conversions / total * 100) if total > 0 else 0
                
                stats_message += (
                    f"<b>Источник:</b> {source}\n"
                    f"👥 Всего переходов: {total}\n"
                    f"👤 Уникальных пользователей: {unique}\n"
                    f"✅ Конверсии: {conversions}\n"
                    f"📈 Конверсия: {conversion_rate:.1f}%\n\n"
                )
            
            await message.reply(stats_message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in sourcestats command: {e}")
            await message.reply(f'Ошибка при получении статистики: {e}')
    else:
        await message.reply('Нет доступа')

@dp.message_handler(commands=['userstats'])
async def send_user_stats(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        try:
            # Получаем ID пользователя из аргументов команды
            args = message.get_args()
            if not args:
                await message.reply("Укажите ID пользователя: /userstats ID")
                return
                
            try:
                user_id = int(args)
            except ValueError:
                await message.reply("ID пользователя должен быть числом")
                return
                
            stats = get_user_stats(user_id)
            
            if not stats:
                await message.reply(f"Статистика по пользователю {user_id} не найдена.")
                return
                
            # Формируем сообщение со статистикой
            stats_message = f"📊 <b>Статистика пользователя {user_id}:</b>\n\n"
            
            for row in stats:
                action = row['action']
                source = row['source']
                timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S')
                
                stats_message += (
                    f"🕒 {timestamp}\n"
                    f"📝 Действие: {action}\n"
                    f"🔗 Источник: {source}\n\n"
                )
            
            await message.reply(stats_message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in userstats command: {e}")
            await message.reply(f'Ошибка при получении статистики: {e}')
    else:
        await message.reply('Нет доступа')

async def send_reminders():
    """Отправляет напоминания пользователям"""
    error_count = 0
    max_errors = 3
    
    while True:
        try:
            # Получаем пользователей для напоминаний
            users = get_users_for_reminder()
            
            # Отправляем напоминания через 1 день
            for user in users['day_1']:
                try:
                    await bot.send_message(
                        chat_id=user['user_id'],
                        text="👋 Приветствую! Прошло уже 24 часа с момента нашего знакомства.\n\n"
                             "Не упустите возможность получить займ на выгодных условиях.\n"
                             "Выберите подходящий вариант в меню бота!",
                        reply_markup=get_main_menu()
                    )
                    mark_reminder_sent(user['user_id'], '1')
                except Exception as e:
                    logger.error(f"Error sending 1-day reminder to user {user['user_id']}: {e}")
            
            # Отправляем напоминания через 3 дня
            for user in users['day_3']:
                try:
                    await bot.send_message(
                        chat_id=user['user_id'],
                        text="👋 Снова здравствуйте! Прошло 3 дня с момента нашего знакомства.\n\n"
                             "Напоминаем о наших выгодных предложениях:\n"
                             "• Первый займ под 0%\n"
                             "• Решение за 15 минут\n"
                             "• Минимум документов\n\n"
                             "Выберите подходящий вариант в меню бота!",
                        reply_markup=get_main_menu()
                    )
                    mark_reminder_sent(user['user_id'], '3')
                except Exception as e:
                    logger.error(f"Error sending 3-day reminder to user {user['user_id']}: {e}")
            
            # Отправляем напоминания через 10 дней
            for user in users['day_10']:
                try:
                    await bot.send_message(
                        chat_id=user['user_id'],
                        text="👋 Добрый день! Напоминаю вам, что специально для вас, мы собрали лучшие предложения на рынке финансирования:\n\n"
                             "• Сниженные ставки\n"
                             "• Увеличенные лимиты\n"
                             "• Персональные условия\n\n"
                             "Выберите подходящий вариант в меню бота!",
                        reply_markup=get_main_menu()
                    )
                    mark_reminder_sent(user['user_id'], '10')
                except Exception as e:
                    logger.error(f"Error sending 10-day reminder to user {user['user_id']}: {e}")
            
            # Сбрасываем счетчик ошибок при успешном выполнении
            error_count = 0
            
            # Проверяем каждые 6 часов
            await asyncio.sleep(6 * 60 * 60)
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error in send_reminders: {e}")
            
            if error_count >= max_errors:
                logger.critical(f"Too many errors in send_reminders ({error_count}). Restarting...")
                # Перезапускаем бота
                await setup_webhook()
                error_count = 0
            
            # Ждем 5 минут перед следующей попыткой
            await asyncio.sleep(300)

async def process_pending_events():
    """Обрабатывает неотвеченные события при запуске бота"""
    events = get_unprocessed_pending_events()
    for event in events:
        try:
            user_id = event['user_id']
            event_type = event['event_type']
            event_data = event['event_data']
            # Универсальная обработка событий
            if event_type == 'start':
                await bot.send_message(
                    chat_id=user_id,
                    text="Привет! Вы запускали бота, когда он был недоступен. Сейчас бот снова работает!\n\n"
                         "Мы собрали для вас лучшие финансовые решения с наиболее выгодными условиями. Выберите подходящий вариант в меню бота!",
                    reply_markup=get_start_menu()
                )
            elif event_type == 'callback':
                # Можно доработать под разные callback, пока просто уведомление
                await bot.send_message(
                    chat_id=user_id,
                    text="Бот был временно недоступен. Пожалуйста, повторите ваш запрос — сейчас всё работает!"
                )
            elif event_type == 'message':
                await bot.send_message(
                    chat_id=user_id,
                    text="Бот был временно недоступен. Пожалуйста, повторите ваш запрос — сейчас всё работает!"
                )
            # Можно добавить обработку других типов событий
            mark_pending_event_processed(event['id'])
        except Exception as e:
            logger.error(f"Ошибка при обработке pending event {event['id']}: {e}")

async def on_startup(dp):
    """Действия при запуске бота"""
    # Создаем таблицу при запуске
    create_table()
    await setup_webhook()
    # Запускаем проверку состояния вебхука и отправку напоминаний в фоновом режиме
    asyncio.create_task(check_webhook_health())
    asyncio.create_task(send_reminders())
    # Обрабатываем неотвеченные события
    await process_pending_events()

async def on_shutdown(dp):
    """Действия при остановке бота"""
    global bot_is_running
    bot_is_running = False
    await bot.delete_webhook()
    logger.info("Webhook удален")

if __name__ == '__main__':
    # Создаем таблицу при запуске скрипта
    create_table()
    
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

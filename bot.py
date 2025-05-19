import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
import os
import asyncio
import aiohttp
from datetime import datetime
from db import create_table, add_stat_row

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
    user = message.from_user
    full_name = user.full_name or f"{user.first_name or ''} {user.last_name or ''}".strip()
    welcome_message = (
        f"Привет, {full_name}. Вы находитесь в Финансовом Агрегаторе.\n\n"
        "Мы собрали для вас лучшие финансовые решения с наиболее выгодными условиями, чтобы помочь вам в важных моментах. В нашем ассортименте:\n\n"
        "🔍 Займы от МФО без залога — быстро и удобно.\n"
        "🔍 Займы под залог авто или недвижимости — надежные решения для получения необходимой суммы.\n"
        "🔍 И другие финансовые инструменты с оптимальными условиями, чтобы каждый нашел подходящий вариант.\n\n"
        "Изучите доступные предложения и выберите то, что соответствует вашим потребностям. Мы здесь, чтобы помочь вам сделать правильный выбор!"
    )
    await message.answer(welcome_message, reply_markup=get_start_menu())
    logger.info(f"User {user.id} started the bot")
    add_stat_row(user.id, user.full_name, user.username, 'start')

@dp.callback_query_handler(lambda c: True)
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
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
        # Получаем id предыдущего сообщения, если есть
        data_state = await state.get_data()
        last_bot_message_id = data_state.get('last_bot_message_id')
        # Удаляем предыдущее сообщение, если оно есть
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=last_bot_message_id)
            except Exception as e:
                logger.error(f'Ошибка при удалении предыдущего сообщения: {e}')
        if data == 'start_menu':
            msg = await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text="Выбери финпродукт, который тебя интересует:",
                reply_markup=get_main_menu()
            )
            await state.update_data(last_bot_message_id=msg.message_id)
        elif data == 'mfo_150k':
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'mfo_150k')
            # Удаляем сообщение с фото, если оно есть
            try:
                await callback_query.message.delete()
            except Exception as e:
                logger.error(f'Ошибка при удалении сообщения с фото: {e}')
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
        elif data.startswith('get_loan_'):
            mfo_name = data.split('_')[2]
            # Для ПТС-операторов показываем картинку, кнопку с внешней ссылкой и кнопку "Назад к списку кредиторов"
            if mfo_name in ["pts_drive", "pts_kredi", "pts_cashdrive", "pts_sovcom"]:
                pts_links = {
                    "pts_drive": "https://slds.pro/az72w",
                    "pts_kredi": "https://slds.pro/vcdj7",
                    "pts_cashdrive": "https://slds.pro/hxhbv",
                    "pts_sovcom": "https://trk.ppdu.ru/click/ELxQqqRu?erid=Kra23xE7N"
                }
                url = pts_links.get(mfo_name)
                action_keyboard = InlineKeyboardMarkup()
                if url:
                    action_keyboard.add(InlineKeyboardButton("✅ ПОЛУЧИТЬ ДЕНЬГИ ЗА ПОЛЧАСА!", url=url))
                else:
                    action_keyboard.add(InlineKeyboardButton("✅ ПОЛУЧИТЬ ДЕНЬГИ ЗА ПОЛЧАСА!", callback_data="none"))
                action_keyboard.add(InlineKeyboardButton("◀️ Назад к списку кредиторов", callback_data="pts_5m"))
                image_extensions = ['jpg', 'jpeg', 'png']
                image_path = None
                for ext in image_extensions:
                    path = f'images/{mfo_name}.{ext}'
                    if os.path.exists(path):
                        image_path = path
                        break
                if image_path:
                    with open(image_path, 'rb') as photo:
                        msg = await bot.send_photo(
                            chat_id=callback_query.message.chat.id,
                            photo=photo,
                            caption=f'Получите займ в {mfo_name.replace("pts_", "").capitalize()}',
                            reply_markup=action_keyboard
                        )
                else:
                    msg = await bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text=f'Получите займ в {mfo_name.replace("pts_", "").capitalize()}',
                        reply_markup=action_keyboard
                    )
                await state.update_data(last_bot_message_id=msg.message_id)
            else:
                # Старое поведение для МФО
                link = mfo_links.get(mfo_name)
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton(text='✅ ЗАБРАТЬ ДЕНЬГИ НА КАРТУ', url=link))
                keyboard.add(InlineKeyboardButton(text='◀️ Назад к списку МФО', callback_data='mfo_150k'))
                image_extensions = ['jpg', 'jpeg', 'png']
                image_path = None
                for ext in image_extensions:
                    path = f'images/{mfo_name}.{ext}'
                    if os.path.exists(path):
                        image_path = path
                        break
                if not image_path:
                    msg = await callback_query.message.answer("Извините, картинка временно недоступна.")
                else:
                    with open(image_path, 'rb') as photo:
                        msg = await bot.send_photo(
                            chat_id=callback_query.message.chat.id,
                            photo=photo,
                            caption=f'Получите займ в {mfo_info[mfo_name][0]}',
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
        elif data == 'pts_5m':
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'pts_5m')
            pts_keyboard = InlineKeyboardMarkup()
            pts_keyboard.add(InlineKeyboardButton("⚡️ Драйв от 2% в мес.", callback_data="pts_drive"))
            pts_keyboard.add(InlineKeyboardButton("⚡️ Креди от 3% в мес.", callback_data="pts_kredi"))
            pts_keyboard.add(InlineKeyboardButton("⚡️ КэшДрайв от 1,7% в мес.", callback_data="pts_cashdrive"))
            pts_keyboard.add(InlineKeyboardButton("⚡️ Совком от 1,5% в мес.", callback_data="pts_sovcom"))
            pts_keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
            msg = await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text="🚀 Займы под залог ПТС – с минимальными переплатами от лицензированных кредиторов!\n\n"
                     "Получите деньги быстро и безопасно, сохранив возможность пользоваться своим авто. Мы сотрудничаем только с проверенными компаниями, предлагающими честные условия по залогу транспортных средств.\n\n"
                     "🔹 Авто остается у вас\n"
                     "🔹 Минимальные требования к документам\n"
                     "🔹 Решение за 15 минут\n\n"
                     "Выбирайте надежного кредитора из нашего тщательно отобранного списка и решайте финансовые вопросы без риска!",
                reply_markup=pts_keyboard
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
        elif data in ["pts_drive", "pts_kredi", "pts_cashdrive", "pts_sovcom"]:
            loan_keyboard = InlineKeyboardMarkup()
            loan_keyboard.add(InlineKeyboardButton("📝 Получить займ", callback_data=f"get_loan_{data}"))
            loan_keyboard.add(InlineKeyboardButton("◀️ Назад к списку кредиторов", callback_data="pts_5m"))
            if data == "pts_drive":
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
            elif data == "pts_kredi":
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
            elif data == "pts_cashdrive":
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
            elif data == "pts_sovcom":
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
                    "🚗 <b>Требования к ТС:</b>\n"
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
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await callback_query.message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз или начните сначала с помощью команды /start")

@dp.message_handler(commands=['help'])
async def help_command_handler(message: types.Message):
    await message.answer(
        "ℹ️ Я бот для оформления займов под залог недвижимости. Вот что я могу для вас сделать:\n\n"
        "🔹 Оформить заявку – подберу лучшие условия от частных инвесторов\n"
        "🔹 Рассчитать сумму – помогу оценить вашу недвижимость и возможный займ\n"
        "🔹 Ответить на вопросы – расскажу о требованиях, сроках и документах\n"
        "🔹 Связать с инвестором – организую быструю и безопасную сделку\n\n"
        "📌 Чтобы начать, выберите нужную опцию в меню или напишите свой вопрос.\n"
        "📌Техподдержка и помощь с заявками: <a href='https://t.me/Odobrenie41Bot'>@support_finagr</a>",
        parse_mode='HTML'
    )

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

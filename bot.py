import logging
import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from db import (
    create_table, add_stat_row, get_source_stats, get_user_stats,
    add_user_first_interaction, get_users_for_reminder, mark_reminder_sent,
    add_pending_event, get_unprocessed_pending_events, mark_pending_event_processed
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    logger.error("API_TOKEN не найден в .env файле!")
    exit(1)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

ADMIN_IDS = [1006600764, 130155491]

mfo_info = {
    'express': ("ЭкспрессДеньги", "0%", "30 000 ₽", "7 дней"),
    'urgent':  ("Срочноденьги",   "0%", "30 000 ₽", "7 дней"),
    'amoney':  ("А Деньги",       "0%", "30 000 ₽", "7 дней"),
    'rocket':  ("РокетМэн",    "0,6%", "30 000 ₽", "7 дней"),
    'nebus':   ("Небус",    "от 0,48%", "30 000 ₽", "7 дней"),
    'dobro':   ("Доброзайм",  "от 0%", "30 000 ₽", "7 дней"),
    'finmoll': ("ФИНМОЛЛ", "от 0,59%", "30 000 ₽", "7 дней"),
}

mfo_links = {
    'express': 'https://clck.ru/3M6gGy',
    'urgent':  'https://trk.ppdu.ru/click/XTQAqAhA?erid=2SDnjc7jaxR',
    'amoney':  'https://trk.ppdu.ru/click/Z2nIYcGH?erid=LjN8KSUm6',
    'rocket':  'https://trk.ppdu.ru/click/Zm2xFzSS?erid=2SDnjcXCda4',
    'nebus':   'https://trk.ppdu.ru/click/jOAljKvs?erid=2SDnjck7R1e',
    'dobro':   'https://trk.ppdu.ru/click/zub20YhE?erid=LjN8JvgqW',
    'finmoll': 'https://trk.ppdu.ru/click/wQwFZLCW?erid=2SDnjd4YnrC',
}


# ─── Клавиатуры ──────────────────────────────────────────────────────

def get_start_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Перейти в меню", callback_data="start_menu")]
    ])

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Без залога до 150к", callback_data="mfo_150k")],
        [InlineKeyboardButton(text="🏎 Под ПТС до 5млн", callback_data="pts_5m")],
        [InlineKeyboardButton(text="🏠 Под недвижимость до 50м", callback_data="pledge_50m")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_start")],
    ])

def get_mfo_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ЭкспрессДеньги 0%", callback_data="mfo_express")],
        [InlineKeyboardButton(text="Срочноденьги 0%", callback_data="mfo_urgent")],
        [InlineKeyboardButton(text="А Деньги 7 дней 0%", callback_data="mfo_amoney")],
        [InlineKeyboardButton(text="РокетМэн 0,6%", callback_data="mfo_rocket")],
        [InlineKeyboardButton(text="Небус от 0,48%", callback_data="mfo_nebus")],
        [InlineKeyboardButton(text="Доброзайм от 0%", callback_data="mfo_dobro")],
        [InlineKeyboardButton(text="ФИНМОЛЛ от 0,59%", callback_data="mfo_finmoll")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")],
    ])

def get_loan_keyboard(mfo_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить займ", callback_data=f"get_loan_{mfo_name}")],
        [InlineKeyboardButton(text="◀ Назад к списку МФО", callback_data="mfo_150k")],
    ])

def get_pts_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Драйв от 2% в мес.", callback_data="pts_drive")],
        [InlineKeyboardButton(text="Креди от 3% в мес.", callback_data="pts_kredi")],
        [InlineKeyboardButton(text="КэшДрайв от 1,7% в мес.", callback_data="pts_cashdrive")],
        [InlineKeyboardButton(text="Совком от 1,5% в мес.", callback_data="pts_sovcom")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")],
    ])

def get_pledge_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить кредит", callback_data="get_pledge_loan")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")],
    ])


# ─── Вспомогательные функции ─────────────────────────────────────────

def find_image(name: str):
    """Ищет картинку для МФО/ПТС, возвращает путь или None"""
    return next(
        (f"images/{name}.{ext}" for ext in ['jpg', 'jpeg', 'png']
         if os.path.exists(f"images/{name}.{ext}")),
        None
    )


# ─── Хендлеры ───────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    try:
        user = message.from_user
        source = command.args if command.args else 'direct'
        add_user_first_interaction(user.id)
        text = (
            f"Добро пожаловать, {user.full_name}! Вы находитесь в Финансовом Агрегаторе.\n\n"
            "Мы собрали для вас лучшие финансовые решения с наиболее выгодными условиями.\n\n"
            "Доступно:\n"
            "- Займы от МФО без залога — быстро и удобно\n"
            "- Займы под залог авто или недвижимости — надежные решения\n"
            "- Финансовые инструменты с оптимальными условиями\n\n"
            "Изучите предложения и выберите подходящий вариант!"
        )
        msg = await message.answer(text, reply_markup=get_start_menu())
        await state.update_data(last_bot_message_id=msg.message_id)
        add_stat_row(user.id, user.full_name, user.username, 'start', source)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        try:
            add_pending_event(message.from_user.id, 'start', '')
        except Exception as db_e:
            logger.error(f"Error saving pending start event: {db_e}")


@dp.callback_query()
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    logger.info(f"Callback from user {callback_query.from_user.id}: {data}")
    try:
        state_data = await state.get_data()
        last_bot_message_id = state_data.get('last_bot_message_id')

        async def delete_old_messages():
            if last_bot_message_id:
                try:
                    await bot.delete_message(callback_query.message.chat.id, last_bot_message_id)
                except Exception as e:
                    if "Message to delete not found" not in str(e):
                        logger.error(f"Ошибка удаления старого сообщения: {e}")
            try:
                await callback_query.message.delete()
            except Exception as e:
                if "Message to delete not found" not in str(e):
                    logger.error(f"Ошибка удаления текущего сообщения: {e}")

        chat_id = callback_query.message.chat.id

        if data == 'start_menu':
            await delete_old_messages()
            msg = await bot.send_message(chat_id, "Выберите финпродукт, который вас интересует:", reply_markup=get_main_menu())
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'mfo_150k':
            await delete_old_messages()
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'mfo_150k')
            msg = await bot.send_message(chat_id,
                "Быстрые займы с нулевыми процентами от лицензированных МФО!\n\n"
                "Получите займ без переплат, выбрав проверенную организацию:\n\n"
                "- Минимум документов\n"
                "- Решение за 15 минут\n"
                "- Деньги на карту за часы",
                reply_markup=get_mfo_menu())
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data.startswith('mfo_') and data != 'mfo_150k':
            mfo_name = data[len('mfo_'):]
            if mfo_name in mfo_info:
                await delete_old_messages()
                texts = {
                    'express': (
                        "<b>ЭкспрессДеньги</b>\n\n"
                        "Условия:\n"
                        "- Первый и шестой займ без процентов\n"
                        "- Постоянные клиенты получают бонусы и привилегии\n"
                        "- Кешбэк за выполнение заданий\n\n"
                        "Требования:\n"
                        "- Гражданство РФ, 18-70 лет\n"
                        "- Сумма: от 1 000 до 100 000 ₽\n"
                        "- Срок: до 52 недель\n\n"
                        "Тарифы:\n"
                        "- Новый клиент: от 1 000 до 30 000 ₽ → до 29 дня 0%, далее 0,6%/день\n"
                        "- Долгосрочный: от 31 000 до 100 000 ₽ → 0,6%/день"
                    ),
                    'urgent': (
                        "<b>Срочноденьги</b>\n\n"
                        "Основное преимущество:\n"
                        "- Первый заём полностью бесплатный!\n\n"
                        "Параметры:\n"
                        "- Сумма: от 2 000 до 30 000 ₽\n"
                        "- Срок: до 30 дней\n"
                        "- До 8 минут — деньги на карте\n\n"
                        "Требования:\n"
                        "- Возраст: 18–65 лет\n"
                        "- Гражданство РФ\n"
                        "- Все регионы РФ, кроме: Крым, Дагестан, Чечня, ДНР, ЛНР\n"
                        "- Только паспорт"
                    ),
                    'amoney': (
                        "<b>Кредитный лимит от «А Деньги»</b>\n\n"
                        "Особенность:\n"
                        "- Для новых клиентов первые 7 дней полностью бесплатно\n"
                        "- Далее — 8 руб./день за каждую 1 000 ₽\n\n"
                        "Параметры:\n"
                        "- Сумма: до 30 000 ₽\n"
                        "- Срок: до 30 дней с автопродлением\n\n"
                        "Условия:\n"
                        "- Без поручителей, справок и залога\n"
                        "- Возраст: 18–75 лет\n"
                        "- Гражданство РФ"
                    ),
                    'rocket': (
                        "<b>РокетМЭН</b>\n\n"
                        "Параметры займа:\n"
                        "- Размер: от 3 000 до 30 000 ₽\n"
                        "- Срок: от 5 до 30 дней\n"
                        "- Ставка: 0.8% в день"
                    ),
                    'nebus': (
                        "<b>Небус</b>\n\n"
                        "Требования:\n"
                        "- Возраст: от 18 до 88 лет\n"
                        "- Паспорт РФ\n\n"
                        "Параметры:\n"
                        "- Сумма: от 7 000 до 100 000 ₽\n"
                        "- Срок: от 7 до 365 дней\n"
                        "- Ставка: от 0,48% до 0,8% в день\n"
                        "- Срок рассмотрения: 15 минут"
                    ),
                    'dobro': (
                        "<b>Доброзайм</b>\n\n"
                        "Компания работает с 2011 года.\n\n"
                        "Параметры:\n"
                        "- Сумма: от 1 000 до 100 000 ₽\n"
                        "- Срок: от 4 до 364 дней\n"
                        "- Ставка: от 0% до 1% в день\n\n"
                        "Условия:\n"
                        "- Только паспорт РФ\n"
                        "- Возраст: от 19 до 90 лет\n"
                        "- Без справок, поручителей и залога"
                    ),
                    'finmoll': (
                        "<b>ФИНМОЛЛ</b>\n\n"
                        "Суммы кредита:\n"
                        "- Новый клиент: от 30 000 до 60 000 ₽\n"
                        "- Повторный: от 30 000 до 200 000 ₽\n\n"
                        "Параметры:\n"
                        "- Срок: до 52 недель\n"
                        "- Платежи: еженедельно\n"
                        "- Ставка: от 215% до 250% годовых\n\n"
                        "Условия:\n"
                        "- Без залога и поручительства\n"
                        "- Гражданство РФ\n"
                        "- Возраст: 18–70 лет (новые), 18–75 лет (повторные)\n"
                        "- Постоянный источник дохода"
                    ),
                }
                msg = await bot.send_message(chat_id, texts[mfo_name], reply_markup=get_loan_keyboard(mfo_name), parse_mode='HTML')
                await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'pts_5m':
            await delete_old_messages()
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'pts_5m')
            msg = await bot.send_message(chat_id,
                "Займы под залог ПТС – с минимальными переплатами!\n\n"
                "- Авто остается у вас\n"
                "- Минимальные требования к документам\n"
                "- Решение за 15 минут",
                reply_markup=get_pts_keyboard())
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data in ["pts_drive", "pts_kredi", "pts_cashdrive", "pts_sovcom"]:
            await delete_old_messages()
            pts_texts = {
                "pts_drive": (
                    "<b>Драйв</b>\n\n"
                    "Условия:\n"
                    "- Ставка: от 2 до 7,4% в месяц\n"
                    "- Срок: 61–1094 дня\n"
                    "- Досрочное погашение без комиссий\n"
                    "- Продление срока займа: доступно\n\n"
                    "Требования к авто:\n"
                    "- ТС остается у вас\n"
                    "- Иномарки не старше 2005 года\n"
                    "- Отечественные не старше 2010 года"
                ),
                "pts_kredi": (
                    "<b>Креди</b>\n\n"
                    "Параметры кредита:\n"
                    "- Сумма: от 50 000 до 500 000 ₽\n"
                    "- Срок: от 3 месяцев до 4 лет\n"
                    "- Время рассмотрения: 30 минут\n\n"
                    "Требования к транспорту:\n"
                    "- Легковые: отечественные до 7 лет, иномарки до 20 лет\n"
                    "- Грузовые: отечественные до 10 лет, иномарки до 15 лет\n"
                    "- Получение: на банковскую карту или через СБП"
                ),
                "pts_cashdrive": (
                    "<b>КэшДрайв</b>\n\n"
                    "Требования:\n"
                    "- Гражданство РФ\n"
                    "- Возраст: 21–70 лет\n\n"
                    "Параметры:\n"
                    "- Сумма: от 5 000 до 250 000 ₽\n"
                    "- Срок: от 1 до 24 месяцев\n"
                    "- Ставка: от 20% годовых\n"
                    "- Получение: онлайн на банковскую карту"
                ),
                "pts_sovcom": (
                    "<b>Совком</b>\n\n"
                    "Параметры кредита:\n"
                    "- Ставка: 14,9% годовых\n"
                    "- Сумма: от 150 000 до 15 000 000 ₽\n"
                    "- Срок: от 12 до 60 месяцев\n\n"
                    "Преимущества:\n"
                    "- Онлайн заявка\n"
                    "- Получение день в день\n"
                    "- Авто остается у вас\n\n"
                    "Требуемые документы:\n"
                    "- Паспорт РФ\n"
                    "- СНИЛС или ВУ\n"
                    "- СТС, ПТС, ОСАГО"
                ),
            }
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Получить займ", callback_data=f"get_loan_{data}")],
                [InlineKeyboardButton(text="◀ Назад к списку кредиторов", callback_data="pts_5m")],
            ])
            msg = await bot.send_message(chat_id, pts_texts[data], reply_markup=kb, parse_mode='HTML')
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data.startswith('get_loan_'):
            mfo_name = data.replace('get_loan_', '')
            await delete_old_messages()
            pts_links = {
                "pts_drive":     "https://slds.pro/az72w",
                "pts_kredi":     "https://slds.pro/vcdj7",
                "pts_cashdrive": "https://slds.pro/hxhbv",
                "pts_sovcom":    "https://trk.ppdu.ru/click/ELxQqqRu?erid=Kra23xE7N",
            }
            if mfo_name in pts_links:
                url = pts_links[mfo_name]
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ ПОЛУЧИТЬ ДЕНЬГИ ЗА ПОЛЧАСА!", url=url)],
                    [InlineKeyboardButton(text="◀ Назад к списку кредиторов", callback_data="pts_5m")],
                ])
                image_path = find_image(mfo_name)
                if image_path:
                    msg = await bot.send_photo(chat_id, FSInputFile(image_path),
                        caption=f"Получите займ в {mfo_name.replace('pts_', '').capitalize()}",
                        reply_markup=kb)
                else:
                    msg = await bot.send_message(chat_id,
                        f"Получите займ в {mfo_name.replace('pts_', '').capitalize()}",
                        reply_markup=kb)
                await state.update_data(last_bot_message_id=msg.message_id)

            elif mfo_name in mfo_links:
                link = mfo_links[mfo_name]
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ ЗАБРАТЬ ДЕНЬГИ НА КАРТУ", url=link)],
                    [InlineKeyboardButton(text="◀ Назад к списку МФО", callback_data="mfo_150k")],
                ])
                image_path = find_image(mfo_name)
                if image_path:
                    msg = await bot.send_photo(chat_id, FSInputFile(image_path),
                        caption=f"Получите займ в {mfo_info[mfo_name][0]}",
                        reply_markup=kb)
                else:
                    msg = await bot.send_message(chat_id,
                        f"Получите займ в {mfo_info[mfo_name][0]}",
                        reply_markup=kb)
                await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'back_to_main':
            await delete_old_messages()
            msg = await bot.send_message(chat_id, "Выберите финпродукт, который вас интересует:", reply_markup=get_main_menu())
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'back_to_start':
            await delete_old_messages()
            msg = await bot.send_message(chat_id,
                f"Здравствуйте, {callback_query.from_user.full_name}! Вы находитесь в Финансовом Агрегаторе.\n\n"
                "- Займы от МФО без залога — быстро и удобно\n"
                "- Займы под залог авто или недвижимости\n"
                "- Финансовые инструменты с оптимальными условиями",
                reply_markup=get_start_menu())
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'pledge_50m':
            await delete_old_messages()
            add_stat_row(callback_query.from_user.id, callback_query.from_user.full_name, callback_query.from_user.username, 'pledge_50m')
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оформить займ", url="https://t.me/Odobrenie41Bot")],
                [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")],
            ])
            msg = await bot.send_message(chat_id,
                "Займы под залог недвижимости – выгодные условия от частного инвестора!\n\n"
                "- Квартира, дом или коммерческая недвижимость\n"
                "- Вы остаетесь собственником\n"
                "- Минимум документов\n"
                "- Без банков — быстро и конфиденциально",
                reply_markup=kb)
            await state.update_data(last_bot_message_id=msg.message_id)

        elif data == 'get_pledge_loan':
            await delete_old_messages()
            msg = await bot.send_message(chat_id,
                "Для получения кредита под залог недвижимости:\n\n"
                "1. Нажмите на кнопку ниже\n"
                "2. Заполните анкету\n"
                "3. Загрузите документы на недвижимость\n"
                "4. Получите решение\n\n"
                "Среднее время рассмотрения: 1-3 дня",
                reply_markup=get_pledge_keyboard())
            await state.update_data(last_bot_message_id=msg.message_id)

        await callback_query.answer()

    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            add_pending_event(callback_query.from_user.id, 'callback', data)
        except Exception as db_e:
            logger.error(f"Error saving pending callback event: {db_e}")


@dp.message(Command("help"))
async def help_command_handler(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        text = (
            "<b>Команды администратора:</b>\n\n"
            "- /sourcestats — Статистика по источникам\n"
            "- /userstats ID — Статистика по пользователю\n"
            "- /getstats — Файл статистики\n"
            "- /getdb — Файл базы данных"
        )
    else:
        text = (
            "ℹ Я бот для оформления займов. Выберите нужную опцию в меню.\n"
            "📌 Техподдержка: <a href='https://t.me/Odobrenie41Bot'>@support_finagr</a>"
        )
    await message.answer(text, parse_mode='HTML')


@dp.message(Command("getstats"))
async def send_stats_file(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply('Нет доступа')
    try:
        await message.answer_document(FSInputFile('stats_log.csv'))
    except Exception as e:
        await message.reply(f'Ошибка: {e}')


@dp.message(Command("getdb"))
async def send_db_file(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply('Нет доступа')
    try:
        await message.answer_document(FSInputFile('stats.db'))
    except Exception as e:
        await message.reply(f'Ошибка: {e}')


@dp.message(Command("sourcestats"))
async def send_source_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply('Нет доступа')
    try:
        stats = get_source_stats()
        if not stats:
            return await message.reply("Статистика пока пуста.")
        text = "<b>Статистика по источникам:</b>\n\n"
        for row in stats:
            rate = (row['conversions'] / row['total_users'] * 100) if row['total_users'] > 0 else 0
            text += (
                f"<b>Источник:</b> {row['source']}\n"
                f"- Переходов: {row['total_users']} | Уникальных: {row['unique_users']}\n"
                f"- Конверсии: {row['conversions']} ({rate:.1f}%)\n\n"
            )
        await message.reply(text, parse_mode='HTML')
    except Exception as e:
        await message.reply(f'Ошибка: {e}')


@dp.message(Command("userstats"))
async def send_user_stats(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply('Нет доступа')
    if not command.args:
        return await message.reply("Укажите ID: /userstats ID")
    try:
        user_id = int(command.args)
    except ValueError:
        return await message.reply("ID должен быть числом")
    stats = get_user_stats(user_id)
    if not stats:
        return await message.reply(f"Статистика по {user_id} не найдена.")
    text = f"<b>Статистика пользователя {user_id}:</b>\n\n"
    for row in stats:
        ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S')
        text += f"Дата: {ts}\n- Действие: {row['action']} | Источник: {row['source']}\n\n"
    await message.reply(text, parse_mode='HTML')


# ─── Напоминания и pending events ─────────────────────────────────────

async def send_reminders():
    """Фоновая задача: проверяет и рассылает напоминания каждые 6 часов"""
    while True:
        try:
            users = get_users_for_reminder()
            for day_key, reminder_text in [
                ('day_1',  "Прошло 24 часа! Не упустите возможность получить займ на выгодных условиях."),
                ('day_3',  "Прошло 3 дня! Напоминаем: первый займ под 0%, решение за 15 минут."),
                ('day_10', "Специально для вас — лучшие предложения рынка: сниженные ставки и персональные условия."),
            ]:
                num = day_key.split('_')[1]
                for user in users[day_key]:
                    try:
                        await bot.send_message(user['user_id'], reminder_text, reply_markup=get_main_menu())
                        mark_reminder_sent(user['user_id'], num)
                    except Exception as e:
                        logger.error(f"Ошибка напоминания {day_key} для {user['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Error in send_reminders: {e}")
        await asyncio.sleep(6 * 3600)


async def process_pending_events():
    """Обрабатывает события, которые не были обработаны при предыдущем запуске"""
    for event in get_unprocessed_pending_events():
        try:
            uid = event['user_id']
            if event['event_type'] == 'start':
                await bot.send_message(uid, "Бот снова работает! Выберите подходящий вариант:", reply_markup=get_start_menu())
            else:
                await bot.send_message(uid, "Бот был временно недоступен. Пожалуйста, повторите запрос.")
            mark_pending_event_processed(event['id'])
        except Exception as e:
            logger.error(f"Ошибка pending event {event['id']}: {e}")


# ─── Запуск (polling) ─────────────────────────────────────────────────────

async def main():
    create_table()
    logger.info("База данных инициализирована")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук сброшен")

    await process_pending_events()

    asyncio.create_task(send_reminders())

    logger.info("Бот запущен в режиме polling")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    asyncio.run(main())

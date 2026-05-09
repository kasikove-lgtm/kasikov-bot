"""
Бот Евгения Касикова — запись на консультации + выдача лид-магнита
Хостинг: bothost.ru (бесплатный тариф)
Хранение данных: shelve (файловая БД, работает на bothost)
Безопасность: токен и пароль берутся из переменных окружения
"""

import asyncio
import calendar
import re
import shelve
import os
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГУРАЦИЯ (из переменных окружения) ==========
TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
CHANNEL = os.environ.get("CHANNEL", "@kasikov_psy")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ВСТАВЬ_ПАРОЛЬ_СЮДА")
LEADMAGNET_URL = os.environ.get("LEADMAGNET_URL", "https://t.me/kasikov_psy/219")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== ХРАНИЛИЩЕ (shelve — работает как файловая БД) ==========
DB_FILE = "bot_data"

def db_get(key, default=None):
    with shelve.open(DB_FILE) as db:
        return db.get(key, default)

def db_set(key, value):
    with shelve.open(DB_FILE) as db:
        db[key] = value

def db_del(key):
    with shelve.open(DB_FILE) as db:
        if key in db:
            del db[key]

# Инициализация данных если их нет
def init_db():
    if db_get("slots") is None:
        db_set("slots", {})           # {"2025-05-20": ["14:00", "15:00", "19:00"]}
    if db_get("appointments") is None:
        db_set("appointments", {})    # {"2025-05-20": [{"user_id":..., "time":..., "name":..., "username":...}]}
    if db_get("blocked_users") is None:
        db_set("blocked_users", [])
    if db_get("admin_chats") is None:
        db_set("admin_chats", [])

init_db()

# ========== ЗАЩИТА ==========
user_last_message = {}
user_state = {}  # состояние диалога пользователя

def is_flood(user_id):
    blocked = db_get("blocked_users", [])
    if user_id in blocked:
        return True
    now = datetime.now().timestamp()
    last = user_last_message.get(user_id, 0)
    if now - last < 2:
        return True
    user_last_message[user_id] = now
    return False

def is_blocked(user_id):
    return user_id in db_get("blocked_users", [])

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def notify_admins(text):
    for chat_id in db_get("admin_chats", []):
        try:
            await bot.send_message(chat_id, text, parse_mode="Markdown")
        except:
            pass

# ========== ВСПОМОГАТЕЛЬНЫЕ ==========
def is_valid_time(time_str):
    return bool(re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str))

def get_free_slots_text():
    """Формирует текст со свободными слотами для сообщения 2"""
    slots = db_get("slots", {})
    today = date.today()
    lines = []
    for date_str in sorted(slots.keys()):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            continue
        if d < today:
            continue
        times = slots[date_str]
        if not times:
            continue
        # Занятые слоты
        appts = db_get("appointments", {})
        taken = [r["time"] for r in appts.get(date_str, [])]
        free = [t for t in times if t not in taken]
        if not free:
            continue
        day_label = "Сегодня" if d == today else d.strftime("%d.%m")
        lines.append(f"{day_label} — {', '.join(free)}")
    if lines:
        return "\n".join(lines)
    return "Свободных слотов пока нет — напишите мне напрямую @kasikovevgenii"

# ========== ТЕКСТЫ ==========
def get_msg1():
    return (
        "Здравствуйте. Спасибо, что написали — решиться на первый шаг бывает непросто.\n\n"
        "Я провожу бесплатную 30-минутную вводную консультацию. "
        "За это время разбираемся с тем, что сейчас происходит — и вы уходите с чуть большей ясностью "
        "и пониманием, что делать дальше.\n\n"
        "После встречи вы получите письменный разбор с конкретными темами и рекомендациями. "
        "Он останется с вами независимо от того, решите ли вы продолжать работу со мной."
    )

def get_msg2():
    slots_text = get_free_slots_text()
    return (
        f"Ближайшее свободное время UTC+3:\n{slots_text}\n\n"
        "Работаю по видео — ВКонтакте, Zoom, Яндекс Телемост, Google Meet и другие. "
        "Для комфортной встречи выберите тихое место, где вас не будут отвлекать."
    )

MSG3 = (
    "Чтобы записаться, напишите:\n\n"
    "1. Где удобно созвониться\n"
    "2. Что сейчас происходит — чем больше контекста, тем лучше подготовлюсь\n"
    "3. Удобное время, если слоты выше не подходят"
)

FINAL_MESSAGE = (
    "✅ Запись принята!\n\n"
    "Напишите мне напрямую, чтобы подтвердить детали встречи:\n"
    "👉 @kasikovevgenii"
)

# ========== МЕНЮ ==========
def get_start_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Получить файл «4 шага»", callback_data="get_file")],
        [InlineKeyboardButton(text="🧠 Записаться на консультацию", callback_data="book")],
        [InlineKeyboardButton(text="📊 Мой инвест", url="https://t.me/pro_invest_capital")],
    ])

def get_book_confirm_menu(date_str, time_str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Подтвердить {date_str} {time_str}", callback_data=f"confirm_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="↩️ Выбрать другое время", callback_data="book")],
    ])

# ========== КАЛЕНДАРЬ ПОЛЬЗОВАТЕЛЯ (показывает даты со свободными слотами) ==========
def get_user_calendar(year, month):
    now = datetime.now()
    cal = calendar.monthcalendar(year, month)
    month_names = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
    keyboard = []
    keyboard.append([InlineKeyboardButton(text=f"📅 {month_names[month-1]} {year}", callback_data="no")])
    keyboard.append([InlineKeyboardButton(text=d, callback_data="no") for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])

    today = now.date()
    slots = db_get("slots", {})
    appts = db_get("appointments", {})

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="no"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime(year, month, day).date()
                if date_obj < today:
                    row.append(InlineKeyboardButton(text="·", callback_data="no"))
                else:
                    day_slots = slots.get(date_str, [])
                    taken = [r["time"] for r in appts.get(date_str, [])]
                    free = [t for t in day_slots if t not in taken]
                    if free:
                        row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"usr_{date_str}"))
                    else:
                        row.append(InlineKeyboardButton(text=str(day), callback_data="no_slots"))
        keyboard.append(row)

    nav = []
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    if datetime(prev_year, prev_month, 1).date() >= today.replace(day=1):
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"user_month_{prev_year}_{prev_month}"))
    nav.append(InlineKeyboardButton(text="❌ Закрыть", callback_data="close"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"user_month_{next_year}_{next_month}"))
    keyboard.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== МЕНЮ ВЫБОРА СЛОТА ==========
def get_slots_menu(date_str):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    day_slots = slots.get(date_str, [])
    taken = [r["time"] for r in appts.get(date_str, [])]
    free = [t for t in day_slots if t not in taken]
    keyboard = []
    for t in free:
        keyboard.append([InlineKeyboardButton(text=f"🕐 {t}", callback_data=f"slot_{date_str}_{t}")])
    keyboard.append([InlineKeyboardButton(text="↩️ Другая дата", callback_data="book")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== АДМИН ПАНЕЛЬ ==========
def get_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список записей", callback_data="admin_list")],
        [InlineKeyboardButton(text="➕ Добавить слоты на дату", callback_data="admin_add_slots")],
        [InlineKeyboardButton(text="🗑 Удалить слоты на дату", callback_data="admin_del_slots")],
        [InlineKeyboardButton(text="📅 Посмотреть все слоты", callback_data="admin_view_slots")],
    ])

# ========== ХЭНДЛЕРЫ: СТАРТ ==========
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return
    if await is_subscribed(msg.from_user.id):
        await msg.answer(
            f"Привет, {msg.from_user.first_name}! 👋\n\nВыбери, что тебя интересует:",
            reply_markup=get_start_menu()
        )
    else:
        sub_menu = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
        ])
        await msg.answer(
            "Для доступа к материалам подпишись на канал 👇\n\n"
            f"После подписки нажми «Я подписался»",
            reply_markup=sub_menu
        )

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(cb: types.CallbackQuery):
    if await is_subscribed(cb.from_user.id):
        await cb.message.delete()
        await cb.message.answer(
            f"✅ Отлично, {cb.from_user.first_name}! Выбери, что тебя интересует:",
            reply_markup=get_start_menu()
        )
    else:
        await cb.answer("❌ Подписка не найдена. Подпишись и нажми снова.", show_alert=True)

# ========== СЦЕНАРИЙ 1: ФАЙЛ ==========
@dp.callback_query(lambda c: c.data == "get_file")
async def give_file(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "📄 Держи файл «4 шага выхода из расставания» — 30 страниц практики.\n\n"
        f"👉 {LEADMAGNET_URL}\n\n"
        "Если после прочтения захочешь разобрать свою ситуацию лично — я провожу "
        "бесплатную 30-минутную консультацию. Нажми кнопку ниже 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Записаться на консультацию", callback_data="book")]
        ])
    )

# ========== СЦЕНАРИЙ 2: ЗАПИСЬ ==========
@dp.callback_query(lambda c: c.data == "book")
async def book_consult(cb: types.CallbackQuery):
    if is_blocked(cb.from_user.id):
        await cb.answer("🚫 Доступ закрыт.", show_alert=True)
        return
    await cb.answer()
    uid = cb.from_user.id
    # Сбрасываем состояние
    if uid in user_state:
        del user_state[uid]

    await cb.message.answer(get_msg1())
    await asyncio.sleep(1)
    await cb.message.answer(get_msg2())
    await asyncio.sleep(1)
    now = datetime.now()
    await cb.message.answer(
        "Выбери удобную дату — ✅ означает, что есть свободные слоты:",
        reply_markup=get_user_calendar(now.year, now.month)
    )

@dp.callback_query(lambda c: c.data == "no_slots")
async def no_slots_cb(cb: types.CallbackQuery):
    await cb.answer("На этот день слотов нет", show_alert=True)

@dp.callback_query(lambda c: c.data and c.data.startswith("usr_"))
async def user_date_selected(cb: types.CallbackQuery):
    if is_blocked(cb.from_user.id):
        await cb.answer("🚫", show_alert=True)
        return
    date_str = cb.data[4:]  # убираем "usr_"
    await cb.message.delete()
    await cb.message.answer(
        f"📅 Выбрана дата: *{date_str}*\n\nВыбери удобное время:",
        parse_mode="Markdown",
        reply_markup=get_slots_menu(date_str)
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("slot_"))
async def slot_selected(cb: types.CallbackQuery):
    if is_blocked(cb.from_user.id):
        await cb.answer("🚫", show_alert=True)
        return
    _, date_str, time_str = cb.data.split("_", 2)
    uid = cb.from_user.id
    user_state[uid] = {"step": "name", "date": date_str, "time": time_str}
    await cb.message.delete()
    await cb.message.answer(
        f"✅ Дата: *{date_str}*, время: *{time_str}* МСК\n\n"
        "Теперь напиши своё *имя* и кратко — *что сейчас происходит* "
        "(чем больше контекста, тем лучше подготовлюсь к встрече):",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("confirm_"))
async def confirm_booking(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    date_str, time_str = parts[1], parts[2]
    uid = cb.from_user.id
    # Финализируем запись
    if uid in user_state and "name" in user_state[uid]:
        name = user_state[uid]["name"]
        appts = db_get("appointments", {})
        entry = {
            "user_id": uid,
            "name": name,
            "time": time_str,
            "username": cb.from_user.username or "нет username"
        }
        if date_str not in appts:
            appts[date_str] = []
        appts[date_str].append(entry)
        db_set("appointments", appts)
        del user_state[uid]
        await cb.message.delete()
        await cb.message.answer(FINAL_MESSAGE)
        await notify_admins(
            f"🔔 *Новая запись!*\n"
            f"📅 {date_str} в {time_str} МСК\n"
            f"👤 {name}\n"
            f"🆔 @{cb.from_user.username or 'нет username'}\n"
            f"🔑 ID: {uid}"
        )

# ========== НАВИГАЦИЯ КАЛЕНДАРЯ ==========
@dp.callback_query(lambda c: c.data and c.data.startswith("user_month_"))
async def user_nav(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    year, month = int(parts[2]), int(parts[3])
    await cb.message.edit_reply_markup(reply_markup=get_user_calendar(year, month))

@dp.callback_query(lambda c: c.data == "close")
async def close_cal(cb: types.CallbackQuery):
    await cb.message.delete()

@dp.callback_query(lambda c: c.data == "no")
async def ignore(cb: types.CallbackQuery):
    await cb.answer()

# ========== ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТА ==========
@dp.message()
async def handle_text(msg: types.Message):
    uid = msg.from_user.id
    text = msg.text.strip() if msg.text else ""

    if is_blocked(uid):
        return
    if is_flood(uid):
        return

    # Авторизация в админ-панель
    if text == ADMIN_PASSWORD:
        chats = db_get("admin_chats", [])
        if uid not in chats:
            chats.append(uid)
            db_set("admin_chats", chats)
        await msg.answer("✅ Добро пожаловать в панель управления!", reply_markup=get_admin_menu())
        return

    # Обработка состояния — шаг "name" (человек пишет своё имя и проблему)
    if uid in user_state:
        state = user_state[uid]
        if state.get("step") == "name":
            state["name"] = text
            state["step"] = "confirm"
            date_str = state["date"]
            time_str = state["time"]
            await msg.answer(
                f"📋 Проверь данные записи:\n\n"
                f"📅 Дата: *{date_str}*\n"
                f"🕐 Время: *{time_str}* МСК\n"
                f"👤 Имя и ситуация: _{text}_\n\n"
                "Всё верно?",
                parse_mode="Markdown",
                reply_markup=get_book_confirm_menu(date_str, time_str)
            )
            return

    # Если ничего не совпало — показываем меню
    if await is_subscribed(uid):
        await msg.answer("Выбери действие:", reply_markup=get_start_menu())
    else:
        sub_menu = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
        ])
        await msg.answer("Сначала подпишись на канал:", reply_markup=sub_menu)

# ========== АДМИН: СПИСОК ЗАПИСЕЙ ==========
@dp.callback_query(lambda c: c.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    appts = db_get("appointments", {})
    if not appts:
        await cb.message.answer("📭 Записей пока нет.")
        return
    today = date.today()
    text = "📋 *Предстоящие записи:*\n\n"
    found = False
    for date_str in sorted(appts.keys()):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            continue
        if d < today:
            continue
        for rec in appts[date_str]:
            text += f"📅 {date_str} {rec['time']} МСК\n👤 {rec['name']}\n🆔 @{rec['username']}\n\n"
            found = True
    if not found:
        text = "📭 Предстоящих записей нет."
    await cb.message.answer(text, parse_mode="Markdown")

# ========== АДМИН: ДОБАВИТЬ СЛОТЫ ==========
@dp.callback_query(lambda c: c.data == "admin_add_slots")
async def admin_add_slots_start(cb: types.CallbackQuery):
    uid = cb.from_user.id
    user_state[uid] = {"step": "admin_add_date"}
    await cb.message.answer(
        "Введи дату в формате *ГГГГ-ММ-ДД* (например `2025-05-22`):",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_del_slots")
async def admin_del_slots_start(cb: types.CallbackQuery):
    uid = cb.from_user.id
    user_state[uid] = {"step": "admin_del_date"}
    await cb.message.answer(
        "Введи дату для удаления слотов в формате *ГГГГ-ММ-ДД*:",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_view_slots")
async def admin_view_slots(cb: types.CallbackQuery):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    today = date.today()
    if not slots:
        await cb.message.answer("Слотов пока нет. Добавь через «Добавить слоты на дату».")
        return
    text = "📅 *Все слоты:*\n\n"
    for date_str in sorted(slots.keys()):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            continue
        if d < today:
            continue
        taken = [r["time"] for r in appts.get(date_str, [])]
        lines = []
        for t in slots[date_str]:
            mark = "🔴 занято" if t in taken else "🟢 свободно"
            lines.append(f"  {t} — {mark}")
        text += f"*{date_str}*\n" + "\n".join(lines) + "\n\n"
    await cb.message.answer(text, parse_mode="Markdown")

# Обработка текста для админ-шагов встроена в handle_text выше — добавим отдельный приоритетный хэндлер
@dp.message()
async def handle_admin_steps(msg: types.Message):
    uid = msg.from_user.id
    text = msg.text.strip() if msg.text else ""
    if uid not in user_state:
        return
    state = user_state[uid]

    if state.get("step") == "admin_add_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Неверный формат. Пример: `2025-05-22`", parse_mode="Markdown")
            return
        state["admin_date"] = text
        state["step"] = "admin_add_times"
        await msg.answer(
            f"Дата: *{text}*\n\nТеперь введи свободные слоты через запятую:\n"
            "Пример: `14:00, 15:00, 19:00`",
            parse_mode="Markdown"
        )

    elif state.get("step") == "admin_add_times":
        times_raw = [t.strip() for t in text.split(",")]
        valid = [t for t in times_raw if is_valid_time(t)]
        invalid = [t for t in times_raw if not is_valid_time(t)]
        if not valid:
            await msg.answer("❌ Ни одно время не распознано. Формат: `14:00, 15:00`", parse_mode="Markdown")
            return
        date_str = state["admin_date"]
        slots = db_get("slots", {})
        if date_str not in slots:
            slots[date_str] = []
        for t in valid:
            if t not in slots[date_str]:
                slots[date_str].append(t)
        slots[date_str] = sorted(slots[date_str])
        db_set("slots", slots)
        del user_state[uid]
        resp = f"✅ Слоты на *{date_str}* добавлены: {', '.join(valid)}"
        if invalid:
            resp += f"\n⚠️ Не распознаны: {', '.join(invalid)}"
        await msg.answer(resp, parse_mode="Markdown", reply_markup=get_admin_menu())

    elif state.get("step") == "admin_del_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Неверный формат. Пример: `2025-05-22`", parse_mode="Markdown")
            return
        slots = db_get("slots", {})
        if text in slots:
            del slots[text]
            db_set("slots", slots)
            await msg.answer(f"✅ Все слоты на *{text}* удалены.", parse_mode="Markdown", reply_markup=get_admin_menu())
        else:
            await msg.answer(f"❌ Слотов на *{text}* нет.", parse_mode="Markdown", reply_markup=get_admin_menu())
        del user_state[uid]

# ========== ЗАПУСК ==========
async def main():
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

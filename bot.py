"""
Бот Евгения Касикова v4.0
"""

import asyncio
import os
import shelve
import calendar
import re
import logging
import sys
import io
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_OK = True
except:
    EXCEL_OK = False

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL = os.environ.get("CHANNEL", "@kasikov_psy")
LEADMAGNET_URL = "https://t.me/kasikov_psy/230"
ADMIN_USERNAMES = ["Iozteam", "kasikovevgenii"]

PLATFORM_LINKS = {
    "Zoom": "https://us04web.zoom.us/j/5806296223?pwd=Kk1taS7afUkbbdxQXnXk2FCc7Sglz4.1",
    "ВКонтакте": "https://vk.ru/call/join/WcLhNuB_1k2NNkqmVirjcn932fkIUIgkQMQomB0kDtA",
    "Яндекс Телемост": "https://telemost.yandex.ru/j/41045386326619",
    "Google Meet": "https://meet.google.com/xea-ubvn-sdg",
    "Microsoft Teams": "https://teams.live.com/meet/93982412886719?p=qS9poHinQUXXWNrRIp",
    "MAX": "https://max.ru/joincall/ahmoeViSGUdzx948lSbeXgSXluuzdJW0h3HVmOepwtc",
}

DURATIONS = ["30 мин", "1 час", "1.5 часа", "2 часа", "2.5 часа", "3 часа"]
DURATION_SLOTS = {"30 мин": 1, "1 час": 2, "1.5 часа": 3, "2 часа": 4, "2.5 часа": 5, "3 часа": 6}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== МАТ ==========
BAD_WORDS = [
    "блять","бля","блядь","блядина","хуй","хуйня","хуёво","хуево","хуёвый",
    "хуевый","хуила","хуило","пиздец","пизда","пиздатый","пизданутый","пиздануть",
    "пиздить","ёбаный","ёб","еб","ебать","ебёт","ебал","ебаный","ебанутый",
    "ёбнутый","ёбнуть","ебнуть","ебись","еби","сука","суки","сучка","сучара",
    "мудак","мудила","залупа","шлюха","шлюшка","пидор","пидорас","гандон",
    "ублюдок","долбоёб","долбоеб","дрочить","дрочила","манда","срань","жопа",
    "педик","педераст","нахуй","нахер","ёпт","епт","курва","дерьмо",
    "fuck","shit","bitch","asshole","cunt","whore","кака","писька","шалава",
]

def has_bad_words(text):
    t = text.lower()
    return any(w in t for w in BAD_WORDS)

def is_random_text(text):
    words = text.split()
    if not words:
        return True
    random_count = sum(1 for w in words if len(w) <= 2 and not w.isalpha())
    return random_count > len(words) * 0.5

# ========== ХРАНИЛИЩЕ ==========
DB_FILE = "bot_data"

def db_get(key, default=None):
    with shelve.open(DB_FILE) as db:
        return db.get(key, default)

def db_set(key, value):
    with shelve.open(DB_FILE) as db:
        db[key] = value

def init_db():
    defaults = [
        ("slots", {}), ("appointments", {}),
        ("admin_chats", []), ("blocked_users", []),
        ("logs", []), ("blocked_dates", []),
        ("all_users", []), ("violations", {}),
        ("regular_clients", []),
    ]
    for key, val in defaults:
        if db_get(key) is None:
            db_set(key, val)

init_db()

# ========== СОСТОЯНИЯ ==========
user_state = {}
user_flood = {}
user_flood_count = {}

def track_violation(uid, vtype):
    violations = db_get("violations", {})
    key = str(uid)
    if key not in violations:
        violations[key] = {"bad_words": 0, "spam": 0, "random": 0}
    violations[key][vtype] = violations[key].get(vtype, 0) + 1
    db_set("violations", violations)
    return violations[key][vtype]

def is_flood(uid):
    now = datetime.now().timestamp()
    last = user_flood.get(uid, 0)
    if now - last < 2:
        cnt = user_flood_count.get(uid, 0) + 1
        user_flood_count[uid] = cnt
        if cnt > 15:
            count = track_violation(uid, "spam")
            if count >= 5:
                auto_block(uid, "спам стартами")
        return True
    user_flood[uid] = now
    user_flood_count[uid] = 0
    return False

def is_blocked(uid):
    return uid in db_get("blocked_users", [])

def auto_block(uid, reason):
    blocked = db_get("blocked_users", [])
    if uid not in blocked:
        blocked.append(uid)
        db_set("blocked_users", blocked)
        log.warning(f"АВТОБЛОК: {uid} — {reason}")
        asyncio.create_task(notify_admins(
            f"🚫 *Автоблок*\nID: {uid}\nПричина: {reason}"
        ))

def is_admin(username):
    if not username:
        return False
    return username.lower() in [u.lower() for u in ADMIN_USERNAMES]

def register_user(uid):
    users = db_get("all_users", [])
    if uid not in users:
        users.append(uid)
        db_set("all_users", users)

def log_action(uid, username, action):
    logs = db_get("logs", [])
    entry = {
        "uid": uid, "username": username or "нет",
        "action": action,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    logs.append(entry)
    if len(logs) > 1000:
        logs = logs[-1000:]
    db_set("logs", logs)
    log.info(f"[{entry['time']}] @{entry['username']} (ID:{uid}) — {action}")

# ========== ПОДПИСКА ==========
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def notify_admins(text, reply_markup=None):
    for chat_id in db_get("admin_chats", []):
        try:
            await bot.send_message(chat_id, text, parse_mode="Markdown",
                                   reply_markup=reply_markup)
        except:
            pass

# ========== СЛОТЫ ==========
def generate_day_slots():
    slots = []
    cur = datetime.strptime("10:00", "%H:%M")
    end = datetime.strptime("21:00", "%H:%M")
    while cur <= end:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=30)
    return slots

ALL_DAY_SLOTS = generate_day_slots()

def get_free_slots(date_str):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    day_slots = slots.get(date_str, [])
    taken = [r["time"] for r in appts.get(date_str, [])]
    return [t for t in day_slots if t not in taken]

def has_booking_today(uid, date_str):
    appts = db_get("appointments", {})
    for rec in appts.get(date_str, []):
        if rec["user_id"] == uid:
            return True
    return False

# ========== ТЕКСТЫ ==========
TEXT_ABOUT = """👤 *Обо мне*

Меня зовут Евгений Касиков.

Я не классический психолог в пиджаке с дипломом на стене. Я человек, который сам прошёл через то, с чем сейчас, скорее всего, пришёл ты.

Двое детей и развод после 15 лет брака. Расставание после пяти лет отношений. Полный финансовый крах. И каждый раз казалось, что мир просто взял и перевернулся.

Я знаю это изнутри. Не по книжкам.

15 лет в продажах — от менеджера до директора по региону. Шесть собственных бизнесов. Флиппинг недвижимости — 175+ объектов за 10 лет.

А потом всё рухнуло разом. Я упал и разбился в дребезги. И не стал делать вид, что всё нормально. Пересобрал себя. Медленно, честно.

Сегодня — более 10 лет практики, более 200 часов личной и групповой терапии, более 200 реальных историй в работе с отношениями.

Я говорю на твоём языке. Смотрю не сверху — а рядом. Потому что я там был.

👉 @kasikovevgenii"""

TEXT_HOW_1 = """⚙️ *Как я работаю*

Сразу скажу честно — чтобы ты понял, подходим ли мы друг другу.

Я не даю советов как жить. Не говорю «сделай вот так». Если ты ищешь именно это — я не тот специалист.

Я помогаю тебе увидеть то, что ты сам не видишь. Твои паттерны, автоматические реакции, то как ты строишь отношения. Задаю вопросы — иногда неудобные. Не осуждаю — но и не сюсюкаю.

Решения всегда остаются за тобой. Работа идёт в живых сессиях — не в переписке.

Я работаю *интегративно* — выбираю конкретный метод под конкретного человека, под его состояние и этап."""

TEXT_HOW_2 = """*НЛП* — хаос в голове в первые недели. Меняет не событие, а то как оно живёт внутри.

*Транзактный анализ (Эрик Бёрн)* — почему снова похожая ситуация. Из какого эго-состояния ты живёшь в отношениях.

*Психология привязанности* — почему так больно. Это не слабость — это твой тип привязанности.

*EMDR* — измена, предательство, внезапный уход. Работает с тем что застряло и не переваривается.

*Работа с телом* — боль живёт не только в голове. Сжатие в груди, тяжесть, невозможность дышать полно.

*Гештальт* — незавершённые разговоры, невысказанное. Завершает прошлое через настоящий момент."""

TEXT_HOW_3 = """*IFS — части личности* — одна часть хочет вернуться, другая знает что нельзя. Помогает перестать воевать с собой.

*Схема-терапия* — «я недостаточно хорош», «меня всё равно бросят». Сформировались рано, тянут в одни и те же ситуации.

*Юнгианский подход* — когда не можешь отпустить. Возвращаем своё золото себе.

*Психодинамический подход* — почему ты выбираешь именно таких людей.

*Травма-информированный подход* — работаю аккуратно, не ломлюсь в то к чему ты ещё не готов.

*Экзистенциальный подход* — кризис идентичности после развода — это нормально.

*Мужская психология* — мужчины горюют иначе, восстанавливаются иначе. Я это учитываю."""

TEXT_PRICE = """💼 *Условия платных консультаций*

*Разовая консультация*
60 минут — 5 000 руб.

*Пакет «Глубокая работа»*
5 консультаций (5 часов) — 20 000 руб.
_экономия 5 000 руб._

Работаю по видео — Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX.

После первой бесплатной встречи ты сам решаешь — продолжать или нет.

Для записи: @kasikovevgenii"""

TEXT_FREE_1 = """Здравствуйте. Спасибо, что написали — решиться на первый шаг бывает непросто.

Я провожу бесплатную 30-минутную вводную консультацию. За это время разбираемся с тем, что сейчас происходит — и вы уходите с чуть большей ясностью и пониманием, что делать дальше.

После встречи вы получите письменный разбор с конкретными темами и рекомендациями. Он останется с вами независимо от того, решите ли вы продолжать работу со мной."""

TEXT_FREE_2 = """Работаю по видео — ВКонтакте, Zoom, Яндекс Телемост, Google Meet, Teams, MAX.

Для комфортной встречи выберите тихое место, где вас не будут отвлекать.

Выберите удобную дату 👇
✅ — есть свободные слоты"""

# ========== МЕНЮ ==========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Первая бесплатная консультация",
                              callback_data="free_consult")],
        [InlineKeyboardButton(text="💼 Условия платных консультаций",
                              callback_data="paid_consult")],
        [InlineKeyboardButton(text="📄 Гайд «4 шага после расставания»",
                              callback_data="get_guide")],
        [InlineKeyboardButton(text="👤 Обо мне", callback_data="about")],
        [InlineKeyboardButton(text="📢 Подписаться на канал",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
    ])

def about_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Обо мне", callback_data="about_me")],
        [InlineKeyboardButton(text="⚙️ Как я работаю", callback_data="how_i_work")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")],
    ])

def back_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Главное меню", callback_data="back_main")],
    ])

def paid_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")],
    ])

def duration_menu():
    rows = []
    for d in DURATIONS:
        rows.append([InlineKeyboardButton(text=d, callback_data=f"dur_{d}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def platform_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Zoom", callback_data="platform_Zoom")],
        [InlineKeyboardButton(text="📱 ВКонтакте", callback_data="platform_ВКонтакте")],
        [InlineKeyboardButton(text="💻 Яндекс Телемост",
                              callback_data="platform_Яндекс Телемост")],
        [InlineKeyboardButton(text="📹 Google Meet", callback_data="platform_Google Meet")],
        [InlineKeyboardButton(text="🖥 Microsoft Teams",
                              callback_data="platform_Microsoft Teams")],
        [InlineKeyboardButton(text="📲 MAX", callback_data="platform_MAX")],
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить слоты", callback_data="adm_add")],
        [InlineKeyboardButton(text="📅 Открыть весь день",
                              callback_data="adm_open_day")],
        [InlineKeyboardButton(text="🗓 Открыть неделю",
                              callback_data="adm_open_week")],
        [InlineKeyboardButton(text="❌ Закрыть день", callback_data="adm_close_day")],
        [InlineKeyboardButton(text="🚫 Заблокировать диапазон дат",
                              callback_data="adm_block_range")],
        [InlineKeyboardButton(text="🔄 Перенести запись", callback_data="adm_move")],
        [InlineKeyboardButton(text="👥 Постоянные клиенты",
                              callback_data="adm_regular")],
        [InlineKeyboardButton(text="📋 Все записи", callback_data="adm_list")],
        [InlineKeyboardButton(text="📅 Мои слоты", callback_data="adm_slots")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="📤 Рассылка всем", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📊 Excel отчёт", callback_data="adm_excel")],
        [InlineKeyboardButton(text="🚫 Заблокированные",
                              callback_data="adm_blocked")],
        [InlineKeyboardButton(text="📊 Логи", callback_data="adm_logs")],
    ])

# ========== КАЛЕНДАРЬ ==========
def user_calendar(year, month):
    today = date.today()
    month_names = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                   'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
    cal = calendar.monthcalendar(year, month)
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    blocked_dates = db_get("blocked_dates", [])
    keyboard = []
    keyboard.append([InlineKeyboardButton(
        text=f"📅 {month_names[month-1]} {year}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(text=d, callback_data="ignore")
                     for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                d = date(year, month, day)
                ds = d.strftime("%Y-%m-%d")
                if d < today or ds in blocked_dates:
                    row.append(InlineKeyboardButton(text="·",
                                                    callback_data="ignore"))
                else:
                    free = get_free_slots(ds)
                    if free:
                        row.append(InlineKeyboardButton(
                            text=f"✅{day}", callback_data=f"day_{ds}"))
                    else:
                        row.append(InlineKeyboardButton(
                            text=str(day), callback_data="no_slots"))
        keyboard.append(row)
    nav = []
    pm = month-1 if month > 1 else 12
    py = year if month > 1 else year-1
    nm = month+1 if month < 12 else 1
    ny = year if month < 12 else year+1
    if date(py, pm, 1) >= today.replace(day=1):
        nav.append(InlineKeyboardButton(text="◀️",
                                        callback_data=f"cal_{py}_{pm}"))
    else:
        nav.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    nav.append(InlineKeyboardButton(text="❌", callback_data="close_cal"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cal_{ny}_{nm}"))
    keyboard.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def slots_menu(date_str):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    day_slots = slots.get(date_str, [])
    taken = [r["time"] for r in appts.get(date_str, [])]
    keyboard = []
    row = []
    for t in day_slots:
        is_taken = t in taken
        emoji = "🔴" if is_taken else "🟢"
        cb = "slot_taken" if is_taken else f"slot_{date_str}_{t}"
        row.append(InlineKeyboardButton(text=f"{emoji}{t}", callback_data=cb))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="↩️ Другая дата",
                                          callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== EXCEL ==========
def generate_excel(date_from, date_to):
    if not EXCEL_OK:
        return None
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Записи"
    headers = ["Дата", "Время", "Тип", "Имя", "Username",
               "Платформа", "Длительность", "Описание"]
    header_fill = PatternFill("solid", fgColor="2E86AB")
    header_font = Font(color="FFFFFF", bold=True)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    appts = db_get("appointments", {})
    row = 2
    for ds in sorted(appts.keys()):
        if ds < date_from or ds > date_to:
            continue
        for rec in appts[ds]:
            ws.cell(row=row, column=1, value=ds)
            ws.cell(row=row, column=2, value=rec.get("time", ""))
            ws.cell(row=row, column=3,
                    value="Платная" if rec.get("type") == "paid" else "Бесплатная")
            ws.cell(row=row, column=4, value=rec.get("name", ""))
            ws.cell(row=row, column=5, value=f"@{rec.get('username', '')}")
            ws.cell(row=row, column=6, value=rec.get("platform", ""))
            ws.cell(row=row, column=7, value=rec.get("duration", ""))
            ws.cell(row=row, column=8, value=rec.get("description", ""))
            row += 1
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# ========== НАПОМИНАНИЯ ==========
async def reminder_loop():
    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.now()
            appts = db_get("appointments", {})
            changed = False
            for ds, records in appts.items():
                for rec in records:
                    try:
                        appt_dt = datetime.strptime(
                            f"{ds} {rec['time']}", "%Y-%m-%d %H:%M")
                    except:
                        continue
                    diff = (appt_dt - now).total_seconds() / 60
                    if 59 <= diff <= 61:
                        platform = rec.get("platform", "")
                        link = PLATFORM_LINKS.get(platform, "")
                        if not rec.get("reminded_client"):
                            try:
                                await bot.send_message(
                                    rec["user_id"],
                                    f"⏰ Напоминание!\n\n"
                                    f"Через час наша встреча — {rec['time']} МСК\n"
                                    f"Платформа: {platform}\n"
                                    f"{'🔗 ' + link if link else ''}\n\n"
                                    "Если что-то изменилось — напишите: "
                                    "@kasikovevgenii"
                                )
                                rec["reminded_client"] = True
                                changed = True
                            except:
                                pass
                        if not rec.get("reminded_admin"):
                            type_label = ("💼 Платная" if rec.get("type") == "paid"
                                          else "🆓 Бесплатная")
                            await notify_admins(
                                f"⏰ *Через час консультация!*\n\n"
                                f"📅 {ds} в {rec['time']} МСК\n"
                                f"{type_label}\n"
                                f"👤 {rec.get('name','—')}\n"
                                f"📱 {platform}\n"
                                f"⏱ {rec.get('duration','—')}\n"
                                f"🆔 @{rec.get('username','—')}"
                            )
                            rec["reminded_admin"] = True
                            changed = True
            if changed:
                db_set("appointments", appts)
        except Exception as e:
            log.error(f"reminder_loop: {e}")

# ========== ХЭНДЛЕРЫ ==========

@dp.message(Command("start"))
async def start(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return
    if is_flood(msg.from_user.id):
        return
    register_user(msg.from_user.id)
    log_action(msg.from_user.id, msg.from_user.username, "/start")
    if is_admin(msg.from_user.username):
        chats = db_get("admin_chats", [])
        if msg.from_user.id not in chats:
            chats.append(msg.from_user.id)
            db_set("admin_chats", chats)
    await msg.answer(
        f"Привет, {msg.from_user.first_name} 👋\n\n"
        "Я помогаю людям пройти через расставание — без застревания "
        "и с пониманием что делать дальше.\n\nЧто тебя интересует?",
        reply_markup=main_menu()
    )

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if not is_admin(msg.from_user.username):
        return
    chats = db_get("admin_chats", [])
    if msg.from_user.id not in chats:
        chats.append(msg.from_user.id)
        db_set("admin_chats", chats)
    await msg.answer("🔐 *Панель администратора*",
                     parse_mode="Markdown", reply_markup=admin_menu())

@dp.message(Command("stop"))
async def stop_cmd(msg: types.Message):
    if not is_admin(msg.from_user.username):
        return
    await msg.answer("🛑 Бот останавливается...")
    log.info("БОТ ОСТАНОВЛЕН командой /stop")
    await dp.stop_polling()

@dp.callback_query(F.data == "about")
async def about(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Выбери:", reply_markup=about_menu())

@dp.callback_query(F.data == "about_me")
async def about_me(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(TEXT_ABOUT, parse_mode="Markdown",
                             reply_markup=back_main_kb())

@dp.callback_query(F.data == "how_i_work")
async def how_i_work(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(TEXT_HOW_1, parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await cb.message.answer(TEXT_HOW_2, parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await cb.message.answer(TEXT_HOW_3, parse_mode="Markdown",
                             reply_markup=back_main_kb())

@dp.callback_query(F.data == "back_main")
async def back_to_main(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Главное меню:", reply_markup=main_menu())

@dp.callback_query(F.data == "get_guide")
async def get_guide(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user.id, cb.from_user.username, "get_guide")
    sub_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался",
                              callback_data="check_sub_guide")],
    ])
    await cb.message.answer(
        "📄 *Гайд «4 шага выхода из расставания»* — 30 страниц практики.\n\n"
        "Чтобы получить — подпишись на канал. Там я каждый день разбираю "
        "реальные ситуации 👇",
        parse_mode="Markdown", reply_markup=sub_kb)

@dp.callback_query(F.data == "check_sub_guide")
async def check_sub_guide(cb: types.CallbackQuery):
    if await is_subscribed(cb.from_user.id):
        log_action(cb.from_user.id, cb.from_user.username, "got_guide")
        await cb.message.delete()
        await cb.message.answer(
            f"✅ Держи гайд!\n\n👉 {LEADMAGNET_URL}\n\n"
            "Если захочешь разобрать ситуацию лично — "
            "провожу бесплатную 30-минутную консультацию 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",
                                     callback_data="free_consult")
            ]])
        )
    else:
        await cb.answer("❌ Подписка не найдена.", show_alert=True)

@dp.callback_query(F.data == "paid_consult")
async def paid_consult(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user.id, cb.from_user.username, "paid_consult")
    await cb.message.answer(TEXT_PRICE, parse_mode="Markdown",
                             reply_markup=paid_menu())

@dp.callback_query(F.data == "book_paid")
async def book_paid(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    user_state[uid] = {"type": "paid"}
    await cb.message.answer(
        "Выбери удобную дату 👇\n✅ — есть свободные слоты",
        reply_markup=user_calendar(date.today().year, date.today().month))

@dp.callback_query(F.data == "free_consult")
async def free_consult(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    user_state[uid] = {"type": "free"}
    log_action(uid, cb.from_user.username, "free_consult")
    await cb.message.answer(TEXT_FREE_1)
    await asyncio.sleep(1)
    await cb.message.answer(TEXT_FREE_2,
        reply_markup=user_calendar(date.today().year, date.today().month))

@dp.callback_query(F.data == "no_slots")
async def no_slots(cb: types.CallbackQuery):
    await cb.answer("На этот день слотов нет", show_alert=True)

@dp.callback_query(F.data == "slot_taken")
async def slot_taken_cb(cb: types.CallbackQuery):
    await cb.answer("Это время занято 🔴", show_alert=True)

@dp.callback_query(F.data.startswith("day_"))
async def day_selected(cb: types.CallbackQuery):
    date_str = cb.data[4:]
    uid = cb.from_user.id
    if has_booking_today(uid, date_str):
        await cb.answer(
            "У вас уже есть запись на этот день. "
            "Для изменения напишите @kasikovevgenii",
            show_alert=True)
        return
    state = user_state.get(uid, {})
    state["date"] = date_str
    user_state[uid] = state
    log_action(uid, cb.from_user.username, f"day_{date_str}")
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{date_str}*\n\nВыбери время:\n🟢 свободно  🔴 занято",
        parse_mode="Markdown", reply_markup=slots_menu(date_str))

@dp.callback_query(F.data.startswith("cal_"))
async def cal_nav(cb: types.CallbackQuery):
    _, y, m = cb.data.split("_")
    await cb.message.edit_reply_markup(
        reply_markup=user_calendar(int(y), int(m)))

@dp.callback_query(F.data == "close_cal")
async def close_cal(cb: types.CallbackQuery):
    await cb.message.delete()

@dp.callback_query(F.data == "ignore")
async def ignore_cb(cb: types.CallbackQuery):
    await cb.answer()

@dp.callback_query(F.data.startswith("slot_"))
async def slot_selected(cb: types.CallbackQuery):
    if cb.data == "slot_taken":
        await cb.answer("Это время занято 🔴", show_alert=True)
        return
    parts = cb.data.split("_")
    date_str = parts[1]
    time_str = parts[2]
    uid = cb.from_user.id
    consult_type = user_state.get(uid, {}).get("type", "free")
    log_action(uid, cb.from_user.username, f"slot_{date_str}_{time_str}")
    await cb.message.delete()

    if consult_type == "free":
        user_state[uid] = {
            "step": "awaiting_info",
            "date": date_str,
            "time": time_str,
            "type": "free",
            "duration": "30 мин"
        }
        await cb.message.answer(
            f"✅ *{date_str}* в *{time_str}* МСК\n\n"
            "Напиши своё *имя* и кратко — *что сейчас происходит*.\n"
            "Чем больше контекста — тем продуктивнее встреча:",
            parse_mode="Markdown")
    else:
        user_state[uid] = {
            "step": "awaiting_duration",
            "date": date_str,
            "time": time_str,
            "type": "paid"
        }
        await cb.message.answer(
            f"✅ *{date_str}* в *{time_str}* МСК\n\nВыбери длительность сессии:",
            parse_mode="Markdown", reply_markup=duration_menu())

@dp.callback_query(F.data.startswith("dur_"))
async def duration_selected(cb: types.CallbackQuery):
    duration = cb.data[4:]
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    state["duration"] = duration
    state["step"] = "awaiting_info"
    user_state[uid] = state
    type_label = "💼 платная" if state.get("type") == "paid" else "🆓 бесплатная"
    await cb.message.answer(
        f"⏱ Длительность: *{duration}* ({type_label})\n\n"
        "Напиши своё *имя* и кратко — *что сейчас происходит*.\n"
        "Чем больше контекста — тем продуктивнее встреча:",
        parse_mode="Markdown")

@dp.callback_query(F.data.startswith("platform_"))
async def platform_selected(cb: types.CallbackQuery):
    platform = cb.data[9:]
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    state["platform"] = platform
    state["step"] = "confirm"
    user_state[uid] = state
    date_str = state["date"]
    time_str = state["time"]
    consult_type = state.get("type", "free")
    duration = state.get("duration", "—")
    type_label = "💼 Платная" if consult_type == "paid" else "🆓 Бесплатная"
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись",
                              callback_data=f"confirm_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="↩️ Начать заново",
                              callback_data="back_main")],
    ])
    await cb.message.answer(
        f"📋 *Проверь данные:*\n\n"
        f"📅 {date_str} в {time_str} МСК\n"
        f"{type_label} | ⏱ {duration}\n"
        f"👤 _{state.get('name', '—')}_\n"
        f"📱 {platform}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=confirm_kb)

@dp.callback_query(F.data == "extend_description")
async def extend_description(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    state["step"] = "awaiting_info_retry"
    user_state[uid] = state
    await cb.message.answer(
        "Пожалуйста, расскажи подробнее — это поможет провести встречу "
        "более продуктивно:")

@dp.callback_query(F.data == "keep_description")
async def keep_description(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    state["step"] = "platform"
    user_state[uid] = state
    await cb.answer()
    await cb.message.answer(
        "Через какую платформу удобнее созвониться?",
        reply_markup=platform_menu())

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    if not state:
        await cb.answer("Ошибка, начни заново", show_alert=True)
        return
    date_str = state["date"]
    time_str = state["time"]
    name = state.get("name", "—")
    consult_type = state.get("type", "free")
    platform = state.get("platform", "—")
    duration = state.get("duration", "—")
    description = state.get("description", "—")
    appts = db_get("appointments", {})
    if date_str not in appts:
        appts[date_str] = []
    appts[date_str].append({
        "user_id": uid, "name": name, "time": time_str,
        "username": cb.from_user.username or "нет",
        "type": consult_type, "platform": platform,
        "duration": duration, "description": description,
        "reminded_client": False, "reminded_admin": False
    })
    db_set("appointments", appts)
    user_state.pop(uid, None)
    await cb.message.delete()
    type_label = "💼 Платная" if consult_type == "paid" else "🆓 Бесплатная"
    await cb.message.answer(
        f"✅ Запись принята!\n\n"
        f"📅 {date_str} в {time_str} МСК\n"
        f"{type_label} | ⏱ {duration}\n"
        f"📱 {platform}\n\n"
        "Евгений свяжется для подтверждения:\n"
        "👉 @kasikovevgenii"
    )
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить",
                              callback_data=f"adm_ok_{uid}_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="❌ Отменить",
                              callback_data=f"adm_cancel_{uid}_{date_str}_{time_str}")],
    ])
    await notify_admins(
        f"🔔 *Новая запись!*\n"
        f"📅 {date_str} в {time_str} МСК\n"
        f"{type_label} | ⏱ {duration}\n"
        f"👤 {name}\n📱 {platform}\n"
        f"💬 {description[:100]}\n"
        f"🆔 @{cb.from_user.username or 'нет'} | ID: {uid}",
        reply_markup=confirm_kb)

@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_ok(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2])
    date_str = parts[3]
    time_str = parts[4]
    appts = db_get("appointments", {})
    platform = "—"
    for rec in appts.get(date_str, []):
        if rec["user_id"] == uid and rec["time"] == time_str:
            platform = rec.get("platform", "—")
            break
    link = PLATFORM_LINKS.get(platform, "")
    try:
        await bot.send_message(uid,
            f"✅ Ваша запись подтверждена!\n\n"
            f"📅 {date_str} в {time_str} МСК\n"
            f"📱 {platform}\n"
            f"{'🔗 ' + link if link else ''}\n\n"
            "Если понадобится перенос: @kasikovevgenii")
    except:
        pass
    await cb.message.edit_text(
        cb.message.text + "\n\n✅ *Подтверждено*", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("adm_cancel_"))
async def adm_cancel(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2])
    try:
        await bot.send_message(uid,
            "❌ К сожалению, это время не получится.\n"
            "Выберите другое время или напишите: @kasikovevgenii")
    except:
        pass
    await cb.message.edit_text(
        cb.message.text + "\n\n❌ *Отменено*", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("block_user_"))
async def block_user_cb(cb: types.CallbackQuery):
    uid = int(cb.data.split("_")[2])
    blocked = db_get("blocked_users", [])
    if uid not in blocked:
        blocked.append(uid)
        db_set("blocked_users", blocked)
    await cb.message.edit_text(
        cb.message.text + "\n\n🚫 *Заблокирован*", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("skip_user_"))
async def skip_user_cb(cb: types.CallbackQuery):
    await cb.message.edit_text(
        cb.message.text + "\n\n✅ *Оставлено*", parse_mode="Markdown")

# ========== АДМИН КОЛБЭКИ ==========
@dp.callback_query(F.data == "adm_add")
async def adm_add(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_date"}
    await cb.message.answer("Введи дату *ГГГГ-ММ-ДД*:", parse_mode="Markdown")

@dp.callback_query(F.data == "adm_open_day")
async def adm_open_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_open_day_date"}
    await cb.message.answer("Дата для открытия всех слотов *ГГГГ-ММ-ДД*:",
                             parse_mode="Markdown")

@dp.callback_query(F.data == "adm_open_week")
async def adm_open_week(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_week_start"}
    await cb.message.answer("Дата *начала* недели *ГГГГ-ММ-ДД*:",
                             parse_mode="Markdown")

@dp.callback_query(F.data == "adm_close_day")
async def adm_close_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_close_day_date"}
    await cb.message.answer("Дата для закрытия *ГГГГ-ММ-ДД*:",
                             parse_mode="Markdown")

@dp.callback_query(F.data == "adm_block_range")
async def adm_block_range(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_block_start"}
    await cb.message.answer("Дата *начала* блокировки *ГГГГ-ММ-ДД*:",
                             parse_mode="Markdown")

@dp.callback_query(F.data == "adm_move")
async def adm_move(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_move_find"}
    await cb.message.answer("Введи ID пользователя для переноса:")

@dp.callback_query(F.data == "adm_regular")
async def adm_regular(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    clients = db_get("regular_clients", [])
    text = "👥 *Постоянные клиенты:*\n\n"
    if clients:
        for c in clients:
            text += f"@{c['username']} — {c['day']} в {c['time']}\n"
    else:
        text += "Нет постоянных клиентов."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить",
                              callback_data="adm_regular_add")],
        [InlineKeyboardButton(text="🗑 Удалить",
                              callback_data="adm_regular_del")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")],
    ])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "adm_regular_add")
async def adm_regular_add(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_reg_username"}
    await cb.message.answer(
        "Введи username клиента (без @):")

@dp.callback_query(F.data == "adm_regular_del")
async def adm_regular_del(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_reg_del"}
    await cb.message.answer("Введи username для удаления (без @):")

@dp.callback_query(F.data == "adm_back")
async def adm_back(cb: types.CallbackQuery):
    await cb.message.answer("Панель:", reply_markup=admin_menu())

@dp.callback_query(F.data == "adm_list")
async def adm_list(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appointments", {})
    today = date.today()
    text = "📋 *Предстоящие записи:*\n\n"
    found = False
    for ds in sorted(appts.keys()):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except:
            continue
        if d < today: continue
        for r in appts[ds]:
            t = "💼" if r.get("type") == "paid" else "🆓"
            text += (f"{t} *{ds}* {r['time']} ⏱{r.get('duration','—')}\n"
                     f"👤 {r['name']} @{r['username']}\n"
                     f"📱 {r.get('platform','—')}\n\n")
            found = True
    if not found: text = "📭 Записей нет."
    await cb.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_slots")
async def adm_slots_cb(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    today = date.today()
    text = "📅 *Мои слоты:*\n\n"
    found = False
    for ds in sorted(slots.keys()):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except:
            continue
        if d < today: continue
        taken = [r["time"] for r in appts.get(ds, [])]
        lines = [f"  {'🔴' if t in taken else '🟢'} {t}"
                 for t in slots[ds]]
        text += f"*{ds}*\n" + "\n".join(lines) + "\n\n"
        found = True
    if not found: text = "Слотов нет."
    await cb.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appointments", {})
    logs = db_get("logs", [])
    now = datetime.now()
    total = free_c = paid_c = 0
    for ds, records in appts.items():
        try:
            d = datetime.strptime(ds, "%Y-%m-%d")
        except:
            continue
        if d.month == now.month and d.year == now.year:
            for r in records:
                total += 1
                if r.get("type") == "paid":
                    paid_c += 1
                else:
                    free_c += 1
    guides = sum(1 for l in logs if l.get("action") == "got_guide")
    users = len(db_get("all_users", []))
    await cb.message.answer(
        f"📊 *Статистика за {now.strftime('%B %Y')}:*\n\n"
        f"📅 Всего записей: {total}\n"
        f"🆓 Бесплатных: {free_c}\n"
        f"💼 Платных: {paid_c}\n"
        f"📄 Гайдов выдано: {guides}\n"
        f"👥 Всего пользователей: {users}",
        parse_mode="Markdown")

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_broadcast_text"}
    await cb.message.answer("Введи текст рассылки — он уйдёт всем пользователям:")

@dp.callback_query(F.data == "adm_excel")
async def adm_excel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    user_state[cb.from_user.id] = {"step": "adm_excel_from"}
    await cb.message.answer(
        "Введи дату *начала* периода *ГГГГ-ММ-ДД*:",
        parse_mode="Markdown")

@dp.callback_query(F.data == "adm_blocked")
async def adm_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    blocked = db_get("blocked_users", [])
    if not blocked:
        await cb.message.answer("Заблокированных нет.")
        return
    text = "🚫 *Заблокированные:*\n\n" + "\n".join(str(u) for u in blocked)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔓 Разблокировать",
                             callback_data="adm_unblock_ask")
    ]])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "adm_unblock_ask")
async def adm_unblock_ask(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_unblock"}
    await cb.message.answer("Введи ID для разблокировки:")

@dp.callback_query(F.data == "adm_logs")
async def adm_logs(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    logs = db_get("logs", [])
    if not logs:
        await cb.message.answer("Логов нет.")
        return
    text = "📊 *Последние 20 действий:*\n\n"
    for e in logs[-20:]:
        text += f"🕐 {e['time']} @{e['username']}\n▶️ {e['action']}\n\n"
    await cb.message.answer(text, parse_mode="Markdown")

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_text(msg: types.Message):
    uid = msg.from_user.id
    text = msg.text.strip() if msg.text else ""
    if is_blocked(uid): return
    if is_flood(uid): return
    register_user(uid)

    if is_admin(msg.from_user.username):
        chats = db_get("admin_chats", [])
        if uid not in chats:
            chats.append(uid)
            db_set("admin_chats", chats)

    # Мат
    if has_bad_words(text):
        count = track_violation(uid, "bad_words")
        await msg.answer("Пожалуйста, давайте общаться без грубостей 🙏")
        if count >= 5:
            auto_block(uid, f"нецензурная лексика ({count} раз)")
            return
        block_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать",
                                  callback_data=f"block_user_{uid}")],
            [InlineKeyboardButton(text="✅ Оставить",
                                  callback_data=f"skip_user_{uid}")],
        ])
        await notify_admins(
            f"⚠️ *Нецензурная лексика* (нарушение {count}/5)\n"
            f"👤 @{msg.from_user.username or 'нет'} (ID: {uid})\n"
            f"💬 {text[:200]}",
            reply_markup=block_kb)
        return

    # Рандомный текст
    if is_random_text(text) and len(text) < 10:
        count = track_violation(uid, "random")
        if count >= 5:
            auto_block(uid, f"рандомные символы ({count} раз)")
        return

    state = user_state.get(uid, {})

    # Ждём имя и описание
    if state.get("step") in ("awaiting_info", "awaiting_info_retry"):
        # Валидация имени
        words = text.split()
        has_valid_name = (
            len(words) >= 2 and
            all(re.match(r'^[а-яёА-ЯЁa-zA-Z\-]+$', w) for w in words[:2])
        )
        if not has_valid_name and state.get("step") == "awaiting_info":
            await msg.answer(
                "Пожалуйста, напиши своё *имя* (минимум имя и фамилия) "
                "и что сейчас происходит:",
                parse_mode="Markdown")
            return

        # Проверка длины описания
        full_text = text
        if len(full_text) < 35:
            state["name"] = words[0] if words else text
            state["description_draft"] = full_text
            user_state[uid] = state
            short_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Дополнить",
                                      callback_data="extend_description")],
                [InlineKeyboardButton(text="✅ Оставить как есть",
                                      callback_data="keep_description")],
            ])
            await msg.answer(
                "Вижу, вы написали довольно мало 🙂\n\n"
                "Пожалуйста, напишите поподробнее — "
                "чтобы сессия прошла более продуктивно.",
                reply_markup=short_kb)
            return

        state["name"] = " ".join(words[:2]) if len(words) >= 2 else words[0]
        state["description"] = full_text
        state["step"] = "platform"
        user_state[uid] = state
        await msg.answer(
            "Через какую платформу удобнее созвониться?",
            reply_markup=platform_menu())
        return

    # Админ-шаги
    if state.get("step") == "adm_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        user_state[uid] = {"step": "adm_times", "adm_date": text}
        await msg.answer(
            f"Дата: *{text}*\nСлоты через запятую: `10:00, 10:30`",
            parse_mode="Markdown")
        return

    if state.get("step") == "adm_times":
        times_raw = [t.strip() for t in text.split(",")]
        valid = [t for t in times_raw
                 if re.match(r'^([01]\d|2[0-3]):[0-5]\d$', t)]
        if not valid:
            await msg.answer("❌ Формат: `10:00, 10:30`", parse_mode="Markdown")
            return
        ds = state["adm_date"]
        slots = db_get("slots", {})
        if ds not in slots: slots[ds] = []
        for t in valid:
            if t not in slots[ds]: slots[ds].append(t)
        slots[ds] = sorted(slots[ds])
        db_set("slots", slots)
        user_state.pop(uid, None)
        await msg.answer(f"✅ Слоты на *{ds}*: {', '.join(valid)}",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_open_day_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        slots = db_get("slots", {})
        slots[text] = ALL_DAY_SLOTS.copy()
        db_set("slots", slots)
        user_state.pop(uid, None)
        await msg.answer(
            f"✅ День *{text}* полностью открыт ({len(ALL_DAY_SLOTS)} слотов)",
            parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_week_start":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        state["week_start"] = text
        state["step"] = "adm_week_end"
        await msg.answer("Дата *конца* недели:", parse_mode="Markdown")
        return

    if state.get("step") == "adm_week_end":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-28`", parse_mode="Markdown")
            return
        start = datetime.strptime(state["week_start"], "%Y-%m-%d").date()
        end = datetime.strptime(text, "%Y-%m-%d").date()
        slots = db_get("slots", {})
        cur = start
        count = 0
        while cur <= end:
            ds = cur.strftime("%Y-%m-%d")
            slots[ds] = ALL_DAY_SLOTS.copy()
            count += 1
            cur += timedelta(days=1)
        db_set("slots", slots)
        user_state.pop(uid, None)
        await msg.answer(
            f"✅ Открыто *{count} дней* с {state['week_start']} по {text}",
            parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_close_day_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        slots = db_get("slots", {})
        if text in slots:
            del slots[text]
            db_set("slots", slots)
        user_state.pop(uid, None)
        await msg.answer(f"✅ День *{text}* закрыт.",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_block_start":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        state["block_start"] = text
        state["step"] = "adm_block_end"
        await msg.answer("Дата *конца* блокировки:", parse_mode="Markdown")
        return

    if state.get("step") == "adm_block_end":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-28`", parse_mode="Markdown")
            return
        start = datetime.strptime(state["block_start"], "%Y-%m-%d").date()
        end = datetime.strptime(text, "%Y-%m-%d").date()
        blocked_dates = db_get("blocked_dates", [])
        cur = start
        while cur <= end:
            ds = cur.strftime("%Y-%m-%d")
            if ds not in blocked_dates:
                blocked_dates.append(ds)
            cur += timedelta(days=1)
        db_set("blocked_dates", blocked_dates)
        user_state.pop(uid, None)
        await msg.answer(
            f"🚫 Заблокировано с *{state['block_start']}* по *{text}*",
            parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_move_find":
        try:
            target_uid = int(text)
        except:
            await msg.answer("❌ Введи числовой ID.")
            return
        appts = db_get("appointments", {})
        found_rec = found_ds = None
        for ds, records in appts.items():
            for rec in records:
                if rec["user_id"] == target_uid:
                    found_rec = rec
                    found_ds = ds
                    break
        if not found_rec:
            await msg.answer("Запись не найдена.", reply_markup=admin_menu())
            user_state.pop(uid, None)
            return
        state["move_uid"] = target_uid
        state["move_old_date"] = found_ds
        state["move_old_time"] = found_rec["time"]
        state["step"] = "adm_move_new_date"
        await msg.answer(
            f"Найдена: *{found_ds}* в *{found_rec['time']}*\n"
            f"👤 {found_rec['name']}\n\nНовая дата:",
            parse_mode="Markdown")
        return

    if state.get("step") == "adm_move_new_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        state["move_new_date"] = text
        state["step"] = "adm_move_new_time"
        await msg.answer("Новое время (например `15:00`):", parse_mode="Markdown")
        return

    if state.get("step") == "adm_move_new_time":
        if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', text):
            await msg.answer("❌ Формат: `15:00`", parse_mode="Markdown")
            return
        appts = db_get("appointments", {})
        old_ds = state["move_old_date"]
        new_ds = state["move_new_date"]
        target_uid = state["move_uid"]
        moved = False
        for rec in appts.get(old_ds, []):
            if rec["user_id"] == target_uid and rec["time"] == state["move_old_time"]:
                appts[old_ds].remove(rec)
                rec["time"] = text
                rec["reminded_client"] = False
                rec["reminded_admin"] = False
                if new_ds not in appts: appts[new_ds] = []
                appts[new_ds].append(rec)
                moved = True
                try:
                    await bot.send_message(target_uid,
                        f"📅 Консультация перенесена:\n"
                        f"*{new_ds}* в *{text}* МСК",
                        parse_mode="Markdown")
                except:
                    pass
                break
        if moved:
            db_set("appointments", appts)
            await msg.answer(f"✅ Перенесено на *{new_ds}* в *{text}*",
                             parse_mode="Markdown", reply_markup=admin_menu())
        else:
            await msg.answer("❌ Не удалось.", reply_markup=admin_menu())
        user_state.pop(uid, None)
        return

    if state.get("step") == "adm_reg_username":
        state["reg_username"] = text.lstrip("@")
        state["step"] = "adm_reg_day"
        days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=d, callback_data=f"regday_{d}")]
            for d in days
        ])
        await msg.answer("Выбери день недели:", reply_markup=kb)
        return

    if state.get("step") == "adm_reg_time":
        if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', text):
            await msg.answer("❌ Формат: `15:00`", parse_mode="Markdown")
            return
        clients = db_get("regular_clients", [])
        clients.append({
            "username": state["reg_username"],
            "day": state["reg_day"],
            "time": text
        })
        db_set("regular_clients", clients)
        user_state.pop(uid, None)
        await msg.answer(
            f"✅ Добавлен постоянный клиент:\n"
            f"@{state['reg_username']} — {state['reg_day']} в {text}",
            reply_markup=admin_menu())
        return

    if state.get("step") == "adm_reg_del":
        username = text.lstrip("@")
        clients = db_get("regular_clients", [])
        new_clients = [c for c in clients if c["username"].lower() != username.lower()]
        db_set("regular_clients", new_clients)
        user_state.pop(uid, None)
        await msg.answer(f"✅ Клиент @{username} удалён.",
                         reply_markup=admin_menu())
        return

    if state.get("step") == "adm_unblock":
        try:
            target = int(text)
            blocked = db_get("blocked_users", [])
            if target in blocked:
                blocked.remove(target)
                db_set("blocked_users", blocked)
                await msg.answer(f"✅ {target} разблокирован.",
                                 reply_markup=admin_menu())
            else:
                await msg.answer("Не найден.", reply_markup=admin_menu())
        except:
            await msg.answer("❌ Введи числовой ID.")
        user_state.pop(uid, None)
        return

    if state.get("step") == "adm_broadcast_text":
        users = db_get("all_users", [])
        sent = 0
        for user_id in users:
            try:
                await bot.send_message(user_id, text)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        user_state.pop(uid, None)
        await msg.answer(f"✅ Рассылка отправлена {sent} пользователям.",
                         reply_markup=admin_menu())
        return

    if state.get("step") == "adm_excel_from":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-01`", parse_mode="Markdown")
            return
        state["excel_from"] = text
        state["step"] = "adm_excel_to"
        await msg.answer("Дата *конца* периода *ГГГГ-ММ-ДД*:",
                         parse_mode="Markdown")
        return

    if state.get("step") == "adm_excel_to":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-31`", parse_mode="Markdown")
            return
        date_from = state["excel_from"]
        date_to = text
        user_state.pop(uid, None)
        if not EXCEL_OK:
            await msg.answer("❌ openpyxl не установлен. Добавь в requirements.txt")
            return
        buf = generate_excel(date_from, date_to)
        if buf:
            await msg.answer_document(
                types.BufferedInputFile(
                    buf.read(),
                    filename=f"записи_{date_from}_{date_to}.xlsx"
                ),
                caption=f"📊 Записи с {date_from} по {date_to}"
            )
        else:
            await msg.answer("Записей за этот период нет.")
        return

    log_action(uid, msg.from_user.username, f"msg:{text[:30]}")
    await msg.answer("Выбери действие:", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("regday_"))
async def regday_selected(cb: types.CallbackQuery):
    day = cb.data[7:]
    uid = cb.from_user.id
    state = user_state.get(uid, {})
    state["reg_day"] = day
    state["step"] = "adm_reg_time"
    user_state[uid] = state
    await cb.message.answer(f"День: *{day}*\nВведи время (например `15:00`):",
                             parse_mode="Markdown")

# ========== ЗАПУСК ==========
async def main():
    log.info("=" * 50)
    log.info("БОТ КАСИКОВА v4.0 ЗАПУЩЕН")
    log.info("Команды: /admin — панель, /stop — остановить")
    log.info("=" * 50)
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

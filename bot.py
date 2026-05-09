"""
Бот Евгения Касикова — психологические консультации
Хостинг: bothost.ru
"""

import asyncio
import os
import shelve
import hashlib
import calendar
import re
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL = os.environ.get("CHANNEL", "@kasikov_psy")
ADMIN_PASSWORD_HASH = hashlib.sha256(
    os.environ.get("ADMIN_PASSWORD").encode()
).hexdigest()
LEADMAGNET_URL = "https://t.me/kasikov_psy/230"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== НЕЦЕНЗУРНАЯ ЛЕКСИКА ==========
BAD_WORDS = [
    "блять","бля","блядь","блядина","блядский","хуй","хуйня","хуёво","хуево",
    "хуёвый","хуевый","хуила","хуило","пиздец","пизда","пиздатый","пизданутый",
    "пиздануть","пиздить","ёбаный","ёб","еб","ебать","ебёт","ебал","ебаный",
    "ебанутый","ёбнутый","ёбнуть","ебнуть","ебись","еби","сука","суки","сучка",
    "сучара","сучий","мудак","мудила","мудачок","мудацкий","залупа","залупиться",
    "шлюха","шлюшка","пидор","пидорас","пидорасина","гандон","гондон",
    "ублюдок","ублюдки","долбоёб","долбоеб","долбануться","дрочить","дрочила",
    "манда","мандавошка","срань","сранье","сраный","жопа","жопный","жопник",
    "педик","педераст","педрила","нахуй","нахер","ёпт","ёпта","епт","епта",
    "курва","дерьмо","дерьмовый","fuck","shit","bitch","asshole","cunt","whore",
    "кака","писька","пися","писю","какашка","залупень","шалава","потаскуха",
]

def has_bad_words(text):
    t = text.lower()
    for w in BAD_WORDS:
        if w in t:
            return True
    return False

# ========== ХРАНИЛИЩЕ ==========
DB_FILE = "bot_data"

def db_get(key, default=None):
    with shelve.open(DB_FILE) as db:
        return db.get(key, default)

def db_set(key, value):
    with shelve.open(DB_FILE) as db:
        db[key] = value

def init_db():
    for key, val in [
        ("slots", {}), ("appointments", {}),
        ("admin_chats", []), ("blocked_users", []), ("logs", []),
    ]:
        if db_get(key) is None:
            db_set(key, val)

init_db()

# ========== СОСТОЯНИЯ ==========
user_state = {}
user_flood = {}
user_flood_count = {}

def is_flood(uid):
    now = datetime.now().timestamp()
    last = user_flood.get(uid, 0)
    if now - last < 2:
        cnt = user_flood_count.get(uid, 0) + 1
        user_flood_count[uid] = cnt
        if cnt > 5:
            blocked = db_get("blocked_users", [])
            if uid not in blocked:
                blocked.append(uid)
                db_set("blocked_users", blocked)
        return True
    user_flood[uid] = now
    user_flood_count[uid] = 0
    return False

def is_blocked(uid):
    return uid in db_get("blocked_users", [])

def log_action(uid, username, action):
    logs = db_get("logs", [])
    logs.append({
        "uid": uid, "username": username or "нет",
        "action": action,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    if len(logs) > 500:
        logs = logs[-500:]
    db_set("logs", logs)

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

# ========== ТЕКСТЫ ==========
TEXT_ABOUT = """👤 *Обо мне*

Меня зовут Евгений Касиков.

Я не классический психолог в пиджаке с дипломом на стене. Я человек, который сам прошёл через то, с чем сейчас, скорее всего, пришёл ты.

Двое детей и развод после 15 лет брака. Расставание после пяти лет отношений. Полный финансовый крах. И каждый раз казалось, что мир просто взял и перевернулся.

Я знаю это изнутри. Не по книжкам.

Сегодня я работаю с людьми в период расставания и развода. За плечами более 10 лет практики и более 200 часов личной и групповой терапии. Более 200 реальных историй в работе с отношениями.

Я говорю на твоём языке. Смотрю не сверху — а рядом. Потому что я там был. И я знаю, что из этого выходят.

👉 @kasikovevgenii"""

TEXT_HOW = """⚙️ *Как я работаю*

Сразу скажу честно — чтобы ты понял, подходим ли мы друг другу.

Я не даю советов как жить. Не говорю «сделай вот так». Я помогаю тебе увидеть то, что ты сам не видишь.

Я работаю *интегративно* — выбираю метод под конкретного человека:

• *НЛП* — хаос в голове в первые недели
• *Транзактный анализ* — почему снова похожая ситуация
• *Психология привязанности* — почему так больно
• *EMDR* — травма от измены, предательства, внезапного ухода
• *Работа с телом* — боль которая живёт не только в голове
• *Гештальт* — незавершённые разговоры
• *IFS* — когда воюешь с собой
• *Схема-терапия* — «я недостаточно хорош»
• *Юнгианский подход* — когда не можешь отпустить
• *Экзистенциальный подход* — кризис идентичности после развода
• *Мужская психология* — мужчины горюют иначе

Решения всегда остаются за тобой. Работа — в живых сессиях, не в переписке."""

TEXT_PRICE = """💼 *Условия платных консультаций*

*Разовая консультация*
60 минут — 5 000 руб.

*Пакет «Глубокая работа»*
5 консультаций (5 часов) — 20 000 руб.
_экономия 5 000 руб._

Работаю по видео — Zoom, ВКонтакте, Яндекс Телемост, Google Meet.

После первой бесплатной встречи ты сам решаешь — продолжать или нет.

Записаться: @kasikovevgenii"""

TEXT_FREE_1 = """Здравствуйте. Спасибо, что написали — решиться на первый шаг бывает непросто.

Я провожу бесплатную 30-минутную вводную консультацию. За это время разбираемся с тем, что сейчас происходит — и вы уходите с чуть большей ясностью и пониманием, что делать дальше.

После встречи вы получите письменный разбор с конкретными темами и рекомендациями. Он останется с вами независимо от того, решите ли вы продолжать работу со мной."""

TEXT_FREE_2 = """Работаю по видео — ВКонтакте, Zoom, Яндекс Телемост, Google Meet.

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
        [InlineKeyboardButton(text="👤 Обо мне",
                              callback_data="about")],
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
        [InlineKeyboardButton(text="📅 Записаться на платную",
                              callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")],
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить слоты", callback_data="adm_add")],
        [InlineKeyboardButton(text="🗑 Удалить слоты на дату", callback_data="adm_del")],
        [InlineKeyboardButton(text="📋 Все записи", callback_data="adm_list")],
        [InlineKeyboardButton(text="📅 Мои слоты", callback_data="adm_slots")],
        [InlineKeyboardButton(text="🚫 Заблокированные", callback_data="adm_blocked")],
        [InlineKeyboardButton(text="📊 Последние логи", callback_data="adm_logs")],
    ])

# ========== КАЛЕНДАРЬ ==========
def user_calendar(year, month):
    today = date.today()
    month_names = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                   'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
    cal = calendar.monthcalendar(year, month)
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
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
                if d < today:
                    row.append(InlineKeyboardButton(text="·", callback_data="ignore"))
                else:
                    free = [t for t in slots.get(ds, [])
                            if t not in [r["time"] for r in appts.get(ds, [])]]
                    if free:
                        row.append(InlineKeyboardButton(
                            text=f"✅{day}", callback_data=f"day_{ds}"))
                    else:
                        row.append(InlineKeyboardButton(
                            text=str(day), callback_data="no_slots"))
        keyboard.append(row)
    nav = []
    pm = month-1 if month>1 else 12
    py = year if month>1 else year-1
    nm = month+1 if month<12 else 1
    ny = year if month<12 else year+1
    if date(py, pm, 1) >= today.replace(day=1):
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cal_{py}_{pm}"))
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
    for i, t in enumerate(day_slots):
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

# ========== ХЭНДЛЕРЫ ==========

@dp.message(Command("start"))
async def start(msg: types.Message):
    if is_blocked(msg.from_user.id): return
    if is_flood(msg.from_user.id): return
    log_action(msg.from_user.id, msg.from_user.username, "/start")
    await msg.answer(
        f"Привет, {msg.from_user.first_name} 👋\n\n"
        "Я помогаю людям пройти через расставание — без застревания "
        "и с пониманием что делать дальше.\n\nЧто тебя интересует?",
        reply_markup=main_menu()
    )

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
    await cb.message.answer(TEXT_HOW, parse_mode="Markdown",
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
        [InlineKeyboardButton(text="📢 Подписаться на канал",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался",
                              callback_data="check_sub_guide")],
    ])
    await cb.message.answer(
        "📄 *Гайд «4 шага выхода из расставания»* — 30 страниц практики.\n\n"
        "Чтобы получить — подпишись на канал. Там я каждый день разбираю "
        "реальные ситуации и делюсь инструментами которые реально работают 👇",
        parse_mode="Markdown", reply_markup=sub_kb
    )

@dp.callback_query(F.data == "check_sub_guide")
async def check_sub_guide(cb: types.CallbackQuery):
    if await is_subscribed(cb.from_user.id):
        log_action(cb.from_user.id, cb.from_user.username, "got_guide")
        await cb.message.delete()
        await cb.message.answer(
            f"✅ Держи гайд!\n\n👉 {LEADMAGNET_URL}\n\n"
            "Если захочешь разобрать свою ситуацию лично — "
            "провожу бесплатную 30-минутную консультацию 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",
                                      callback_data="free_consult")]
            ])
        )
    else:
        await cb.answer("❌ Подписка не найдена. Подпишись и нажми снова.",
                        show_alert=True)

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
        reply_markup=user_calendar(date.today().year, date.today().month)
    )

@dp.callback_query(F.data == "free_consult")
async def free_consult(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    user_state[uid] = {"type": "free"}
    log_action(uid, cb.from_user.username, "free_consult")
    await cb.message.answer(TEXT_FREE_1)
    await asyncio.sleep(1)
    await cb.message.answer(
        TEXT_FREE_2,
        reply_markup=user_calendar(date.today().year, date.today().month)
    )

@dp.callback_query(F.data == "no_slots")
async def no_slots(cb: types.CallbackQuery):
    await cb.answer("На этот день слотов нет", show_alert=True)

@dp.callback_query(F.data == "slot_taken")
async def slot_taken_cb(cb: types.CallbackQuery):
    await cb.answer("Это время занято 🔴", show_alert=True)

@dp.callback_query(F.data.startswith("day_"))
async def day_selected(cb: types.CallbackQuery):
    date_str = cb.data[4:]
    log_action(cb.from_user.id, cb.from_user.username, f"day_{date_str}")
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{date_str}*\n\nВыбери время:\n🟢 свободно  🔴 занято",
        parse_mode="Markdown", reply_markup=slots_menu(date_str)
    )

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
    user_state[uid] = {
        "step": "awaiting_info",
        "date": date_str,
        "time": time_str,
        "type": consult_type
    }
    log_action(uid, cb.from_user.username, f"slot_{date_str}_{time_str}")
    await cb.message.delete()
    type_label = "💼 платная" if consult_type == "paid" else "🆓 бесплатная"
    await cb.message.answer(
        f"✅ *{date_str}* в *{time_str}* МСК ({type_label})\n\n"
        "Напиши своё *имя* и кратко — *что сейчас происходит*.\n"
        "Чем больше контекста — тем лучше подготовлюсь к встрече:",
        parse_mode="Markdown"
    )

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
    appts = db_get("appointments", {})
    if date_str not in appts:
        appts[date_str] = []
    appts[date_str].append({
        "user_id": uid, "name": name, "time": time_str,
        "username": cb.from_user.username or "нет",
        "type": consult_type
    })
    db_set("appointments", appts)
    user_state.pop(uid, None)
    await cb.message.delete()
    type_label = "💼 Платная" if consult_type == "paid" else "🆓 Бесплатная"
    await cb.message.answer(
        f"✅ Запись принята!\n\n📅 {date_str} в {time_str} МСК\n"
        f"{type_label} консультация\n\n"
        "Напишите мне для подтверждения:\n👉 @kasikovevgenii"
    )
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить",
                              callback_data=f"adm_ok_{uid}_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="❌ Отменить",
                              callback_data=f"adm_cancel_{uid}_{date_str}_{time_str}")],
    ])
    await notify_admins(
        f"🔔 *Новая запись!*\n📅 {date_str} в {time_str} МСК\n"
        f"{type_label}\n👤 {name}\n"
        f"🆔 @{cb.from_user.username or 'нет'} | ID: {uid}",
        reply_markup=confirm_kb
    )

@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_ok(cb: types.CallbackQuery):
    uid = int(cb.data.split("_")[2])
    try:
        await bot.send_message(uid,
            "✅ Ваша запись подтверждена!\n"
            "Если понадобится перенос — напишите: @kasikovevgenii")
    except: pass
    await cb.message.edit_text(
        cb.message.text + "\n\n✅ *Подтверждено*", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("adm_cancel_"))
async def adm_cancel(cb: types.CallbackQuery):
    uid = int(cb.data.split("_")[2])
    try:
        await bot.send_message(uid,
            "❌ К сожалению, это время не получится.\n"
            "Выберите другое время или напишите: @kasikovevgenii")
    except: pass
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

@dp.callback_query(F.data == "adm_add")
async def adm_add(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_date"}
    await cb.message.answer(
        "Введи дату *ГГГГ-ММ-ДД*\nПример: `2026-05-22`",
        parse_mode="Markdown")

@dp.callback_query(F.data == "adm_del")
async def adm_del(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_del_date"}
    await cb.message.answer(
        "Введи дату для удаления *ГГГГ-ММ-ДД*:", parse_mode="Markdown")

@dp.callback_query(F.data == "adm_list")
async def adm_list(cb: types.CallbackQuery):
    appts = db_get("appointments", {})
    today = date.today()
    text = "📋 *Предстоящие записи:*\n\n"
    found = False
    for ds in sorted(appts.keys()):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d < today: continue
        for r in appts[ds]:
            t = "💼" if r.get("type") == "paid" else "🆓"
            text += f"{t} *{ds}* {r['time']}\n👤 {r['name']} @{r['username']}\n\n"
            found = True
    if not found: text = "📭 Записей нет."
    await cb.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_slots")
async def adm_slots(cb: types.CallbackQuery):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    today = date.today()
    text = "📅 *Мои слоты:*\n\n"
    found = False
    for ds in sorted(slots.keys()):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d < today: continue
        taken = [r["time"] for r in appts.get(ds, [])]
        lines = [f"  {'🔴' if t in taken else '🟢'} {t}" for t in slots[ds]]
        text += f"*{ds}*\n" + "\n".join(lines) + "\n\n"
        found = True
    if not found: text = "Слотов нет. Добавь через «➕»."
    await cb.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_blocked")
async def adm_blocked(cb: types.CallbackQuery):
    blocked = db_get("blocked_users", [])
    if not blocked:
        await cb.message.answer("Заблокированных нет.")
        return
    text = "🚫 *Заблокированные:*\n\n" + "\n".join(str(u) for u in blocked)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔓 Разблокировать по ID",
                             callback_data="adm_unblock_ask")
    ]])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "adm_unblock_ask")
async def adm_unblock_ask(cb: types.CallbackQuery):
    user_state[cb.from_user.id] = {"step": "adm_unblock"}
    await cb.message.answer("Введи ID пользователя для разблокировки:")

@dp.callback_query(F.data == "adm_logs")
async def adm_logs(cb: types.CallbackQuery):
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

    # Проверка пароля админа
    if hashlib.sha256(text.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
        chats = db_get("admin_chats", [])
        if uid not in chats:
            chats.append(uid)
            db_set("admin_chats", chats)
        await msg.answer("🔐 *Панель администратора*",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return

    # Мат
    if has_bad_words(text):
        await msg.answer("Пожалуйста, давайте общаться без грубостей 🙏")
        block_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать",
                                  callback_data=f"block_user_{uid}")],
            [InlineKeyboardButton(text="✅ Оставить",
                                  callback_data=f"skip_user_{uid}")],
        ])
        await notify_admins(
            f"⚠️ *Нецензурная лексика*\n"
            f"👤 @{msg.from_user.username or 'нет'} (ID: {uid})\n"
            f"💬 {text[:200]}",
            reply_markup=block_kb
        )
        return

    state = user_state.get(uid, {})

    # Ждём имя и ситуацию
    if state.get("step") == "awaiting_info":
        state["name"] = text
        state["step"] = "confirm"
        date_str = state["date"]
        time_str = state["time"]
        consult_type = state.get("type", "free")
        type_label = "💼 Платная" if consult_type == "paid" else "🆓 Бесплатная"
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить запись",
                                  callback_data=f"confirm_{date_str}_{time_str}")],
            [InlineKeyboardButton(text="↩️ Начать заново",
                                  callback_data="back_main")],
        ])
        await msg.answer(
            f"📋 *Проверь данные:*\n\n"
            f"📅 {date_str} в {time_str} МСК\n"
            f"{type_label}\n👤 _{text}_\n\nВсё верно?",
            parse_mode="Markdown", reply_markup=confirm_kb
        )
        return

    # Админ-шаги
    if state.get("step") == "adm_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        user_state[uid] = {"step": "adm_times", "adm_date": text}
        await msg.answer(
            f"Дата: *{text}*\nВведи слоты через запятую:\n`10:00, 10:30, 11:00`",
            parse_mode="Markdown")
        return

    if state.get("step") == "adm_times":
        times_raw = [t.strip() for t in text.split(",")]
        valid = [t for t in times_raw if re.match(r'^([01]\d|2[0-3]):[0-5]\d$', t)]
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
        await msg.answer(f"✅ Слоты на *{ds}*:\n{', '.join(valid)}",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return

    if state.get("step") == "adm_del_date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        slots = db_get("slots", {})
        if text in slots:
            del slots[text]
            db_set("slots", slots)
            await msg.answer(f"✅ Слоты на *{text}* удалены.",
                             parse_mode="Markdown", reply_markup=admin_menu())
        else:
            await msg.answer(f"❌ Слотов на *{text}* нет.",
                             parse_mode="Markdown", reply_markup=admin_menu())
        user_state.pop(uid, None)
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

    log_action(uid, msg.from_user.username, f"msg:{text[:30]}")
    await msg.answer("Выбери действие:", reply_markup=main_menu())

# ========== ЗАПУСК ==========
async def main():
    print("✅ Бот Касикова запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

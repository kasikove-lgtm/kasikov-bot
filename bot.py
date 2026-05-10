"""
Бот Евгения Касикова v5.0
Все баги исправлены. user_state сохраняется в shelve.
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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
 
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_OK = True
except:
    EXCEL_OK = False
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log", encoding="utf-8")]
)
log = logging.getLogger(__name__)
 
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
TRAFFIC_SOURCES = [
    ("📸 Instagram", "instagram"), ("🎵 TikTok", "tiktok"),
    ("▶️ YouTube", "youtube"), ("💙 ВКонтакте", "vk"), ("🌐 Другой", "other"),
]
 
bot = Bot(token=TOKEN)
dp = Dispatcher()
 
BAD_WORDS = [
    "блять","бля","блядь","хуй","хуйня","хуёво","хуево","хуёвый","хуевый",
    "хуила","хуило","пиздец","пизда","пиздатый","пизданутый","пиздить",
    "ёбаный","еб","ебать","ебёт","ебал","ебаный","ебанутый","ёбнуть","ебнуть",
    "сука","суки","сучка","сучара","мудак","мудила","залупа","шлюха","шлюшка",
    "пидор","пидорас","гандон","ублюдок","долбоёб","долбоеб","дрочить",
    "манда","срань","жопа","педик","педераст","нахуй","нахер","ёпт","епт",
    "курва","дерьмо","fuck","shit","bitch","asshole","cunt","whore","кака","писька","шалава",
]
 
def has_bad_words(text):
    t = text.lower()
    return any(w in t for w in BAD_WORDS)
 
DB_FILE = "bot_data"
 
def db_get(key, default=None):
    with shelve.open(DB_FILE) as db:
        return db.get(key, default)
 
def db_set(key, value):
    with shelve.open(DB_FILE) as db:
        db[key] = value
 
def init_db():
    for key, val in [
        ("slots",{}),("appointments",{}),("admin_chats",[]),("blocked_users",[]),
        ("logs",[]),("blocked_dates",[]),("all_users",[]),("violations",{}),
        ("regular_clients",[]),("user_states",{}),("drip_queue",[]),
        ("invited_clients",[]),("reviews",[]),
    ]:
        if db_get(key) is None:
            db_set(key, val)
 
init_db()
 
def get_state(uid):
    states = db_get("user_states", {})
    return states.get(str(uid), {})
 
def set_state(uid, state):
    states = db_get("user_states", {})
    states[str(uid)] = state
    db_set("user_states", states)
 
def clear_state(uid):
    states = db_get("user_states", {})
    states.pop(str(uid), None)
    db_set("user_states", states)
 
user_flood = {}
user_flood_count = {}
 
def track_violation(uid, vtype):
    v = db_get("violations", {})
    k = str(uid)
    if k not in v: v[k] = {}
    v[k][vtype] = v[k].get(vtype, 0) + 1
    db_set("violations", v)
    return v[k][vtype]
 
def is_flood(uid):
    now = datetime.now().timestamp()
    last = user_flood.get(uid, 0)
    if now - last < 2:
        cnt = user_flood_count.get(uid, 0) + 1
        user_flood_count[uid] = cnt
        if cnt > 15:
            count = track_violation(uid, "spam")
            if count >= 5:
                asyncio.create_task(auto_block_async(uid, "спам"))
        return True
    user_flood[uid] = now
    user_flood_count[uid] = 0
    return False
 
def is_blocked(uid): return uid in db_get("blocked_users", [])
 
async def auto_block_async(uid, reason):
    blocked = db_get("blocked_users", [])
    if uid not in blocked:
        blocked.append(uid)
        db_set("blocked_users", blocked)
        log.warning(f"АВТОБЛОК: {uid} — {reason}")
        await notify_admins(f"🚫 *Автоблок*\nID: {uid}\nПричина: {reason}")
 
def is_admin(username):
    if not username: return False
    return username.lower() in [u.lower() for u in ADMIN_USERNAMES]
 
def register_user(uid):
    users = db_get("all_users", [])
    if uid not in users:
        users.append(uid)
        db_set("all_users", users)
 
def log_action(uid, username, action):
    logs = db_get("logs", [])
    entry = {"uid": uid, "username": username or "нет", "action": action,
             "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
    logs.append(entry)
    if len(logs) > 1000: logs = logs[-1000:]
    db_set("logs", logs)
    log.info(f"[{entry['time']}] @{entry['username']} (ID:{uid}) — {action}")
 
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member","administrator","creator")
    except: return False
 
async def notify_admins(text, reply_markup=None):
    for chat_id in db_get("admin_chats", []):
        try: await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        except: pass
 
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
    return [t for t in slots.get(date_str, [])
            if t not in [r["time"] for r in appts.get(date_str, [])]]
 
def has_booking_today(uid, date_str):
    return any(r["user_id"]==uid for r in db_get("appointments",{}).get(date_str,[]))
 
TEXT_ABOUT = """👤 *Обо мне*
 
Меня зовут Евгений Касиков.
 
Я не классический психолог в пиджаке с дипломом на стене. Я человек, который сам прошёл через то, с чем сейчас, скорее всего, пришёл ты.
 
Двое детей и развод после 15 лет брака. Расставание после пяти лет отношений. Полный финансовый крах. И каждый раз казалось, что мир просто взял и перевернулся. То ощущение утром, когда просыпаешься, смотришь в потолок и думаешь: кто я теперь? Что вообще осталось?
 
Я знаю это изнутри. Не по книжкам.
 
Я из тех, кто привык добиваться результата. Кандидат в мастера спорта по плаванию, семь лет музыкальной школы. Потом 15 лет в найме в продажах: от рядового менеджера до директора по региону. Шесть собственных бизнесов. Флиппинг недвижимости — 10+ лет в рынке, 175+ объектов.
 
А потом всё рухнуло разом. Бизнес, отношения, темп. Деньги, статус, ориентиры. Я упал и разбился в дребезги.
 
И я не стал делать вид, что всё нормально. Пересобрал себя. Медленно, честно, без имитации бодрости.
 
Сегодня я работаю с людьми в период расставания и развода. За плечами более 10 лет практики и более 200 часов личной и групповой терапии. Более 200 реальных историй в работе с отношениями.
 
Я работаю интегративно — это значит, что я не привязан к одному методу. Я использую то, что работает для конкретного человека в конкретной ситуации: НЛП, транзактный анализ, гештальт, схема-терапия, работа с привязанностью, EMDR, IFS, психодинамический и экзистенциальный подходы, юнгианская психология, мужская психология, работа с телом.
 
Я говорю на твоём языке. Смотрю не сверху — а рядом. Потому что я там был. И я знаю, что из этого выходят.
 
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
 
TEXT_FAQ = """❓ *Часто задаваемые вопросы*
 
*Это конфиденциально?*
Да. Всё что происходит на сессии остаётся между нами. Я не делюсь информацией ни с кем.
 
*Как проходит первая встреча?*
30 минут по видео. Никакого давления и обязательств. После встречи ты уходишь с письменным разбором — независимо от того решишь ли продолжать работу со мной.
 
*Можно перенести или отменить?*
Да. Напиши мне минимум за 2 часа: @kasikovevgenii — или используй кнопку переноса в боте.
 
*Вы работаете только с мужчинами?*
Нет. Около половины моих клиентов — женщины. Тема расставания одинаково тяжела для всех.
 
*Сколько сессий нужно?*
Зависит от запроса. Есть люди которым хватает 5-6 встреч. Есть те кто работает дольше. Первая встреча даст понимание что подходит именно тебе.
 
*Как технически проходит сессия?*
По видеосвязи — Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX. Нужно тихое место где тебя не будут отвлекать."""
 
TEXT_FEEDBACK_REQUEST = """Независимо от того, будешь ли ты работать со мной дальше или нет — хочу попросить короткую обратную связь по нашей первой сессии.
 
Если откликается, ответь на несколько вопросов — коротко, как идёт:
 
1. С каким состоянием ты пришёл на сессию?
2. Что из сессии было для тебя самым полезным?
3. С каким состоянием ты вышел после неё?
4. Планируешь ли продолжать работу дальше?
 
Если ты не против, я могу использовать твой ответ в обезличенном виде — без имён и деталей — как обобщённую обратную связь о работе."""
 
DRIP_MESSAGES = {
    1: {"text": "Успел заглянуть в гайд? Там есть практика которую можно применить прямо сегодня — особенно второй шаг.\n\nЕсли захочется разобрать свою ситуацию лично — первая встреча бесплатно 👇", "kb": "free_consult"},
    7: {"text": "После расставания больно не потому что ты слабый.\n\nНейробиолог Этан Кросс из Мичиганского университета выяснил: мозг воспринимает социальную боль в тех же зонах что и физическую. Когда тебе разбивают сердце — мозг регистрирует это как удар. Буквально.\n\nТы терял не просто человека. Ты терял версию себя который существовал рядом с этим человеком.\n\nБоль после расставания — это не слабость. Это нормально.\n\nБольше об этом на канале 👉 @kasikov_psy", "kb": None},
    14: {"text": "Три вещи которые не надо делать в первый месяц. Я сам делал все три.\n\n1. Новые отношения сразу — рана переезжает, не заживает.\n2. Полный контакт с бывшим — мозгу нужна дистанция.\n3. Заливать боль чем угодно — она накапливается и потом выходит.\n\nПодробнее на канале 👉 @kasikov_psy", "kb": None},
    30: {"text": "Прошёл месяц. Как вы?\n\nЕсли чувствуешь что стало не легче а тяжелее — это сигнал. Не «возьми себя в руки». А сигнал что иногда в одиночку дольше и тяжелее.\n\nЯ провожу бесплатную вводную встречу — 30 минут чтобы разобраться что сейчас происходит.\n\nЕсли актуально 👇", "kb": "free_consult"},
}
 
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Первая бесплатная консультация", callback_data="free_consult")],
        [InlineKeyboardButton(text="💼 Условия платных консультаций", callback_data="paid_consult")],
        [InlineKeyboardButton(text="📄 Гайд «4 шага после расставания»", callback_data="get_guide")],
        [InlineKeyboardButton(text="👤 Обо мне", callback_data="about")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton(text="🔄 Перенести мою запись", callback_data="client_reschedule")],
        [InlineKeyboardButton(text="❌ Отменить мою запись", callback_data="client_cancel")],
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
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
    rows = [[InlineKeyboardButton(text=d, callback_data=f"dur_{d}")] for d in DURATIONS]
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def platform_menu(back_cb="back_main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Zoom", callback_data="platform_Zoom")],
        [InlineKeyboardButton(text="📱 ВКонтакте", callback_data="platform_ВКонтакте")],
        [InlineKeyboardButton(text="💻 Яндекс Телемост", callback_data="platform_Яндекс Телемост")],
        [InlineKeyboardButton(text="📹 Google Meet", callback_data="platform_Google Meet")],
        [InlineKeyboardButton(text="🖥 Microsoft Teams", callback_data="platform_Microsoft Teams")],
        [InlineKeyboardButton(text="📲 MAX", callback_data="platform_MAX")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data=back_cb)],
    ])
 
def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Управление слотами", callback_data="adm_cal_open")],
        [InlineKeyboardButton(text="📅 Открыть весь день", callback_data="adm_open_day")],
        [InlineKeyboardButton(text="🗓 Открыть неделю", callback_data="adm_open_week")],
        [InlineKeyboardButton(text="📆 Быстрая рабочая неделя пн-пт", callback_data="adm_quick_week")],
        [InlineKeyboardButton(text="📋 Скопировать прошлую неделю", callback_data="adm_copy_week")],
        [InlineKeyboardButton(text="🚫 Заблокировать месяц", callback_data="adm_block_month")],
        [InlineKeyboardButton(text="✏️ Записать клиента вручную", callback_data="adm_manual_book")],
        [InlineKeyboardButton(text="📋 Прошедшие бесплатные", callback_data="adm_past_free")],
        [InlineKeyboardButton(text="📋 Все записи", callback_data="adm_list")],
        [InlineKeyboardButton(text="📅 Мои слоты таблицей", callback_data="adm_slots_table")],
        [InlineKeyboardButton(text="👥 Постоянные клиенты", callback_data="adm_regular")],
        [InlineKeyboardButton(text="➕ Новый клиент", callback_data="adm_new_client")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="📤 Рассылка всем", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📤 Отправить пост из канала", callback_data="adm_send_post")],
        [InlineKeyboardButton(text="📊 Excel отчёт", callback_data="adm_excel")],
        [InlineKeyboardButton(text="⭐️ Отзывы", callback_data="adm_reviews")],
        [InlineKeyboardButton(text="🚫 Заблокированные", callback_data="adm_blocked")],
        [InlineKeyboardButton(text="📊 Логи", callback_data="adm_logs")],
    ])
 
def user_calendar(year, month):
    today = date.today()
    month_names = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                   "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    cal = calendar.monthcalendar(year, month)
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    blocked_dates = db_get("blocked_dates", [])
    keyboard = []
    keyboard.append([InlineKeyboardButton(text=f"📅 {month_names[month-1]} {year}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(text=d, callback_data="ignore") for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                d = date(year, month, day)
                ds = d.strftime("%Y-%m-%d")
                if d < today or ds in blocked_dates:
                    row.append(InlineKeyboardButton(text="·", callback_data="ignore"))
                else:
                    free = get_free_slots(ds)
                    if free:
                        row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"day_{ds}"))
                    else:
                        row.append(InlineKeyboardButton(text=str(day), callback_data="no_slots"))
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
    keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
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
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
 
def admin_calendar(year, month):
    today = date.today()
    month_names = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                   "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    cal = calendar.monthcalendar(year, month)
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    blocked_dates = db_get("blocked_dates", [])
    keyboard = []
    keyboard.append([InlineKeyboardButton(text=f"🔧 {month_names[month-1]} {year}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton(text=d, callback_data="ignore") for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
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
                elif ds in blocked_dates:
                    row.append(InlineKeyboardButton(text=f"❌{day}", callback_data=f"adm_day_{ds}"))
                else:
                    day_appts = appts.get(ds, [])
                    day_slots_list = slots.get(ds, [])
                    if day_appts:
                        row.append(InlineKeyboardButton(text=f"🔵{day}", callback_data=f"adm_day_{ds}"))
                    elif day_slots_list:
                        row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"adm_day_{ds}"))
                    else:
                        row.append(InlineKeyboardButton(text=str(day), callback_data=f"adm_day_{ds}"))
        keyboard.append(row)
    nav = []
    pm = month-1 if month>1 else 12
    py = year if month>1 else year-1
    nm = month+1 if month<12 else 1
    ny = year if month<12 else year+1
    nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm_cal_{py}_{pm}"))
    nav.append(InlineKeyboardButton(text="↩️ Меню", callback_data="adm_back"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm_cal_{ny}_{nm}"))
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
 
def admin_day_slots(date_str):
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    day_slots = slots.get(date_str, [])
    taken_recs = {r["time"]: r for r in appts.get(date_str, [])}
    keyboard = []
    row = []
    for t in day_slots:
        if t in taken_recs:
            emoji = "🔵"
            cb = f"adm_slot_booked_{date_str}_{t}"
        else:
            emoji = "🟢"
            cb = f"adm_slot_close_{date_str}_{t}"
        row.append(InlineKeyboardButton(text=f"{emoji}{t}", callback_data=cb))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить слоты", callback_data=f"adm_add_to_{date_str}"),
        InlineKeyboardButton(text="✏️ Записать клиента", callback_data=f"adm_manual_{date_str}"),
    ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад к календарю", callback_data="adm_cal_open")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
 
def format_slots_table():
    slots = db_get("slots", {})
    appts = db_get("appointments", {})
    today = date.today()
    dates = sorted([ds for ds in slots.keys()
                    if datetime.strptime(ds, "%Y-%m-%d").date() >= today])[:7]
    if not dates:
        return "Слотов нет."
    text = "```\n"
    text += "Время |" + "|".join(d[5:] for d in dates) + "\n"
    text += "------|" + "|".join("-----" for _ in dates) + "\n"
    all_times = set()
    for ds in dates: all_times.update(slots.get(ds, []))
    for t in sorted(all_times):
        row = f"{t} |"
        for ds in dates:
            taken = [r["time"] for r in appts.get(ds, [])]
            day_slots = slots.get(ds, [])
            if t not in day_slots: row += "  -  |"
            elif t in taken: row += "  🔵 |"
            else: row += "  🟢 |"
        text += row + "\n"
    text += "```\n🟢 свободно  🔵 запись  - нет слота"
    return text
 
def generate_excel(date_from, date_to):
    if not EXCEL_OK: return None
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Записи"
    headers = ["Дата","Время","Тип","Статус","Имя","Username","Платформа","Длительность","Описание","Источник"]
    hf = PatternFill("solid", fgColor="2E86AB")
    hfont = Font(color="FFFFFF", bold=True)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = hf; cell.font = hfont
        cell.alignment = Alignment(horizontal="center")
    appts = db_get("appointments", {})
    row = 2
    for ds in sorted(appts.keys()):
        if ds < date_from or ds > date_to: continue
        for rec in appts[ds]:
            ws.cell(row=row, column=1, value=ds)
            ws.cell(row=row, column=2, value=rec.get("time",""))
            ws.cell(row=row, column=3, value="Платная" if rec.get("type")=="paid" else "Бесплатная")
            ws.cell(row=row, column=4, value=rec.get("status",""))
            ws.cell(row=row, column=5, value=rec.get("name",""))
            ws.cell(row=row, column=6, value=f"@{rec.get('username','')}")
            ws.cell(row=row, column=7, value=rec.get("platform",""))
            ws.cell(row=row, column=8, value=rec.get("duration",""))
            ws.cell(row=row, column=9, value=rec.get("description",""))
            ws.cell(row=row, column=10, value=rec.get("source","бот"))
            row += 1
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len+4, 40)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
 
def add_to_drip(uid):
    queue = db_get("drip_queue", [])
    now = datetime.now()
    for day in DRIP_MESSAGES.keys():
        queue.append({"uid": uid, "day": day, "send_at": (now+timedelta(days=day)).isoformat()})
    db_set("drip_queue", queue)
 
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
                        appt_dt = datetime.strptime(f"{ds} {rec['time']}", "%Y-%m-%d %H:%M")
                    except: continue
                    diff = (appt_dt - now).total_seconds() / 60
                    if 59 <= diff <= 61:
                        platform = rec.get("platform","")
                        link = PLATFORM_LINKS.get(platform,"")
                        if not rec.get("reminded_client"):
                            try:
                                await bot.send_message(rec["user_id"],
                                    f"⏰ Напоминание!\n\nЧерез час наша встреча — {rec['time']} МСК\n"
                                    f"Платформа: {platform}\n{'🔗 '+link if link else ''}\n\n"
                                    "Если что-то изменилось — напишите: @kasikovevgenii")
                                rec["reminded_client"] = True
                                changed = True
                            except: pass
                        if not rec.get("reminded_admin"):
                            type_label = "💼 Платная" if rec.get("type")=="paid" else "🆓 Бесплатная"
                            await notify_admins(
                                f"⏰ *Через час консультация!*\n\n"
                                f"📅 {ds} в {rec['time']} МСК\n{type_label}\n"
                                f"👤 {rec.get('name','—')}\n📱 {platform}\n"
                                f"⏱ {rec.get('duration','—')}\n🆔 @{rec.get('username','—')}")
                            rec["reminded_admin"] = True
                            changed = True
                    hours_passed = (now - appt_dt).total_seconds() / 3600
                    if rec.get("status") == "проведена":
                        if 23 <= hours_passed <= 25 and not rec.get("followup_1"):
                            try:
                                await bot.send_message(rec["user_id"],
                                    "Как вы после нашей встречи? Надеюсь, стало немного яснее.\n\n"
                                    "Если захотите продолжить работу — я здесь. Вот условия:",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text="💼 Условия платных консультаций",
                                                             callback_data="paid_consult")
                                    ]]))
                                rec["followup_1"] = True
                                changed = True
                            except: pass
                        if 71 <= hours_passed <= 73 and not rec.get("followup_3"):
                            try:
                                await bot.send_message(rec["user_id"], TEXT_FEEDBACK_REQUEST)
                                rec["followup_3"] = True
                                changed = True
                            except: pass
            if changed: db_set("appointments", appts)
            queue = db_get("drip_queue", [])
            remaining = []
            for item in queue:
                send_at = datetime.fromisoformat(item["send_at"])
                if now >= send_at:
                    day = item["day"]
                    msg_data = DRIP_MESSAGES.get(day)
                    if msg_data:
                        try:
                            kb = None
                            if msg_data["kb"] == "free_consult":
                                kb = InlineKeyboardMarkup(inline_keyboard=[[
                                    InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",
                                                         callback_data="free_consult")
                                ]])
                            await bot.send_message(item["uid"], msg_data["text"], reply_markup=kb)
                        except: pass
                else:
                    remaining.append(item)
            db_set("drip_queue", remaining)
        except Exception as e:
            log.error(f"reminder_loop: {e}")
 
@dp.message(Command("start"))
async def start(msg: types.Message):
    if is_blocked(msg.from_user.id): return
    if is_flood(msg.from_user.id): return
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
        reply_markup=main_menu())
 
@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if not is_admin(msg.from_user.username): return
    chats = db_get("admin_chats", [])
    if msg.from_user.id not in chats:
        chats.append(msg.from_user.id)
        db_set("admin_chats", chats)
    await msg.answer("🔐 *Панель администратора*", parse_mode="Markdown", reply_markup=admin_menu())
 
@dp.message(Command("stop"))
async def stop_cmd(msg: types.Message):
    if not is_admin(msg.from_user.username): return
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
    await cb.message.answer(TEXT_ABOUT, parse_mode="Markdown", reply_markup=back_main_kb())
 
@dp.callback_query(F.data == "how_i_work")
async def how_i_work(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(TEXT_HOW_1, parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await cb.message.answer(TEXT_HOW_2, parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await cb.message.answer(TEXT_HOW_3, parse_mode="Markdown", reply_markup=back_main_kb())
 
@dp.callback_query(F.data == "faq")
async def faq(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(TEXT_FAQ, parse_mode="Markdown", reply_markup=back_main_kb())
 
@dp.callback_query(F.data == "back_main")
async def back_to_main(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Главное меню:", reply_markup=main_menu())
 
@dp.callback_query(F.data == "get_guide")
async def get_guide(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user.id, cb.from_user.username, "get_guide")
    sub_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub_guide")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")],
    ])
    await cb.message.answer(
        "📄 *Гайд «4 шага выхода из расставания»* — 30 страниц практики.\n\n"
        "Чтобы получить — подпишись на канал. Там я каждый день разбираю реальные ситуации 👇",
        parse_mode="Markdown", reply_markup=sub_kb)
 
@dp.callback_query(F.data == "check_sub_guide")
async def check_sub_guide(cb: types.CallbackQuery):
    if await is_subscribed(cb.from_user.id):
        log_action(cb.from_user.id, cb.from_user.username, "got_guide")
        add_to_drip(cb.from_user.id)
        await cb.message.delete()
        await cb.message.answer(
            f"✅ Держи гайд!\n\n👉 {LEADMAGNET_URL}\n\n"
            "Если захочешь разобрать ситуацию лично — провожу бесплатную 30-минутную консультацию 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="1️⃣ Записаться на бесплатную", callback_data="free_consult")
            ]]))
    else:
        await cb.answer("❌ Подписка не найдена.", show_alert=True)
 
@dp.callback_query(F.data == "paid_consult")
async def paid_consult(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(TEXT_PRICE, parse_mode="Markdown", reply_markup=paid_menu())
 
@dp.callback_query(F.data == "book_paid")
async def book_paid(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    set_state(uid, {"type": "paid"})
    await cb.message.answer("Выбери дату 👇\n✅ — есть свободные слоты",
        reply_markup=user_calendar(date.today().year, date.today().month))
 
@dp.callback_query(F.data == "free_consult")
async def free_consult(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    set_state(uid, {"type": "free"})
    log_action(uid, cb.from_user.username, "free_consult")
    await cb.message.answer(TEXT_FREE_1)
    await asyncio.sleep(1)
    await cb.message.answer(TEXT_FREE_2,
        reply_markup=user_calendar(date.today().year, date.today().month))
 
@dp.callback_query(F.data == "client_cancel")
async def client_cancel(cb: types.CallbackQuery):
    uid = cb.from_user.id
    appts = db_get("appointments", {})
    today = date.today()
    found = found_ds = None
    for ds, records in appts.items():
        try: d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d >= today:
            for rec in records:
                if rec["user_id"] == uid:
                    found = rec; found_ds = ds; break
    if not found:
        await cb.answer("У вас нет предстоящих записей.", show_alert=True)
        return
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отменить",
                              callback_data=f"client_cancel_confirm_{found_ds}_{found['time']}")],
        [InlineKeyboardButton(text="↩️ Нет, назад", callback_data="back_main")],
    ])
    await cb.message.answer(
        f"Ваша запись:\n📅 {found_ds} в {found['time']} МСК\n\nОтменить?",
        reply_markup=confirm_kb)
 
@dp.callback_query(F.data.startswith("client_cancel_confirm_"))
async def client_cancel_confirm(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    date_str = parts[3]; time_str = parts[4]; uid = cb.from_user.id
    appts = db_get("appointments", {})
    if date_str in appts:
        appts[date_str] = [r for r in appts[date_str]
                           if not (r["user_id"]==uid and r["time"]==time_str)]
        db_set("appointments", appts)
    await cb.message.delete()
    await cb.message.answer("✅ Запись отменена. Если захотите записаться снова — я здесь.",
                             reply_markup=main_menu())
    await notify_admins(f"❌ Клиент отменил запись\n📅 {date_str} в {time_str}\n"
                        f"🆔 @{cb.from_user.username or 'нет'}")
 
@dp.callback_query(F.data == "client_reschedule")
async def client_reschedule(cb: types.CallbackQuery):
    uid = cb.from_user.id
    set_state(uid, {"type": "reschedule"})
    await cb.message.answer("Выбери новую дату:",
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
    state = get_state(uid)
    if state.get("type") != "reschedule" and has_booking_today(uid, date_str):
        await cb.answer("У вас уже есть запись на этот день.", show_alert=True)
        return
    state["date"] = date_str
    set_state(uid, state)
    await cb.message.delete()
    await cb.message.answer(f"📅 *{date_str}*\n\nВыбери время:\n🟢 свободно  🔴 занято",
        parse_mode="Markdown", reply_markup=slots_menu(date_str))
 
@dp.callback_query(F.data.startswith("cal_"))
async def cal_nav(cb: types.CallbackQuery):
    _, y, m = cb.data.split("_")
    await cb.message.edit_reply_markup(reply_markup=user_calendar(int(y), int(m)))
 
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
    date_str = parts[1]; time_str = parts[2]
    uid = cb.from_user.id
    state = get_state(uid)
    consult_type = state.get("type", "free")
    await cb.message.delete()
    if consult_type in ("free", "reschedule"):
        state.update({"step": "awaiting_info", "date": date_str, "time": time_str, "duration": "30 мин"})
        set_state(uid, state)
        await cb.message.answer(
            f"✅ *{date_str}* в *{time_str}* МСК\n\n"
            "Напиши своё *имя* и кратко — *что сейчас происходит*:",
            parse_mode="Markdown")
    else:
        state.update({"step": "awaiting_duration", "date": date_str, "time": time_str})
        set_state(uid, state)
        await cb.message.answer(f"✅ *{date_str}* в *{time_str}* МСК\n\nВыбери длительность:",
            parse_mode="Markdown", reply_markup=duration_menu())
 
@dp.callback_query(F.data.startswith("dur_"))
async def duration_selected(cb: types.CallbackQuery):
    duration = cb.data[4:]
    uid = cb.from_user.id
    state = get_state(uid)
    state["duration"] = duration; state["step"] = "awaiting_info"
    set_state(uid, state)
    await cb.message.answer(f"⏱ Длительность: *{duration}*\n\nНапиши своё *имя* и кратко — *что сейчас происходит*:",
        parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("platform_"))
async def platform_selected(cb: types.CallbackQuery):
    platform = cb.data[9:]
    uid = cb.from_user.id
    state = get_state(uid)
 
    # Ручная запись администратором
    if state.get("step") == "adm_manual_platform":
        state["manual_platform"] = platform
        state["step"] = "adm_manual_type_select"
        set_state(uid, state)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="adm_manual_type_free")],
            [InlineKeyboardButton(text="💼 Платная", callback_data="adm_manual_type_paid")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")],
        ])
        await cb.answer()
        await cb.message.answer("Тип консультации?", reply_markup=kb)
        return
 
    # Обычная запись клиента
    state["platform"] = platform; state["step"] = "confirm"
    set_state(uid, state)
    date_str = state.get("date","—"); time_str = state.get("time","—")
    consult_type = state.get("type","free")
    duration = state.get("duration","—")
    type_label = "💼 Платная" if consult_type=="paid" else "🆓 Бесплатная"
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")],
    ])
    await cb.message.answer(
        f"📋 *Проверь данные:*\n\n"
        f"📅 {date_str} в {time_str} МСК\n{type_label} | ⏱ {duration}\n"
        f"👤 _{state.get('name','—')}_\n📱 {platform}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=confirm_kb)
 
@dp.callback_query(F.data == "extend_description")
async def extend_description(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = get_state(uid)
    state["step"] = "awaiting_info_retry"
    set_state(uid, state)
    await cb.message.answer("Расскажи подробнее — это поможет провести встречу продуктивнее:")
 
@dp.callback_query(F.data == "keep_description")
async def keep_description(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = get_state(uid)
    state["step"] = "platform"
    set_state(uid, state)
    await cb.answer()
    await cb.message.answer("Через какую платформу удобнее созвониться?", reply_markup=platform_menu())
 
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(cb: types.CallbackQuery):
    uid = cb.from_user.id
    state = get_state(uid)
    if not state:
        await cb.answer("Ошибка, начни заново", show_alert=True)
        return
    date_str = state["date"]; time_str = state["time"]
    name = state.get("name","—"); consult_type = state.get("type","free")
    platform = state.get("platform","—"); duration = state.get("duration","—")
    description = state.get("description","—")
    appts = db_get("appointments", {})
    if date_str not in appts: appts[date_str] = []
    appts[date_str].append({
        "user_id": uid, "name": name, "time": time_str,
        "username": cb.from_user.username or "нет",
        "type": consult_type, "platform": platform,
        "duration": duration, "description": description,
        "reminded_client": False, "reminded_admin": False,
        "status": "", "source": "бот",
        "followup_1": False, "followup_3": False,
    })
    db_set("appointments", appts)
    clear_state(uid)
    await cb.message.delete()
    type_label = "💼 Платная" if consult_type=="paid" else "🆓 Бесплатная"
    await cb.message.answer(
        f"✅ Запись принята!\n\n📅 {date_str} в {time_str} МСК\n"
        f"{type_label} | ⏱ {duration}\n📱 {platform}\n\n"
        "Евгений свяжется для подтверждения:\n👉 @kasikovevgenii")
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить",
                              callback_data=f"adm_ok_{uid}_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="❌ Отменить",
                              callback_data=f"adm_cancel_{uid}_{date_str}_{time_str}")],
    ])
    await notify_admins(
        f"🔔 *Новая запись!*\n📅 {date_str} в {time_str} МСК\n{type_label} | ⏱ {duration}\n"
        f"👤 {name}\n📱 {platform}\n💬 {description[:100]}\n"
        f"🆔 @{cb.from_user.username or 'нет'} | ID: {uid}",
        reply_markup=confirm_kb)
 
@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_ok(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2]); date_str = parts[3]; time_str = parts[4]
    appts = db_get("appointments", {})
    platform = "—"
    for rec in appts.get(date_str, []):
        if rec["user_id"]==uid and rec["time"]==time_str:
            platform = rec.get("platform","—"); break
    link = PLATFORM_LINKS.get(platform,"")
    try:
        await bot.send_message(uid,
            f"✅ Запись подтверждена!\n\n📅 {date_str} в {time_str} МСК\n"
            f"📱 {platform}\n{'🔗 '+link if link else ''}\n\n"
            "Если понадобится перенос: @kasikovevgenii")
    except: pass
    await cb.message.edit_text(cb.message.text+"\n\n✅ *Подтверждено*", parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("adm_cancel_"))
async def adm_cancel(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2])
    try:
        await bot.send_message(uid, "❌ К сожалению, это время не получится.\nВыберите другое: @kasikovevgenii")
    except: pass
    await cb.message.edit_text(cb.message.text+"\n\n❌ *Отменено*", parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("block_user_"))
async def block_user_cb(cb: types.CallbackQuery):
    uid = int(cb.data.split("_")[2])
    blocked = db_get("blocked_users", [])
    if uid not in blocked: blocked.append(uid); db_set("blocked_users", blocked)
    await cb.message.edit_text(cb.message.text+"\n\n🚫 *Заблокирован*", parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("skip_user_"))
async def skip_user_cb(cb: types.CallbackQuery):
    await cb.message.edit_text(cb.message.text+"\n\n✅ *Оставлено*", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_cal_open")
async def adm_cal_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    now = date.today()
    await cb.message.answer(
        "📅 *Управление слотами*\n\n✅ слоты  🔵 записи  ❌ заблокирован",
        parse_mode="Markdown", reply_markup=admin_calendar(now.year, now.month))
 
@dp.callback_query(F.data.startswith("adm_cal_"))
async def adm_cal_nav(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_")
    y, m = int(parts[2]), int(parts[3])
    await cb.message.edit_reply_markup(reply_markup=admin_calendar(y, m))
 
@dp.callback_query(F.data.startswith("adm_day_"))
async def adm_day_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    date_str = cb.data[8:]
    uid = cb.from_user.id
    state = get_state(uid)
    step = state.get("step","")
 
    # Режим: открыть весь день
    if step == "adm_open_day_pick":
        slots = db_get("slots", {})
        slots[date_str] = ALL_DAY_SLOTS.copy()
        db_set("slots", slots)
        clear_state(uid)
        await cb.answer(f"✅ День {date_str} открыт")
        await cb.message.answer(f"✅ День *{date_str}* открыт ({len(ALL_DAY_SLOTS)} слотов)",
                                 parse_mode="Markdown", reply_markup=admin_menu())
        return
 
    # Режим: открыть неделю с этого дня
    if step == "adm_week_pick_start":
        start = datetime.strptime(date_str, "%Y-%m-%d").date()
        slots = db_get("slots", {})
        count = 0
        for i in range(7):
            d = start + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            slots[ds] = ALL_DAY_SLOTS.copy()
            count += 1
        db_set("slots", slots)
        clear_state(uid)
        end_ds = (start + timedelta(days=6)).strftime("%d.%m")
        await cb.answer(f"✅ Открыто 7 дней")
        await cb.message.answer(
            f"✅ Открыта неделя с *{date_str}* по *{end_ds}* ({count} дней)",
            parse_mode="Markdown", reply_markup=admin_menu())
        return
 
    # Режим: ручная запись — выбор даты
    if step in ("adm_manual_date", "adm_move_pick_date"):
        if step == "adm_move_pick_date":
            state["move_new_date"] = date_str
            state["step"] = "adm_move_pick_time"
            set_state(uid, state)
            await cb.answer()
            await cb.message.answer(f"Новая дата: *{date_str}*\nВведи новое время (`14:00`):",
                                     parse_mode="Markdown")
        else:
            state["adm_date"] = date_str
            state["step"] = "adm_manual_slot_pick"
            set_state(uid, state)
            await cb.answer()
            await cb.message.delete()
            await cb.message.answer(
                f"📅 *{date_str}*\nВыбери свободный слот для записи клиента:",
                parse_mode="Markdown", reply_markup=admin_day_slots(date_str))
        return
 
    # Стандартный режим — управление слотами
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{date_str}*\n🟢 свободно  🔵 запись\nНажми на слот для управления:",
        parse_mode="Markdown", reply_markup=admin_day_slots(date_str))
 
@dp.callback_query(F.data.startswith("adm_slot_close_"))
async def adm_slot_close(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]
    uid = cb.from_user.id
    state = get_state(uid)
    # Если в режиме ручной записи — сразу записываем клиента
    if state.get("step") == "adm_manual_slot_pick" and state.get("manual_tg"):
        state["adm_date"] = date_str
        state["adm_time"] = time_str
        state["step"] = "adm_manual_platform"
        set_state(uid, state)
        await cb.answer()
        await cb.message.answer(
            f"✅ @{state['manual_tg']} — *{date_str}* в *{time_str}*\n\nПлатформа для связи?",
            parse_mode="Markdown", reply_markup=platform_menu("adm_back"))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Закрыть слот",
                              callback_data=f"adm_do_close_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="✏️ Записать клиента",
                              callback_data=f"adm_manual_{date_str}_{time_str}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data=f"adm_day_{date_str}")],
    ])
    await cb.answer()
    await cb.message.answer(f"🟢 Слот {date_str} в {time_str} — свободен. Что сделать?",
                             reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_do_close_"))
async def adm_do_close(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]
    slots = db_get("slots", {})
    if date_str in slots and time_str in slots[date_str]:
        slots[date_str].remove(time_str); db_set("slots", slots)
    await cb.answer("🔴 Слот закрыт")
    await cb.message.delete()
    await cb.message.answer(f"📅 *{date_str}*", parse_mode="Markdown",
                             reply_markup=admin_day_slots(date_str))
 
@dp.callback_query(F.data.startswith("adm_slot_booked_"))
async def adm_slot_booked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]
    appts = db_get("appointments", {})
    rec = next((r for r in appts.get(date_str,[]) if r["time"]==time_str), None)
    if not rec: await cb.answer("Не найдено", show_alert=True); return
    type_label = "💼 Платная" if rec.get("type")=="paid" else "🆓 Бесплатная"
    await cb.answer(
        f"👤 {rec['name']}\n{type_label} | ⏱{rec.get('duration','—')}\n📱{rec.get('platform','—')}",
        show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перенести",
                              callback_data=f"adm_move_rec_{date_str}_{time_str}_{rec['user_id']}")],
        [InlineKeyboardButton(text="❌ Отменить запись",
                              callback_data=f"adm_cancel_rec_{date_str}_{time_str}_{rec['user_id']}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data=f"adm_day_{date_str}")],
    ])
    await cb.message.answer(
        f"🔵 *{date_str}* в *{time_str}*\n\n"
        f"👤 {rec['name']} @{rec.get('username','')}\n"
        f"{type_label} | ⏱ {rec.get('duration','—')}\n📱 {rec.get('platform','—')}",
        parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_cancel_rec_"))
async def adm_cancel_rec(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]; user_id = int(parts[5])
    appts = db_get("appointments", {})
    if date_str in appts:
        appts[date_str] = [r for r in appts[date_str]
                           if not (r["user_id"]==user_id and r["time"]==time_str)]
        db_set("appointments", appts)
    try:
        await bot.send_message(user_id,
            f"❌ К сожалению, запись на {date_str} в {time_str} отменена.\n"
            "Для записи на другое время: @kasikovevgenii")
    except: pass
    await cb.answer("✅ Запись отменена")
    await cb.message.delete()
    await cb.message.answer(f"📅 *{date_str}*", parse_mode="Markdown",
                             reply_markup=admin_day_slots(date_str))
 
@dp.callback_query(F.data.startswith("adm_move_rec_"))
async def adm_move_rec(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]; user_id = int(parts[5])
    uid = cb.from_user.id
    set_state(uid, {"step": "adm_move_pick_date", "move_old_date": date_str,
                    "move_old_time": time_str, "move_uid": user_id})
    now = date.today()
    await cb.message.answer("Выбери новую дату для переноса:",
                             reply_markup=admin_calendar(now.year, now.month))
 
@dp.callback_query(F.data.startswith("adm_add_to_"))
async def adm_add_to(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    date_str = cb.data[11:]
    set_state(cb.from_user.id, {"step": "adm_add_slots_to", "adm_date": date_str})
    await cb.message.answer(f"Слоты для *{date_str}* через запятую:\n`10:00, 11:00`",
                             parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("adm_manual_"))
async def adm_manual_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_")
    date_str = parts[2]
    time_str = parts[3] if len(parts) > 3 else None
    uid = cb.from_user.id
    state = get_state(uid)
    # Если уже знаем username клиента — просто обновляем дату/время
    if state.get("manual_tg"):
        state["adm_date"] = date_str
        if time_str: state["adm_time"] = time_str
        state["step"] = "adm_manual_platform"
        set_state(uid, state)
        await cb.answer()
        await cb.message.answer(
            f"✅ @{state['manual_tg']} — {date_str}{' в '+time_str if time_str else ''}\n\nПлатформа для связи?",
            reply_markup=platform_menu("adm_back"))
    else:
        state = {"step": "adm_manual_name", "adm_date": date_str}
        if time_str: state["adm_time"] = time_str
        set_state(uid, state)
        await cb.answer()
        await cb.message.answer(
            f"Записываю клиента на *{date_str}*{' в '+time_str if time_str else ''}.\n\nВведи *имя клиента*:",
            parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_open_day")
async def adm_open_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    set_state(cb.from_user.id, {"step": "adm_open_day_pick"})
    now = date.today()
    await cb.message.answer(
        "Выбери день для открытия всех слотов (10:00-21:00):",
        reply_markup=admin_calendar(now.year, now.month))
 
@dp.callback_query(F.data == "adm_open_week")
async def adm_open_week(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    set_state(cb.from_user.id, {"step": "adm_week_pick_start"})
    now = date.today()
    await cb.message.answer(
        "Нажми на день — с него откроется неделя (7 дней вперёд):",
        reply_markup=admin_calendar(now.year, now.month))
 
@dp.callback_query(F.data == "adm_quick_week")
async def adm_quick_week(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    today = date.today()
    # Текущая неделя — понедельник этой недели
    monday = today - timedelta(days=today.weekday())
    slots = db_get("slots", {})
    count = 0
    for i in range(5):
        d = monday + timedelta(days=i)
        if d >= today:  # не открываем прошедшие дни
            slots[d.strftime("%Y-%m-%d")] = ALL_DAY_SLOTS.copy()
            count += 1
    db_set("slots", slots)
    await cb.answer()
    await cb.message.answer(
        f"✅ Открыта рабочая неделя пн-пт с {monday.strftime('%d.%m')} ({count} дней)",
        reply_markup=admin_menu())
 
@dp.callback_query(F.data == "adm_copy_week")
async def adm_copy_week(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    today = date.today()
    last_monday = today - timedelta(days=today.weekday()+7)
    this_monday = today - timedelta(days=today.weekday())
    slots = db_get("slots", {})
    count = 0
    for i in range(7):
        last_ds = (last_monday+timedelta(days=i)).strftime("%Y-%m-%d")
        this_ds = (this_monday+timedelta(days=i)).strftime("%Y-%m-%d")
        # Копируем даже если прошлой недели нет — открываем стандартные слоты для пн-пт
        d = this_monday + timedelta(days=i)
        if d >= today:
            if last_ds in slots:
                slots[this_ds] = slots[last_ds].copy()
            elif i < 5:  # пн-пт — открываем стандартные слоты
                slots[this_ds] = ALL_DAY_SLOTS.copy()
            count += 1
    db_set("slots", slots)
    await cb.answer()
    await cb.message.answer(f"✅ Скопировано/открыто {count} дней", reply_markup=admin_menu())
 
@dp.callback_query(F.data == "adm_block_month")
async def adm_block_month(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    now = date.today()
    months = ["Январь","Февраль","Март","Апрель","Май","Июнь",
              "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    keyboard = []
    for y in [now.year, now.year+1]:
        for m in range(1, 13):
            if date(y, m, 1) < now.replace(day=1): continue
            keyboard.append([InlineKeyboardButton(
                text=f"{months[m-1]} {y}",
                callback_data=f"adm_block_month_pick_{y}_{m:02d}")])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    await cb.message.answer("Выбери месяц для блокировки:",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
 
@dp.callback_query(F.data == "adm_manual_book")
async def adm_manual_book(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    set_state(cb.from_user.id, {"step": "adm_manual_tg"})
    await cb.message.answer("Введи username клиента в Telegram (без @):")
 
@dp.callback_query(F.data == "adm_past_free")
async def adm_past_free(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appointments", {})
    today = date.today()
    week_ago = today - timedelta(days=7)
    keyboard = []
    for ds in sorted(appts.keys(), reverse=True):
        try: d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d > today or d < week_ago: continue
        for rec in appts[ds]:
            if rec.get("type") != "free": continue
            status = rec.get("status","")
            icon = "✅" if status=="проведена" else ("❌" if status=="не состоялась" else "⏳")
            keyboard.append([InlineKeyboardButton(
                text=f"{icon} {ds} {rec['time']} — {rec['name']}",
                callback_data=f"adm_free_rec_{ds}_{rec['time']}_{rec['user_id']}")])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    if len(keyboard) == 1:
        await cb.message.answer("Прошедших бесплатных за неделю нет.", reply_markup=admin_menu())
        return
    await cb.message.answer("📋 *Прошедшие бесплатные (7 дней):*",
                             parse_mode="Markdown",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
 
@dp.callback_query(F.data.startswith("adm_free_rec_"))
async def adm_free_rec(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]; user_id = int(parts[5])
    appts = db_get("appointments", {})
    rec = next((r for r in appts.get(date_str,[]) if r["user_id"]==user_id and r["time"]==time_str), None)
    if not rec: await cb.answer("Не найдено", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проведена",
                              callback_data=f"adm_status_done_{date_str}_{time_str}_{user_id}")],
        [InlineKeyboardButton(text="❌ Не состоялась",
                              callback_data=f"adm_status_miss_{date_str}_{time_str}_{user_id}")],
        [InlineKeyboardButton(text="📝 Отправить обратную связь",
                              callback_data=f"adm_feedback_{date_str}_{time_str}_{user_id}")],
        [InlineKeyboardButton(text="💼 Записать на платную",
                              callback_data=f"adm_to_paid_{date_str}_{time_str}_{user_id}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_past_free")],
    ])
    status = rec.get("status","не отмечен")
    await cb.message.answer(
        f"👤 *{rec['name']}* @{rec.get('username','')}\n📅 {date_str} в {time_str}\nСтатус: {status}",
        parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_status_done_"))
async def adm_status_done(cb: types.CallbackQuery):
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]; user_id = int(parts[5])
    appts = db_get("appointments", {})
    for rec in appts.get(date_str,[]): 
        if rec["user_id"]==user_id and rec["time"]==time_str: rec["status"]="проведена"
    db_set("appointments", appts)
    await cb.answer("✅ Отмечено: проведена")
 
@dp.callback_query(F.data.startswith("adm_status_miss_"))
async def adm_status_miss(cb: types.CallbackQuery):
    parts = cb.data.split("_"); date_str = parts[3]; time_str = parts[4]; user_id = int(parts[5])
    appts = db_get("appointments", {})
    for rec in appts.get(date_str,[]):
        if rec["user_id"]==user_id and rec["time"]==time_str: rec["status"]="не состоялась"
    db_set("appointments", appts)
    await cb.answer("❌ Отмечено: не состоялась")
 
@dp.callback_query(F.data.startswith("adm_feedback_"))
async def adm_feedback_start(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); date_str = parts[2]; time_str = parts[3]; user_id = int(parts[4])
    set_state(cb.from_user.id, {"step": "adm_feedback_text",
                                 "feedback_uid": user_id,
                                 "feedback_date": date_str, "feedback_time": time_str})
    await cb.message.answer("Введи текст обратной связи и план работы.\n"
                             "Уйдёт клиенту вместе с условиями платных консультаций:")
 
@dp.callback_query(F.data.startswith("adm_to_paid_"))
async def adm_to_paid(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); user_id = int(parts[4])
    try:
        await bot.send_message(user_id,
            "После нашей встречи хочу предложить продолжить работу.\n\n"+TEXT_PRICE,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📅 Записаться на платную", callback_data="book_paid")
            ]]))
        await cb.answer("✅ Предложение отправлено")
    except Exception as e:
        await cb.answer(f"Ошибка: {e}", show_alert=True)
 
@dp.callback_query(F.data == "adm_list")
async def adm_list(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appointments", {})
    today = date.today()
    text = "📋 *Предстоящие записи:*\n\n"
    found = False
    for ds in sorted(appts.keys()):
        try: d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d < today: continue
        for r in appts[ds]:
            t = "💼" if r.get("type")=="paid" else "🆓"
            text += (f"{t} *{ds}* {r['time']} ⏱{r.get('duration','—')}\n"
                     f"👤 {r['name']} @{r.get('username','')}\n"
                     f"📱 {r.get('platform','—')}\n\n")
            found = True
    if not found: text = "📭 Записей нет."
    await cb.message.answer(text, parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_slots_table")
async def adm_slots_table(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.message.answer(format_slots_table(), parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_regular")
async def adm_regular(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    clients = db_get("regular_clients", [])
    text = "👥 *Постоянные клиенты:*\n\n"
    text += "\n".join(f"@{c['username']} — {c['day']} в {c['time']}" for c in clients) if clients else "Нет."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="adm_regular_add")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="adm_regular_del")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")],
    ])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "adm_regular_add")
async def adm_regular_add(cb: types.CallbackQuery):
    set_state(cb.from_user.id, {"step": "adm_reg_username"})
    await cb.message.answer("Введи username клиента (без @):")
 
@dp.callback_query(F.data == "adm_regular_del")
async def adm_regular_del(cb: types.CallbackQuery):
    set_state(cb.from_user.id, {"step": "adm_reg_del"})
    await cb.message.answer("Введи username для удаления (без @):")
 
@dp.callback_query(F.data.startswith("regday_"))
async def regday_selected(cb: types.CallbackQuery):
    day = cb.data[7:]
    uid = cb.from_user.id
    state = get_state(uid)
    state["reg_day"] = day; state["step"] = "adm_reg_time"
    set_state(uid, state)
    await cb.message.answer(f"День: *{day}*\nВведи время (`15:00`):", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_new_client")
async def adm_new_client(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"adm_src_{src}")]
        for label, src in TRAFFIC_SOURCES
    ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")]])
    await cb.message.answer("Откуда клиент?", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_src_"))
async def adm_src_selected(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    src = cb.data[8:]
    set_state(cb.from_user.id, {"step": "adm_new_client_username", "client_source": src})
    await cb.message.answer("Введи username клиента в Telegram (без @):")
 
@dp.callback_query(F.data == "adm_stats")
async def adm_stats(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appointments", {})
    logs = db_get("logs", [])
    now = datetime.now()
    total = free_c = paid_c = done_c = miss_c = 0
    sources = {}
    for ds, records in appts.items():
        try: d = datetime.strptime(ds, "%Y-%m-%d")
        except: continue
        if d.month==now.month and d.year==now.year:
            for r in records:
                total += 1
                if r.get("type")=="paid": paid_c += 1
                else: free_c += 1
                if r.get("status")=="проведена": done_c += 1
                if r.get("status")=="не состоялась": miss_c += 1
                src = r.get("source","бот")
                sources[src] = sources.get(src, 0) + 1
    guides = sum(1 for l in logs if l.get("action")=="got_guide")
    users = len(db_get("all_users", []))
    src_text = "\n".join(f"  {k}: {v}" for k,v in sources.items())
    await cb.message.answer(
        f"📊 *Статистика {now.strftime('%B %Y')}:*\n\n"
        f"📅 Всего записей: {total}\n🆓 Бесплатных: {free_c}\n💼 Платных: {paid_c}\n"
        f"✅ Проведено: {done_c}\n❌ Не состоялось: {miss_c}\n"
        f"📄 Гайдов: {guides}\n👥 Пользователей: {users}\n\n"
        f"*Источники:*\n{src_text or '  нет данных'}",
        parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_state(cb.from_user.id, {"step": "adm_broadcast_text"})
    await cb.message.answer("Введи текст рассылки — уйдёт всем пользователям:")
 
@dp.callback_query(F.data == "adm_send_post")
async def adm_send_post(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_state(cb.from_user.id, {"step": "adm_post_link"})
    await cb.message.answer("Вставь ссылку на пост из канала:")
 
@dp.callback_query(F.data == "adm_excel")
async def adm_excel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_state(cb.from_user.id, {"step": "adm_excel_from"})
    await cb.message.answer("Дата *начала* периода *ГГГГ-ММ-ДД*:", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_reviews")
async def adm_reviews(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    reviews = db_get("reviews", [])
    if not reviews: await cb.message.answer("Отзывов пока нет."); return
    text = "⭐️ *Отзывы:*\n\n"
    for r in reviews[-10:]:
        text += f"👤 {r.get('name','—')} | {'⭐️'*r.get('stars',5)}\n{r.get('text','')}\n\n"
    await cb.message.answer(text, parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_blocked")
async def adm_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    blocked = db_get("blocked_users", [])
    if not blocked: await cb.message.answer("Заблокированных нет."); return
    text = "🚫 *Заблокированные:*\n\n" + "\n".join(str(u) for u in blocked)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔓 Разблокировать", callback_data="adm_unblock_ask")
    ]])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "adm_unblock_ask")
async def adm_unblock_ask(cb: types.CallbackQuery):
    set_state(cb.from_user.id, {"step": "adm_unblock"})
    await cb.message.answer("Введи ID для разблокировки:")
 
@dp.callback_query(F.data == "adm_logs")
async def adm_logs(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    logs = db_get("logs", [])
    if not logs: await cb.message.answer("Логов нет."); return
    text = "📊 *Последние 20 действий:*\n\n"
    for e in logs[-20:]:
        text += f"🕐 {e['time']} @{e['username']}\n▶️ {e['action']}\n\n"
    await cb.message.answer(text, parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_back")
async def adm_back(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Панель:", reply_markup=admin_menu())
 
@dp.callback_query(F.data == "adm_block_month_yes")
async def adm_block_month_yes(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uid = cb.from_user.id
    state = get_state(uid)
    month_str = state.get("block_month","")
    if not month_str: return
    year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
    days_in_month = calendar.monthrange(year, month)[1]
    blocked_dates = db_get("blocked_dates", [])
    for day in range(1, days_in_month+1):
        ds = f"{year}-{month:02d}-{day:02d}"
        if ds not in blocked_dates: blocked_dates.append(ds)
    db_set("blocked_dates", blocked_dates)
    clear_state(uid)
    await cb.message.answer(f"🚫 Месяц *{month_str}* заблокирован (записи сохранены).",
                             parse_mode="Markdown", reply_markup=admin_menu())
 
@dp.callback_query(F.data.startswith("adm_block_month_pick_"))
async def adm_block_month_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_")
    year, month = int(parts[4]), int(parts[5])
    month_str = f"{year}-{month:02d}"
    days_in_month = calendar.monthrange(year, month)[1]
    appts = db_get("appointments", {})
    conflicts = []
    for day in range(1, days_in_month+1):
        ds = f"{year}-{month:02d}-{day:02d}"
        if appts.get(ds):
            conflicts.append(ds)
    if conflicts:
        uid = cb.from_user.id
        set_state(uid, {"step": "adm_block_month_confirm", "block_month": month_str})
        conflict_text = "\n".join(f"  {ds}: {len(appts[ds])} записей" for ds in conflicts)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заблокировать несмотря на записи",
                                  callback_data="adm_block_month_yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
        ])
        await cb.message.answer(
            f"⚠️ В {month_str} есть записи:\n{conflict_text}\n\nВсё равно заблокировать?",
            reply_markup=kb)
    else:
        blocked_dates = db_get("blocked_dates", [])
        for day in range(1, days_in_month+1):
            ds = f"{year}-{month:02d}-{day:02d}"
            if ds not in blocked_dates: blocked_dates.append(ds)
        db_set("blocked_dates", blocked_dates)
        await cb.answer(f"🚫 {month_str} заблокирован")
        await cb.message.answer(f"🚫 Месяц *{month_str}* заблокирован.",
                                 parse_mode="Markdown", reply_markup=admin_menu())
 
@dp.callback_query(F.data.startswith("adm_manual_type_"))
async def adm_manual_type(cb: types.CallbackQuery):
    consult_type = "paid" if "paid" in cb.data else "free"
    uid = cb.from_user.id
    state = get_state(uid)
    state["manual_type"] = consult_type
    name = state.get("manual_name","—"); tg = state.get("manual_tg","—")
    platform = state.get("manual_platform","—")
    ds = state.get("adm_date","—"); time_str = state.get("adm_time","—")
    type_label = "💼 Платная" if consult_type=="paid" else "🆓 Бесплатная"
    appts = db_get("appointments", {})
    if ds not in appts: appts[ds] = []
    appts[ds].append({
        "user_id": 0, "name": name, "time": time_str,
        "username": tg, "type": consult_type, "platform": platform,
        "duration": "—", "description": "Ручная запись", "source": "вручную",
        "reminded_client": True, "reminded_admin": False, "status": "",
        "followup_1": True, "followup_3": True,
    })
    db_set("appointments", appts)
    clear_state(uid)
    await cb.message.answer(
        f"✅ Клиент записан вручную!\n\n📅 {ds} в {time_str}\n{type_label}\n"
        f"👤 {name} @{tg}\n📱 {platform}", reply_markup=admin_menu())
    await notify_admins(f"✏️ *Ручная запись*\n📅 {ds} в {time_str}\n{type_label}\n"
                        f"👤 {name} @{tg}\n📱 {platform}")
 
@dp.callback_query(F.data.startswith("rate_"))
async def rate_cb(cb: types.CallbackQuery):
    stars = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    set_state(uid, {"step": "awaiting_review_text", "stars": stars})
    await cb.message.answer(f"Спасибо за оценку {'⭐️'*stars}!\n\nНапиши пару слов — что было полезным:")
 
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
 
    if has_bad_words(text):
        count = track_violation(uid, "bad_words")
        await msg.answer("Пожалуйста, давайте общаться без грубостей 🙏")
        if count >= 5:
            await auto_block_async(uid, f"мат ({count} раз)")
            return
        block_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_user_{uid}")],
            [InlineKeyboardButton(text="✅ Оставить", callback_data=f"skip_user_{uid}")],
        ])
        await notify_admins(
            f"⚠️ *Нецензурная лексика* ({count}/5)\n"
            f"👤 @{msg.from_user.username or 'нет'} (ID:{uid})\n💬 {text[:200]}",
            reply_markup=block_kb)
        return
 
    state = get_state(uid)
 
    # Ждём имя и описание
    if state.get("step") in ("awaiting_info", "awaiting_info_retry"):
        words = text.split()
        has_valid_name = (len(words) >= 2 and
                          all(re.match(r"^[а-яёА-ЯЁa-zA-Z\-]+$", w) for w in words[:2]))
        if not has_valid_name and state.get("step") == "awaiting_info":
            await msg.answer("Напиши своё *имя* (минимум имя и фамилия) и что сейчас происходит:",
                             parse_mode="Markdown")
            return
        if len(text) < 35:
            state["name"] = words[0] if words else text
            state["description"] = text
            set_state(uid, state)
            short_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Дополнить", callback_data="extend_description")],
                [InlineKeyboardButton(text="✅ Оставить как есть", callback_data="keep_description")],
            ])
            await msg.answer(
                "Вижу, вы написали довольно мало 🙂\n\n"
                "Пожалуйста, напишите поподробнее — чтобы сессия прошла более продуктивно.",
                reply_markup=short_kb)
            return
        state["name"] = " ".join(words[:2]) if len(words) >= 2 else words[0]
        state["description"] = text
        state["step"] = "platform"
        set_state(uid, state)
        await msg.answer("Через какую платформу удобнее созвониться?", reply_markup=platform_menu())
        return
 
    # Отзыв
    if state.get("step") == "awaiting_review_text":
        reviews = db_get("reviews", [])
        reviews.append({
            "uid": uid, "name": msg.from_user.first_name,
            "stars": state.get("stars", 5), "text": text,
            "time": datetime.now().strftime("%d.%m.%Y")
        })
        db_set("reviews", reviews)
        clear_state(uid)
        await msg.answer("Спасибо! Ваш отзыв очень важен для меня 🙏", reply_markup=main_menu())
        await notify_admins(f"⭐️ *Новый отзыв!*\n{'⭐️'*state.get('stars',5)}\n{text[:200]}")
        return
 
    # Обратная связь клиенту
    if state.get("step") == "adm_feedback_text":
        feedback_uid = state["feedback_uid"]
        try:
            await bot.send_message(feedback_uid,
                text + "\n\n" + TEXT_PRICE,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="💼 Записаться на платную", callback_data="book_paid")
                ]]))
            await msg.answer("✅ Обратная связь отправлена клиенту.", reply_markup=admin_menu())
        except Exception as e:
            await msg.answer(f"❌ Ошибка: {e}")
        clear_state(uid)
        return
 
    # Ручная запись — имя
    if state.get("step") == "adm_manual_name":
        state["manual_name"] = text
        state["step"] = "adm_manual_tg"
        set_state(uid, state)
        await msg.answer("Введи username клиента в Telegram (без @):")
        return
 
    # Ручная запись — tg → потом интерактивный календарь
    if state.get("step") == "adm_manual_tg":
        state["manual_tg"] = text.lstrip("@")
        state["step"] = "adm_manual_date"
        set_state(uid, state)
        now = date.today()
        await msg.answer(
            f"Клиент @{state['manual_tg']} — выбери дату записи:",
            reply_markup=admin_calendar(now.year, now.month))
        return
 
    # Ручная запись — время
    if state.get("step") == "adm_manual_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text):
            await msg.answer("❌ Формат: `14:00`", parse_mode="Markdown")
            return
        state["adm_time"] = text
        state["step"] = "adm_manual_platform"
        set_state(uid, state)
        await msg.answer("Платформа для связи?", reply_markup=platform_menu("adm_back"))
        return
 
    # Платформа для ручной записи
    if state.get("step") == "adm_manual_platform":
        state["manual_platform"] = text
        state["step"] = "adm_manual_type_select"
        set_state(uid, state)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="adm_manual_type_free")],
            [InlineKeyboardButton(text="💼 Платная", callback_data="adm_manual_type_paid")],
        ])
        await msg.answer("Тип консультации?", reply_markup=kb)
        return
 
    # Новый клиент
    if state.get("step") == "adm_new_client_username":
        username = text.lstrip("@")
        source = state.get("client_source", "other")
        invited = db_get("invited_clients", [])
        invited.append({"username": username, "source": source,
                        "invited_at": datetime.now().isoformat(), "status": "приглашён"})
        db_set("invited_clients", invited)
        clear_state(uid)
        try:
            me = await bot.get_me()
            bot_link = f"https://t.me/{me.username}"
        except:
            bot_link = "https://t.me/kasikov_bot"
        await msg.answer(
            f"✅ Клиент @{username} добавлен.\n\nОтправь ему эту ссылку:\n{bot_link}",
            reply_markup=admin_menu())
        return
 
    # Добавить слоты к дате
    if state.get("step") == "adm_add_slots_to":
        times_raw = [t.strip() for t in text.split(",")]
        valid = [t for t in times_raw if re.match(r"^([01]\d|2[0-3]):[0-5]\d$", t)]
        if not valid:
            await msg.answer("❌ Формат: `10:00, 11:00`", parse_mode="Markdown")
            return
        ds = state["adm_date"]
        slots = db_get("slots", {})
        if ds not in slots: slots[ds] = []
        for t in valid:
            if t not in slots[ds]: slots[ds].append(t)
        slots[ds] = sorted(slots[ds])
        db_set("slots", slots)
        clear_state(uid)
        await msg.answer(f"✅ Слоты на *{ds}*: {', '.join(valid)}",
                         parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                             InlineKeyboardButton(text="↩️ Назад к дню", callback_data=f"adm_day_{ds}")
                         ]]))
        return
 
    # Открытие дня/недели теперь через интерактивный календарь (adm_day_ колбэк)
    # Fallback для текстового ввода
    if state.get("step") == "adm_open_day_date":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        slots = db_get("slots", {})
        slots[text] = ALL_DAY_SLOTS.copy()
        db_set("slots", slots)
        clear_state(uid)
        await msg.answer(f"✅ День *{text}* открыт ({len(ALL_DAY_SLOTS)} слотов)",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_block_month_input":
        if not re.match(r"^\d{4}-\d{2}$", text):
            await msg.answer("❌ Формат: `2026-08`", parse_mode="Markdown")
            return
        year, month = int(text.split("-")[0]), int(text.split("-")[1])
        days_in_month = calendar.monthrange(year, month)[1]
        appts = db_get("appointments", {})
        conflicts = [f"{year}-{month:02d}-{day:02d}" for day in range(1, days_in_month+1)
                     if appts.get(f"{year}-{month:02d}-{day:02d}")]
        if conflicts:
            state["block_month"] = text; state["step"] = "adm_block_month_confirm"
            set_state(uid, state)
            conflict_text = "\n".join(f"  {ds}: {len(appts[ds])} записей" for ds in conflicts)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Заблокировать несмотря на записи",
                                      callback_data="adm_block_month_yes")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
            ])
            await msg.answer(f"⚠️ В {text} есть записи:\n{conflict_text}\n\nВсё равно заблокировать?",
                             reply_markup=kb)
        else:
            blocked_dates = db_get("blocked_dates", [])
            for day in range(1, days_in_month+1):
                ds = f"{year}-{month:02d}-{day:02d}"
                if ds not in blocked_dates: blocked_dates.append(ds)
            db_set("blocked_dates", blocked_dates)
            clear_state(uid)
            await msg.answer(f"🚫 Месяц *{text}* заблокирован.",
                             parse_mode="Markdown", reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_move_pick_date":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            await msg.answer("❌ Формат: `2026-05-22`", parse_mode="Markdown")
            return
        state["move_new_date"] = text; state["step"] = "adm_move_pick_time"
        set_state(uid, state)
        await msg.answer("Введи новое время (`14:00`):", parse_mode="Markdown")
        return
 
    if state.get("step") == "adm_move_pick_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text):
            await msg.answer("❌ Формат: `14:00`", parse_mode="Markdown")
            return
        appts = db_get("appointments", {})
        old_ds = state["move_old_date"]; new_ds = state["move_new_date"]
        target_uid = state["move_uid"]; new_time = text
        moved = False
        for rec in appts.get(old_ds, []):
            if rec["user_id"]==target_uid and rec["time"]==state["move_old_time"]:
                appts[old_ds].remove(rec)
                rec["time"] = new_time
                rec["reminded_client"] = False; rec["reminded_admin"] = False
                if new_ds not in appts: appts[new_ds] = []
                appts[new_ds].append(rec)
                moved = True
                try:
                    await bot.send_message(target_uid,
                        f"📅 Ваша консультация перенесена:\n*{new_ds}* в *{new_time}* МСК",
                        parse_mode="Markdown")
                except: pass
                break
        if moved:
            db_set("appointments", appts)
            await msg.answer(f"✅ Перенесено на *{new_ds}* в *{new_time}*",
                             parse_mode="Markdown", reply_markup=admin_menu())
        else:
            await msg.answer("❌ Не удалось.", reply_markup=admin_menu())
        clear_state(uid)
        return
 
    if state.get("step") == "adm_reg_username":
        state["reg_username"] = text.lstrip("@"); state["step"] = "adm_reg_day"
        set_state(uid, state)
        days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=d, callback_data=f"regday_{d}")] for d in days
        ])
        await msg.answer("Выбери день недели:", reply_markup=kb)
        return
 
    if state.get("step") == "adm_reg_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text):
            await msg.answer("❌ Формат: `15:00`", parse_mode="Markdown")
            return
        clients = db_get("regular_clients", [])
        clients.append({"username": state["reg_username"], "day": state["reg_day"], "time": text})
        db_set("regular_clients", clients)
        clear_state(uid)
        await msg.answer(f"✅ Постоянный клиент @{state['reg_username']} добавлен.",
                         reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_reg_del":
        username = text.lstrip("@")
        clients = db_get("regular_clients", [])
        db_set("regular_clients", [c for c in clients if c["username"].lower()!=username.lower()])
        clear_state(uid)
        await msg.answer(f"✅ @{username} удалён.", reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_unblock":
        try:
            target = int(text)
            blocked = db_get("blocked_users", [])
            if target in blocked:
                blocked.remove(target)
                db_set("blocked_users", blocked)
                await msg.answer(f"✅ {target} разблокирован.", reply_markup=admin_menu())
            else:
                await msg.answer("Не найден.", reply_markup=admin_menu())
        except:
            await msg.answer("❌ Введи числовой ID.")
        clear_state(uid)
        return
 
    if state.get("step") == "adm_broadcast_text":
        users = db_get("all_users", [])
        sent = 0
        for user_id in users:
            try:
                await bot.send_message(user_id, text)
                sent += 1
                await asyncio.sleep(0.05)
            except: pass
        clear_state(uid)
        await msg.answer(f"✅ Рассылка отправлена {sent} пользователям.", reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_post_link":
        users = db_get("all_users", [])
        sent = 0
        for user_id in users:
            try:
                await bot.send_message(user_id,
                    f"На канале много полезного — вот свежий материал:\n{text}\n\n"
                    f"Подписывайтесь если ещё нет 👉 @kasikov_psy")
                sent += 1
                await asyncio.sleep(0.05)
            except: pass
        clear_state(uid)
        await msg.answer(f"✅ Пост разослан {sent} пользователям.", reply_markup=admin_menu())
        return
 
    if state.get("step") == "adm_excel_from":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            await msg.answer("❌ Формат: `2026-05-01`", parse_mode="Markdown")
            return
        state["excel_from"] = text; state["step"] = "adm_excel_to"
        set_state(uid, state)
        await msg.answer("Дата *конца* периода *ГГГГ-ММ-ДД*:", parse_mode="Markdown")
        return
 
    if state.get("step") == "adm_excel_to":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            await msg.answer("❌ Формат: `2026-05-31`", parse_mode="Markdown")
            return
        date_from = state["excel_from"]; date_to = text
        clear_state(uid)
        if not EXCEL_OK:
            await msg.answer("❌ openpyxl не установлен.")
            return
        buf = generate_excel(date_from, date_to)
        if buf:
            await msg.answer_document(
                BufferedInputFile(buf.read(), filename=f"записи_{date_from}_{date_to}.xlsx"),
                caption=f"📊 Записи с {date_from} по {date_to}")
        else:
            await msg.answer("Записей за этот период нет.")
        return
 
    log_action(uid, msg.from_user.username, f"msg:{text[:30]}")
    await msg.answer("Выбери действие:", reply_markup=main_menu())
 
 
async def main():
    log.info("=" * 50)
    log.info("БОТ КАСИКОВА v5.0 ЗАПУЩЕН")
    log.info("/admin — панель  |  /stop — остановить")
    log.info("=" * 50)
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)
 
if __name__ == "__main__":
    asyncio.run(main())

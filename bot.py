"""
Бот Евгения Касикова v7.0
"""
import asyncio, os, shelve, calendar, re, logging, sys, io
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                            BufferedInputFile)
 
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_OK = True
except:
    EXCEL_OK = False
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("bot.log", encoding="utf-8")]
)
log = logging.getLogger(__name__)
 
TOKEN   = os.environ.get("BOT_TOKEN", "")
CHANNEL = os.environ.get("CHANNEL", "@kasikov_psy")
LEAD    = "https://t.me/kasikov_psy/230"
ADMINS  = ["Iozteam", "kasikovevgenii"]
 
PLATFORMS = {
    "Zoom":            "https://us04web.zoom.us/j/5806296223?pwd=Kk1taS7afUkbbdxQXnXk2FCc7Sglz4.1",
    "ВКонтакте":       "https://vk.ru/call/join/WcLhNuB_1k2NNkqmVirjcn932fkIUIgkQMQomB0kDtA",
    "Яндекс Телемост": "https://telemost.yandex.ru/j/41045386326619",
    "Google Meet":     "https://meet.google.com/xea-ubvn-sdg",
    "Teams":           "https://teams.live.com/meet/93982412886719?p=qS9poHinQUXXWNrRIp",
    "MAX":             "https://max.ru/joincall/ahmoeViSGUdzx948lSbeXgSXluuzdJW0h3HVmOepwtc",
}
DURATIONS = ["30 мин", "1 час", "1.5 часа", "2 часа", "2.5 часа", "3 часа"]
 
PRICES = {
    "30 мин":   2500,
    "1 час":    5000,
    "1.5 часа": 7500,
    "2 часа":   10000,
    "2.5 часа": 12500,
    "3 часа":   15000,
}
 
PAYMENT_CARD_RU = """💳 *Оплата картой РФ / СБП*
 
По номеру телефона СБП:
`+7 965 763-48-79`
Евгений Александрович К.
 
Банки: Сбер, ВТБ, Альфа, Газпром, Озон
 
После оплаты нажмите кнопку ниже 👇"""
 
PAYMENT_CARD_INTL = """💳 *Оплата зарубежной картой*
 
Номер карты:
`4916 9903 1291 7674`
Jamolov Nurmuxammad
 
После оплаты нажмите кнопку ниже 👇"""
 
PRICES = {
    "30 мин":   2500,
    "1 час":    5000,
    "1.5 часа": 7500,
    "2 часа":   10000,
    "2.5 часа": 12500,
    "3 часа":   15000,
}
 
RF_CARD = """💳 *Оплата картой РФ / СБП*
 
Номер телефона (СБП): *+7 965 763-48-79*
Получатель: Евгений Александрович К.
Банки: Сбер, ВТБ, Альфа, Газпром, Озон
 
После оплаты нажмите кнопку «✅ Оплатил»"""
 
FOREIGN_CARD = """💳 *Оплата зарубежной картой*
 
Номер карты: *4916 9903 1291 7674*
Получатель: Jamolov Nurmuxammad
 
После оплаты нажмите кнопку «✅ Оплатил»"""
 
SOURCES   = [("📸 Instagram","ig"),("🎵 TikTok","tt"),
             ("▶️ YouTube","yt"),("💙 ВКонтакте","vk"),("🌐 Другой","other")]
 
bot = Bot(token=TOKEN)
dp  = Dispatcher()
 
DB = "kasikov_bot"
 
def db_get(k, d=None):
    with shelve.open(DB) as s: return s.get(k, d)
 
def db_set(k, v):
    with shelve.open(DB) as s: s[k] = v
 
def db_init():
    for k, v in [
        ("slots",{}),("appts",{}),("admin_chats",[]),("blocked",[]),
        ("logs",[]),("blocked_dates",[]),("users",[]),("violations",{}),
        ("regulars",[]),("states",{}),("drip",[]),("invited",[]),
        ("reviews",[]),("pending_feedback",{}),("closed_slots",{}),
    ]:
        if db_get(k) is None: db_set(k, v)
 
db_init()
 
def get_st(uid):
    return db_get("states", {}).get(str(uid), {})
 
def set_st(uid, st):
    s = db_get("states", {})
    s[str(uid)] = st
    db_set("states", s)
 
def clr_st(uid):
    s = db_get("states", {})
    s.pop(str(uid), None)
    db_set("states", s)
 
_flood_last  = {}
_flood_count = {}
 
BAD = [
    "блять","бля","блядь","хуй","хуйня","хуёво","хуево","хуёвый","хуевый",
    "хуила","хуило","пиздец","пизда","пиздатый","пизданутый","пиздить",
    "ёбаный","еб","ебать","ебёт","ебал","ебаный","ебанутый","ёбнуть","ебнуть",
    "сука","суки","сучка","мудак","мудила","залупа","шлюха","шлюшка",
    "пидор","пидорас","гандон","ублюдок","долбоёб","долбоеб","дрочить",
    "манда","срань","жопа","педик","педераст","нахуй","нахер","ёпт","епт",
    "курва","дерьмо","fuck","shit","bitch","asshole","cunt","whore","шалава",
]
 
def has_bad(t): return any(w in t.lower() for w in BAD)
 
def viol(uid, tp):
    v = db_get("violations", {})
    v.setdefault(str(uid), {})[tp] = v.get(str(uid), {}).get(tp, 0) + 1
    db_set("violations", v)
    return v[str(uid)][tp]
 
def is_flood(uid):
    now = datetime.now().timestamp()
    if now - _flood_last.get(uid, 0) < 2:
        c = _flood_count.get(uid, 0) + 1
        _flood_count[uid] = c
        if c > 15 and viol(uid, "spam") >= 5:
            asyncio.create_task(_auto_block(uid, "спам"))
        return True
    _flood_last[uid] = now
    _flood_count[uid] = 0
    return False
 
def is_blocked(uid): return uid in db_get("blocked", [])
def is_admin(u): return bool(u) and u.lower() in [a.lower() for a in ADMINS]
 
async def _auto_block(uid, reason):
    bl = db_get("blocked", [])
    if uid not in bl:
        bl.append(uid); db_set("blocked", bl)
        log.warning(f"АВТОБЛОК {uid} - {reason}")
        await notify_adm(f"🚫 *Автоблок*\nID: {uid}\nПричина: {reason}")
 
def reg_user(uid):
    u = db_get("users", [])
    if uid not in u: u.append(uid); db_set("users", u)
 
def log_act(uid, uname, act):
    ls = db_get("logs", [])
    ls.append({"uid": uid, "u": uname or "?", "a": act,
               "t": datetime.now().strftime("%d.%m.%Y %H:%M:%S")})
    if len(ls) > 1000: ls = ls[-1000:]
    db_set("logs", ls)
    log.info(f"@{uname}({uid}) - {act}")
 
async def is_sub(uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status in ("member", "administrator", "creator")
    except: return False
 
async def notify_adm(text, kb=None):
    for cid in db_get("admin_chats", []):
        try: await bot.send_message(cid, text, parse_mode="Markdown", reply_markup=kb)
        except: pass
 
def day_slots_all():
    r = []; c = datetime.strptime("10:00", "%H:%M"); e = datetime.strptime("21:00", "%H:%M")
    while c <= e: r.append(c.strftime("%H:%M")); c += timedelta(minutes=30)
    return r
 
ALL_SLOTS = day_slots_all()
 
def free_slots(ds):
    slots        = db_get("slots", {})
    closed_slots = db_get("closed_slots", {})
    appts        = db_get("appts", {})
    taken  = [r["time"] for r in appts.get(ds, [])]
    closed = closed_slots.get(ds, [])
    return [t for t in slots.get(ds, []) if t not in taken and t not in closed]
 
def has_booking(uid, ds):
    return any(r["user_id"] == uid for r in db_get("appts", {}).get(ds, []))
 
# ── ТЕКСТЫ ──────────────────────────────────────────────────────────────
 
T_ABOUT = """👤 *Обо мне*
 
Меня зовут Евгений Касиков.
 
Я не классический психолог в пиджаке с дипломом на стене. Я человек, который сам прошёл через то, с чем сейчас, скорее всего, пришли вы.
 
Двое детей и развод после 15 лет брака. Расставание после пяти лет отношений. Полный финансовый крах. И каждый раз казалось, что мир просто взял и перевернулся. То ощущение утром, когда просыпаешься, смотришь в потолок и думаешь: кто я теперь? Что вообще осталось?
 
Я знаю это изнутри. Не по книжкам.
 
Я из тех, кто привык добиваться результата. Кандидат в мастера спорта по плаванию, семь лет музыкальной школы. Потом 15 лет в найме в продажах: от рядового менеджера до директора по региону. Шесть собственных бизнесов. Флиппинг недвижимости - 10+ лет в рынке, 175+ объектов.
 
А потом всё рухнуло разом. Бизнес, отношения, темп. Деньги, статус, ориентиры. Я упал и разбился в дребезги.
 
И я не стал делать вид, что всё нормально. Пересобрал себя. Медленно, честно, без имитации бодрости.
 
Сегодня я работаю с людьми в период расставания и развода. За плечами более 10 лет практики и более 200 часов личной и групповой терапии. Более 200 реальных историй в работе с отношениями.
 
Я говорю на вашем языке. Смотрю не сверху - а рядом. Потому что я там был. И я знаю, что из этого выходят.
 
👉 @kasikovevgenii"""
 
T_HOW1 = """⚙️ *Как я работаю*
 
Сразу скажу честно - чтобы вы понимали, подходим ли мы друг другу.
 
Я не даю советов как жить. Не говорю «сделайте вот так». Если вы ищете именно это - я не тот специалист.
 
Я помогаю вам увидеть то, что вы сами не видите. Ваши паттерны, автоматические реакции, то как вы строите отношения. Задаю вопросы - иногда неудобные. Не осуждаю - но и не сюсюкаю.
 
Решения всегда остаются за вами. Работа идёт в живых сессиях - не в переписке. Завершить можно в любой момент.
 
Я работаю интегративно - это значит, я не привязан к одному методу. Выбираю то, что работает для конкретного человека в конкретной ситуации."""
 
T_HOW2 = """*НЛП*
Первые недели после расставания - хаос в голове. Одна и та же картинка прокручивается по кругу. НЛП работает с тем, как вы воспринимаете произошедшее - меняет не событие, а то, как оно живёт внутри.
 
*Транзактный анализ (Эрик Бёрн)*
Почему снова похожая ситуация, похожий партнёр, похожий финал. Смотрим из какого эго-состояния вы живёте в отношениях - из Родителя, Ребёнка или Взрослого.
 
*Психология привязанности (Боулби, Эйнсворт)*
Почему расставание бьёт так сильно - это не слабость. Это ваш тип привязанности, сформированный очень давно. Когда понимаете свой паттерн - перестаёте себя винить.
 
*EMDR*
Измена, предательство, внезапный уход - это травма. EMDR работает с тем, что застряло и не переваривается - воспоминания которые возвращаются снова и снова.
 
*Работа с телом*
Боль после расставания живёт не только в голове. Сжатие в груди, тяжесть, невозможность дышать полно. Работа с телесными реакциями помогает добраться до того, что словами не выражается.
 
*Гештальт*
Незавершённые разговоры, невысказанное, то что так и осталось внутри. Гештальт работает в настоящем моменте - завершает прошлое."""
 
T_HOW3 = """*IFS - работа с частями личности*
Одна часть хочет вернуться - другая знает что нельзя. Одна злится - другая скучает. Работа с частями помогает перестать воевать с собой и начать слышать что каждая из них на самом деле хочет.
 
*Схема-терапия (Джеффри Янг)*
Глубокие убеждения - «я недостаточно хорош», «меня всё равно бросят», «доверять нельзя». Они сформировались рано и тянут в одни и те же ситуации.
 
*Юнгианский подход*
Когда не можете отпустить - часто дело не в том человеке, а в том что вы видели в нём. Возвращаем это золото себе. Тогда отпускание происходит само.
 
*Психодинамический подход*
Почему вы выбираете именно таких людей, почему реагируете именно так - работаем с бессознательными паттернами.
 
*Травма-информированный подход*
Работаю аккуратно - не ломлюсь в то, к чему вы ещё не готовы.
 
*Экзистенциальный подход*
После развода многие теряют не только партнёра - они теряют себя. Кризис идентичности - это нормально. Находим новую опору внутри.
 
*Мужская психология*
Мужчины горюют иначе, восстанавливаются иначе, просят о помощи иначе. Я это учитываю - и не работаю с вами как с универсальным клиентом."""
 
T_PRICE = """💼 *Условия платных консультаций*
 
*Разовая консультация*
60 минут - 5 000 руб.
 
*Пакет «Глубокая работа»*
5 консультаций (5 часов) - 20 000 руб.
_экономия 5 000 руб._
 
Работаю по видео - Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX.
 
После первой бесплатной встречи вы сами решаете - продолжать или нет.
 
Для записи: @kasikovevgenii"""
 
T_FREE1 = """Благодарю за проявленный интерес.
Решиться на первый шаг бывает непросто.
 
Я провожу бесплатную 30-минутную вводную консультацию. За это время разбираемся с тем, что сейчас происходит - и вы уходите с чуть большей ясностью и пониманием что делать дальше.
 
После встречи вы получите письменный разбор с конкретными темами и рекомендациями. Он останется с вами независимо от того, решите ли вы продолжать работу со мной."""
 
T_FREE2 = """Работаю по видео - ВКонтакте, Zoom, Яндекс Телемост, Google Meet, Teams, MAX.
 
Для комфортной встречи выберите тихое место, где вас не будут отвлекать.
 
Выберите удобную дату 👇
✅ - есть свободные слоты"""
 
T_FAQ = """❓ *Часто задаваемые вопросы*
 
*Это конфиденциально?*
Да. Всё что происходит на сессии остаётся между нами. Я не делюсь информацией ни с кем.
 
*Как проходит первая встреча?*
30 минут по видео. Никакого давления и обязательств. После встречи вы уходите с письменным разбором - независимо от того, решите ли продолжать работу со мной.
 
*Можно перенести или отменить?*
Да. Напишите мне минимум за 2 часа: @kasikovevgenii - или используйте кнопки в боте.
 
*Вы работаете только с мужчинами?*
Нет. Около половины моих клиентов - женщины. Тема расставания одинаково тяжела для всех.
 
*Сколько сессий нужно?*
Зависит от запроса. Есть люди которым хватает 5-6 встреч. Есть те кто работает дольше. Первая встреча даст понимание что подходит именно вам.
 
*Как технически проходит сессия?*
По видеосвязи - Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX. Нужно тихое место где вас не будут отвлекать."""
 
T_FEEDBACK = """Независимо от того, будете ли вы работать со мной дальше или нет - хочу попросить короткую обратную связь по нашей первой сессии.
 
Если откликается, ответьте на несколько вопросов - коротко, как идёт:
 
1. С каким состоянием вы пришли на сессию?
2. Что из сессии было для вас самым полезным или важным?
3. С каким состоянием вы вышли после неё?
4. Планируете ли продолжать работу дальше?
 
Если вы не против, я могу использовать ваш ответ в обезличенном виде - без имён и любых деталей по которым можно вас узнать.
 
Если нет - абсолютно нормально, просто дайте знать."""
 
DRIP = {
    1:   {"text": "Успели заглянуть в гайд? Там есть практика которую можно применить прямо сегодня - особенно второй шаг.\n\nЕсли захочется разобрать свою ситуацию лично - первая встреча бесплатно 👇", "kb": "free"},
    7:   {"text": "После расставания больно не потому что вы слабый.\n\nНейробиолог Этан Кросс из Мичиганского университета выяснил: мозг воспринимает социальную боль в тех же зонах что и физическую. Когда вам разбивают сердце - мозг регистрирует это как удар. Буквально.\n\nВы теряли не просто человека. Вы теряли версию себя который существовал рядом с этим человеком.\n\nБоль после расставания - это не слабость. Это нормально.\n\nБольше об этом на канале 👉 @kasikov_psy", "kb": None},
    14:  {"text": "Три вещи которые не надо делать в первый месяц. Я сам делал все три.\n\n1. Новые отношения сразу - рана переезжает, не заживает.\n2. Полный контакт с бывшим - мозгу нужна дистанция.\n3. Заливать боль чем угодно - она накапливается и потом выходит.\n\nПодробнее на канале 👉 @kasikov_psy", "kb": None},
    30:  {"text": "Прошёл месяц. Как вы?\n\nЕсли чувствуете что стало не легче а тяжелее - это сигнал. Не «возьмите себя в руки». А сигнал что иногда в одиночку дольше и тяжелее.\n\nЯ провожу бесплатную вводную встречу - 30 минут чтобы разобраться что сейчас происходит.\n\nЕсли актуально 👇", "kb": "free"},
    60:  {"text": "Почему вы скучаете по тому кто причинил вам боль?\n\nОн изменил. Она ушла без объяснений. И всё равно - скучаете. Всё равно думаете.\n\nПсихиатр Сью Джонсон объясняет через теорию привязанности: мозг привязывается не к хорошим людям. Он привязывается к знакомым людям.\n\nНо самое важное - вы скучаете не по человеку. Вы скучаете по версии себя который верил что всё получится.\n\nКогда понимаешь это - отпускание происходит само.\n\nБольше на канале 👉 @kasikov_psy", "kb": None},
    90:  {"text": "Почему вы снова выбираете похожих людей?\n\nРазные люди, разные истории - а паттерн один и тот же.\n\nПсихоаналитик Зигмунд Фрейд называл это «повторением навязчивости» - бессознательным стремлением воспроизводить знакомые ситуации.\n\nДжеффри Янг - создатель схема-терапии - называет это «схемами». Убеждения «я недостаточно хорош», «меня всё равно бросят» формируются рано и управляют выбором партнёров.\n\nЭто не ваша вина. Но это ваша ответственность - если хотите что-то изменить.\n\nНа канале подробнее 👉 @kasikov_psy", "kb": None},
    120: {"text": "Злость после расставания - куда её деть?\n\nПосле развода я был очень зол. На неё. На себя. На ситуацию.\n\nПсихотерапевт Лесли Гринберг: злость после расставания чаще всего вторичная эмоция. За ней прячется страх, боль, стыд, беспомощность.\n\nЗлость которую подавляют никуда не девается. Она либо разворачивается внутрь - и становится депрессией. Либо выплёскивается на следующего партнёра.\n\nЗлость которую проживают - проходит.\n\n👉 @kasikov_psy", "kb": None},
    150: {"text": "Как перестать проверять соцсети бывшего?\n\nНейробиолог Роберт Сапольски: мозг выделяет дофамин не когда получает награду - а когда ожидает её. Именно поэтому вы снова заходите на его страницу - вдруг там что-то новое.\n\nОблегчения это не даёт. Но мозг продолжает искать.\n\nПсихолог Гай Уинч пишет что восстановление после расставания работает как восстановление после зависимости. Первый шаг - убрать доступ к веществу.\n\nЗаблокировать. Не потому что вы слабый. А потому что вы умный.\n\n👉 @kasikov_psy", "kb": None},
    180: {"text": "Разница между горем и депрессией.\n\nГоре - нормальная реакция на потерю. Психиатр Элизабет Кюблер-Росс описала стадии: отрицание, злость, торг, депрессия, принятие. Горе движется. Медленно - но движется.\n\nДепрессия - другое. Стойкое ощущение пустоты больше двух недель. Потеря интереса к тому что раньше нравилось.\n\nЕсли через месяц-два вам не становится хотя бы немного легче - это сигнал обратиться за помощью.\n\nЯ говорю это как человек который сам понял что в одиночку тяжелее.\n\n👉 @kasikov_psy", "kb": None},
    210: {"text": "Тревожная привязанность - почему одни страдают после расставания сильнее других.\n\nПсихологи Джон Боулби и Мэри Эйнсворт: паттерн того как мы строим близкие отношения формируется в первые годы жизни.\n\nЧеловек с тревожной привязанностью постоянно боится что его бросят. Когда отношения заканчиваются - это не просто потеря. Это подтверждение самого страшного страха: «я недостаточно хорош».\n\nХорошая новость: тип привязанности не приговор. Он меняется. Понять свой паттерн - это уже половина работы.\n\n👉 @kasikov_psy", "kb": None},
    240: {"text": "Как говорить с детьми о разводе.\n\nДетский психолог Джудит Валлерстайн посвятила 25 лет этой теме. Её главный вывод: дети переживают не сам развод, а то как родители ведут себя во время и после него.\n\nТри вещи которые важно знать:\n\n1. Говорите правду - но возрастную. «Мы решили жить отдельно. Это не ваша вина».\n2. Никогда не делайте ребёнка союзником против другого родителя.\n3. Дайте ребёнку право на все чувства - злость, грусть, растерянность.\n\n👉 @kasikov_psy", "kb": None},
    270: {"text": "Когда вы готовы к новым отношениям - честный ответ.\n\nДело не во времени. Вот несколько признаков:\n\nВы можете думать о бывшем без острой боли.\nВы знаете что пошло не так - и видите в этом свой вклад.\nВы хотите новых отношений - а не хотите убежать от одиночества.\n\nПсихолог Харвилл Хендрикс пишет что зрелые отношения начинаются с двух целостных людей. Стать целым - это и есть работа после расставания.\n\n👉 @kasikov_psy", "kb": "free"},
    300: {"text": "10 месяцев назад вы забрали гайд. Хочу спросить - как вы сейчас?\n\nЗа это время я отправил несколько материалов о расставании, боли, паттернах и восстановлении. Надеюсь, что-то из этого было полезным.\n\nЕсли вы всё ещё в процессе - это нормально. У каждого свой темп.\n\nЕсли захотите пройти этот путь с поддержкой - я здесь. Первая встреча по-прежнему бесплатно 👇", "kb": "free"},
}
 
# ── МЕНЮ ────────────────────────────────────────────────────────────────
 
MN = ["Январь","Февраль","Март","Апрель","Май","Июнь",
      "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
 
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Первая бесплатная консультация", callback_data="free")],
        [InlineKeyboardButton(text="💼 Условия платных консультаций",    callback_data="paid_info")],
        [InlineKeyboardButton(text="📄 Гайд «4 шага после расставания»", callback_data="guide")],
        [InlineKeyboardButton(text="👤 Обо мне",                         callback_data="about")],
        [InlineKeyboardButton(text="❓ FAQ",                              callback_data="faq")],
        [InlineKeyboardButton(text="📅 Мои записи",                      callback_data="my_appts")],
        [InlineKeyboardButton(text="📢 Подписаться на канал",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
    ])
 
def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Главное меню", callback_data="main")]
    ])
 
def kb_platform(back="main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Zoom",            callback_data="plat_Zoom")],
        [InlineKeyboardButton(text="📱 ВКонтакте",       callback_data="plat_ВКонтакте")],
        [InlineKeyboardButton(text="💻 Яндекс Телемост", callback_data="plat_Яндекс Телемост")],
        [InlineKeyboardButton(text="📹 Google Meet",     callback_data="plat_Google Meet")],
        [InlineKeyboardButton(text="🖥 Teams",           callback_data="plat_Teams")],
        [InlineKeyboardButton(text="📲 MAX",             callback_data="plat_MAX")],
        [InlineKeyboardButton(text="↩️ Назад",           callback_data=back)],
    ])
 
def kb_duration():
    rows = [[InlineKeyboardButton(text=d, callback_data=f"dur_{d}")] for d in DURATIONS]
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Календарь",                callback_data="adm_cal")],
        [InlineKeyboardButton(text="✅ Открыть неделю",           callback_data="adm_open_week")],
        [InlineKeyboardButton(text="❌ Заблокировать неделю",     callback_data="adm_block_week")],
        [InlineKeyboardButton(text="❌ Заблокировать месяц",      callback_data="adm_block_month")],
        [InlineKeyboardButton(text="🟡 Неподтверждённые записи", callback_data="adm_unconf")],
        [InlineKeyboardButton(text="📋 Прошедшие бесплатные",    callback_data="adm_past_free")],
        [InlineKeyboardButton(text="📋 Все записи",              callback_data="adm_list")],
        [InlineKeyboardButton(text="📅 Мои слоты таблицей",      callback_data="adm_table")],
        [InlineKeyboardButton(text="👥 Постоянные клиенты",      callback_data="adm_regulars")],
        [InlineKeyboardButton(text="➕ Новый клиент из соцсетей",callback_data="adm_new_src")],
        [InlineKeyboardButton(text="📊 Статистика",              callback_data="adm_stats")],
        [InlineKeyboardButton(text="📤 Рассылка всем",           callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📤 Отправить пост из канала",callback_data="adm_post")],
        [InlineKeyboardButton(text="📊 Excel отчёт",             callback_data="adm_excel")],
        [InlineKeyboardButton(text="⭐️ Отзывы",                  callback_data="adm_reviews")],
        [InlineKeyboardButton(text="🚫 Заблокированные",         callback_data="adm_blocked")],
        [InlineKeyboardButton(text="📊 Логи",                    callback_data="adm_logs")],
    ])
 
def cal_user(year, month):
    today = date.today()
    cal   = calendar.monthcalendar(year, month)
    bd    = db_get("blocked_dates", [])
    rows  = []
    rows.append([InlineKeyboardButton(text=f"📅 {MN[month-1]} {year}", callback_data="noop")])
    rows.append([InlineKeyboardButton(text=d, callback_data="noop")
                 for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                d  = date(year, month, day)
                ds = d.strftime("%Y-%m-%d")
                if d < today:
                    row.append(InlineKeyboardButton(text="·", callback_data="noop"))
                elif ds in bd:
                    row.append(InlineKeyboardButton(text="❌", callback_data="noop"))
                elif free_slots(ds):
                    row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"uday_{ds}"))
                else:
                    row.append(InlineKeyboardButton(text=str(day), callback_data="no_slots"))
        rows.append(row)
    pm, py = (month-1, year) if month > 1 else (12, year-1)
    nm, ny = (month+1, year) if month < 12 else (1, year+1)
    nav = []
    if date(py, pm, 1) >= today.replace(day=1):
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ucal_{py}_{pm}"))
    else:
        nav.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    nav.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"ucal_{ny}_{nm}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def cal_admin(year, month):
    today = date.today()
    cal   = calendar.monthcalendar(year, month)
    appts = db_get("appts", {})
    slots = db_get("slots", {})
    bd    = db_get("blocked_dates", [])
    rows  = []
    rows.append([InlineKeyboardButton(text=f"🔧 {MN[month-1]} {year}", callback_data="noop")])
    rows.append([InlineKeyboardButton(text=d, callback_data="noop")
                 for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                d  = date(year, month, day)
                ds = d.strftime("%Y-%m-%d")
                if d < today:
                    row.append(InlineKeyboardButton(text="·", callback_data=f"aday_{ds}"))
                else:
                    # Сначала проверяем записи (приоритет выше блокировки)
                    day_a      = appts.get(ds, [])
                    has_unconf = any(not r.get("confirmed") for r in day_a)
                    has_conf   = any(r.get("confirmed") for r in day_a)
                    is_blocked = ds in bd
                    if has_unconf:
                        row.append(InlineKeyboardButton(text=f"🟡{day}", callback_data=f"aday_{ds}"))
                    elif has_conf:
                        row.append(InlineKeyboardButton(text=f"🔵{day}", callback_data=f"aday_{ds}"))
                    elif is_blocked:
                        row.append(InlineKeyboardButton(text=f"❌{day}", callback_data=f"aday_{ds}"))
                    elif slots.get(ds):
                        row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"aday_{ds}"))
                    else:
                        row.append(InlineKeyboardButton(text=str(day), callback_data=f"aday_{ds}"))
        rows.append(row)
    pm, py = (month-1, year) if month > 1 else (12, year-1)
    nm, ny = (month+1, year) if month < 12 else (1, year+1)
    rows.append([
        InlineKeyboardButton(text="◀️",      callback_data=f"acal_{py}_{pm}"),
        InlineKeyboardButton(text="↩️ Меню", callback_data="adm_back"),
        InlineKeyboardButton(text="▶️",      callback_data=f"acal_{ny}_{nm}"),
    ])
    rows.append([
        InlineKeyboardButton(text="✏️ Записать",          callback_data="adm_book_menu"),
        InlineKeyboardButton(text="✅ Открыть неделю",    callback_data="adm_open_week_cal"),
        InlineKeyboardButton(text="❌ Закрыть неделю",    callback_data="adm_block_week_cal"),
    ])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def slots_day_admin(ds):
    slots        = db_get("slots", {})
    closed_slots = db_get("closed_slots", {})
    appts        = db_get("appts", {})
    bd           = db_get("blocked_dates", [])
    today        = date.today()
    is_past      = datetime.strptime(ds, "%Y-%m-%d").date() < today
    is_blocked_day = ds in bd
    # Все слоты дня = открытые + закрытые + если день заблокирован — все
    open_slots   = slots.get(ds, [])
    closed_day   = closed_slots.get(ds, [])
    if is_blocked_day:
        all_day_slots = ALL_SLOTS
    else:
        all_day_slots = sorted(set(open_slots + closed_day))
    taken = {r["time"]: r for r in appts.get(ds, [])}
    rows = []
    row  = []
    for t in all_day_slots:
        if t in taken:
            emoji   = "🔵" if taken[t].get("confirmed") else "🟡"
            cb_data = f"aslot_{ds}_{t}"
        elif t in closed_day or is_blocked_day:
            emoji   = "🔴"
            cb_data = f"aslot_blocked_{ds}_{t}"
        else:
            emoji   = "🟢"
            cb_data = f"aslot_{ds}_{t}"
        row.append(InlineKeyboardButton(text=f"{emoji}{t}", callback_data=cb_data))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    if is_past:
        rows.append([InlineKeyboardButton(text="➕ Добавить сессию",
                                          callback_data=f"adm_add_session_{ds}")])
    elif is_blocked_day:
        rows.append([
            InlineKeyboardButton(text="✅ Открыть весь день",
                                 callback_data=f"adm_unblock_day_{ds}"),
            InlineKeyboardButton(text="✏️ Записать",
                                 callback_data=f"adm_book_slot_{ds}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="➕ Добавить слоты", callback_data=f"adm_add_slots_{ds}"),
            InlineKeyboardButton(text="✏️ Записать",       callback_data=f"adm_book_slot_{ds}"),
        ])
    rows.append([InlineKeyboardButton(text="↩️ Назад к календарю", callback_data="adm_cal")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def slots_menu_user(ds):
    slots        = db_get("slots", {})
    closed_slots = db_get("closed_slots", {})
    appts        = db_get("appts", {})
    taken  = [r["time"] for r in appts.get(ds, [])]
    closed = closed_slots.get(ds, [])
    rows   = []
    row    = []
    for t in slots.get(ds, []):
        if t in closed: continue  # закрытые не показываем клиенту
        if t in taken:
            row.append(InlineKeyboardButton(text=f"🔴{t}", callback_data="slot_taken"))
        else:
            row.append(InlineKeyboardButton(text=f"🟢{t}", callback_data=f"uslot_{ds}_{t}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def make_excel(d_from, d_to):
    if not EXCEL_OK: return None
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Записи"
    hdr = ["Дата","Время","Тип","Статус","Имя","Username",
           "Платформа","Длительность","Описание","Источник"]
    hf = PatternFill("solid", fgColor="2E86AB")
    for i, h in enumerate(hdr, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = hf; c.font = Font(color="FFFFFF", bold=True)
        c.alignment = Alignment(horizontal="center")
    appts = db_get("appts", {})
    row = 2
    for ds in sorted(appts.keys()):
        if ds < d_from or ds > d_to: continue
        for r in appts[ds]:
            ws.cell(row=row, column=1, value=ds)
            ws.cell(row=row, column=2, value=r.get("time", ""))
            ws.cell(row=row, column=3, value="Платная" if r.get("type") == "paid" else "Бесплатная")
            ws.cell(row=row, column=4, value=r.get("status", ""))
            ws.cell(row=row, column=5, value=r.get("name", ""))
            ws.cell(row=row, column=6, value=f"@{r.get('username','')}")
            ws.cell(row=row, column=7, value=r.get("platform", ""))
            ws.cell(row=row, column=8, value=r.get("duration", ""))
            ws.cell(row=row, column=9, value=r.get("desc", ""))
            ws.cell(row=row, column=10, value=r.get("source", "бот"))
            row += 1
    for col in ws.columns:
        ml = max((len(str(c.value or "")) for c in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(ml + 4, 40)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf
 
# ── ФОНОВЫЕ ЗАДАЧИ ──────────────────────────────────────────────────────
 
async def bg_loop():
    while True:
        await asyncio.sleep(60)
        try:
            now   = datetime.now()
            appts = db_get("appts", {})
            changed = False
 
            for ds, recs in appts.items():
                for rec in recs:
                    try:
                        appt_dt = datetime.strptime(f"{ds} {rec['time']}", "%Y-%m-%d %H:%M")
                    except: continue
                    diff_min = (appt_dt - now).total_seconds() / 60
 
                    # Напоминание за 60 мин
                    if 59 <= diff_min <= 61:
                        plat = rec.get("platform", "")
                        link = PLATFORMS.get(plat, "")
                        if not rec.get("rem_client") and rec.get("user_id"):
                            try:
                                kb = InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="✅ Подтверждаю",
                                                          callback_data=f"cli_ok_{ds}_{rec['time']}")],
                                    [InlineKeyboardButton(text="❌ Отменить",
                                                          callback_data=f"cli_cancel_{ds}_{rec['time']}")],
                                    [InlineKeyboardButton(text="🔄 Перенести",
                                                          callback_data=f"cli_move_{ds}_{rec['time']}")],
                                ])
                                await bot.send_message(rec["user_id"],
                                    f"⏰ Напоминание!\n\n"
                                    f"Через час наша встреча - {rec['time']} МСК\n"
                                    f"Платформа: {plat}\n"
                                    f"{'🔗 ' + link if link else ''}\n\n"
                                    f"Если всё окей 😁 просьба подтвердить:",
                                    reply_markup=kb)
                                rec["rem_client"] = True; changed = True
                            except: pass
                        if not rec.get("rem_admin"):
                            tl = "💼 Платная" if rec.get("type") == "paid" else "🆓 Бесплатная"
                            kb2 = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Подтвердить",
                                                      callback_data=f"adm_ok_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="❌ Отменить",
                                                      callback_data=f"adm_cncl_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="🔄 Перенести",
                                                      callback_data=f"adm_mv_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                            ])
                            await notify_adm(
                                f"⏰ *Через час консультация!*\n\n"
                                f"📅 {ds} в {rec['time']} МСК\n{tl}\n"
                                f"👤 {rec.get('name','—')}\n📱 {plat}\n"
                                f"⏱ {rec.get('duration','—')}\n🆔 @{rec.get('username','—')}",
                                kb=kb2)
                            rec["rem_admin"] = True; changed = True
 
                    # Повтор если клиент не подтвердил через 30 мин
                    if 29 <= diff_min <= 31 and rec.get("rem_client") and not rec.get("cli_confirmed") and rec.get("user_id"):
                        try:
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Подтверждаю",
                                                      callback_data=f"cli_ok_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="❌ Отменить",
                                                      callback_data=f"cli_cancel_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="🔄 Перенести",
                                                      callback_data=f"cli_move_{ds}_{rec['time']}")],
                            ])
                            await bot.send_message(rec["user_id"],
                                "Вы ещё не подтвердили участие. Всё в силе? 😊",
                                reply_markup=kb)
                        except: pass
 
                    # Через 5 мин после окончания
                    dur_map = {"30 мин":30,"1 час":60,"1.5 часа":90,
                               "2 часа":120,"2.5 часа":150,"3 часа":180}
                    dur_m   = dur_map.get(rec.get("duration","30 мин"), 30)
                    past    = (now - (appt_dt + timedelta(minutes=dur_m+5))).total_seconds() / 60
                    if 0 <= past <= 2 and not rec.get("session_asked"):
                        tl = "💼 Платная" if rec.get("type") == "paid" else "🆓 Бесплатная"
                        kb3 = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Да, бесплатная",
                                                  callback_data=f"sess_yes_free_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="✅ Да, платная",
                                                  callback_data=f"sess_yes_paid_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="❌ Нет, бесплатная",
                                                  callback_data=f"sess_no_free_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="❌ Нет, платная",
                                                  callback_data=f"sess_no_paid_{ds}_{rec['time']}")],
                        ])
                        await notify_adm(
                            f"📅 {ds} в {rec['time']} МСК\n{tl} | ⏱ {rec.get('duration','—')}\n"
                            f"👤 {rec.get('name','—')}\n🆔 @{rec.get('username','—')}\n\n"
                            f"Сессия состоялась?", kb=kb3)
                        rec["session_asked"] = True; changed = True
 
            if changed: db_set("appts", appts)
 
            # Напоминание Евгению об обратной связи
            pf = db_get("pending_feedback", {})
            for key, item in list(pf.items()):
                if item.get("sent"): continue
                if now >= datetime.fromisoformat(item["remind_at"]):
                    await notify_adm(
                        f"📅 {item['ds']} в {item['time']}\n"
                        f"🆓 Бесплатная | ⏱ {item.get('dur','—')}\n"
                        f"👤 {item['name']}\n🆔 @{item['username']}\n\n"
                        f"Жду от вас обратную связь и план работы, Евгений.",
                        kb=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="📝 Отправить обратную связь",
                                                 callback_data=f"send_fb_{key}")
                        ]]))
                    item["remind_at"] = (now + timedelta(hours=24)).isoformat()
            db_set("pending_feedback", pf)
 
            # Капельная воронка
            drip = db_get("drip", [])
            left = []
            for item in drip:
                if now >= datetime.fromisoformat(item["at"]):
                    d = DRIP.get(item["day"])
                    if d:
                        try:
                            kb = None
                            if d["kb"] == "free":
                                kb = InlineKeyboardMarkup(inline_keyboard=[[
                                    InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",
                                                         callback_data="free")
                                ]])
                            await bot.send_message(item["uid"], d["text"], reply_markup=kb)
                        except: pass
                else:
                    left.append(item)
            db_set("drip", left)
 
        except Exception as e:
            log.error(f"bg_loop: {e}")
 
def drip_add(uid):
    q   = db_get("drip", [])
    now = datetime.now()
    for day in DRIP:
        q.append({"uid": uid, "day": day,
                  "at": (now + timedelta(days=day)).isoformat()})
    db_set("drip", q)
 
# ── ХЭНДЛЕРЫ КЛИЕНТА ────────────────────────────────────────────────────
 
@dp.message(Command("start","admin","stop"))
async def cmd_handler(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid): return
    clr_st(uid); reg_user(uid)
    log_act(uid, msg.from_user.username, msg.text or "cmd")
    if is_admin(msg.from_user.username):
        chats = db_get("admin_chats", [])
        if uid not in chats: chats.append(uid); db_set("admin_chats", chats)
    cmd = (msg.text or "").split()[0]
    if cmd == "/stop":
        if is_admin(msg.from_user.username):
            await msg.answer("🛑 Бот останавливается...")
            await dp.stop_polling()
        return
    if cmd == "/admin":
        if is_admin(msg.from_user.username):
            await msg.answer("🔐 *Панель администратора*",
                             parse_mode="Markdown", reply_markup=kb_admin())
        return
    await msg.answer(
        f"Приветствую, {msg.from_user.first_name} 👋\n\n"
        "Меня зовут Евгений.\n\n"
        "Я помогаю людям пройти через расставание - без застревания "
        "и с пониманием что делать дальше.\n\n"
        "Кто я и как работаю смотрите ниже 👇\n\n"
        "Что вас интересует?",
        reply_markup=kb_main())
 
@dp.callback_query(F.data == "noop")
async def noop(cb): await cb.answer()
 
@dp.callback_query(F.data == "no_slots")
async def no_slots(cb): await cb.answer("На этот день слотов нет", show_alert=True)
 
@dp.callback_query(F.data == "slot_taken")
async def slot_taken(cb): await cb.answer("Это время занято 🔴", show_alert=True)
 
@dp.callback_query(F.data == "main")
async def go_main(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Главное меню:", reply_markup=kb_main())
 
@dp.callback_query(F.data == "close_cal")
async def close_cal(cb: types.CallbackQuery):
    await cb.message.delete()
 
@dp.callback_query(F.data == "about")
async def about(cb: types.CallbackQuery):
    await cb.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Как я работаю",               callback_data="how_work")],
        [InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",     callback_data="free")],
        [InlineKeyboardButton(text="💼 Записаться на платную",        callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад",                        callback_data="main")],
    ])
    await cb.message.answer(T_ABOUT, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "how_work")
async def how_work(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer(T_HOW1, parse_mode="Markdown")
    await asyncio.sleep(0.3)
    await cb.message.answer(T_HOW2, parse_mode="Markdown")
    await asyncio.sleep(0.3)
    cta_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",  callback_data="free")],
        [InlineKeyboardButton(text="💼 Записаться на платную",     callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад",                     callback_data="main")],
    ])
    await cb.message.answer(T_HOW3, parse_mode="Markdown", reply_markup=cta_kb)
 
@dp.callback_query(F.data == "faq")
async def faq(cb: types.CallbackQuery):
    await cb.answer()
    faq_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Записаться на бесплатную",  callback_data="free")],
        [InlineKeyboardButton(text="💼 Записаться на платную",     callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад",                     callback_data="main")],
    ])
    await cb.message.answer(T_FAQ, parse_mode="Markdown", reply_markup=faq_kb)
 
@dp.callback_query(F.data == "paid_info")
async def paid_info(cb: types.CallbackQuery):
    await cb.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ Назад",      callback_data="main")],
    ])
    await cb.message.answer(T_PRICE, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "guide")
async def guide(cb: types.CallbackQuery):
    await cb.answer()
    log_act(cb.from_user.id, cb.from_user.username, "guide")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
        [InlineKeyboardButton(text="↩️ Назад",        callback_data="main")],
    ])
    await cb.message.answer(
        "📄 *Гайд «4 шага выхода из расставания»* - 30 страниц практики.\n\n"
        "Чтобы получить - подпишитесь на канал 👇",
        parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "check_sub")
async def check_sub(cb: types.CallbackQuery):
    if await is_sub(cb.from_user.id):
        log_act(cb.from_user.id, cb.from_user.username, "got_guide")
        drip_add(cb.from_user.id)
        await cb.message.delete()
        await cb.message.answer(
            f"✅ Держите гайд!\n\n👉 {LEAD}\n\n"
            "Если захочется разобрать свою ситуацию лично - первая встреча бесплатно 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="1️⃣ Записаться на бесплатную", callback_data="free")
            ]]))
    else:
        await cb.answer("❌ Подписка не найдена.", show_alert=True)
 
@dp.callback_query(F.data == "free")
async def free_consult(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    set_st(uid, {"type": "free"})
    log_act(uid, cb.from_user.username, "free_consult")
    await cb.message.answer(T_FREE1)
    await asyncio.sleep(0.5)
    today = date.today()
    await cb.message.answer(T_FREE2,
                             reply_markup=cal_user(today.year, today.month))
 
@dp.callback_query(F.data == "book_paid")
async def book_paid(cb: types.CallbackQuery):
    await cb.answer()
    set_st(cb.from_user.id, {"type": "paid"})
    today = date.today()
    await cb.message.answer("Выберите удобную дату 👇\n✅ - есть свободные слоты",
                             reply_markup=cal_user(today.year, today.month))
 
@dp.callback_query(F.data.startswith("ucal_"))
async def ucal_nav(cb: types.CallbackQuery):
    _, y, m = cb.data.split("_")
    await cb.message.edit_reply_markup(reply_markup=cal_user(int(y), int(m)))
 
@dp.callback_query(F.data.startswith("uday_"))
async def uday_sel(cb: types.CallbackQuery):
    ds  = cb.data[5:]
    uid = cb.from_user.id
    st  = get_st(uid)
    if st.get("type") != "reschedule" and has_booking(uid, ds):
        await cb.answer("У вас уже есть запись на этот день.", show_alert=True)
        return
    st["date"] = ds; set_st(uid, st)
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{ds}*\n\nВыберите время:\n🟢 свободно  🔴 занято",
        parse_mode="Markdown", reply_markup=slots_menu_user(ds))
 
@dp.callback_query(F.data.startswith("uslot_"))
async def uslot_sel(cb: types.CallbackQuery):
    parts  = cb.data.split("_")
    ds, tm = parts[1], parts[2]
    uid    = cb.from_user.id
    st     = get_st(uid)
    ctype  = st.get("type", "free")
    await cb.message.delete()
    if ctype in ("free", "reschedule"):
        st.update({"step":"desc","date":ds,"time":tm,"duration":"30 мин"})
        set_st(uid, st)
        name = cb.from_user.first_name or "Клиент"
        await cb.message.answer(
            f"{name}, чтобы сессия была для вас максимально полезной, "
            "по желанию опишите пожалуйста что сейчас у вас происходит:")
    else:
        st.update({"step":"duration","date":ds,"time":tm})
        set_st(uid, st)
        await cb.message.answer("Выберите длительность сессии:",
                                 reply_markup=kb_duration())
 
@dp.callback_query(F.data.startswith("dur_"))
async def dur_sel(cb: types.CallbackQuery):
    dur = cb.data[4:]
    uid = cb.from_user.id
    st  = get_st(uid)
    st["duration"] = dur; set_st(uid, st)
    await cb.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Первый раз",  callback_data="paid_first")],
        [InlineKeyboardButton(text="🔄 Повтор",       callback_data="paid_repeat")],
    ])
    await cb.message.answer("Это первая сессия или повторная?", reply_markup=kb)
 
@dp.callback_query(F.data == "paid_first")
async def paid_first_cb(cb: types.CallbackQuery):
    uid  = cb.from_user.id
    st   = get_st(uid); st["step"] = "desc"; st["is_repeat"] = False; set_st(uid, st)
    name = cb.from_user.first_name or "Клиент"
    await cb.answer()
    await cb.message.answer(
        f"{name}, чтобы сессия была для вас максимально полезной, "
        "по желанию опишите пожалуйста что сейчас у вас происходит:")
 
@dp.callback_query(F.data == "paid_repeat")
async def paid_repeat_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    st  = get_st(uid); st["step"] = "platform"; st["is_repeat"] = True
    st.setdefault("name", cb.from_user.first_name or "Клиент")
    st.setdefault("desc", "Повторная сессия")
    set_st(uid, st)
    await cb.answer()
    await cb.message.answer("Через какую платформу удобнее созвониться?",
                             reply_markup=kb_platform())
 
@dp.callback_query(F.data == "desc_extend")
async def desc_extend(cb: types.CallbackQuery):
    uid = cb.from_user.id
    st  = get_st(uid); st["step"] = "desc_retry"; set_st(uid, st)
    await cb.answer()
    await cb.message.answer("Пожалуйста, расскажите подробнее:")
 
@dp.callback_query(F.data == "desc_keep")
async def desc_keep(cb: types.CallbackQuery):
    uid = cb.from_user.id
    st  = get_st(uid); st["step"] = "platform"; set_st(uid, st)
    await cb.answer()
    await cb.message.answer("Через какую платформу удобнее созвониться?",
                             reply_markup=kb_platform())
 
@dp.callback_query(F.data.startswith("plat_"))
async def plat_sel(cb: types.CallbackQuery):
    plat = cb.data[5:]
    uid  = cb.from_user.id
    st   = get_st(uid)
    if st.get("step") == "adm_manual_plat":
        st["platform"] = plat; st["step"] = "adm_manual_type"; set_st(uid, st)
        await cb.answer()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="adm_mtype_free")],
            [InlineKeyboardButton(text="💼 Платная",    callback_data="adm_mtype_paid")],
            [InlineKeyboardButton(text="↩️ Назад",      callback_data="adm_back")],
        ])
        await cb.message.answer("Тип консультации?", reply_markup=kb)
        return
    st["platform"] = plat; st["step"] = "confirm"; set_st(uid, st)
    ds   = st.get("date","?"); tm = st.get("time","?")
    dur  = st.get("duration","30 мин")
    name = st.get("name", cb.from_user.first_name or "?")
    tl   = "💼 Платная" if st.get("type") == "paid" else "🆓 Бесплатная"
    ck   = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ Назад",       callback_data="main")],
    ])
    await cb.message.answer(
        f"📋 *Проверьте данные:*\n\n"
        f"📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n"
        f"👤 {name}\n📱 {plat}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=ck)
 
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_book(cb: types.CallbackQuery):
    uid = cb.from_user.id
    st  = get_st(uid)
    if not st: await cb.answer("Ошибка, начните заново", show_alert=True); return
    ds    = st["date"]; tm = st["time"]
    name  = st.get("name", cb.from_user.first_name or "—")
    ctype = st.get("type", "free")
    plat  = st.get("platform", "—")
    dur   = st.get("duration", "30 мин")
    desc  = st.get("desc", "—")
    uname = cb.from_user.username or "нет"
    appts = db_get("appts", {})
    if ds not in appts: appts[ds] = []
    if any(r["user_id"] == uid and r["time"] == tm for r in appts[ds]):
        await cb.answer("Вы уже записаны на это время", show_alert=True); return
    appts[ds].append({
        "user_id":uid,"name":name,"time":tm,"username":uname,
        "type":ctype,"platform":plat,"duration":dur,"desc":desc,
        "source":"бот","status":"","confirmed":False,
        "rem_client":False,"rem_admin":False,"session_asked":False,
        "cli_confirmed":False,"followup1":False,"followup3":False
    })
    db_set("appts", appts); clr_st(uid)
    await cb.message.delete()
    tl = "💼 Платная" if ctype == "paid" else "🆓 Бесплатная"
    ck = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перенести",  callback_data="reschedule")],
        [InlineKeyboardButton(text="❌ Отменить",   callback_data=f"cancel_{ds}_{tm}")],
        [InlineKeyboardButton(text="📅 Мои записи", callback_data="my_appts")],
    ])
    await cb.message.answer(
        f"✅ Запись принята!\n\n"
        f"📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n📱 {plat}\n\n"
        "Евгений скоро подтвердит и пришлёт ссылку на видеочат.",
        reply_markup=ck)
    # Для платной — сразу отправляем реквизиты
    if ctype == "paid":
        price = PRICES.get(dur, 5000)
        pay_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплата картой РФ / СБП",
                                  callback_data=f"pay_rf_{uid}_{ds}_{tm}")],
            [InlineKeyboardButton(text="💳 Оплата зарубежной картой",
                                  callback_data=f"pay_foreign_{uid}_{ds}_{tm}")],
        ])
        await cb.message.answer(
            f"💰 Стоимость сессии {dur}: *{price:,} руб.*\n\n"
            "Выберите удобный способ оплаты:",
            parse_mode="Markdown", reply_markup=pay_kb)
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить",
                              callback_data=f"adm_ok_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="❌ Отменить",
                              callback_data=f"adm_cncl_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="🔄 Перенести",
                              callback_data=f"adm_mv_{uid}_{ds}_{tm}")],
    ])
    await notify_adm(
        f"🔔 *Новая запись!*\n📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n"
        f"👤 {name}\n📱 {plat}\n💬 {desc[:100]}\n🆔 @{uname} | ID: {uid}",
        kb=adm_kb)
 
    # Реквизиты на оплату уходят сразу (только для платных)
    if ctype == "paid":
        price = PRICES.get(dur, 5000)
        pay_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплата картой РФ / СБП",
                                  callback_data=f"pay_ru_{uid}_{ds}_{tm}")],
            [InlineKeyboardButton(text="💳 Оплата зарубежной картой",
                                  callback_data=f"pay_intl_{uid}_{ds}_{tm}")],
        ])
        await bot.send_message(uid,
            f"💰 *Стоимость сессии: {price:,} руб.*\n\n"
            f"Выберите удобный способ оплаты:",
            parse_mode="Markdown", reply_markup=pay_kb)
 
@dp.callback_query(F.data == "my_appts")
async def my_appts(cb: types.CallbackQuery):
    uid   = cb.from_user.id
    appts = db_get("appts", {})
    today = date.today()
    rows  = []
    for ds in sorted(appts.keys()):
        try: d = datetime.strptime(ds, "%Y-%m-%d").date()
        except: continue
        if d < today: continue
        for r in appts[ds]:
            if r["user_id"] != uid: continue
            tl = "💼" if r.get("type") == "paid" else "🆓"
            rows.append([InlineKeyboardButton(
                text=f"📅 {ds} {r['time']} {tl}",
                callback_data=f"my_rec_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="main")])
    if len(rows) == 1:
        await cb.message.answer("У вас нет предстоящих записей.", reply_markup=kb_back())
    else:
        await cb.message.answer("📅 *Ваши записи:*", parse_mode="Markdown",
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data.startswith("my_rec_"))
async def my_rec(cb: types.CallbackQuery):
    _, _, ds, tm = cb.data.split("_", 3)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перенести", callback_data="reschedule")],
        [InlineKeyboardButton(text="❌ Отменить",  callback_data=f"cancel_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ Назад",     callback_data="my_appts")],
    ])
    await cb.message.answer(f"📅 {ds} в {tm} МСК", reply_markup=kb)
 
@dp.callback_query(F.data == "reschedule")
async def reschedule(cb: types.CallbackQuery):
    set_st(cb.from_user.id, {"type":"reschedule"})
    today = date.today()
    await cb.message.answer("Выберите новую дату:",
                             reply_markup=cal_user(today.year, today.month))
 
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_appt(cb: types.CallbackQuery):
    parts = cb.data.split("_"); ds = parts[1]; tm = parts[2]
    uid   = cb.from_user.id
    appts = db_get("appts", {})
    if ds in appts:
        appts[ds] = [r for r in appts[ds]
                     if not (r["user_id"] == uid and r["time"] == tm)]
        db_set("appts", appts)
    await cb.message.delete()
    await cb.message.answer("✅ Запись отменена. Если захотите записаться снова - я здесь.",
                             reply_markup=kb_main())
    await notify_adm(f"❌ Клиент отменил запись\n📅 {ds} в {tm}\n"
                     f"🆔 @{cb.from_user.username or 'нет'}")
 
@dp.callback_query(F.data.startswith("cli_ok_"))
async def cli_ok(cb: types.CallbackQuery):
    parts = cb.data.split("_"); ds = parts[2]; tm = parts[3]
    appts = db_get("appts", {})
    for r in appts.get(ds, []):
        if r["user_id"] == cb.from_user.id and r["time"] == tm:
            r["cli_confirmed"] = True
    db_set("appts", appts)
    await cb.answer("✅ Отлично! Ждём вас!")
    await notify_adm(f"✅ {cb.from_user.first_name} подтвердил участие\n📅 {ds} в {tm}")
 
@dp.callback_query(F.data.startswith("cli_cancel_"))
async def cli_cancel(cb: types.CallbackQuery):
    parts = cb.data.split("_"); ds = parts[2]; tm = parts[3]
    uid   = cb.from_user.id
    appts = db_get("appts", {})
    if ds in appts:
        appts[ds] = [r for r in appts[ds]
                     if not (r["user_id"] == uid and r["time"] == tm)]
        db_set("appts", appts)
    await cb.answer()
    await cb.message.answer("Запись отменена. Для новой записи: @kasikovevgenii",
                             reply_markup=kb_main())
    await notify_adm(f"❌ Клиент отменил перед сессией\n📅 {ds} в {tm}\n"
                     f"🆔 @{cb.from_user.username or 'нет'}")
 
@dp.callback_query(F.data.startswith("cli_move_"))
async def cli_move(cb: types.CallbackQuery):
    set_st(cb.from_user.id, {"type":"reschedule"})
    today = date.today()
    await cb.answer()
    await cb.message.answer("Выберите новую дату:",
                             reply_markup=cal_user(today.year, today.month))
    await notify_adm(f"🔄 Клиент хочет перенести\n🆔 @{cb.from_user.username or 'нет'}")
 
# ── ХЭНДЛЕРЫ ЕВГЕНИЯ ────────────────────────────────────────────────────
 
@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_ok(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    appts = db_get("appts", {}); plat = "—"; link = ""
    for r in appts.get(ds, []):
        if r["user_id"] == uid and r["time"] == tm:
            r["confirmed"] = True; plat = r.get("platform","—"); link = PLATFORMS.get(plat,"")
    db_set("appts", appts)
    try:
        ck = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перенести",  callback_data=f"cli_move_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ Отменить",   callback_data=f"cli_cancel_{ds}_{tm}")],
            [InlineKeyboardButton(text="📅 Мои записи", callback_data="my_appts")],
        ])
        await bot.send_message(uid,
            f"✅ Ваша запись подтверждена!\n\n"
            f"📅 {ds} в {tm} МСК\n📱 {plat}\n"
            f"{'🔗 ' + link if link else ''}\n\n"
            "За час до сессии вам придёт напоминание.\nПросьба подтвердить участие.",
            reply_markup=ck)
    except: pass
    await cb.message.edit_text(cb.message.text + "\n\n✅ *Подтверждено*",
                               parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("adm_cncl_"))
async def adm_cncl(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    appts = db_get("appts", {})
    if ds in appts:
        appts[ds] = [r for r in appts[ds]
                     if not (r["user_id"] == uid and r["time"] == tm)]
        db_set("appts", appts)
    try:
        await bot.send_message(uid,
            "❌ К сожалению, это время не получится.\n"
            "Для записи на другое время: @kasikovevgenii", reply_markup=kb_main())
    except: pass
    await cb.message.edit_text(cb.message.text + "\n\n❌ *Отменено*",
                               parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("adm_mv_"))
async def adm_mv(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    set_st(cb.from_user.id, {"step":"adm_move_new_date",
                              "move_uid":uid,"move_ds":ds,"move_tm":tm})
    today = date.today()
    await cb.message.answer("Выберите новую дату для переноса:",
                             reply_markup=cal_admin(today.year, today.month))
 
@dp.callback_query(F.data.startswith("sess_"))
async def sess_result(cb: types.CallbackQuery):
    parts  = cb.data.split("_")
    result = parts[1]; stype = parts[2]; ds = parts[3]; tm = parts[4]
    appts  = db_get("appts", {})
    rec    = next((r for r in appts.get(ds, []) if r["time"] == tm), None)
    name   = rec.get("name","—") if rec else "—"
    uname  = rec.get("username","—") if rec else "—"
    dur    = rec.get("duration","—") if rec else "—"
    if result == "yes":
        if rec: rec["status"] = "проведена"
        db_set("appts", appts)
        if stype == "free":
            key = f"{ds}_{tm}"
            pf  = db_get("pending_feedback", {})
            pf[key] = {
                "uid": rec.get("user_id",0) if rec else 0,
                "ds":ds,"time":tm,"dur":dur,"name":name,"username":uname,
                "sent":False,
                "remind_at": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            db_set("pending_feedback", pf)
            await cb.message.edit_text(cb.message.text + "\n\n✅ Отмечено: проведена")
        else:
            tl = "💼 Платная"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Скопировать запись (постоянный)",
                                      callback_data=f"reg_copy_{ds}_{tm}")],
                [InlineKeyboardButton(text="➕ Новая запись (постоянный)",
                                      callback_data=f"reg_new_{ds}_{tm}")],
            ])
            await cb.message.edit_text(
                f"✅ Платная сессия записана в статистику.\n\n"
                f"📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n"
                f"👤 {name}\n🆔 @{uname}", reply_markup=kb)
    else:
        if rec: rec["status"] = "не состоялась"
        db_set("appts", appts)
        sl = "Бесплатная" if stype == "free" else "Платная"
        await cb.message.edit_text(cb.message.text + f"\n\n❌ {sl} не состоялась.")
 
@dp.callback_query(F.data.startswith("send_fb_"))
async def send_fb(cb: types.CallbackQuery):
    key = cb.data[8:]
    set_st(cb.from_user.id, {"step":"adm_fb_text","fb_key":key})
    await cb.answer()
    await cb.message.answer(
        "Введите текст обратной связи и план работы.\n"
        "Он уйдёт клиенту вместе с предложением продолжить работу:")
 
@dp.callback_query(F.data.startswith("reg_copy_"))
async def reg_copy(cb: types.CallbackQuery):
    _, _, ds, tm = cb.data.split("_", 3)
    appts = db_get("appts", {})
    rec   = next((r for r in appts.get(ds,[]) if r["time"] == tm), None)
    if not rec: await cb.answer("Запись не найдена", show_alert=True); return
    regs = db_get("regulars", [])
    regs.append({"username":rec.get("username",""),"name":rec.get("name",""),
                 "day":"","time":tm,"source":"авто"})
    db_set("regulars", regs)
    await cb.answer("✅ Добавлен в постоянные клиенты")
 
@dp.callback_query(F.data.startswith("reg_new_"))
async def reg_new(cb: types.CallbackQuery):
    _, _, ds, tm = cb.data.split("_", 3)
    appts = db_get("appts", {})
    rec   = next((r for r in appts.get(ds,[]) if r["time"] == tm), None)
    tg    = rec.get("username","") if rec else ""
    name  = rec.get("name","") if rec else ""
    set_st(cb.from_user.id, {"step":"adm_book_date","manual_tg":tg,"manual_name":name})
    today = date.today()
    await cb.message.answer(f"Записываю @{tg}. Выберите дату следующей сессии:",
                             reply_markup=cal_admin(today.year, today.month))
 
# ── АДМИН КАЛЕНДАРЬ ─────────────────────────────────────────────────────
 
@dp.callback_query(F.data == "adm_cal")
async def adm_cal(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer()
    today = date.today()
    await cb.message.answer(
        "📅 *Управление днями*\n\n"
        "✅ свободный  🔵 записи  🟡 неподтверждённые  ❌ закрыт  · прошедший",
        parse_mode="Markdown", reply_markup=cal_admin(today.year, today.month))
 
@dp.callback_query(F.data.startswith("acal_"))
async def acal_nav(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    _, y, m = cb.data.split("_")
    await cb.message.edit_reply_markup(reply_markup=cal_admin(int(y), int(m)))
 
@dp.callback_query(F.data.startswith("aday_"))
async def aday_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds  = cb.data[5:]
    uid = cb.from_user.id
    st  = get_st(uid)
    step = st.get("step","")
 
    if step == "adm_open_day_pick":
        slots = db_get("slots",{}); slots[ds] = ALL_SLOTS.copy(); db_set("slots",slots)
        bd    = db_get("blocked_dates",[])
        if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
        clr_st(uid); await cb.answer(f"✅ День {ds} открыт")
        await cb.message.answer(
            f"✅ День *{ds}* открыт — {len(ALL_SLOTS)} слотов\n🟢 свободно",
            parse_mode="Markdown", reply_markup=slots_day_admin(ds))
        return
 
    if step == "adm_week_pick":
        start = datetime.strptime(ds,"%Y-%m-%d").date()
        slots = db_get("slots",{})
        bd    = db_get("blocked_dates",[])
        for i in range(7):
            d2  = start + timedelta(days=i)
            ds2 = d2.strftime("%Y-%m-%d")
            slots[ds2] = ALL_SLOTS.copy()
            if ds2 in bd: bd.remove(ds2)
        db_set("slots",slots); db_set("blocked_dates",bd); clr_st(uid)
        end_s = (start + timedelta(days=6)).strftime("%d.%m")
        await cb.answer("✅ Неделя открыта")
        today = date.today()
        await cb.message.answer(
            f"✅ Неделя с *{ds}* по *{end_s}* открыта.",
            parse_mode="Markdown",
            reply_markup=cal_admin(start.year, start.month))
        return
 
    if step == "adm_block_week_pick":
        start = datetime.strptime(ds,"%Y-%m-%d").date()
        appts = db_get("appts",{})
        conflicts = [
            (start+timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
            if appts.get((start+timedelta(days=i)).strftime("%Y-%m-%d"))
        ]
        if conflicts:
            set_st(uid,{"step":"adm_block_week_confirm","block_week_start":ds})
            ct = "\n".join(f"  {d}: {len(appts[d])} записей" for d in conflicts)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Заблокировать несмотря на записи",
                                      callback_data="adm_bw_yes")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
            ])
            await cb.answer()
            await cb.message.answer(
                f"⚠️ В этой неделе есть записи:\n{ct}\n\nВсё равно заблокировать?",
                reply_markup=kb)
        else:
            bd    = db_get("blocked_dates",[])
            for i in range(7):
                ds2 = (start+timedelta(days=i)).strftime("%Y-%m-%d")
                if ds2 not in bd: bd.append(ds2)
            db_set("blocked_dates",bd); clr_st(uid)
            end_s = (start+timedelta(days=6)).strftime("%d.%m")
            await cb.answer("❌ Неделя заблокирована")
            await cb.message.answer(
                f"❌ Неделя с *{ds}* по *{end_s}* заблокирована.",
                parse_mode="Markdown",
                reply_markup=cal_admin(start.year, start.month))
        return
 
    if step == "adm_move_new_date":
        st["move_new_ds"] = ds; st["step"] = "adm_move_new_time"; set_st(uid,st)
        await cb.answer()
        await cb.message.answer(f"Новая дата: *{ds}*\nВведите новое время (`14:00`):",
                                 parse_mode="Markdown")
        return
 
    if step in ("adm_book_date","adm_reg_from_paid"):
        st["book_ds"] = ds; st["step"] = "adm_book_slot_pick"; set_st(uid,st)
        await cb.answer()
        await cb.message.delete()
        await cb.message.answer(f"📅 *{ds}*\nВыберите слот для записи:",
                                 parse_mode="Markdown", reply_markup=slots_day_admin(ds))
        return
 
    today   = date.today()
    is_past = datetime.strptime(ds,"%Y-%m-%d").date() < today
    bd      = db_get("blocked_dates",[])
 
    if is_past:
        # Показываем слоты прошедшего дня + кнопку добавить сессию
        await cb.message.delete()
        await cb.message.answer(
            f"📅 *{ds}* (прошедший день)\n🔵 запись  🟡 неподтверждённая",
            parse_mode="Markdown", reply_markup=slots_day_admin(ds))
        return
 
    # Заблокированный день — показываем слоты как 🔴
    if ds in bd:
        await cb.message.delete()
        await cb.message.answer(
            f"📅 *{ds}* — день закрыт\n🔴 закрыто  🟡 неподтверждённая запись  🔵 запись",
            parse_mode="Markdown", reply_markup=slots_day_admin(ds))
        return
 
    # Пустой день (нет слотов)
    slots = db_get("slots",{})
    if not slots.get(ds):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Открыть день",
                                  callback_data=f"adm_do_open_{ds}")],
            [InlineKeyboardButton(text="✏️ Записать",
                                  callback_data=f"adm_book_slot_{ds}")],
            [InlineKeyboardButton(text="❌ Закрыть",
                                  callback_data=f"adm_do_close_day_{ds}")],
            [InlineKeyboardButton(text="↩️ Назад к календарю", callback_data="adm_cal")],
        ])
        await cb.answer()
        await cb.message.answer(f"📅 *{ds}* - день пустой", parse_mode="Markdown",
                                 reply_markup=kb)
        return
 
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{ds}*\n🟢 свободно  🔵 запись  🟡 неподтверждённая",
        parse_mode="Markdown", reply_markup=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_do_open_"))
async def adm_do_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds    = cb.data[12:]
    slots = db_get("slots",{}); slots[ds] = ALL_SLOTS.copy(); db_set("slots",slots)
    bd    = db_get("blocked_dates",[])
    if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
    await cb.answer(f"✅ День {ds} открыт")
    await cb.message.delete()
    await cb.message.answer(
        f"✅ День *{ds}* открыт — {len(ALL_SLOTS)} слотов\n🟢 свободно",
        parse_mode="Markdown", reply_markup=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_do_close_day_"))
async def adm_do_close_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds    = cb.data[17:]
    bd    = db_get("blocked_dates",[])
    if ds not in bd: bd.append(ds); db_set("blocked_dates",bd)
    slots = db_get("slots",{})
    if ds in slots: del slots[ds]; db_set("slots",slots)
    await cb.answer(f"❌ День {ds} закрыт")
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{ds}* — день закрыт\n🔴 все слоты заблокированы",
        parse_mode="Markdown", reply_markup=slots_day_admin(ds))
 
 
@dp.callback_query(F.data.startswith("aslot_blocked_"))
async def aslot_blocked_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[2]; tm = parts[3]
    uid   = cb.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Открыть слот",
                              callback_data=f"adm_unblock_slot_{ds}_{tm}")],
        [InlineKeyboardButton(text="✏️ Записать клиента",
                              callback_data=f"adm_book_blocked_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data=f"aday_{ds}")],
    ])
    await cb.answer()
    await cb.message.answer(f"🔴 Слот {ds} в {tm} — закрыт. Что сделать?",
                             reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_book_blocked_"))
async def adm_book_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[3]; tm = parts[4]
    uid   = cb.from_user.id
    set_st(uid, {"step":"adm_manual_tg","book_ds":ds,"book_tm":tm})
    await cb.answer()
    await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_unblock_slot_"))
async def adm_unblock_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[3]; tm = parts[4]
    slots        = db_get("slots",{})
    closed_slots = db_get("closed_slots",{})
    if ds not in slots: slots[ds] = []
    if tm not in slots[ds]:
        slots[ds].append(tm); slots[ds] = sorted(slots[ds])
    if ds in closed_slots and tm in closed_slots[ds]:
        closed_slots[ds].remove(tm)
    db_set("slots",slots); db_set("closed_slots",closed_slots)
    await cb.answer(f"🟢 Слот {tm} открыт")
    await cb.message.delete()
    await cb.message.answer(
        f"📅 *{ds}*\n🔴 закрыто  🟢 открыто",
        parse_mode="Markdown", reply_markup=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_unblock_day_"))
async def adm_unblock_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds    = cb.data[16:]
    bd    = db_get("blocked_dates",[])
    slots = db_get("slots",{})
    if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
    slots[ds] = ALL_SLOTS.copy(); db_set("slots",slots)
    await cb.answer(f"✅ День {ds} полностью открыт")
    await cb.message.delete()
    await cb.message.answer(
        f"✅ День *{ds}* открыт — {len(ALL_SLOTS)} слотов\n🟢 свободно",
        parse_mode="Markdown", reply_markup=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("aslot_"))
async def aslot_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[1]; tm = parts[2]
    uid   = cb.from_user.id; st = get_st(uid)
    appts = db_get("appts",{}); slots = db_get("slots",{})
 
    if st.get("step") == "adm_book_slot_pick":
        st["book_tm"] = tm; st["step"] = "adm_manual_plat"; set_st(uid,st)
        await cb.answer()
        tg = st.get("manual_tg","")
        await cb.message.answer(
            f"✅ @{tg} - *{ds}* в *{tm}*\n\nПлатформа для связи?",
            parse_mode="Markdown", reply_markup=kb_platform("adm_back"))
        return
 
    rec = next((r for r in appts.get(ds,[]) if r["time"] == tm), None)
    if rec:
        tl   = "💼 Платная" if rec.get("type") == "paid" else "🆓 Бесплатная"
        conf = "✅ подтверждена" if rec.get("confirmed") else "🟡 не подтверждена"
        await cb.answer(f"{rec['name']} | {tl} | {rec.get('duration','—')} | {conf}",
                        show_alert=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить",
                                  callback_data=f"adm_ok_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ Отменить запись",
                                  callback_data=f"adm_cncl_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="🔄 Перенести",
                                  callback_data=f"adm_mv_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="📝 Обратная связь",
                                  callback_data=f"send_fb_{ds}_{tm}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=f"aday_{ds}")],
        ])
        await cb.message.answer(
            f"🔵 *{ds}* в *{tm}*\n\n"
            f"👤 {rec['name']} @{rec.get('username','')}\n"
            f"{tl} | ⏱ {rec.get('duration','—')}\n"
            f"📱 {rec.get('platform','—')}\nСтатус: {conf}",
            parse_mode="Markdown", reply_markup=kb)
    else:
        in_slots = tm in slots.get(ds,[])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔴 Закрыть слот" if in_slots else "🟢 Открыть слот",
                callback_data=f"adm_toggle_slot_{ds}_{tm}")],
            [InlineKeyboardButton(text="✏️ Записать клиента",
                                  callback_data=f"adm_book_to_{ds}_{tm}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=f"aday_{ds}")],
        ])
        await cb.answer()
        status = "🟢 Свободен" if in_slots else "🔴 Закрыт"
        await cb.message.answer(f"{status} - {ds} в {tm}", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_toggle_slot_"))
async def adm_toggle_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[3]; tm = parts[4]
    slots        = db_get("slots",{})
    closed_slots = db_get("closed_slots",{})
    if ds not in slots: slots[ds] = []
    if ds not in closed_slots: closed_slots[ds] = []
    if tm in slots[ds]:
        # Закрываем: убираем из открытых, добавляем в закрытые
        slots[ds].remove(tm)
        if tm not in closed_slots[ds]: closed_slots[ds].append(tm)
        await cb.answer(f"🔴 Слот {tm} закрыт")
    else:
        # Открываем: добавляем в открытые, убираем из закрытых
        slots[ds].append(tm); slots[ds] = sorted(slots[ds])
        if tm in closed_slots[ds]: closed_slots[ds].remove(tm)
        await cb.answer(f"🟢 Слот {tm} открыт")
    db_set("slots",slots); db_set("closed_slots",closed_slots)
    await cb.message.delete()
    await cb.message.answer(f"📅 *{ds}*", parse_mode="Markdown",
                             reply_markup=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_book_to_"))
async def adm_book_to(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[3]; tm = parts[4]
    uid   = cb.from_user.id; st = get_st(uid)
    if st.get("manual_tg"):
        st["book_ds"] = ds; st["book_tm"] = tm; st["step"] = "adm_manual_plat"
        set_st(uid,st); await cb.answer()
        await cb.message.answer(
            f"✅ @{st['manual_tg']} - *{ds}* в *{tm}*\n\nПлатформа?",
            parse_mode="Markdown", reply_markup=kb_platform("adm_back"))
    else:
        set_st(uid,{"step":"adm_manual_tg","book_ds":ds,"book_tm":tm})
        await cb.answer()
        await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_add_slots_"))
async def adm_add_slots(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds = cb.data[14:]
    set_st(cb.from_user.id, {"step":"adm_add_slots_to","adm_date":ds})
    await cb.answer()
    await cb.message.answer(f"Слоты для *{ds}* через запятую:\n`10:00, 11:00`",
                             parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("adm_book_slot_"))
async def adm_book_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds  = cb.data[14:]
    uid = cb.from_user.id; st = get_st(uid)
    if st.get("manual_tg"):
        st["book_ds"] = ds; st["step"] = "adm_book_slot_pick"; set_st(uid,st)
        await cb.answer()
        await cb.message.delete()
        await cb.message.answer(f"📅 *{ds}*\nВыберите слот:",
                                 parse_mode="Markdown", reply_markup=slots_day_admin(ds))
    else:
        set_st(uid,{"step":"adm_manual_tg","book_ds":ds})
        await cb.answer()
        await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_add_session_"))
async def adm_add_session(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds = cb.data[16:]
    set_st(cb.from_user.id, {"step":"adm_session_name","session_ds":ds})
    await cb.answer()
    await cb.message.answer(f"Добавляю сессию за *{ds}*.\nВведите имя клиента:",
                             parse_mode="Markdown")
 
# ── АДМИН МЕНЮ ЗАПИСИ ───────────────────────────────────────────────────
 
@dp.callback_query(F.data == "adm_book_menu")
async def adm_book_menu(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Записать нового - бесплатная",
                              callback_data="adm_book_new_free")],
        [InlineKeyboardButton(text="✏️ Записать нового - платная",
                              callback_data="adm_book_new_paid")],
        [InlineKeyboardButton(text="✏️ Записать постоянного",
                              callback_data="adm_book_reg")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_cal")],
    ])
    await cb.answer()
    await cb.message.answer("Выберите тип записи:", reply_markup=kb)
 
@dp.callback_query(F.data == "adm_book_new_free")
async def adm_book_new_free(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_manual_tg","forced_type":"free"})
    await cb.answer()
    await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data == "adm_book_new_paid")
async def adm_book_new_paid(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_manual_tg","forced_type":"paid"})
    await cb.answer()
    await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.in_({"adm_open_week","adm_open_week_cal"}))
async def adm_open_week_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_week_pick"})
    today = date.today()
    await cb.answer()
    await cb.message.answer(
        "Нажмите на любой день - с него откроется неделя (7 дней вперёд):",
        reply_markup=cal_admin(today.year, today.month))
 
@dp.callback_query(F.data.in_({"adm_block_week","adm_block_week_cal"}))
async def adm_block_week_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_block_week_pick"})
    today = date.today()
    await cb.answer()
    await cb.message.answer(
        "Нажмите на любой день - с него заблокируется неделя (7 дней вперёд):",
        reply_markup=cal_admin(today.year, today.month))
 
@dp.callback_query(F.data == "adm_bw_yes")
async def adm_bw_yes(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uid = cb.from_user.id; st = get_st(uid); ds = st.get("block_week_start","")
    if not ds: return
    start = datetime.strptime(ds,"%Y-%m-%d").date()
    bd    = db_get("blocked_dates",[])
    for i in range(7):
        ds2 = (start+timedelta(days=i)).strftime("%Y-%m-%d")
        if ds2 not in bd: bd.append(ds2)
    db_set("blocked_dates",bd); clr_st(uid)
    end_s = (start+timedelta(days=6)).strftime("%d.%m")
    await cb.message.answer(
        f"❌ Неделя с *{ds}* по *{end_s}* заблокирована (записи сохранены).",
        parse_mode="Markdown",
        reply_markup=cal_admin(start.year, start.month))
 
@dp.callback_query(F.data == "adm_book_reg")
async def adm_book_reg(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    regs = db_get("regulars",[])
    if not regs: await cb.answer("Нет постоянных клиентов", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"@{r['username']} - {r['name']}",
                              callback_data=f"adm_reg_pick_{r['username']}")]
        for r in regs
    ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="adm_cal")]])
    await cb.answer()
    await cb.message.answer("Выберите постоянного клиента:", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("adm_reg_pick_"))
async def adm_reg_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uname = cb.data[13:]
    regs  = db_get("regulars",[])
    rec   = next((r for r in regs if r["username"] == uname), None)
    if not rec: await cb.answer("Не найден", show_alert=True); return
    set_st(cb.from_user.id, {"step":"adm_book_date","manual_tg":uname,
                              "manual_name":rec.get("name","")})
    today = date.today()
    await cb.answer()
    await cb.message.answer(f"Записываю @{uname}. Выберите дату:",
                             reply_markup=cal_admin(today.year, today.month))
 
# ── ОСТАЛЬНЫЕ КНОПКИ АДМИНКИ ─────────────────────────────────────────────
 
@dp.callback_query(F.data == "adm_back")
async def adm_back(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("Панель:", reply_markup=kb_admin())
 
@dp.callback_query(F.data == "adm_unconf")
async def adm_unconf(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appts",{}); today = date.today(); rows = []
    for ds in sorted(appts.keys()):
        try: d = datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d < today: continue
        for r in appts[ds]:
            if not r.get("confirmed"):
                tl = "💼" if r.get("type") == "paid" else "🆓"
                rows.append([InlineKeyboardButton(
                    text=f"🟡 {ds} {r['time']} {tl} - {r['name']}",
                    callback_data=f"aslot_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    if len(rows) == 1:
        await cb.message.answer("Неподтверждённых нет.", reply_markup=kb_admin()); return
    await cb.message.answer("🟡 *Неподтверждённые:*", parse_mode="Markdown",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data == "adm_past_free")
async def adm_past_free(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appts",{}); today = date.today()
    week_ago = today - timedelta(days=7); rows = []
    for ds in sorted(appts.keys(), reverse=True):
        try: d = datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d > today or d < week_ago: continue
        for r in appts[ds]:
            if r.get("type") != "free": continue
            st = r.get("status","")
            ic = "✅" if st == "проведена" else ("❌" if st == "не состоялась" else "⏳")
            rows.append([InlineKeyboardButton(
                text=f"{ic} {ds} {r['time']} - {r['name']}",
                callback_data=f"aslot_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    if len(rows) == 1:
        await cb.message.answer("Прошедших бесплатных за неделю нет.", reply_markup=kb_admin())
        return
    await cb.message.answer("📋 *Прошедшие бесплатные (7 дней):*", parse_mode="Markdown",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data == "adm_list")
async def adm_list(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appts",{}); today = date.today()
    text  = "📋 *Предстоящие записи:*\n\n"; found = False
    for ds in sorted(appts.keys()):
        try: d = datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d < today: continue
        for r in appts[ds]:
            tl = "💼" if r.get("type") == "paid" else "🆓"
            co = "✅" if r.get("confirmed") else "🟡"
            text += (f"{co}{tl} *{ds}* {r['time']} ⏱{r.get('duration','—')}\n"
                     f"👤 {r['name']} @{r.get('username','')}\n"
                     f"📱 {r.get('platform','—')}\n\n")
            found = True
    await cb.message.answer(text if found else "📭 Записей нет.", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_table")
async def adm_table(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    slots = db_get("slots",{}); appts = db_get("appts",{})
    today = date.today()
    dates = sorted([ds for ds in slots if datetime.strptime(ds,"%Y-%m-%d").date() >= today])[:7]
    if not dates: await cb.message.answer("Слотов нет."); return
    text = "```\n"
    text += "Время |" + "|".join(d[5:] for d in dates) + "\n"
    text += "------|" + "------" * len(dates) + "\n"
    all_t = set()
    for ds in dates: all_t.update(slots.get(ds,[]))
    for t in sorted(all_t):
        row = f"{t} |"
        for ds in dates:
            taken = [r["time"] for r in appts.get(ds,[])]
            if t not in slots.get(ds,[]): row += "  -  |"
            elif t in taken: row += "  🔵 |"
            else: row += "  🟢 |"
        text += row + "\n"
    text += "```\n🟢 свободно  🔵 запись"
    await cb.message.answer(text, parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_regulars")
async def adm_regulars(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    regs = db_get("regulars",[])
    text = "👥 *Постоянные клиенты:*\n\n"
    text += "\n".join(f"@{r['username']} - {r['name']} | {r.get('day','')} {r.get('time','')}"
                       for r in regs) if regs else "Нет."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="adm_reg_add")],
        [InlineKeyboardButton(text="🗑 Удалить",  callback_data="adm_reg_del")],
        [InlineKeyboardButton(text="↩️ Назад",    callback_data="adm_back")],
    ])
    await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "adm_reg_add")
async def adm_reg_add(cb: types.CallbackQuery):
    set_st(cb.from_user.id, {"step":"adm_reg_username"})
    await cb.message.answer("Введите username клиента (без @):")
 
@dp.callback_query(F.data == "adm_reg_del")
async def adm_reg_del_btn(cb: types.CallbackQuery):
    set_st(cb.from_user.id, {"step":"adm_reg_del_name"})
    await cb.message.answer("Введите username для удаления (без @):")
 
@dp.callback_query(F.data.startswith("regday_"))
async def regday(cb: types.CallbackQuery):
    day = cb.data[7:]; uid = cb.from_user.id
    st  = get_st(uid); st["reg_day"] = day; st["step"] = "adm_reg_time"; set_st(uid,st)
    await cb.message.answer(f"День: *{day}*\nВведите время (`15:00`):", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_new_src")
async def adm_new_src(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"src_{code}")]
        for label, code in SOURCES
    ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")]])
    await cb.message.answer("Откуда клиент?", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("src_"))
async def src_sel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    src = cb.data[4:]
    set_st(cb.from_user.id, {"step":"adm_src_username","source":src})
    await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data == "adm_stats")
async def adm_stats(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts = db_get("appts",{}); logs = db_get("logs",[])
    now   = datetime.now(); total=free_c=paid_c=done=miss=0; srcs={}
    for ds, recs in appts.items():
        try: d = datetime.strptime(ds,"%Y-%m-%d")
        except: continue
        if d.month == now.month and d.year == now.year:
            for r in recs:
                total += 1
                if r.get("type") == "paid": paid_c += 1
                else: free_c += 1
                if r.get("status") == "проведена": done += 1
                if r.get("status") == "не состоялась": miss += 1
                src = r.get("source","бот"); srcs[src] = srcs.get(src,0) + 1
    guides = sum(1 for l in logs if l.get("a") == "got_guide")
    users  = len(db_get("users",[]))
    src_t  = "\n".join(f"  {k}: {v}" for k,v in srcs.items())
    await cb.message.answer(
        f"📊 *Статистика {now.strftime('%B %Y')}:*\n\n"
        f"📅 Всего: {total}\n🆓 Бесплатных: {free_c}\n💼 Платных: {paid_c}\n"
        f"✅ Проведено: {done}\n❌ Не состоялось: {miss}\n"
        f"📄 Гайдов: {guides}\n👥 Пользователей: {users}\n\n"
        f"*Источники:*\n{src_t or '  нет данных'}",
        parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_broadcast_text"})
    await cb.message.answer("Введите текст рассылки:")
 
@dp.callback_query(F.data == "adm_post")
async def adm_post(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_post_link"})
    await cb.message.answer("Вставьте ссылку на пост из канала:")
 
@dp.callback_query(F.data == "adm_excel")
async def adm_excel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id, {"step":"adm_excel_from"})
    await cb.message.answer("Дата *начала* периода *ГГГГ-ММ-ДД*:", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_reviews")
async def adm_reviews(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    reviews = db_get("reviews",[])
    if not reviews: await cb.message.answer("Отзывов пока нет."); return
    text = "⭐️ *Отзывы:*\n\n"
    for r in reviews[-10:]:
        text += f"👤 {r.get('name','—')} | {'⭐️'*r.get('stars',5)}\n{r.get('text','')}\n\n"
    await cb.message.answer(text, parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_blocked")
async def adm_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    bl = db_get("blocked",[])
    if not bl: await cb.message.answer("Заблокированных нет."); return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔓 Разблокировать", callback_data="adm_unblock_ask")
    ]])
    await cb.message.answer("🚫 *Заблокированные:*\n\n" + "\n".join(str(u) for u in bl),
                             parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data == "adm_unblock_ask")
async def adm_unblock_ask(cb: types.CallbackQuery):
    set_st(cb.from_user.id, {"step":"adm_unblock"})
    await cb.message.answer("Введите ID для разблокировки:")
 
@dp.callback_query(F.data == "adm_logs")
async def adm_logs(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    logs = db_get("logs",[]); text = "📊 *Последние 20 действий:*\n\n"
    for e in logs[-20:]:
        text += f"🕐 {e['t']} @{e['u']}\n▶️ {e['a']}\n\n"
    await cb.message.answer(text if logs else "Логов нет.", parse_mode="Markdown")
 
@dp.callback_query(F.data == "adm_block_month")
async def adm_block_month_btn(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    now = date.today()
    months_kb = []
    for y in [now.year, now.year+1]:
        for m in range(1,13):
            if date(y,m,1) < now.replace(day=1): continue
            months_kb.append([InlineKeyboardButton(
                text=f"{MN[m-1]} {y}", callback_data=f"adm_bm_{y}_{m:02d}")])
    months_kb.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    await cb.message.answer("Выберите месяц для блокировки:",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=months_kb))
 
@dp.callback_query(F.data.startswith("adm_bm_"))
async def adm_bm_sel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    _, _, y, m = cb.data.split("_"); y = int(y); m = int(m)
    ms    = f"{y}-{m:02d}"
    dn    = calendar.monthrange(y,m)[1]
    appts = db_get("appts",{})
    conf  = [f"{y}-{m:02d}-{d:02d}" for d in range(1,dn+1)
             if appts.get(f"{y}-{m:02d}-{d:02d}")]
    if conf:
        set_st(cb.from_user.id, {"step":"adm_bm_confirm","block_month":ms})
        ct = "\n".join(f"  {ds}: {len(appts[ds])} записей" for ds in conf)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заблокировать несмотря на записи",
                                  callback_data="adm_bm_yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
        ])
        await cb.message.answer(f"⚠️ В {ms} есть записи:\n{ct}\n\nВсё равно?",
                                 reply_markup=kb)
    else:
        bd = db_get("blocked_dates",[])
        for d in range(1,dn+1):
            ds = f"{y}-{m:02d}-{d:02d}"
            if ds not in bd: bd.append(ds)
        db_set("blocked_dates",bd); await cb.answer(f"🚫 {ms} заблокирован")
        await cb.message.answer(f"🚫 Месяц *{ms}* заблокирован.", parse_mode="Markdown",
                                 reply_markup=kb_admin())
 
@dp.callback_query(F.data == "adm_bm_yes")
async def adm_bm_yes(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uid = cb.from_user.id; st = get_st(uid); ms = st.get("block_month","")
    if not ms: return
    y,m = int(ms.split("-")[0]), int(ms.split("-")[1])
    dn  = calendar.monthrange(y,m)[1]
    bd  = db_get("blocked_dates",[])
    for d in range(1,dn+1):
        ds = f"{y}-{m:02d}-{d:02d}"
        if ds not in bd: bd.append(ds)
    db_set("blocked_dates",bd); clr_st(uid)
    await cb.message.answer(f"🚫 Месяц *{ms}* заблокирован (записи сохранены).",
                             parse_mode="Markdown", reply_markup=kb_admin())
 
@dp.callback_query(F.data.startswith("adm_mtype_"))
async def adm_mtype(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ctype = "paid" if "paid" in cb.data else "free"
    uid   = cb.from_user.id; st = get_st(uid)
    ds    = st.get("book_ds","?"); tm = st.get("book_tm","?")
    name  = st.get("manual_name","?"); tg = st.get("manual_tg","?")
    plat  = st.get("platform","?")
    forced = st.get("forced_type")
    if forced: ctype = forced
    tl    = "💼 Платная" if ctype == "paid" else "🆓 Бесплатная"
    appts = db_get("appts",{})
    if ds not in appts: appts[ds] = []
    appts[ds].append({
        "user_id":0,"name":name,"time":tm,"username":tg,
        "type":ctype,"platform":plat,"duration":"—","desc":"Ручная запись",
        "source":"вручную","status":"","confirmed":True,
        "rem_client":True,"rem_admin":False,"session_asked":False,
        "cli_confirmed":True,"followup1":True,"followup3":True
    })
    db_set("appts",appts); clr_st(uid)
    await cb.message.answer(
        f"✅ Записан вручную!\n\n📅 {ds} в {tm}\n{tl}\n👤 {name} @{tg}\n📱 {plat}",
        reply_markup=kb_admin())
    await notify_adm(f"✏️ *Ручная запись*\n📅 {ds} в {tm}\n{tl}\n👤 {name} @{tg}")
 
@dp.callback_query(F.data.startswith("ban_"))
async def ban_cb(cb: types.CallbackQuery):
    uid = int(cb.data[4:]); bl = db_get("blocked",[])
    if uid not in bl: bl.append(uid); db_set("blocked",bl)
    await cb.message.edit_text(cb.message.text + "\n\n🚫 *Заблокирован*", parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("skip_"))
async def skip_cb(cb: types.CallbackQuery):
    await cb.message.edit_text(cb.message.text + "\n\n✅ *Оставлено*", parse_mode="Markdown")
 
@dp.callback_query(F.data.startswith("stype_"))
async def stype_cb(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); uid = cb.from_user.id; st = get_st(uid)
    ds    = st.get("session_ds","?"); name = st.get("session_name","?")
    stype = "_".join(parts[1:])
    type_map = {
        "free_first":   ("🆓 Бесплатная первичная","free"),
        "paid_first":   ("💼 Платная первичная","paid"),
        "paid_repeat":  ("💼 Платная повторная","paid"),
    }
    label, ctype = type_map.get(stype, (stype,"paid"))
    appts = db_get("appts",{})
    if ds not in appts: appts[ds] = []
    appts[ds].append({
        "user_id":0,"name":name,"time":"00:00","username":"—",
        "type":ctype,"platform":"—","duration":"—","desc":"Ручная сессия",
        "source":"вручную","status":"проведена","confirmed":True,
        "rem_client":True,"rem_admin":True,"session_asked":True,
        "cli_confirmed":True,"followup1":True,"followup3":True
    })
    db_set("appts",appts); clr_st(uid)
    await cb.message.answer(f"✅ Сессия добавлена.\n{ds} | {label} | {name}",
                             reply_markup=kb_admin())
 
# ── ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТА ───────────────────────────────────────────
 
 
@dp.callback_query(F.data.startswith("pay_rf_"))
async def pay_rf(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid_c = parts[2]; ds = parts[3]; tm = parts[4]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатил",
                              callback_data=f"paid_confirm_{uid_c}_{ds}_{tm}_rf")],
    ])
    await cb.answer()
    await cb.message.answer(RF_CARD, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("pay_foreign_"))
async def pay_foreign(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid_c = parts[2]; ds = parts[3]; tm = parts[4]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатил",
                              callback_data=f"paid_confirm_{uid_c}_{ds}_{tm}_foreign")],
    ])
    await cb.answer()
    await cb.message.answer(FOREIGN_CARD, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("paid_confirm_"))
async def paid_confirm(cb: types.CallbackQuery):
    parts  = cb.data.split("_")
    uid_c  = parts[2]; ds = parts[3]; tm = parts[4]; method = parts[5]
    method_label = "💳 Карта РФ/СБП" if method == "rf" else "💳 Зарубежная карта"
    await cb.answer("✅ Спасибо! Ожидайте подтверждения.", show_alert=False)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "✅ Спасибо! Сообщение об оплате отправлено.\n"
        "Евгений подтвердит получение.")
    appts = db_get("appts", {})
    name = "—"; uname = "—"; dur = "—"
    for r in appts.get(ds, []):
        if r["time"] == tm:
            r["payment_reported"] = True
            r["payment_method"]   = method_label
            name  = r.get("name","—")
            uname = r.get("username","—")
            dur   = r.get("duration","—")
    db_set("appts", appts)
    price = PRICES.get(dur, 5000)
    await notify_adm(
        f"💰 *Клиент сообщил об оплате!*\n\n"
        f"📅 {ds} в {tm} МСК\n"
        f"👤 {name} @{uname}\n"
        f"💳 {method_label}\n"
        f"💵 {price:,} руб. | ⏱ {dur}")
 
 
@dp.callback_query(F.data.startswith("pay_ru_"))
async def pay_ru(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Оплатил",
                             callback_data=f"paid_confirm_{uid}_{ds}_{tm}")
    ]])
    await cb.answer()
    await cb.message.answer(PAYMENT_CARD_RU, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("pay_intl_"))
async def pay_intl(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Оплатил",
                             callback_data=f"paid_confirm_{uid}_{ds}_{tm}")
    ]])
    await cb.answer()
    await cb.message.answer(PAYMENT_CARD_INTL, parse_mode="Markdown", reply_markup=kb)
 
@dp.callback_query(F.data.startswith("paid_confirm_"))
async def paid_confirm(cb: types.CallbackQuery):
    parts = cb.data.split("_"); uid = int(parts[2]); ds = parts[3]; tm = parts[4]
    # Отмечаем оплату в записи
    appts = db_get("appts", {})
    for r in appts.get(ds, []):
        if r["user_id"] == uid and r["time"] == tm:
            r["paid"] = True
    db_set("appts", appts)
    await cb.answer("✅ Спасибо! Информация об оплате отправлена.")
    await cb.message.edit_text(cb.message.text + "\n\n✅ *Оплата подтверждена клиентом*",
                               parse_mode="Markdown")
    # Уведомляем Евгения
    await notify_adm(
        f"💰 *Клиент сообщил об оплате!*\n\n"
        f"📅 {ds} в {tm} МСК\n"
        f"🆔 ID: {uid}\n\n"
        f"Проверьте поступление средств.")
 
 
@dp.callback_query(F.data.startswith("adm_book_blocked_"))
async def adm_book_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts = cb.data.split("_"); ds = parts[3]; tm = parts[4]
    uid   = cb.from_user.id
    st    = get_st(uid)
    # Если уже есть username — сразу к платформе
    if st.get("manual_tg"):
        st["book_ds"] = ds; st["book_tm"] = tm; st["step"] = "adm_manual_plat"
        set_st(uid, st)
        await cb.answer()
        await cb.message.answer(
            f"✅ @{st['manual_tg']} - *{ds}* в *{tm}*\n\nПлатформа для связи?",
            parse_mode="Markdown", reply_markup=kb_platform("adm_back"))
    else:
        set_st(uid, {"step":"adm_manual_tg","book_ds":ds,"book_tm":tm})
        await cb.answer()
        await cb.message.answer("Введите username клиента в Telegram (без @):")
 
@dp.message()
async def handle_text(msg: types.Message):
    uid  = msg.from_user.id
    text = msg.text.strip() if msg.text else ""
    if is_blocked(uid): return
    if is_flood(uid): return
    reg_user(uid)
 
    # Команды сбрасывают состояние
    if text.startswith("/"):
        clr_st(uid)
        await msg.answer("Главное меню:", reply_markup=kb_main())
        return
 
    if is_admin(msg.from_user.username):
        chats = db_get("admin_chats",[])
        if uid not in chats: chats.append(uid); db_set("admin_chats",chats)
 
    if has_bad(text):
        cnt = viol(uid,"bad")
        await msg.answer("Пожалуйста, давайте общаться без грубостей 🙏")
        if cnt >= 5:
            await _auto_block(uid, f"мат ({cnt}x)"); return
        bk = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать",callback_data=f"ban_{uid}")],
            [InlineKeyboardButton(text="✅ Оставить",     callback_data=f"skip_{uid}")],
        ])
        await notify_adm(f"⚠️ *Мат* ({cnt}/5)\n@{msg.from_user.username or '?'}(ID:{uid})\n{text[:200]}",
                         kb=bk)
        return
 
    st   = get_st(uid)
    step = st.get("step","")
 
    # Описание клиента
    if step in ("desc","desc_retry"):
        name = msg.from_user.first_name or "Клиент"
        if len(text) < 35:
            st["desc"] = text; set_st(uid,st)
            bk = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Дополнить",          callback_data="desc_extend")],
                [InlineKeyboardButton(text="✅ Оставить как есть",   callback_data="desc_keep")],
            ])
            await msg.answer(
                "Вижу, вы написали довольно мало. Либо не хотите писать и это ок, "
                "либо случайно отправили - тогда можете дописать.",
                reply_markup=bk)
            return
        st["name"] = name; st["desc"] = text; st["step"] = "platform"
        set_st(uid,st)
        await msg.answer("Через какую платформу удобнее созвониться?",
                         reply_markup=kb_platform())
        return
 
    # Обратная связь клиенту
    if step == "adm_fb_text":
        key     = st.get("fb_key","")
        pf      = db_get("pending_feedback",{})
        item    = pf.get(key,{})
        cli_uid = item.get("uid",0)
        if cli_uid:
            try:
                cname = item.get("name","")
                await bot.send_message(cli_uid,
                    f"Здравствуйте, {cname}!\n\n"
                    "Как вы после нашей встречи? Надеюсь, стало немного яснее.\n\n"
                    f"Как обещал - обратная связь и план работы.\n\n{text}")
                await asyncio.sleep(0.5)
                await bot.send_message(cli_uid,
                    "Если захотите продолжить работу - я здесь. Вот условия:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="💼 Условия платных консультаций",
                                             callback_data="paid_info")
                    ]]))
                await asyncio.sleep(0.5)
                await bot.send_message(cli_uid, T_FEEDBACK)
                item["sent"] = True; pf[key] = item; db_set("pending_feedback",pf)
                await msg.answer("✅ Отправлено клиенту.", reply_markup=kb_admin())
            except Exception as e:
                await msg.answer(f"❌ Ошибка: {e}")
        clr_st(uid); return
 
    # Ручная запись - username
    if step == "adm_manual_tg":
        tg = text.lstrip("@"); st["manual_tg"] = tg
        if st.get("book_ds") and st.get("book_tm"):
            st["step"] = "adm_manual_plat"; set_st(uid,st)
            await msg.answer("Платформа для связи?", reply_markup=kb_platform("adm_back"))
        else:
            st["step"] = "adm_book_date"; set_st(uid,st)
            today = date.today()
            await msg.answer(f"Записываю @{tg}. Выберите дату:",
                             reply_markup=cal_admin(today.year, today.month))
        return
 
    # Ручная запись - имя
    if step == "adm_manual_name":
        st["manual_name"] = text; st["step"] = "adm_manual_tg"; set_st(uid,st)
        await msg.answer("Введите username клиента в Telegram (без @):")
        return
 
    # Перенос записи - новое время
    if step == "adm_move_new_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text):
            await msg.answer("❌ Формат: `14:00`", parse_mode="Markdown"); return
        appts    = db_get("appts",{})
        old_ds   = st["move_ds"]; new_ds = st["move_new_ds"]
        old_tm   = st["move_tm"]; target = st["move_uid"]; moved = False
        for rec in appts.get(old_ds,[]):
            if rec["user_id"] == target and rec["time"] == old_tm:
                appts[old_ds].remove(rec)
                rec["time"] = text; rec["rem_client"] = False; rec["rem_admin"] = False
                if new_ds not in appts: appts[new_ds] = []
                appts[new_ds].append(rec); moved = True
                try:
                    await bot.send_message(target,
                        f"📅 Ваша консультация перенесена:\n*{new_ds}* в *{text}* МСК",
                        parse_mode="Markdown")
                except: pass
                break
        if moved: db_set("appts",appts)
        clr_st(uid)
        await msg.answer("✅ Перенесено." if moved else "❌ Не удалось.",
                         reply_markup=kb_admin())
        return
 
    # Добавить сессию - имя
    if step == "adm_session_name":
        st["session_name"] = text; st["step"] = "adm_session_type"; set_st(uid,st)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Бесплатная первичная",  callback_data="stype_free_first")],
            [InlineKeyboardButton(text="💼 Платная первичная",     callback_data="stype_paid_first")],
            [InlineKeyboardButton(text="💼 Платная повторная",     callback_data="stype_paid_repeat")],
        ])
        await msg.answer("Тип сессии?", reply_markup=kb)
        return
 
    # Добавить слоты к дате
    if step == "adm_add_slots_to":
        times_raw = [t.strip() for t in text.split(",")]
        valid = [t for t in times_raw if re.match(r"^([01]\d|2[0-3]):[0-5]\d$",t)]
        if not valid: await msg.answer("❌ Формат: `10:00, 11:00`",parse_mode="Markdown"); return
        ds    = st["adm_date"]; slots = db_get("slots",{})
        if ds not in slots: slots[ds] = []
        for t in valid:
            if t not in slots[ds]: slots[ds].append(t)
        slots[ds] = sorted(slots[ds]); db_set("slots",slots); clr_st(uid)
        await msg.answer(
            f"✅ Добавлено на *{ds}*: {', '.join(valid)}",
            parse_mode="Markdown", reply_markup=slots_day_admin(ds))
        return
 
    # Постоянный клиент - добавить
    if step == "adm_reg_username":
        st["reg_username"] = text.lstrip("@"); st["step"] = "adm_reg_name"; set_st(uid,st)
        await msg.answer("Введите имя клиента:"); return
 
    if step == "adm_reg_name":
        st["reg_name"] = text; st["step"] = "adm_reg_day"; set_st(uid,st)
        days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        kb   = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=d, callback_data=f"regday_{d}")] for d in days
        ])
        await msg.answer("День недели:", reply_markup=kb); return
 
    if step == "adm_reg_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$",text):
            await msg.answer("❌ Формат: `15:00`",parse_mode="Markdown"); return
        regs = db_get("regulars",[])
        regs.append({"username":st["reg_username"],"name":st["reg_name"],
                     "day":st["reg_day"],"time":text})
        db_set("regulars",regs); clr_st(uid)
        await msg.answer(f"✅ Добавлен @{st['reg_username']}.", reply_markup=kb_admin())
        return
 
    if step == "adm_reg_del_name":
        u = text.lstrip("@"); regs = db_get("regulars",[])
        db_set("regulars",[r for r in regs if r["username"].lower() != u.lower()])
        clr_st(uid); await msg.answer(f"✅ @{u} удалён.", reply_markup=kb_admin()); return
 
    # Новый клиент из соцсетей
    if step == "adm_src_username":
        u   = text.lstrip("@"); src = st.get("source","other")
        inv = db_get("invited",[])
        inv.append({"username":u,"source":src,"at":datetime.now().isoformat(),"status":"приглашён"})
        db_set("invited",inv); clr_st(uid)
        try: me = await bot.get_me(); link = f"https://t.me/{me.username}"
        except: link = "https://t.me/kasikov_bot"
        await msg.answer(f"✅ Клиент @{u} добавлен.\n\nОтправьте ему ссылку:\n{link}",
                         reply_markup=kb_admin())
        return
 
    # Разблокировать
    if step == "adm_unblock":
        try:
            target = int(text); bl = db_get("blocked",[])
            if target in bl:
                bl.remove(target); db_set("blocked",bl)
                await msg.answer(f"✅ {target} разблокирован.", reply_markup=kb_admin())
            else: await msg.answer("Не найден.", reply_markup=kb_admin())
        except: await msg.answer("❌ Введите числовой ID.")
        clr_st(uid); return
 
    # Рассылка
    if step == "adm_broadcast_text":
        users = db_get("users",[]); sent = 0
        for u in users:
            try: await bot.send_message(u,text); sent += 1; await asyncio.sleep(0.05)
            except: pass
        clr_st(uid)
        await msg.answer(f"✅ Разослано {sent} пользователям.", reply_markup=kb_admin())
        return
 
    # Пост из канала
    if step == "adm_post_link":
        users = db_get("users",[]); sent = 0
        for u in users:
            try:
                await bot.send_message(u,
                    f"На канале много полезного - вот свежий материал:\n{text}\n\n"
                    "Подписывайтесь если ещё нет 👉 @kasikov_psy")
                sent += 1; await asyncio.sleep(0.05)
            except: pass
        clr_st(uid)
        await msg.answer(f"✅ Пост разослан {sent} пользователям.", reply_markup=kb_admin())
        return
 
    # Excel
    if step == "adm_excel_from":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$",text):
            await msg.answer("❌ Формат: `2026-05-01`",parse_mode="Markdown"); return
        st["excel_from"] = text; st["step"] = "adm_excel_to"; set_st(uid,st)
        await msg.answer("Дата *конца* периода *ГГГГ-ММ-ДД*:", parse_mode="Markdown")
        return
 
    if step == "adm_excel_to":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$",text):
            await msg.answer("❌ Формат: `2026-05-31`",parse_mode="Markdown"); return
        d_from = st["excel_from"]; d_to = text; clr_st(uid)
        if not EXCEL_OK: await msg.answer("❌ openpyxl не установлен."); return
        buf = make_excel(d_from, d_to)
        if buf:
            await msg.answer_document(
                BufferedInputFile(buf.read(), filename=f"записи_{d_from}_{d_to}.xlsx"),
                caption=f"📊 Записи с {d_from} по {d_to}")
        else: await msg.answer("Записей за этот период нет.")
        return
 
    log_act(uid, msg.from_user.username, f"msg:{text[:30]}")
    await msg.answer("Выберите действие:", reply_markup=kb_main())
 
 
# ── ЗАПУСК ───────────────────────────────────────────────────────────────
 
async def main():
    log.info("=" * 50)
    log.info("БОТ КАСИКОВА v7.0 ЗАПУЩЕН")
    log.info("/admin - панель | /stop - остановить")
    log.info("=" * 50)
    asyncio.create_task(bg_loop())
    await dp.start_polling(bot)
 
if __name__ == "__main__":
    asyncio.run(main())

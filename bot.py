"""
Бот Евгения Касикова v9.0
edit везде где возможно
"""
import asyncio, os, shelve, calendar, re, logging, sys, io
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
 
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("bot.log", encoding="utf-8")])
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
DURATIONS = ["30 мин","1 час","1.5 часа","2 часа","2.5 часа","3 часа"]
BANKS     = ["Сбер","ВТБ","Альфа","Газпром","Озон"]
SOURCES   = [("📸 Instagram","ig"),("🎵 TikTok","tt"),
             ("▶️ YouTube","yt"),("💙 ВКонтакте","vk"),("🌐 Другой","other")]
PRICES = {
    "paid_first_30":3000,"30 мин":2500,"1 час":5000,
    "1.5 часа":7500,"2 часа":10000,"2.5 часа":12500,"3 часа":15000,
}
 
PAYMENT_CARD_RU = (
    "💳 *ОПЛАТА КАРТОЙ РФ / СБП*\n\n"
    "По номеру телефона СБП:\n`+7 965 763-48-79`\n"
    "Евгений Александрович К.\n\n"
    "Банки: Сбер, ВТБ, Альфа, Газпром, Озон\n\n"
    "После оплаты нажмите кнопку ниже и выберите банк 👇"
)
PAYMENT_CARD_INTL = (
    "💳 *ОПЛАТА ЗАРУБЕЖНОЙ КАРТОЙ*\n\n"
    "Нажмите «ПОЛУЧИТЬ РЕКВИЗИТЫ» и Евгений пришлёт реквизиты в личные сообщения.\n\n"
    "После оплаты нажмите кнопку ниже 👇"
)
 
bot = Bot(token=TOKEN)
dp  = Dispatcher()
DB  = "kasikov_bot"
 
def db_get(k,d=None):
    with shelve.open(DB) as s: return s.get(k,d)
def db_set(k,v):
    with shelve.open(DB) as s: s[k]=v
def db_init():
    for k,v in [
        ("slots",{}),("appts",{}),("admin_chats",[]),("blocked",[]),
        ("logs",[]),("blocked_dates",[]),("users",[]),("violations",{}),
        ("regulars",[]),("states",{}),("drip",[]),("invited",[]),
        ("reviews",[]),("pending_feedback",{}),("closed_slots",{}),
        ("users_src",{}),("free_used",{}),("all_users_data",{}),
    ]:
        if db_get(k) is None: db_set(k,v)
db_init()
 
def get_st(uid): return db_get("states",{}).get(str(uid),{})
def set_st(uid,st):
    s=db_get("states",{}); s[str(uid)]=st; db_set("states",s)
def clr_st(uid):
    s=db_get("states",{}); s.pop(str(uid),None); db_set("states",s)
 
_fl={};_fc={}
BAD=["блять","бля","блядь","хуй","пиздец","пизда","ёбаный","ебать","ебал",
     "сука","суки","мудак","шлюха","пидор","гандон","ублюдок","долбоёб",
     "манда","жопа","нахуй","курва","дерьмо","fuck","shit","bitch","asshole","cunt"]
def has_bad(t): return any(w in t.lower() for w in BAD)
def viol(uid,tp):
    v=db_get("violations",{}); v.setdefault(str(uid),{})[tp]=v.get(str(uid),{}).get(tp,0)+1
    db_set("violations",v); return v[str(uid)][tp]
def is_flood(uid):
    now=datetime.now().timestamp()
    if now-_fl.get(uid,0)<2:
        c=_fc.get(uid,0)+1; _fc[uid]=c
        if c>15 and viol(uid,"spam")>=5: asyncio.create_task(_auto_block(uid,"спам"))
        return True
    _fl[uid]=now; _fc[uid]=0; return False
 
def is_blocked(uid): return uid in db_get("blocked",[])
def is_admin(u): return bool(u) and u.lower() in [a.lower() for a in ADMINS]
 
async def _auto_block(uid,reason):
    bl=db_get("blocked",[])
    if uid not in bl: bl.append(uid); db_set("blocked",bl)
    await notify_adm(f"🚫 *Автоблок*\nID: {uid}\nПричина: {reason}")
 
def reg_user(uid,username=None,first_name=None):
    u=db_get("users",[])
    if uid not in u: u.append(uid); db_set("users",u)
    if username or first_name:
        ud=db_get("all_users_data",{})
        ud[str(uid)]={"username":username or "","name":first_name or "","uid":uid}
        db_set("all_users_data",ud)
 
def log_act(uid,uname,act):
    ls=db_get("logs",[]); ls.append({"uid":uid,"u":uname or "?","a":act,
        "t":datetime.now().strftime("%d.%m.%Y %H:%M:%S")})
    if len(ls)>1000: ls=ls[-1000:]
    db_set("logs",ls)
 
async def is_sub(uid):
    try:
        m=await bot.get_chat_member(CHANNEL,uid)
        return m.status in ("member","administrator","creator")
    except: return False
 
async def notify_adm(text,kb=None):
    for cid in db_get("admin_chats",[]):
        try: await bot.send_message(cid,text,parse_mode="Markdown",reply_markup=kb)
        except: pass
 
def get_free_used(uid): return db_get("free_used",{}).get(str(uid),False)
def set_free_used(uid,val=True):
    fu=db_get("free_used",{}); fu[str(uid)]=val; db_set("free_used",fu)
 
def day_slots_all():
    r=[]; c=datetime.strptime("10:00","%H:%M"); e=datetime.strptime("21:00","%H:%M")
    while c<=e: r.append(c.strftime("%H:%M")); c+=timedelta(minutes=30)
    return r
ALL_SLOTS=day_slots_all()
MN=["Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
 
def _block_adj(ds,tm,dur,unblock=False):
    dm={"30 мин":1,"1 час":2,"1.5 часа":3,"2 часа":4,"2.5 часа":5,"3 часа":6}
    n=dm.get(dur,2)
    if n<=1: return
    try: sdt=datetime.strptime(f"{ds} {tm}","%Y-%m-%d %H:%M")
    except: return
    cs=db_get("closed_slots",{})
    if ds not in cs: cs[ds]=[]
    for i in range(1,n):
        st=(sdt+timedelta(minutes=30*i)).strftime("%H:%M")
        if unblock:
            if st in cs[ds]: cs[ds].remove(st)
        else:
            if st not in cs[ds]: cs[ds].append(st)
    db_set("closed_slots",cs)
 
def free_slots(ds):
    slots=db_get("slots",{}); cs=db_get("closed_slots",{})
    appts=db_get("appts",{}); bd=db_get("blocked_dates",[])
    if ds in bd: return []
    taken=[r["time"] for r in appts.get(ds,[])]
    closed=cs.get(ds,[])
    today=date.today(); now=datetime.now()
    result=[]
    for t in slots.get(ds,[]):
        if t in taken or t in closed: continue
        if datetime.strptime(ds,"%Y-%m-%d").date()==today:
            se=datetime.strptime(f"{ds} {t}","%Y-%m-%d %H:%M")+timedelta(minutes=30)
            if se<=now: continue
        result.append(t)
    return result
 
def has_booking(uid,ds):
    return any(r["user_id"]==uid for r in db_get("appts",{}).get(ds,[]))
 
async def eoa(cb,text,kb=None,pm="Markdown"):
    """edit_or_answer — редактирует если возможно, иначе отправляет новое"""
    try: await cb.message.edit_text(text,parse_mode=pm,reply_markup=kb)
    except: await cb.message.answer(text,parse_mode=pm,reply_markup=kb)
 
 
# ═══════════════════════════════════════════════════
# ТЕКСТЫ
# ═══════════════════════════════════════════════════
 
T_ABOUT = """👤 *ОБО МНЕ*
 
Меня зовут Евгений Касиков.
 
Я не классический психолог в пиджаке с дипломом на стене. Я человек, который сам прошёл через то, с чем сейчас, скорее всего, пришли вы.
 
Двое детей и развод после 15 лет брака. Расставание после пяти лет отношений. Полный финансовый крах. И каждый раз казалось, что мир просто взял и перевернулся. То ощущение утром, когда просыпаешься, смотришь в потолок и думаешь: кто я теперь? Что вообще осталось?
 
Я знаю это изнутри. Не по книжкам.
 
Я из тех, кто привык добиваться результата. Кандидат в мастера спорта по плаванию, семь лет музыкальной школы. 15 лет я работал в продажах - от мерчендайзера до директора по региону. Провёл больше 500 собеседований, вёл тренинги, строил команды. Шесть собственных бизнесов. Флиппинг недвижимости 175+ инвест-объектов, больше 10 лет на рынке и по сей день.
 
Это дало мне навык который важен в нашей работе - быстро и точно понимать человека, слышать не только слова, но и то, что за ними.
 
А потом всё рухнуло разом. Бизнес, отношения, темп. Деньги, статус, ориентиры. Я упал и разбился в дребезги.
 
И я не стал делать вид, что всё нормально. Пересобрал себя. В своём темпе, честно, бережно к себе, без имитации бодрости.
 
Сегодня я работаю с людьми в период расставания и развода. За плечами более 10 лет практики и более 200 часов личной и групповой терапии. Более 200 реальных историй в работе с отношениями.
 
Я говорю на вашем языке. Смотрю не сверху - а рядом. Потому что я там был. И я знаю, что из этого выходят.
 
👉 @kasikovevgenii"""
 
T_HOW1 = """🔬 *МОИ МЕТОДЫ РАБОТЫ*
 
Сразу скажу честно - чтобы вы понимали, подходим ли мы друг другу.
 
Я не даю советов как жить. Не говорю «сделайте вот так». Если вы ищете именно это - я не тот специалист.
 
Я помогаю вам увидеть то, что вы сами не видите. Ваши паттерны, автоматические реакции, то как вы строите отношения. Задаю вопросы - иногда неудобные. Не осуждаю - но и не сюсюкаю.
 
Решения всегда остаются за вами. Работа идёт в живых сессиях - не в переписке. Завершить можно в любой момент.
 
Я работаю интегративно - выбираю то, что работает для конкретного человека в конкретной ситуации."""
 
T_HOW2 = """*НЛП*
Первые недели после расставания - хаос в голове. НЛП работает с тем, как вы воспринимаете произошедшее - меняет не событие, а то, как оно живёт внутри.
 
*Транзактный анализ (Эрик Бёрн)*
Почему снова похожая ситуация, похожий партнёр, похожий финал. Смотрим из какого эго-состояния вы живёте в отношениях.
 
*Психология привязанности (Боулби, Эйнсворт)*
Почему расставание бьёт так сильно - это не слабость. Это ваш тип привязанности, сформированный очень давно.
 
*EMDR*
Измена, предательство, внезапный уход - это травма. EMDR работает с тем, что застряло и не переваривается.
 
*Работа с телом*
Боль после расставания живёт не только в голове. Работа с телесными реакциями помогает добраться до того, что словами не выражается.
 
*Гештальт*
Незавершённые разговоры, невысказанное. Гештальт работает в настоящем моменте - завершает прошлое."""
 
T_HOW3 = """*IFS - работа с частями личности*
Одна часть хочет вернуться - другая знает что нельзя. Работа с частями помогает перестать воевать с собой.
 
*Схема-терапия (Джеффри Янг)*
«Я недостаточно хорош», «меня всё равно бросят». Они сформировались рано и тянут в одни и те же ситуации.
 
*Юнгианский подход*
Когда не можете отпустить - часто дело не в том человеке, а в том что вы видели в нём. Возвращаем это золото себе.
 
*Психодинамический подход*
Почему вы выбираете именно таких людей - работаем с бессознательными паттернами.
 
*Травма-информированный подход*
Работаю аккуратно - не ломлюсь в то, к чему вы ещё не готовы.
 
*Экзистенциальный подход*
После развода многие теряют не только партнёра - они теряют себя. Кризис идентичности - это нормально.
 
*Мужская психология*
Мужчины горюют иначе, восстанавливаются иначе. Я это учитываю."""
 
T_PRICE = """💼 *ПЛАТНАЯ КОНСУЛЬТАЦИЯ*
 
*1-я платная консультация*
_(если на бесплатную опоздали более 10 мин или отменили менее чем за 24 часа)_
30 минут - 3 000 руб.
 
*Разовая консультация*
60 минут - 5 000 руб.
_Минимальная сессия для постоянной работы - 60 минут._
 
*Пакет «Глубокая работа»*
5 консультаций (5 часов) - 20 000 руб.
_экономия 5 000 руб._
 
*Длительные сессии:*
1.5 часа - 7 500 руб.
2 часа - 10 000 руб.
2.5 часа - 12 500 руб.
3 часа - 15 000 руб.
 
Работаю по видео - Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX."""
 
T_FREE1 = """Благодарю за проявленный интерес.
Решиться на первый шаг бывает непросто.
 
Я провожу бесплатную 30-минутную вводную консультацию. За это время разбираемся с тем, что сейчас происходит - и вы уходите с чуть большей ясностью и пониманием что делать дальше.
 
После встречи вы получите письменный разбор с конкретными темами и рекомендациями. Он останется с вами независимо от того, решите ли вы продолжать работу со мной."""
 
T_FREE2 = """Работаю по видео - ВКонтакте, Zoom, Яндекс Телемост, Google Meet, Teams, MAX.
 
Для комфортной встречи выберите тихое место, где вас не будут отвлекать.
 
Выберите удобную дату 👇
✅ - есть свободные слоты"""
 
T_FAQ = """❓ *FAQ ЧАСТЫЕ ВОПРОСЫ*
 
*Это конфиденциально?*
Да. Всё что происходит на сессии остаётся между нами.
 
*Как проходит первая встреча?*
30 минут по видео. Никакого давления и обязательств. После встречи вы уходите с письменным разбором.
 
*Можно перенести или отменить?*
Да. Напишите мне минимум за 24 часа: @kasikovevgenii
 
*Вы работаете только с мужчинами?*
Нет. Около половины моих клиентов - женщины.
 
*Сколько сессий нужно?*
Зависит от запроса. Первая встреча даст понимание что подходит именно вам.
 
*Как технически проходит сессия?*
По видеосвязи - Zoom, ВКонтакте, Яндекс Телемост, Google Meet, Teams, MAX."""
 
T_CONTRACT_1 = """📋 *КАК УСТРОЕНА РАБОТА СО МНОЙ*
 
*БЕСПЛАТНАЯ ДИАГНОСТИЧЕСКАЯ СЕССИЯ*
Первая встреча - 30 минут, бесплатно. После сессии в течение 2-3 дней присылаю обратную связь и план на 10 платных сессий.
 
Сессия проводится один раз. Перенос возможен если предупредили не позднее чем за 24 часа.
 
Не пришли без предупреждения - следующая встреча в платном формате (30 минут).
 
Опоздали больше чем на 10 минут без предупреждения - сессия считается состоявшейся, следующая встреча платная."""
 
T_CONTRACT_2 = """*ПЛАТНЫЕ СЕССИИ - ВРЕМЯ И РИТМ*
Встречаемся в один и тот же день и время каждую неделю.
 
*ОПЛАТА*
Разовая сессия - оплата в день сессии за 2-3 часа до начала.
Пакет из 5 сессий - оплачивается полностью до первой сессии. Действует 2 месяца.
 
*ОТМЕНА И ПЕРЕНОС*
Отменить или перенести можно если предупредили не позднее чем за 24 часа.
Если не предупредили - сессия оплачивается полностью.
Переносить можно не более двух раз в месяц."""
 
T_CONTRACT_3 = """*ОПОЗДАНИЕ*
Больше 15 минут без предупреждения - сессия оплачивается полностью.
 
*ПАУЗЫ В РАБОТЕ*
Предупредите заранее. Слот сохраняю до месяца.
 
*СВЯЗЬ МЕЖДУ СЕССИЯМИ*
Я не консультирую в переписке. Работа - на сессиях.
Если накрыло - напишите коротко. Отвечаю в течение суток в будние дни.
Если состояние острое - найдите телефон доверия.
 
*ЗАВЕРШЕНИЕ РАБОТЫ*
Завершить можно в любой момент. Предупредите за одну сессию.
 
*КОНФИДЕНЦИАЛЬНОСТЬ*
Всё что происходит на сессиях - остаётся между нами."""
 
T_FEEDBACK = """Независимо от того, будете ли вы работать со мной дальше - хочу попросить короткую обратную связь.
 
Если откликается, ответьте коротко:
 
1. С каким состоянием вы пришли на сессию?
2. Что было для вас самым полезным?
3. С каким состоянием вы вышли после неё?
4. Планируете ли продолжать работу дальше?"""
 
DRIP = {
    1:   {"text":"Успели заглянуть в гайд? Там есть практика которую можно применить прямо сегодня.\n\nЕсли захочется разобрать свою ситуацию лично - первая встреча бесплатно 👇","kb":"free"},
    7:   {"text":"После расставания больно не потому что вы слабый.\n\nНейробиолог Этан Кросс: мозг воспринимает социальную боль в тех же зонах что и физическую.\n\nВы теряли не просто человека. Вы теряли версию себя который существовал рядом с этим человеком.\n\n👉 @kasikov_psy","kb":None},
    14:  {"text":"Три вещи которые не надо делать в первый месяц.\n\n1. Новые отношения сразу - рана переезжает, не заживает.\n2. Полный контакт с бывшим - мозгу нужна дистанция.\n3. Заливать боль чем угодно - она накапливается.\n\n👉 @kasikov_psy","kb":None},
    30:  {"text":"Прошёл месяц. Как вы?\n\nЕсли чувствуете что стало не легче - это сигнал что иногда в одиночку дольше и тяжелее.\n\nЕсли актуально 👇","kb":"free"},
    60:  {"text":"Почему вы скучаете по тому кто причинил вам боль?\n\nПсихиатр Сью Джонсон: мозг привязывается не к хорошим людям. Он привязывается к знакомым.\n\nВы скучаете не по человеку. Вы скучаете по версии себя который верил что всё получится.\n\n👉 @kasikov_psy","kb":None},
    90:  {"text":"Почему вы снова выбираете похожих людей?\n\nДжеффри Янг: убеждения «я недостаточно хорош», «меня всё равно бросят» формируются рано и управляют выбором партнёров.\n\n👉 @kasikov_psy","kb":None},
    120: {"text":"Злость после расставания - куда её деть?\n\nЛесли Гринберг: злость после расставания чаще всего вторичная эмоция. За ней прячется страх, боль, стыд.\n\n👉 @kasikov_psy","kb":None},
    150: {"text":"Как перестать проверять соцсети бывшего?\n\nРоберт Сапольски: мозг выделяет дофамин не когда получает награду - а когда ожидает её.\n\nПервый шаг - убрать доступ. Заблокировать. Не потому что вы слабый. А потому что вы умный.\n\n👉 @kasikov_psy","kb":None},
    180: {"text":"Разница между горем и депрессией.\n\nГоре движется. Медленно - но движется. Если через два месяца не становится легче - это сигнал обратиться за помощью.\n\n👉 @kasikov_psy","kb":None},
    210: {"text":"Тревожная привязанность - почему одни страдают сильнее.\n\nДжон Боулби: паттерн привязанности формируется в первые годы жизни. Тип привязанности не приговор - он меняется.\n\n👉 @kasikov_psy","kb":None},
    240: {"text":"Как говорить с детьми о разводе.\n\nДжудит Валлерстайн: дети переживают не сам развод, а то как родители ведут себя во время и после него.\n\n👉 @kasikov_psy","kb":None},
    270: {"text":"Когда вы готовы к новым отношениям.\n\nВы можете думать о бывшем без острой боли. Вы хотите новых отношений - а не хотите убежать от одиночества.\n\n👉 @kasikov_psy","kb":"free"},
    300: {"text":"10 месяцев назад вы забрали гайд. Как вы сейчас?\n\nЕсли захотите пройти этот путь с поддержкой - я здесь. Первая встреча по-прежнему бесплатно 👇","kb":"free"},
}
 
# ═══════════════════════════════════════════════════
# МЕНЮ И КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════
 
MN=["Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
 
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ БЕСПЛАТНАЯ КОНСУЛЬТАЦИЯ",callback_data="free")],
        [InlineKeyboardButton(text="💼 ПЛАТНАЯ КОНСУЛЬТАЦИЯ",   callback_data="paid_info")],
        [InlineKeyboardButton(text="📄 ГАЙД «4 ШАГА ПОСЛЕ РАССТАВАНИЯ»",callback_data="guide")],
        [InlineKeyboardButton(text="👤 ОБО МНЕ",               callback_data="about")],
        [InlineKeyboardButton(text="❓ FAQ ЧАСТЫЕ ВОПРОСЫ",     callback_data="faq")],
        [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ",             callback_data="my_appts")],
        [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА МОЙ ТГ КАНАЛ О ПСИХОЛОГИИ",
                              url=f"https://t.me/{CHANNEL.lstrip('@')}")],
    ])
 
def kb_cta():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ",callback_data="free")],
        [InlineKeyboardButton(text="💰 ЗАПИСАТЬСЯ НА ПЛАТНУЮ",  callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                   callback_data="main")],
    ])
 
def kb_about():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔬 МОИ МЕТОДЫ РАБОТЫ",           callback_data="how_work")],
        [InlineKeyboardButton(text="📋 КАК УСТРОЕНА РАБОТА СО МНОЙ", callback_data="contract")],
        [InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ",    callback_data="free")],
        [InlineKeyboardButton(text="💰 ЗАПИСАТЬСЯ НА ПЛАТНУЮ",        callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                        callback_data="main")],
    ])
 
def kb_how_after():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 КАК УСТРОЕНА РАБОТА СО МНОЙ",callback_data="contract")],
        [InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ",   callback_data="free")],
        [InlineKeyboardButton(text="💰 ЗАПИСАТЬСЯ НА ПЛАТНУЮ",       callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                        callback_data="main")],
    ])
 
def kb_contract_after():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔬 МОИ МЕТОДЫ РАБОТЫ",        callback_data="how_work")],
        [InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ", callback_data="free")],
        [InlineKeyboardButton(text="💰 ЗАПИСАТЬСЯ НА ПЛАТНУЮ",     callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                     callback_data="main")],
    ])
 
def kb_platform(back="main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 ZOOM",            callback_data="plat_Zoom")],
        [InlineKeyboardButton(text="📱 ВКОНТАКТЕ",       callback_data="plat_ВКонтакте")],
        [InlineKeyboardButton(text="💻 ЯНДЕКС ТЕЛЕМОСТ", callback_data="plat_Яндекс Телемост")],
        [InlineKeyboardButton(text="📹 GOOGLE MEET",     callback_data="plat_Google Meet")],
        [InlineKeyboardButton(text="🖥 TEAMS",           callback_data="plat_Teams")],
        [InlineKeyboardButton(text="📲 MAX",             callback_data="plat_MAX")],
        [InlineKeyboardButton(text="↩️ НАЗАД",           callback_data=back)],
    ])
 
def kb_duration():
    rows=[[InlineKeyboardButton(text=d,callback_data=f"dur_{d}")] for d in DURATIONS]
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def kb_banks(uid,ds,tm):
    rows=[[InlineKeyboardButton(text=b,callback_data=f"bank_{b}_{uid}_{ds}_{tm}")] for b in BANKS]
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 КАЛЕНДАРЬ",                  callback_data="adm_cal")],
        [InlineKeyboardButton(text="✅ ДЕНЬ ОТКРЫТЬ",               callback_data="adm_open_day_btn"),
         InlineKeyboardButton(text="❌ ДЕНЬ ЗАКРЫТЬ",               callback_data="adm_close_day_btn")],
        [InlineKeyboardButton(text="✅ НЕДЕЛЮ ОТКРЫТЬ",             callback_data="adm_open_week"),
         InlineKeyboardButton(text="❌ НЕДЕЛЮ ЗАКРЫТЬ",             callback_data="adm_block_week")],
        [InlineKeyboardButton(text="❌ ЗАБЛОКИРОВАТЬ МЕСЯЦ",        callback_data="adm_block_month")],
        [InlineKeyboardButton(text="🟡 НЕПОДТВЕРЖДЁННЫЕ ЗАПИСИ",   callback_data="adm_unconf")],
        [InlineKeyboardButton(text="📋 ПРОШЕДШИЕ БЕСПЛАТНЫЕ",       callback_data="adm_past_free")],
        [InlineKeyboardButton(text="📋 ВСЕ ЗАПИСИ",                 callback_data="adm_list")],
        [InlineKeyboardButton(text="👥 ПОСТОЯННЫЕ КЛИЕНТЫ",         callback_data="adm_regulars")],
        [InlineKeyboardButton(text="➕ НОВЫЙ КЛИЕНТ ИЗ СОЦСЕТЕЙ",  callback_data="adm_new_src")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА",                 callback_data="adm_stats")],
        [InlineKeyboardButton(text="📤 РАССЫЛКА ВСЕМ",              callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📤 ПОСТ ИЗ КАНАЛА",             callback_data="adm_post")],
        [InlineKeyboardButton(text="📊 EXCEL ОТЧЁТ",                callback_data="adm_excel")],
        [InlineKeyboardButton(text="⭐️ ОТЗЫВЫ",                     callback_data="adm_reviews")],
        [InlineKeyboardButton(text="🚫 ЗАБЛОКИРОВАННЫЕ",            callback_data="adm_blocked")],
        [InlineKeyboardButton(text="📊 ЛОГИ",                       callback_data="adm_logs")],
    ])
 
def cal_user(year,month):
    today=date.today(); cal=calendar.monthcalendar(year,month)
    bd=db_get("blocked_dates",[]); rows=[]
    rows.append([InlineKeyboardButton(text=f"📅 {MN[month-1]} {year}",callback_data="noop")])
    rows.append([InlineKeyboardButton(text=d,callback_data="noop") for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row=[]
        for day in week:
            if day==0: row.append(InlineKeyboardButton(text=" ",callback_data="noop"))
            else:
                d=date(year,month,day); ds=d.strftime("%Y-%m-%d")
                if d<today: row.append(InlineKeyboardButton(text="·",callback_data="noop"))
                elif ds in bd: row.append(InlineKeyboardButton(text="❌",callback_data="noop"))
                elif free_slots(ds): row.append(InlineKeyboardButton(text=f"✅{day}",callback_data=f"uday_{ds}"))
                else: row.append(InlineKeyboardButton(text=str(day),callback_data="no_slots"))
        rows.append(row)
    pm,py=(month-1,year) if month>1 else (12,year-1)
    nm,ny=(month+1,year) if month<12 else (1,year+1)
    nav=[]
    if date(py,pm,1)>=today.replace(day=1): nav.append(InlineKeyboardButton(text="◀️",callback_data=f"ucal_{py}_{pm}"))
    else: nav.append(InlineKeyboardButton(text=" ",callback_data="noop"))
    nav.append(InlineKeyboardButton(text=" ",callback_data="noop"))
    nav.append(InlineKeyboardButton(text="▶️",callback_data=f"ucal_{ny}_{nm}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 МЕНЮ КЛИЕНТА",callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def cal_admin(year,month):
    today=date.today(); cal=calendar.monthcalendar(year,month)
    appts=db_get("appts",{}); slots=db_get("slots",{}); bd=db_get("blocked_dates",[]); rows=[]
    rows.append([InlineKeyboardButton(text=f"🔧 {MN[month-1]} {year}",callback_data="noop")])
    rows.append([InlineKeyboardButton(text=d,callback_data="noop") for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    for week in cal:
        row=[]
        for day in week:
            if day==0: row.append(InlineKeyboardButton(text=" ",callback_data="noop"))
            else:
                d=date(year,month,day); ds=d.strftime("%Y-%m-%d")
                if d<today: row.append(InlineKeyboardButton(text="·",callback_data=f"aday_{ds}"))
                else:
                    da=appts.get(ds,[]); is_bd=ds in bd
                    hu=any(not r.get("confirmed") for r in da)
                    hc=any(r.get("confirmed") for r in da)
                    if hu: row.append(InlineKeyboardButton(text=f"🟡{day}",callback_data=f"aday_{ds}"))
                    elif hc: row.append(InlineKeyboardButton(text=f"🔵{day}",callback_data=f"aday_{ds}"))
                    elif is_bd: row.append(InlineKeyboardButton(text=f"❌{day}",callback_data=f"aday_{ds}"))
                    elif slots.get(ds): row.append(InlineKeyboardButton(text=f"✅{day}",callback_data=f"aday_{ds}"))
                    else: row.append(InlineKeyboardButton(text=str(day),callback_data=f"aday_{ds}"))
        rows.append(row)
    pm,py=(month-1,year) if month>1 else (12,year-1)
    nm,ny=(month+1,year) if month<12 else (1,year+1)
    rows.append([
        InlineKeyboardButton(text="◀️",callback_data=f"acal_{py}_{pm}"),
        InlineKeyboardButton(text="📅 ЗАПИСАТЬСЯ",callback_data="adm_book_menu"),
        InlineKeyboardButton(text="▶️",callback_data=f"acal_{ny}_{nm}"),
    ])
    rows.append([
        InlineKeyboardButton(text="✅ ДЕНЬ ОТКРЫТЬ",   callback_data="adm_open_day_btn"),
        InlineKeyboardButton(text="❌ ДЕНЬ ЗАКРЫТЬ",   callback_data="adm_close_day_btn"),
    ])
    rows.append([
        InlineKeyboardButton(text="✅ НЕДЕЛЮ ОТКРЫТЬ", callback_data="adm_open_week_cal"),
        InlineKeyboardButton(text="❌ НЕДЕЛЮ ЗАКРЫТЬ", callback_data="adm_block_week_cal"),
    ])
    rows.append([
        InlineKeyboardButton(text="🏠 МЕНЮ КЛИЕНТА",callback_data="main"),
        InlineKeyboardButton(text="🔐 МЕНЮ АДМИН",  callback_data="adm_back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def slots_day_admin(ds):
    slots=db_get("slots",{}); cs=db_get("closed_slots",{})
    appts=db_get("appts",{}); bd=db_get("blocked_dates",[])
    today=date.today(); is_past=datetime.strptime(ds,"%Y-%m-%d").date()<today
    is_bd=ds in bd
    open_s=slots.get(ds,[]); closed_d=cs.get(ds,[])
    all_d=ALL_SLOTS if is_bd else sorted(set(open_s+closed_d))
    taken={r["time"]:r for r in appts.get(ds,[])}
    rows=[]; row=[]
    for t in all_d:
        if t in taken:
            em="🔵" if taken[t].get("confirmed") else "🟡"; cb=f"aslot_{ds}_{t}"
        elif t in closed_d or is_bd:
            em="🔴"; cb=f"aslot_blocked_{ds}_{t}"
        else:
            em="🟢"; cb=f"aslot_{ds}_{t}"
        row.append(InlineKeyboardButton(text=f"{em}{t}",callback_data=cb))
        if len(row)==3: rows.append(row); row=[]
    if row: rows.append(row)
    if is_past:
        rows.append([InlineKeyboardButton(text="➕ ДОБАВИТЬ СЕССИЮ",callback_data=f"adm_add_session_{ds}")])
    else:
        rows.append([
            InlineKeyboardButton(text="✅ ОТКРЫТЬ ДЕНЬ ПОЛНОСТЬЮ",callback_data=f"adm_full_open_{ds}"),
            InlineKeyboardButton(text="❌ ЗАКРЫТЬ ДЕНЬ ПОЛНОСТЬЮ",callback_data=f"adm_full_close_{ds}"),
        ])
        rows.append([
            InlineKeyboardButton(text="➕ ДОБАВИТЬ СЛОТЫ",callback_data=f"adm_add_slots_{ds}"),
            InlineKeyboardButton(text="✏️ ЗАПИСАТЬ",      callback_data=f"adm_book_slot_{ds}"),
        ])
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД К КАЛЕНДАРЮ",callback_data="adm_cal")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def slots_menu_user(ds):
    slots=db_get("slots",{}); cs=db_get("closed_slots",{})
    appts=db_get("appts",{}); taken=[r["time"] for r in appts.get(ds,[])]
    closed=cs.get(ds,[]); rows=[]; row=[]
    for t in slots.get(ds,[]):
        if t in closed: continue
        if t in taken: row.append(InlineKeyboardButton(text=f"🔴{t}",callback_data="slot_taken"))
        else: row.append(InlineKeyboardButton(text=f"🟢{t}",callback_data=f"uslot_{ds}_{t}"))
        if len(row)==3: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def get_clients_kb(step):
    ud=db_get("all_users_data",{}); appts=db_get("appts",{})
    seen=set(); users_data=[]
    for info in ud.values():
        u=info.get("username",""); n=info.get("name","")
        if u and u not in seen:
            seen.add(u); users_data.append({"name":n,"username":u,"uid":info.get("uid",0)})
    for ds,recs in appts.items():
        for r in recs:
            u=r.get("username","")
            if u and u!="нет" and u not in seen:
                seen.add(u); users_data.append({"name":r.get("name","—"),"username":u,"uid":r.get("user_id",0)})
    rows=[]
    for u in users_data[:20]:
        lbl=f"👤 {u['name']} @{u['username']}" if u['name'] else f"👤 @{u['username']}"
        rows.append([InlineKeyboardButton(text=lbl,callback_data=f"pick_client_{step}_{u['username']}")])
    rows.append([InlineKeyboardButton(text="🔍 НАЙТИ ПО ИМЕНИ", callback_data=f"search_client_{step}")])
    rows.append([InlineKeyboardButton(text="✏️ ВВЕСТИ ВРУЧНУЮ", callback_data=f"manual_client_{step}")])
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",          callback_data="adm_cal")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
def make_excel(d_from,d_to):
    if not EXCEL_OK: return None
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="Записи"
    hdr=["Дата","Время","Тип","Статус","Имя","Username","Платформа","Длительность","Описание","Источник","Оплата"]
    hf=PatternFill("solid",fgColor="2E86AB")
    for i,h in enumerate(hdr,1):
        c=ws.cell(row=1,column=i,value=h); c.fill=hf
        c.font=Font(color="FFFFFF",bold=True); c.alignment=Alignment(horizontal="center")
    appts=db_get("appts",{}); row=2
    for ds in sorted(appts.keys()):
        if ds<d_from or ds>d_to: continue
        for r in appts[ds]:
            ws.cell(row=row,column=1,value=ds); ws.cell(row=row,column=2,value=r.get("time",""))
            ws.cell(row=row,column=3,value="Платная" if r.get("type")=="paid" else "Бесплатная")
            ws.cell(row=row,column=4,value=r.get("status",""))
            ws.cell(row=row,column=5,value=r.get("name",""))
            ws.cell(row=row,column=6,value=f"@{r.get('username','')}")
            ws.cell(row=row,column=7,value=r.get("platform",""))
            ws.cell(row=row,column=8,value=r.get("duration",""))
            ws.cell(row=row,column=9,value=r.get("desc",""))
            ws.cell(row=row,column=10,value=r.get("source","бот"))
            ws.cell(row=row,column=11,value=r.get("bank","не указан") if r.get("paid") else "не оплачено")
            row+=1
    for col in ws.columns:
        ml=max((len(str(c.value or "")) for c in col),default=0)
        ws.column_dimensions[col[0].column_letter].width=min(ml+4,40)
    buf=io.BytesIO(); wb.save(buf); buf.seek(0); return buf
 
def drip_add(uid):
    q=db_get("drip",[]); now=datetime.now()
    for day in DRIP: q.append({"uid":uid,"day":day,"at":(now+timedelta(days=day)).isoformat()})
    db_set("drip",q)
 
# ═══════════════════════════════════════════════════
# ФОНОВЫЕ ЗАДАЧИ
# ═══════════════════════════════════════════════════
 
async def bg_loop():
    while True:
        await asyncio.sleep(60)
        try:
            now=datetime.now(); appts=db_get("appts",{})
            for ds,recs in appts.items():
                changed=False
                for rec in recs:
                    try: adt=datetime.strptime(f"{ds} {rec['time']}","%Y-%m-%d %H:%M")
                    except: continue
                    diff=(adt-now).total_seconds()/60
                    plat=rec.get("platform",""); link=PLATFORMS.get(plat,"")
                    tl="💼 Платная" if rec.get("type")=="paid" else "🆓 Бесплатная"
 
                    if 59<=diff<=61 and not rec.get("rem_client") and rec.get("user_id"):
                        try:
                            kb=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ ПОДТВЕРЖДАЮ",callback_data=f"cli_ok_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{rec['time']}")],
                            ])
                            await bot.send_message(rec["user_id"],
                                f"⏰ Напоминание!\n\nЧерез час наша встреча - {rec['time']} МСК\n"
                                f"Платформа: {plat}\n{'🔗 '+link if link else ''}\n\n"
                                "Если всё окей 😁 просьба подтвердить:",reply_markup=kb)
                            rec["rem_client"]=True; changed=True
                        except: pass
 
                    if 59<=diff<=61 and not rec.get("rem_admin"):
                        kb2=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ",callback_data=f"adm_ok_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"adm_cncl_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"adm_mv_{rec.get('user_id',0)}_{ds}_{rec['time']}")],
                        ])
                        await notify_adm(
                            f"⏰ *Через час консультация!*\n\n📅 {ds} в {rec['time']} МСК\n{tl}\n"
                            f"👤 {rec.get('name','—')}\n📱 {plat}\n{'🔗 '+link if link else ''}\n"
                            f"⏱ {rec.get('duration','—')}\n🆔 @{rec.get('username','—')}",kb=kb2)
                        rec["rem_admin"]=True; changed=True
 
                    if 29<=diff<=31 and rec.get("rem_client") and not rec.get("cli_confirmed") and rec.get("user_id"):
                        try:
                            kb=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ ПОДТВЕРЖДАЮ",callback_data=f"cli_ok_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{rec['time']}")],
                                [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{rec['time']}")],
                            ])
                            await bot.send_message(rec["user_id"],"Вы ещё не подтвердили участие. Всё в силе? 😊",reply_markup=kb)
                        except: pass
 
                    dm={"30 мин":30,"1 час":60,"1.5 часа":90,"2 часа":120,"2.5 часа":150,"3 часа":180}
                    dm2=dm.get(rec.get("duration","30 мин"),30)
                    past=(now-(adt+timedelta(minutes=dm2+5))).total_seconds()/60
                    if 0<=past<=2 and not rec.get("session_asked"):
                        kb3=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ ДА, БЕСПЛАТНАЯ",      callback_data=f"sess_yes_free_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="✅ ДА, ПЛАТНАЯ",          callback_data=f"sess_yes_paid_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="❌ НЕТ, БЕСПЛАТНАЯ",     callback_data=f"sess_no_free_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="❌ НЕТ, ПЛАТНАЯ",         callback_data=f"sess_no_paid_{ds}_{rec['time']}")],
                            [InlineKeyboardButton(text="⏰ ОПОЗДАЛ/НЕ ПРИШЁЛ",  callback_data=f"sess_noshow_{ds}_{rec['time']}")],
                        ])
                        await notify_adm(
                            f"📅 {ds} в {rec['time']} МСК\n{tl} | ⏱ {rec.get('duration','—')}\n"
                            f"👤 {rec.get('name','—')}\n🆔 @{rec.get('username','—')}\n\nСессия состоялась?",kb=kb3)
                        rec["session_asked"]=True; changed=True
 
                if changed:
                    a=db_get("appts",{}); a[ds]=recs; db_set("appts",a)
 
            pf=db_get("pending_feedback",{})
            for key,item in list(pf.items()):
                if item.get("sent"): continue
                if now>=datetime.fromisoformat(item["remind_at"]):
                    await notify_adm(
                        f"📅 {item['ds']} в {item['time']}\n🆓 Бесплатная | ⏱ {item.get('dur','—')}\n"
                        f"👤 {item['name']}\n🆔 @{item['username']}\n\nЖду от вас обратную связь и план работы, Евгений.",
                        kb=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="📝 ОТПРАВИТЬ ОБРАТНУЮ СВЯЗЬ",callback_data=f"send_fb_{key}")
                        ]]))
                    item["remind_at"]=(now+timedelta(hours=24)).isoformat()
            db_set("pending_feedback",pf)
 
            drip=db_get("drip",[]); left=[]
            for item in drip:
                if now>=datetime.fromisoformat(item["at"]):
                    d=DRIP.get(item["day"])
                    if d:
                        try:
                            kb=None
                            if d["kb"]=="free":
                                kb=InlineKeyboardMarkup(inline_keyboard=[[
                                    InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ",callback_data="free")
                                ]])
                            await bot.send_message(item["uid"],d["text"],reply_markup=kb)
                        except: pass
                else: left.append(item)
            db_set("drip",left)
 
        except Exception as e: log.error(f"bg_loop: {e}")
 
# ═══════════════════════════════════════════════════
# ХЭНДЛЕРЫ — СТАРТ И КЛИЕНТ
# ═══════════════════════════════════════════════════
 
@dp.message(Command("start","admin","stop"))
async def cmd_handler(msg: types.Message):
    uid=msg.from_user.id
    if is_blocked(uid): return
    clr_st(uid)
    reg_user(uid, msg.from_user.username, msg.from_user.first_name)
    log_act(uid,msg.from_user.username,msg.text or "cmd")
    if is_admin(msg.from_user.username):
        chats=db_get("admin_chats",[])
        if uid not in chats: chats.append(uid); db_set("admin_chats",chats)
    cmd=(msg.text or "").split()[0]
    if cmd=="/stop":
        if is_admin(msg.from_user.username):
            await msg.answer("🛑 Бот останавливается..."); await dp.stop_polling()
        return
    if cmd=="/admin":
        if is_admin(msg.from_user.username):
            await msg.answer("🔐 *ПАНЕЛЬ АДМИНИСТРАТОРА*",parse_mode="Markdown",reply_markup=kb_admin())
        return
    # Проверяем ожидающую запись
    appts=db_get("appts",{}); today_d=date.today(); pending=None
    for ds,recs in appts.items():
        try: d=datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d<today_d: continue
        for r in recs:
            if r.get("username","").lower()==(msg.from_user.username or "").lower() and r.get("user_id",0)==0:
                r["user_id"]=uid; pending=(ds,r); break
        if pending: break
    if pending:
        db_set("appts",appts); ds,r=pending
        tl="💼 Платная" if r.get("type")=="paid" else "🆓 Бесплатная"
        plat=r.get("platform","—"); link=PLATFORMS.get(plat,""); dur=r.get("duration","—")
        ck=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{r['time']}")],
            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{r['time']}")],
            [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ", callback_data="my_appts")],
        ])
        await msg.answer(
            f"Приветствую, {msg.from_user.first_name} 👋\n\n✅ Ваша запись уже создана:\n\n"
            f"📅 {ds} в {r['time']} МСК\n{tl} | ⏱ {dur}\n📱 {plat}\n"
            f"{'🔗 '+link if link else ''}\n\nЗа час до сессии вам придёт напоминание.",reply_markup=ck)
        if r.get("type")=="paid":
            price=PRICES.get(dur,5000)
            pay_kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 ОПЛАТА КАРТОЙ РФ / СБП",  callback_data=f"pay_ru_{uid}_{ds}_{r['time']}")],
                [InlineKeyboardButton(text="💳 ОПЛАТА ЗАРУБЕЖНОЙ КАРТОЙ",callback_data=f"pay_intl_{uid}_{ds}_{r['time']}")],
            ])
            await msg.answer(f"💰 *Стоимость сессии: {price:,} руб.*\n\nВыберите способ оплаты:",
                             parse_mode="Markdown",reply_markup=pay_kb)
        return
    # Спрашиваем источник
    src_kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 INSTAGRAM",   callback_data="src_start_ig")],
        [InlineKeyboardButton(text="🎵 TIKTOK",      callback_data="src_start_tt")],
        [InlineKeyboardButton(text="▶️ YOUTUBE",     callback_data="src_start_yt")],
        [InlineKeyboardButton(text="💙 ВКОНТАКТЕ",   callback_data="src_start_vk")],
        [InlineKeyboardButton(text="👥 ОТ ЗНАКОМЫХ", callback_data="src_start_ref")],
        [InlineKeyboardButton(text="🌐 ДРУГОЕ",      callback_data="src_start_other")],
    ])
    await msg.answer(
        f"Приветствую, {msg.from_user.first_name} 👋\n\nПодскажите пожалуйста — откуда вы обо мне узнали?",
        reply_markup=src_kb)
 
@dp.callback_query(F.data.startswith("src_start_"))
async def src_start(cb: types.CallbackQuery):
    sm={"ig":"📸 Instagram","tt":"🎵 TikTok","yt":"▶️ YouTube",
        "vk":"💙 ВКонтакте","ref":"👥 От знакомых","other":"🌐 Другое"}
    code=cb.data[10:]; label=sm.get(code,code); uid=cb.from_user.id
    us=db_get("users_src",{}); us[str(uid)]=label; db_set("users_src",us)
    log_act(uid,cb.from_user.username,f"src:{code}")
    await cb.answer()
    await eoa(cb,
        "Меня зовут Евгений.\n\n"
        "Я помогаю людям пройти через расставание - без застревания "
        "и с пониманием что делать дальше.\n\n"
        "Кто я и как работаю можно посмотреть ниже ⤵️",
        kb=kb_main())
 
@dp.callback_query(F.data=="noop")
async def noop(cb): await cb.answer()
@dp.callback_query(F.data=="no_slots")
async def no_slots(cb): await cb.answer("На этот день слотов нет",show_alert=True)
@dp.callback_query(F.data=="slot_taken")
async def slot_taken(cb): await cb.answer("Это время занято 🔴",show_alert=True)
 
@dp.callback_query(F.data=="main")
async def go_main(cb: types.CallbackQuery):
    await cb.answer()
    await eoa(cb,"🏠 Главное меню:",kb=kb_main())
 
@dp.callback_query(F.data=="about")
async def about(cb: types.CallbackQuery):
    await cb.answer()
    await eoa(cb,T_ABOUT,kb=kb_about())
 
@dp.callback_query(F.data=="how_work")
async def how_work(cb: types.CallbackQuery):
    await cb.answer()
    await eoa(cb,T_HOW1+"\n\n"+T_HOW2+"\n\n"+T_HOW3,kb=kb_how_after())
 
@dp.callback_query(F.data=="contract")
async def contract_cb(cb: types.CallbackQuery):
    await cb.answer()
    pay_btn=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💼 ПЛАТНАЯ КОНСУЛЬТАЦИЯ",callback_data="paid_info")
    ]])
    await eoa(cb,T_CONTRACT_1+"\n\n"+T_CONTRACT_2,kb=pay_btn)
    await cb.message.answer(T_CONTRACT_3,parse_mode="Markdown",reply_markup=kb_contract_after())
 
@dp.callback_query(F.data=="faq")
async def faq(cb: types.CallbackQuery):
    await cb.answer()
    await eoa(cb,T_FAQ,kb=kb_cta())
 
@dp.callback_query(F.data=="paid_info")
async def paid_info(cb: types.CallbackQuery):
    await cb.answer()
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 ЗАПИСАТЬСЯ НА ПЛАТНУЮ",callback_data="book_paid")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                callback_data="main")],
    ])
    await eoa(cb,T_PRICE,kb=kb)
 
@dp.callback_query(F.data=="guide")
async def guide(cb: types.CallbackQuery):
    await cb.answer(); log_act(cb.from_user.id,cb.from_user.username,"guide")
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ",url=f"https://t.me/{CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я ПОДПИСАЛСЯ",callback_data="check_sub")],
        [InlineKeyboardButton(text="↩️ НАЗАД",       callback_data="main")],
    ])
    await eoa(cb,
        "📄 *Гайд «4 шага выхода из расставания»* - 30 страниц практики.\n\n"
        "Чтобы получить - подпишитесь на канал 👇",kb=kb)
 
@dp.callback_query(F.data=="check_sub")
async def check_sub(cb: types.CallbackQuery):
    if await is_sub(cb.from_user.id):
        log_act(cb.from_user.id,cb.from_user.username,"got_guide"); drip_add(cb.from_user.id)
        await eoa(cb,
            f"✅ Держите гайд!\n\n👉 {LEAD}\n\n"
            "Если захочется разобрать свою ситуацию лично - первая встреча бесплатно 👇",
            kb=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="1️⃣ ЗАПИСАТЬСЯ НА БЕСПЛАТНУЮ",callback_data="free")
            ]]))
    else: await cb.answer("❌ Подписка не найдена.",show_alert=True)
 
@dp.callback_query(F.data=="free")
async def free_consult(cb: types.CallbackQuery):
    uid=cb.from_user.id
    if get_free_used(uid):
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 ПЛАТНАЯ КОНСУЛЬТАЦИЯ",callback_data="paid_info")],
            [InlineKeyboardButton(text="↩️ НАЗАД",              callback_data="main")],
        ])
        await cb.answer()
        await eoa(cb,
            "Бесплатная диагностическая сессия уже была использована или не состоялась по вашей инициативе.\n\n"
            "Первая платная сессия - 30 минут - 3 000 руб.",kb=kb)
        return
    await cb.answer(); set_st(uid,{"type":"free"})
    log_act(uid,cb.from_user.username,"free_consult")
    await eoa(cb,T_FREE1)
    await asyncio.sleep(0.3)
    today=date.today()
    await cb.message.answer(T_FREE2,reply_markup=cal_user(today.year,today.month))
 
@dp.callback_query(F.data=="book_paid")
async def book_paid(cb: types.CallbackQuery):
    await cb.answer(); set_st(cb.from_user.id,{"type":"paid"})
    today=date.today()
    await eoa(cb,"Выберите удобную дату 👇\n✅ - есть свободные слоты",
              kb=cal_user(today.year,today.month))
 
@dp.callback_query(F.data.startswith("ucal_"))
async def ucal_nav(cb: types.CallbackQuery):
    _,y,m=cb.data.split("_")
    try: await cb.message.edit_reply_markup(reply_markup=cal_user(int(y),int(m)))
    except: pass
 
@dp.callback_query(F.data.startswith("uday_"))
async def uday_sel(cb: types.CallbackQuery):
    ds=cb.data[5:]; uid=cb.from_user.id; st=get_st(uid)
    if st.get("type")!="reschedule" and has_booking(uid,ds):
        await cb.answer("У вас уже есть запись на этот день.",show_alert=True); return
    st["date"]=ds; set_st(uid,st); await cb.answer()
    await eoa(cb,f"📅 *{ds}*\n\nВыберите время:\n🟢 свободно  🔴 занято",
              kb=slots_menu_user(ds))
 
@dp.callback_query(F.data.startswith("uslot_"))
async def uslot_sel(cb: types.CallbackQuery):
    parts=cb.data.split("_"); ds,tm=parts[1],parts[2]
    uid=cb.from_user.id; st=get_st(uid); ctype=st.get("type","free")
    await cb.answer()
    if ctype in ("free","reschedule"):
        st.update({"step":"desc","date":ds,"time":tm,"duration":"30 мин"}); set_st(uid,st)
        name=cb.from_user.first_name or "Клиент"
        await eoa(cb,
            f"{name}, чтобы сессия была для вас максимально полезной, "
            "по желанию опишите пожалуйста что сейчас у вас происходит:")
    else:
        st.update({"step":"duration","date":ds,"time":tm}); set_st(uid,st)
        await eoa(cb,"Выберите длительность сессии:",kb=kb_duration())
 
@dp.callback_query(F.data.startswith("dur_"))
async def dur_sel(cb: types.CallbackQuery):
    dur=cb.data[4:]; uid=cb.from_user.id; st=get_st(uid); st["duration"]=dur; set_st(uid,st)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ ПЕРВАЯ ПЛАТНАЯ СЕССИЯ", callback_data="session_first")],
        [InlineKeyboardButton(text="🔄 ПОВТОРНАЯ ПЛАТНАЯ СЕССИЯ",callback_data="session_repeat")],
    ])
    await eoa(cb,"Это первая или повторная платная сессия?",kb=kb)
 
@dp.callback_query(F.data=="session_first")
async def session_first(cb: types.CallbackQuery):
    uid=cb.from_user.id; st=get_st(uid); st["step"]="desc"; set_st(uid,st)
    name=cb.from_user.first_name or "Клиент"; await cb.answer()
    await eoa(cb,
        f"{name}, чтобы сессия была для вас максимально полезной, "
        "по желанию опишите пожалуйста что сейчас у вас происходит:")
 
@dp.callback_query(F.data=="session_repeat")
async def session_repeat(cb: types.CallbackQuery):
    uid=cb.from_user.id; st=get_st(uid)
    st["step"]="platform"; st["desc"]="Повторная сессия"; st["name"]=cb.from_user.first_name or "Клиент"
    set_st(uid,st); await cb.answer()
    await eoa(cb,"Через какую платформу удобнее созвониться?",kb=kb_platform())
 
@dp.callback_query(F.data=="desc_extend")
async def desc_extend(cb: types.CallbackQuery):
    uid=cb.from_user.id; st=get_st(uid); st["step"]="desc_retry"; set_st(uid,st); await cb.answer()
    await eoa(cb,"Пожалуйста, расскажите подробнее:")
 
@dp.callback_query(F.data=="desc_keep")
async def desc_keep(cb: types.CallbackQuery):
    uid=cb.from_user.id; st=get_st(uid); st["step"]="platform"; set_st(uid,st); await cb.answer()
    await eoa(cb,"Через какую платформу удобнее созвониться?",kb=kb_platform())
 
@dp.callback_query(F.data.startswith("plat_"))
async def plat_sel(cb: types.CallbackQuery):
    plat=cb.data[5:]; uid=cb.from_user.id; st=get_st(uid)
    if st.get("step")=="adm_manual_plat":
        st["platform"]=plat; st["step"]="adm_manual_type"; set_st(uid,st); await cb.answer()
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 БЕСПЛАТНАЯ",callback_data="adm_mtype_free")],
            [InlineKeyboardButton(text="💼 ПЛАТНАЯ",   callback_data="adm_mtype_paid")],
            [InlineKeyboardButton(text="↩️ НАЗАД",     callback_data="adm_back")],
        ])
        await eoa(cb,"Тип консультации?",kb=kb); return
    st["platform"]=plat; st["step"]="confirm"; set_st(uid,st)
    ds=st.get("date","?"); tm=st.get("time","?"); dur=st.get("duration","30 мин")
    name=st.get("name",cb.from_user.first_name or "?")
    tl="💼 Платная" if st.get("type")=="paid" else "🆓 Бесплатная"
    ck=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ",callback_data=f"confirm_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ НАЗАД",      callback_data="main")],
    ])
    await eoa(cb,
        f"📋 *Проверьте данные:*\n\n📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n"
        f"👤 {name}\n📱 {plat}\n\nВсё верно?",kb=ck)
 
@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_book(cb: types.CallbackQuery):
    uid=cb.from_user.id; st=get_st(uid)
    if not st: await cb.answer("Ошибка, начните заново",show_alert=True); return
    ds=st["date"]; tm=st["time"]; name=st.get("name",cb.from_user.first_name or "—")
    ctype=st.get("type","free"); plat=st.get("platform","—")
    dur=st.get("duration","30 мин"); desc=st.get("desc","—"); uname=cb.from_user.username or "нет"
    appts=db_get("appts",{})
    if ds not in appts: appts[ds]=[]
    if any(r["user_id"]==uid and r["time"]==tm for r in appts[ds]):
        await cb.answer("Вы уже записаны на это время",show_alert=True); return
    appts[ds].append({
        "user_id":uid,"name":name,"time":tm,"username":uname,
        "type":ctype,"platform":plat,"duration":dur,"desc":desc,
        "source":"бот","status":"","confirmed":False,
        "rem_client":False,"rem_admin":False,"session_asked":False,
        "cli_confirmed":False,"paid":False,"bank":"",
    })
    db_set("appts",appts); _block_adj(ds,tm,dur); clr_st(uid)
    tl="💼 Платная" if ctype=="paid" else "🆓 Бесплатная"
    ck=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data="reschedule")],
        [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cancel_{ds}_{tm}")],
        [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ", callback_data="my_appts")],
    ])
    await eoa(cb,
        f"✅ Запись принята!\n\n📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n📱 {plat}\n\n"
        "Евгений скоро подтвердит и пришлёт ссылку на видеочат.",kb=ck)
    adm_kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ",callback_data=f"adm_ok_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"adm_cncl_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"adm_mv_{uid}_{ds}_{tm}")],
    ])
    await notify_adm(
        f"🔔 *Новая запись!*\n📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n"
        f"👤 {name}\n📱 {plat}\n💬 {desc[:100]}\n🆔 @{uname} | ID: {uid}",kb=adm_kb)
    if ctype=="paid":
        price=PRICES.get(dur,5000)
        pay_kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 ОПЛАТА КАРТОЙ РФ / СБП",  callback_data=f"pay_ru_{uid}_{ds}_{tm}")],
            [InlineKeyboardButton(text="💳 ОПЛАТА ЗАРУБЕЖНОЙ КАРТОЙ",callback_data=f"pay_intl_{uid}_{ds}_{tm}")],
        ])
        await bot.send_message(uid,
            f"💰 *Стоимость сессии: {price:,} руб.*\n\nВыберите способ оплаты:",
            parse_mode="Markdown",reply_markup=pay_kb)
 
@dp.callback_query(F.data=="my_appts")
async def my_appts(cb: types.CallbackQuery):
    uid=cb.from_user.id; appts=db_get("appts",{}); today=date.today(); rows=[]
    for ds in sorted(appts.keys()):
        try: d=datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d<today: continue
        for r in appts[ds]:
            if r["user_id"]!=uid: continue
            tl="💼" if r.get("type")=="paid" else "🆓"
            rows.append([InlineKeyboardButton(text=f"📅 {ds} {r['time']} {tl}",
                                               callback_data=f"my_rec_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="main")])
    if len(rows)==1:
        await eoa(cb,"У вас нет предстоящих записей.",kb=InlineKeyboardMarkup(inline_keyboard=rows))
    else:
        await eoa(cb,"📅 *Ваши записи:*",kb=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data.startswith("my_rec_"))
async def my_rec(cb: types.CallbackQuery):
    _,_,ds,tm=cb.data.split("_",3)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",callback_data="reschedule")],
        [InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data=f"cancel_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ НАЗАД",    callback_data="my_appts")],
    ])
    await eoa(cb,f"📅 {ds} в {tm} МСК",kb=kb)
 
@dp.callback_query(F.data=="reschedule")
async def reschedule(cb: types.CallbackQuery):
    set_st(cb.from_user.id,{"type":"reschedule"}); today=date.today(); await cb.answer()
    await eoa(cb,"Выберите новую дату:",kb=cal_user(today.year,today.month))
 
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_appt(cb: types.CallbackQuery):
    parts=cb.data.split("_"); ds=parts[1]; tm=parts[2]; uid=cb.from_user.id
    dur="30 мин"; appts=db_get("appts",{})
    if ds in appts:
        for r in appts[ds]:
            if r["user_id"]==uid and r["time"]==tm: dur=r.get("duration","30 мин"); break
        appts[ds]=[r for r in appts[ds] if not (r["user_id"]==uid and r["time"]==tm)]
        db_set("appts",appts)
    _block_adj(ds,tm,dur,unblock=True)
    await eoa(cb,"✅ Запись отменена. Если захотите записаться снова - я здесь.",kb=kb_main())
    await notify_adm(f"❌ Клиент отменил запись\n📅 {ds} в {tm}\n🆔 @{cb.from_user.username or 'нет'}")
 
@dp.callback_query(F.data.startswith("cli_ok_"))
async def cli_ok(cb: types.CallbackQuery):
    parts=cb.data.split("_"); ds=parts[2]; tm=parts[3]
    appts=db_get("appts",{})
    for r in appts.get(ds,[]):
        if r["user_id"]==cb.from_user.id and r["time"]==tm: r["cli_confirmed"]=True
    db_set("appts",appts); await cb.answer("✅ Отлично! Ждём вас!")
    await notify_adm(f"✅ {cb.from_user.first_name} подтвердил участие\n📅 {ds} в {tm}")
 
@dp.callback_query(F.data.startswith("cli_cancel_"))
async def cli_cancel(cb: types.CallbackQuery):
    parts=cb.data.split("_"); ds=parts[2]; tm=parts[3]; uid=cb.from_user.id
    dur="30 мин"; appts=db_get("appts",{})
    if ds in appts:
        for r in appts[ds]:
            if r["user_id"]==uid and r["time"]==tm: dur=r.get("duration","30 мин"); break
        appts[ds]=[r for r in appts[ds] if not (r["user_id"]==uid and r["time"]==tm)]
        db_set("appts",appts)
    _block_adj(ds,tm,dur,unblock=True); await cb.answer()
    await eoa(cb,"Запись отменена. Для новой записи нажмите кнопку ниже:",kb=kb_main())
    await notify_adm(f"❌ Клиент отменил перед сессией\n📅 {ds} в {tm}\n🆔 @{cb.from_user.username or 'нет'}")
 
@dp.callback_query(F.data.startswith("cli_move_"))
async def cli_move(cb: types.CallbackQuery):
    set_st(cb.from_user.id,{"type":"reschedule"}); today=date.today(); await cb.answer()
    await eoa(cb,"Выберите новую дату:",kb=cal_user(today.year,today.month))
    await notify_adm(f"🔄 Клиент хочет перенести\n🆔 @{cb.from_user.username or 'нет'}")
 
# ═══════════════════════════════════════════════════
# ОПЛАТА
# ═══════════════════════════════════════════════════
 
@dp.callback_query(F.data.startswith("pay_ru_"))
async def pay_ru(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОПЛАТИЛ",callback_data=f"pay_ru_confirm_{uid}_{ds}_{tm}")]
    ])
    await cb.answer()
    await eoa(cb,PAYMENT_CARD_RU,kb=kb)
 
@dp.callback_query(F.data.startswith("pay_ru_confirm_"))
async def pay_ru_confirm(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[3]); ds=parts[4]; tm=parts[5]
    await cb.answer()
    await eoa(cb,"Выберите банк через который вы перевели:",kb=kb_banks(uid,ds,tm))
 
@dp.callback_query(F.data.startswith("bank_"))
async def bank_sel(cb: types.CallbackQuery):
    parts=cb.data.split("_"); bank=parts[1]; uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    appts=db_get("appts",{})
    name="—"; dur="—"; price=5000
    for r in appts.get(ds,[]):
        if r["user_id"]==uid and r["time"]==tm:
            name=r.get("name","—"); dur=r.get("duration","—"); r["bank"]=bank
            price=PRICES.get(dur,5000); break
    db_set("appts",appts)
    await cb.answer(f"✅ Банк {bank} выбран")
    await eoa(cb,f"✅ Отлично! Информация об оплате отправлена Евгению.\nОжидайте подтверждения.")
    kb=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ ОПЛАТУ",callback_data=f"adm_confirm_pay_{uid}_{ds}_{tm}")
    ]])
    await notify_adm(
        f"💰 *Клиент оплатил!*\n\n"
        f"👤 {name}\n🆔 @{cb.from_user.username or '—'}\n"
        f"📅 {ds} в {tm} МСК\n⏱ {dur}\n"
        f"💳 Банк: {bank}\n💰 Сумма: {price:,} руб.",kb=kb)
 
@dp.callback_query(F.data.startswith("adm_confirm_pay_"))
async def adm_confirm_pay(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); uid=int(parts[3]); ds=parts[4]; tm=parts[5]
    appts=db_get("appts",{})
    plat="—"; link=""; name="—"
    for r in appts.get(ds,[]):
        if r["user_id"]==uid and r["time"]==tm:
            r["paid"]=True; plat=r.get("platform","—"); link=PLATFORMS.get(plat,""); name=r.get("name","—")
    db_set("appts",appts)
    try:
        ck=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{tm}")],
            [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ", callback_data="my_appts")],
        ])
        await bot.send_message(uid,
            f"✅ Оплата подтверждена!\n\n📅 {ds} в {tm} МСК\n📱 {plat}\n"
            f"{'🔗 '+link if link else ''}\n\nЗа час до сессии вам придёт напоминание.",
            reply_markup=ck)
    except: pass
    await eoa(cb,cb.message.text+"\n\n✅ *Оплата подтверждена*")
 
@dp.callback_query(F.data.startswith("pay_intl_"))
async def pay_intl(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 ПОЛУЧИТЬ РЕКВИЗИТЫ",callback_data=f"intl_req_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="✅ ОПЛАТИЛ",           callback_data=f"intl_paid_{uid}_{ds}_{tm}")],
    ])
    await cb.answer()
    await eoa(cb,PAYMENT_CARD_INTL,kb=kb)
 
@dp.callback_query(F.data.startswith("intl_req_"))
async def intl_req(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    await cb.answer("✅ Запрос отправлен Евгению")
    await eoa(cb,"✅ Евгений получил ваш запрос и пришлёт реквизиты в ближайшее время.")
    appts=db_get("appts",{})
    name="—"
    for r in appts.get(ds,[]):
        if r["user_id"]==uid and r["time"]==tm: name=r.get("name","—"); break
    await notify_adm(
        f"💳 *Запрос реквизитов зарубежной карты*\n\n"
        f"👤 {name}\n🆔 @{cb.from_user.username or '—'} | ID: {uid}\n"
        f"📅 {ds} в {tm} МСК\n\nОтправьте реквизиты клиенту в личку.")
 
@dp.callback_query(F.data.startswith("intl_paid_"))
async def intl_paid(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    appts=db_get("appts",{}); name="—"; dur="—"; price=5000
    for r in appts.get(ds,[]):
        if r["user_id"]==uid and r["time"]==tm:
            name=r.get("name","—"); dur=r.get("duration","—"); price=PRICES.get(dur,5000); break
    db_set("appts",appts)
    await cb.answer()
    await eoa(cb,"✅ Информация об оплате отправлена Евгению. Ожидайте подтверждения.")
    kb=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ ОПЛАТУ",callback_data=f"adm_confirm_pay_{uid}_{ds}_{tm}")
    ]])
    await notify_adm(
        f"💰 *Клиент сообщил об оплате (зарубежная карта)*\n\n"
        f"👤 {name}\n🆔 @{cb.from_user.username or '—'}\n"
        f"📅 {ds} в {tm} МСК\n⏱ {dur}\n💰 Сумма: {price:,} руб.",kb=kb)
 
# ═══════════════════════════════════════════════════
# ЕВГЕНИЙ — ПОДТВЕРЖДЕНИЕ, РЕЗУЛЬТАТ
# ═══════════════════════════════════════════════════
 
@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_ok(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    appts=db_get("appts",{}); plat="—"; link=""
    for r in appts.get(ds,[]):
        if r["user_id"]==uid and r["time"]==tm:
            r["confirmed"]=True; plat=r.get("platform","—"); link=PLATFORMS.get(plat,"")
    db_set("appts",appts)
    try:
        ck=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{tm}")],
            [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ", callback_data="my_appts")],
        ])
        await bot.send_message(uid,
            f"✅ Ваша запись подтверждена!\n\n📅 {ds} в {tm} МСК\n📱 {plat}\n"
            f"{'🔗 '+link if link else ''}\n\nЗа час до сессии вам придёт напоминание.\nПросьба подтвердить участие.",
            reply_markup=ck)
    except: pass
    adm_kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"adm_cncl_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"adm_mv_{uid}_{ds}_{tm}")],
        [InlineKeyboardButton(text="🔐 МЕНЮ АДМИН", callback_data="adm_back")],
    ])
    await eoa(cb,f"✅ *Запись подтверждена!*\n\n📅 {ds} в {tm} МСК\n👤 клиент уведомлён.",kb=adm_kb)
 
@dp.callback_query(F.data.startswith("adm_cncl_"))
async def adm_cncl(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    dur="30 мин"; appts=db_get("appts",{})
    if ds in appts:
        for r in appts[ds]:
            if r["user_id"]==uid and r["time"]==tm: dur=r.get("duration","30 мин"); break
        appts[ds]=[r for r in appts[ds] if not (r["user_id"]==uid and r["time"]==tm)]
        db_set("appts",appts)
    _block_adj(ds,tm,dur,unblock=True)
    try:
        await bot.send_message(uid,"❌ К сожалению, это время не получится.\nДля новой записи нажмите кнопку ниже:",
                               reply_markup=kb_main())
    except: pass
    await cb.answer("❌ Запись отменена")
    await eoa(cb,f"📅 *{ds}* — запись отменена, слот освобождён 🟢",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_mv_"))
async def adm_mv(cb: types.CallbackQuery):
    parts=cb.data.split("_"); uid=int(parts[2]); ds=parts[3]; tm=parts[4]
    set_st(cb.from_user.id,{"step":"adm_move_new_date","move_uid":uid,"move_ds":ds,"move_tm":tm})
    today=date.today(); await cb.answer()
    await eoa(cb,"Выберите новую дату для переноса:",kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data.startswith("sess_"))
async def sess_result(cb: types.CallbackQuery):
    parts=cb.data.split("_"); result=parts[1]; stype=parts[2]; ds=parts[3]; tm=parts[4]
    appts=db_get("appts",{})
    rec=next((r for r in appts.get(ds,[]) if r["time"]==tm),None)
    name=rec.get("name","—") if rec else "—"
    uname=rec.get("username","—") if rec else "—"
    dur=rec.get("duration","—") if rec else "—"
    cli_uid=rec.get("user_id",0) if rec else 0
    if result=="yes":
        if rec: rec["status"]="проведена"
        db_set("appts",appts)
        if stype=="free":
            key=f"{ds}_{tm}"; pf=db_get("pending_feedback",{})
            pf[key]={"uid":cli_uid,"ds":ds,"time":tm,"dur":dur,"name":name,"username":uname,
                     "sent":False,"remind_at":(datetime.now()+timedelta(minutes=5)).isoformat()}
            db_set("pending_feedback",pf)
            await eoa(cb,cb.message.text+"\n\n✅ Отмечено: проведена")
        else:
            kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 СКОПИРОВАТЬ ЗАПИСЬ (ПОСТОЯННЫЙ)",callback_data=f"reg_copy_{ds}_{tm}")],
                [InlineKeyboardButton(text="➕ НОВАЯ ЗАПИСЬ (ПОСТОЯННЫЙ)",     callback_data=f"reg_new_{ds}_{tm}")],
            ])
            await eoa(cb,
                f"✅ Платная сессия записана.\n\n📅 {ds} в {tm}\n💼 Платная | ⏱ {dur}\n"
                f"👤 {name}\n🆔 @{uname}",kb=kb)
    elif result=="noshow":
        if rec: rec["status"]="missed_no_show"
        db_set("appts",appts)
        if cli_uid: set_free_used(cli_uid,True)
        await eoa(cb,cb.message.text+"\n\n⏰ Отмечено: не пришёл. Следующая встреча - платная (30 мин / 3 000 руб.)")
    else:
        if rec: rec["status"]="не состоялась"
        db_set("appts",appts)
        sl="Бесплатная" if stype=="free" else "Платная"
        await eoa(cb,cb.message.text+f"\n\n❌ {sl} не состоялась.")
 
@dp.callback_query(F.data.startswith("send_fb_"))
async def send_fb(cb: types.CallbackQuery):
    key=cb.data[8:]; set_st(cb.from_user.id,{"step":"adm_fb_text","fb_key":key}); await cb.answer()
    await eoa(cb,"Введите текст обратной связи и план работы.\nОн уйдёт клиенту вместе с предложением продолжить:")
 
@dp.callback_query(F.data.startswith("reg_copy_"))
async def reg_copy(cb: types.CallbackQuery):
    _,_,ds,tm=cb.data.split("_",3); appts=db_get("appts",{})
    rec=next((r for r in appts.get(ds,[]) if r["time"]==tm),None)
    if not rec: await cb.answer("Запись не найдена",show_alert=True); return
    regs=db_get("regulars",[]); regs.append({
        "username":rec.get("username",""),"name":rec.get("name",""),"day":"","time":tm,"source":"авто"})
    db_set("regulars",regs); await cb.answer("✅ Добавлен в постоянные клиенты")
 
@dp.callback_query(F.data.startswith("reg_new_"))
async def reg_new(cb: types.CallbackQuery):
    _,_,ds,tm=cb.data.split("_",3); appts=db_get("appts",{})
    rec=next((r for r in appts.get(ds,[]) if r["time"]==tm),None)
    tg=rec.get("username","") if rec else ""; name=rec.get("name","") if rec else ""
    set_st(cb.from_user.id,{"step":"adm_book_date","manual_tg":tg,"manual_name":name})
    today=date.today(); await cb.answer()
    await eoa(cb,f"Записываю @{tg}. Выберите дату следующей сессии:",kb=cal_admin(today.year,today.month))
 
# ═══════════════════════════════════════════════════
# АДМИН — КАЛЕНДАРЬ
# ═══════════════════════════════════════════════════
 
@dp.callback_query(F.data=="adm_cal")
async def adm_cal(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    await cb.answer(); today=date.today()
    await eoa(cb,
        "📅 *УПРАВЛЕНИЕ ДНЯМИ*\n\n✅ свободный  🔵 записи  🟡 неподтверждённые  ❌ закрыт  · прошедший",
        kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data.startswith("acal_"))
async def acal_nav(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    _,y,m=cb.data.split("_")
    try: await cb.message.edit_reply_markup(reply_markup=cal_admin(int(y),int(m)))
    except: pass
 
@dp.callback_query(F.data.startswith("aday_"))
async def aday_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[5:]; uid=cb.from_user.id; st=get_st(uid); step=st.get("step","")
    today=date.today(); is_past=datetime.strptime(ds,"%Y-%m-%d").date()<today
    bd=db_get("blocked_dates",[])
 
    if step=="adm_open_day_pick":
        mode=st.get("mode","open")
        if mode=="close":
            if ds not in bd: bd.append(ds); db_set("blocked_dates",bd)
            slots=db_get("slots",{})
            if ds in slots: del slots[ds]; db_set("slots",slots)
            clr_st(uid); await cb.answer(f"❌ День {ds} закрыт")
            await eoa(cb,f"📅 *{ds}* — день закрыт",kb=slots_day_admin(ds))
        else:
            slots=db_get("slots",{}); slots[ds]=ALL_SLOTS.copy(); db_set("slots",slots)
            if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
            clr_st(uid); await cb.answer(f"✅ День {ds} открыт")
            await eoa(cb,f"✅ День *{ds}* открыт — {len(ALL_SLOTS)} слотов",kb=slots_day_admin(ds))
        return
 
    if step=="adm_week_pick":
        start=datetime.strptime(ds,"%Y-%m-%d").date()
        slots=db_get("slots",{}); bd2=db_get("blocked_dates",[])
        for i in range(7):
            d2=start+timedelta(days=i); ds2=d2.strftime("%Y-%m-%d")
            slots[ds2]=ALL_SLOTS.copy()
            if ds2 in bd2: bd2.remove(ds2)
        db_set("slots",slots); db_set("blocked_dates",bd2); clr_st(uid)
        end_s=(start+timedelta(days=6)).strftime("%d.%m"); await cb.answer("✅ Неделя открыта")
        await eoa(cb,f"✅ Неделя с *{ds}* по *{end_s}* открыта.",
                  kb=cal_admin(start.year,start.month))
        return
 
    if step=="adm_block_week_pick":
        start=datetime.strptime(ds,"%Y-%m-%d").date()
        appts=db_get("appts",{})
        conflicts=[(start+timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)
                   if appts.get((start+timedelta(days=i)).strftime("%Y-%m-%d"))]
        if conflicts:
            set_st(uid,{"step":"adm_block_week_confirm","block_week_start":ds})
            ct="\n".join(f"  {d}: {len(appts[d])} записей" for d in conflicts)
            kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ ЗАБЛОКИРОВАТЬ НЕСМОТРЯ НА ЗАПИСИ",callback_data="adm_bw_yes")],
                [InlineKeyboardButton(text="❌ ОТМЕНА",callback_data="adm_back")],
            ])
            await cb.answer()
            await eoa(cb,f"⚠️ В этой неделе есть записи:\n{ct}\n\nВсё равно заблокировать?",kb=kb)
        else:
            bd2=db_get("blocked_dates",[])
            for i in range(7):
                ds2=(start+timedelta(days=i)).strftime("%Y-%m-%d")
                if ds2 not in bd2: bd2.append(ds2)
            db_set("blocked_dates",bd2); clr_st(uid)
            end_s=(start+timedelta(days=6)).strftime("%d.%m"); await cb.answer("❌ Неделя заблокирована")
            await eoa(cb,f"❌ Неделя с *{ds}* по *{end_s}* заблокирована.",
                      kb=cal_admin(start.year,start.month))
        return
 
    if step=="adm_move_new_date":
        st["move_new_ds"]=ds; st["step"]="adm_move_new_time"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"Новая дата: *{ds}*\nВведите новое время (`14:00`):")
        return
 
    if step in ("adm_book_date","adm_reg_from_paid"):
        st["book_ds"]=ds; st["step"]="adm_book_slot_pick"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"📅 *{ds}*\nВыберите слот для записи:",kb=slots_day_admin(ds))
        return
 
    if is_past:
        await cb.answer()
        await eoa(cb,f"📅 *{ds}* (прошедший день)",kb=slots_day_admin(ds))
        return
 
    await cb.answer()
    await eoa(cb,f"📅 *{ds}*\n🟢 свободно  🔵 запись  🟡 неподтверждённая  🔴 закрыто",
              kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_full_open_"))
async def adm_full_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[14:]
    slots=db_get("slots",{}); slots[ds]=ALL_SLOTS.copy(); db_set("slots",slots)
    bd=db_get("blocked_dates",[])
    if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
    cs=db_get("closed_slots",{})
    if ds in cs: cs[ds]=[]; db_set("closed_slots",cs)
    await cb.answer(f"✅ День {ds} полностью открыт")
    await eoa(cb,f"✅ День *{ds}* полностью открыт — {len(ALL_SLOTS)} слотов",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_full_close_"))
async def adm_full_close(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[15:]
    bd=db_get("blocked_dates",[])
    if ds not in bd: bd.append(ds); db_set("blocked_dates",bd)
    slots=db_get("slots",{})
    if ds in slots: del slots[ds]; db_set("slots",slots)
    await cb.answer(f"❌ День {ds} полностью закрыт")
    await eoa(cb,f"📅 *{ds}* — день полностью закрыт",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("aslot_blocked_"))
async def aslot_blocked_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[2]; tm=parts[3]
    uid=cb.from_user.id; st=get_st(uid)
    if st.get("manual_tg") and st.get("step")=="adm_book_slot_pick":
        st["book_tm"]=tm; st["step"]="adm_manual_plat"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"✅ @{st['manual_tg']} - *{ds}* в *{tm}*\n\nПлатформа для связи?",
                  kb=kb_platform("adm_back"))
        return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 ОТКРЫТЬ СЛОТ",     callback_data=f"adm_unblock_slot_{ds}_{tm}")],
        [InlineKeyboardButton(text="✏️ ЗАПИСАТЬ КЛИЕНТА", callback_data=f"adm_book_blocked_{ds}_{tm}")],
        [InlineKeyboardButton(text="↩️ НАЗАД",             callback_data=f"aday_{ds}")],
    ])
    await cb.answer()
    await eoa(cb,f"🔴 Слот {ds} в {tm} — закрыт. Что сделать?",kb=kb)
 
@dp.callback_query(F.data.startswith("adm_unblock_slot_"))
async def adm_unblock_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[3]; tm=parts[4]
    slots=db_get("slots",{}); cs=db_get("closed_slots",{}); bd=db_get("blocked_dates",[])
    if ds not in slots: slots[ds]=[]
    if tm not in slots[ds]: slots[ds].append(tm); slots[ds]=sorted(slots[ds])
    if ds in cs and tm in cs[ds]: cs[ds].remove(tm)
    if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
    db_set("slots",slots); db_set("closed_slots",cs)
    await cb.answer(f"🟢 Слот {tm} открыт")
    await eoa(cb,f"📅 *{ds}*\n🔴 закрыто  🟢 открыто",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_unblock_day_"))
async def adm_unblock_day(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[16:]; bd=db_get("blocked_dates",[])
    slots=db_get("slots",{})
    if ds in bd: bd.remove(ds); db_set("blocked_dates",bd)
    slots[ds]=ALL_SLOTS.copy(); db_set("slots",slots)
    await cb.answer(f"✅ День {ds} открыт")
    await eoa(cb,f"✅ День *{ds}* открыт — {len(ALL_SLOTS)} слотов",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("aslot_"))
async def aslot_open(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[1]; tm=parts[2]
    uid=cb.from_user.id; st=get_st(uid)
    appts=db_get("appts",{}); slots=db_get("slots",{})
    if st.get("step")=="adm_book_slot_pick":
        st["book_tm"]=tm; st["step"]="adm_manual_plat"; set_st(uid,st); await cb.answer()
        tg=st.get("manual_tg","")
        await eoa(cb,f"✅ @{tg} - *{ds}* в *{tm}*\n\nПлатформа для связи?",kb=kb_platform("adm_back"))
        return
    rec=next((r for r in appts.get(ds,[]) if r["time"]==tm),None)
    if rec:
        tl="💼 Платная" if rec.get("type")=="paid" else "🆓 Бесплатная"
        conf="✅ подтверждена" if rec.get("confirmed") else "🟡 не подтверждена"
        await cb.answer()
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ",    callback_data=f"adm_ok_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ ЗАПИСЬ",callback_data=f"adm_cncl_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",      callback_data=f"adm_mv_{rec['user_id']}_{ds}_{tm}")],
            [InlineKeyboardButton(text="↩️ НАЗАД",          callback_data=f"aday_{ds}")],
        ])
        await eoa(cb,
            f"🔵 *{ds}* в *{tm}*\n\n👤 {rec['name']} @{rec.get('username','')}\n"
            f"{tl} | ⏱ {rec.get('duration','—')}\n📱 {rec.get('platform','—')}\nСтатус: {conf}",kb=kb)
    else:
        in_s=tm in slots.get(ds,[]); cs=db_get("closed_slots",{}).get(ds,[])
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔴 ЗАКРЫТЬ СЛОТ" if in_s else "🟢 ОТКРЫТЬ СЛОТ",
                callback_data=f"adm_toggle_slot_{ds}_{tm}")],
            [InlineKeyboardButton(text="✏️ ЗАПИСАТЬ КЛИЕНТА",callback_data=f"adm_book_to_{ds}_{tm}")],
            [InlineKeyboardButton(text="↩️ НАЗАД",           callback_data=f"aday_{ds}")],
        ])
        await cb.answer()
        status="🟢 Свободен" if in_s and tm not in cs else "🔴 Закрыт"
        await eoa(cb,f"{status} - {ds} в {tm}",kb=kb)
 
@dp.callback_query(F.data.startswith("adm_toggle_slot_"))
async def adm_toggle_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[3]; tm=parts[4]
    slots=db_get("slots",{}); cs=db_get("closed_slots",{})
    if ds not in slots: slots[ds]=[]
    if ds not in cs: cs[ds]=[]
    if tm in slots[ds]:
        slots[ds].remove(tm)
        if tm not in cs[ds]: cs[ds].append(tm)
        await cb.answer(f"🔴 Слот {tm} закрыт")
    else:
        slots[ds].append(tm); slots[ds]=sorted(slots[ds])
        if tm in cs[ds]: cs[ds].remove(tm)
        await cb.answer(f"🟢 Слот {tm} открыт")
    db_set("slots",slots); db_set("closed_slots",cs)
    await eoa(cb,f"📅 *{ds}*",kb=slots_day_admin(ds))
 
@dp.callback_query(F.data.startswith("adm_book_to_"))
async def adm_book_to(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[3]; tm=parts[4]
    uid=cb.from_user.id; st=get_st(uid)
    if st.get("manual_tg"):
        st["book_ds"]=ds; st["book_tm"]=tm; st["step"]="adm_manual_plat"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"✅ @{st['manual_tg']} - *{ds}* в *{tm}*\n\nПлатформа?",kb=kb_platform("adm_back"))
    else:
        set_st(uid,{"step":"adm_manual_tg","book_ds":ds,"book_tm":tm}); await cb.answer()
        await eoa(cb,"Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_book_blocked_"))
async def adm_book_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); ds=parts[3]; tm=parts[4]
    uid=cb.from_user.id; st=get_st(uid)
    if st.get("manual_tg"):
        st["book_ds"]=ds; st["book_tm"]=tm; st["step"]="adm_manual_plat"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"✅ @{st['manual_tg']} - *{ds}* в *{tm}*\n\nПлатформа?",kb=kb_platform("adm_back"))
    else:
        set_st(uid,{"step":"adm_manual_tg","book_ds":ds,"book_tm":tm}); await cb.answer()
        await eoa(cb,"Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_add_slots_"))
async def adm_add_slots(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[14:]; set_st(cb.from_user.id,{"step":"adm_add_slots_to","adm_date":ds}); await cb.answer()
    await eoa(cb,f"Слоты для *{ds}* через запятую:\n`10:00, 11:00`")
 
@dp.callback_query(F.data.startswith("adm_book_slot_"))
async def adm_book_slot(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[14:]; uid=cb.from_user.id; st=get_st(uid)
    if st.get("manual_tg"):
        st["book_ds"]=ds; st["step"]="adm_book_slot_pick"; set_st(uid,st); await cb.answer()
        await eoa(cb,f"📅 *{ds}*\nВыберите слот:",kb=slots_day_admin(ds))
    else:
        set_st(uid,{"step":"adm_manual_tg","book_ds":ds}); await cb.answer()
        await eoa(cb,"Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("adm_add_session_"))
async def adm_add_session(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ds=cb.data[16:]; set_st(cb.from_user.id,{"step":"adm_session_name","session_ds":ds}); await cb.answer()
    await eoa(cb,f"Добавляю сессию за *{ds}*.\nВведите имя клиента:")
 
@dp.callback_query(F.data=="adm_open_day_btn")
async def adm_open_day_btn(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_open_day_pick","mode":"open"}); today=date.today(); await cb.answer()
    await eoa(cb,"Нажмите на день для открытия:",kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data=="adm_close_day_btn")
async def adm_close_day_btn(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_open_day_pick","mode":"close"}); today=date.today(); await cb.answer()
    await eoa(cb,"Нажмите на день для закрытия:",kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data.in_({"adm_open_week","adm_open_week_cal"}))
async def adm_open_week_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_week_pick"}); today=date.today(); await cb.answer()
    await eoa(cb,"Нажмите на любой день - с него откроется неделя (7 дней):",
              kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data.in_({"adm_block_week","adm_block_week_cal"}))
async def adm_block_week_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_block_week_pick"}); today=date.today(); await cb.answer()
    await eoa(cb,"Нажмите на любой день - с него заблокируется неделя (7 дней):",
              kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data=="adm_bw_yes")
async def adm_bw_yes(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uid=cb.from_user.id; st=get_st(uid); ds=st.get("block_week_start","")
    if not ds: return
    start=datetime.strptime(ds,"%Y-%m-%d").date(); bd=db_get("blocked_dates",[])
    for i in range(7):
        ds2=(start+timedelta(days=i)).strftime("%Y-%m-%d")
        if ds2 not in bd: bd.append(ds2)
    db_set("blocked_dates",bd); clr_st(uid)
    end_s=(start+timedelta(days=6)).strftime("%d.%m")
    await eoa(cb,f"❌ Неделя с *{ds}* по *{end_s}* заблокирована (записи сохранены).",
              kb=cal_admin(start.year,start.month))
 
# ═══════════════════════════════════════════════════
# АДМИН — МЕНЮ И ЗАПИСИ
# ═══════════════════════════════════════════════════
 
@dp.callback_query(F.data=="adm_book_menu")
async def adm_book_menu(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ЗАПИСАТЬ НОВОГО - БЕСПЛАТНАЯ",callback_data="adm_book_new_free")],
        [InlineKeyboardButton(text="✏️ ЗАПИСАТЬ НОВОГО - ПЛАТНАЯ",   callback_data="adm_book_new_paid")],
        [InlineKeyboardButton(text="✏️ ЗАПИСАТЬ ПОСТОЯННОГО",        callback_data="adm_book_reg")],
        [InlineKeyboardButton(text="↩️ НАЗАД",                        callback_data="adm_cal")],
    ])
    await cb.answer(); await eoa(cb,"Выберите тип записи:",kb=kb)
 
@dp.callback_query(F.data=="adm_book_new_free")
async def adm_book_new_free(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"forced_type":"free"}); await cb.answer()
    await eoa(cb,"Выберите клиента:",kb=get_clients_kb("free"))
 
@dp.callback_query(F.data=="adm_book_new_paid")
async def adm_book_new_paid(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"forced_type":"paid"}); await cb.answer()
    await eoa(cb,"Выберите клиента:",kb=get_clients_kb("paid"))
 
@dp.callback_query(F.data=="adm_book_reg")
async def adm_book_reg(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"forced_type":"paid"}); await cb.answer()
    await eoa(cb,"Выберите клиента:",kb=get_clients_kb("reg"))
 
@dp.callback_query(F.data.startswith("pick_client_"))
async def pick_client(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_",3); step=parts[2]; uname=parts[3]
    uid=cb.from_user.id; appts=db_get("appts",{})
    client_uid=0; client_name=uname
    ud=db_get("all_users_data",{})
    for info in ud.values():
        if info.get("username","").lower()==uname.lower():
            client_uid=info.get("uid",0); client_name=info.get("name",uname); break
    if not client_uid:
        for ds,recs in appts.items():
            for r in recs:
                if r.get("username","").lower()==uname.lower():
                    client_uid=r.get("user_id",0); client_name=r.get("name",uname); break
            if client_uid: break
    forced="free" if step=="free" else "paid"
    set_st(uid,{"step":"adm_book_date","manual_tg":uname,"manual_name":client_name,
                "manual_uid":client_uid,"forced_type":forced})
    today=date.today(); await cb.answer()
    await eoa(cb,f"✅ Клиент: *{client_name}* @{uname}\nВыберите дату:",
              kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data.startswith("manual_client_"))
async def manual_client(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    step=cb.data[14:]; forced="free" if step=="free" else "paid"
    set_st(cb.from_user.id,{"step":"adm_manual_tg","forced_type":forced}); await cb.answer()
    await eoa(cb,"Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data.startswith("search_client_"))
async def search_client(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    step=cb.data[14:]; forced="free" if step=="free" else "paid"
    set_st(cb.from_user.id,{"step":"adm_search_client","forced_type":forced}); await cb.answer()
    await eoa(cb,"Введите часть имени или username для поиска:")
 
@dp.callback_query(F.data.startswith("adm_reg_pick_"))
async def adm_reg_pick(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uname=cb.data[13:]; regs=db_get("regulars",[])
    rec=next((r for r in regs if r["username"]==uname),None)
    if not rec: await cb.answer("Не найден",show_alert=True); return
    set_st(cb.from_user.id,{"step":"adm_book_date","manual_tg":uname,
                             "manual_name":rec.get("name",""),"forced_type":"paid"})
    today=date.today(); await cb.answer()
    await eoa(cb,f"Записываю @{uname}. Выберите дату:",kb=cal_admin(today.year,today.month))
 
@dp.callback_query(F.data=="adm_back")
async def adm_back(cb: types.CallbackQuery):
    await cb.answer(); await eoa(cb,"🔐 *ПАНЕЛЬ АДМИНИСТРАТОРА*",kb=kb_admin())
 
@dp.callback_query(F.data=="adm_unconf")
async def adm_unconf(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts=db_get("appts",{}); today=date.today(); rows=[]
    for ds in sorted(appts.keys()):
        try: d=datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d<today: continue
        for r in appts[ds]:
            if not r.get("confirmed"):
                tl="💼" if r.get("type")=="paid" else "🆓"
                rows.append([InlineKeyboardButton(text=f"🟡 {ds} {r['time']} {tl} - {r['name']}",
                                                   callback_data=f"aslot_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_back")])
    if len(rows)==1: await eoa(cb,"Неподтверждённых нет.",kb=kb_admin()); return
    await eoa(cb,"🟡 *НЕПОДТВЕРЖДЁННЫЕ:*",kb=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data=="adm_past_free")
async def adm_past_free(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts=db_get("appts",{}); today=date.today(); week_ago=today-timedelta(days=7); rows=[]
    for ds in sorted(appts.keys(),reverse=True):
        try: d=datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d>today or d<week_ago: continue
        for r in appts[ds]:
            if r.get("type")!="free": continue
            s=r.get("status",""); ic="✅" if s=="проведена" else ("❌" if s=="не состоялась" else "⏳")
            rows.append([InlineKeyboardButton(text=f"{ic} {ds} {r['time']} - {r['name']}",
                                               callback_data=f"aslot_{ds}_{r['time']}")])
    rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_back")])
    if len(rows)==1: await eoa(cb,"Прошедших бесплатных за неделю нет.",kb=kb_admin()); return
    await eoa(cb,"📋 *ПРОШЕДШИЕ БЕСПЛАТНЫЕ (7 дней):*",kb=InlineKeyboardMarkup(inline_keyboard=rows))
 
@dp.callback_query(F.data=="adm_list")
async def adm_list(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts=db_get("appts",{}); today=date.today(); text="📋 *ПРЕДСТОЯЩИЕ ЗАПИСИ:*\n\n"; found=False
    for ds in sorted(appts.keys()):
        try: d=datetime.strptime(ds,"%Y-%m-%d").date()
        except: continue
        if d<today: continue
        for r in appts[ds]:
            tl="💼" if r.get("type")=="paid" else "🆓"; co="✅" if r.get("confirmed") else "🟡"
            text+=f"{co}{tl} *{ds}* {r['time']} ⏱{r.get('duration','—')}\n👤 {r['name']} @{r.get('username','')}\n📱 {r.get('platform','—')}\n\n"
            found=True
    await eoa(cb,text if found else "📭 Записей нет.")
 
@dp.callback_query(F.data=="adm_regulars")
async def adm_regulars(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    regs=db_get("regulars",[]); text="👥 *ПОСТОЯННЫЕ КЛИЕНТЫ:*\n\n"
    text+="\n".join(f"@{r['username']} - {r['name']} | {r.get('day','')} {r.get('time','')}" for r in regs) if regs else "Нет."
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ДОБАВИТЬ",callback_data="adm_reg_add")],
        [InlineKeyboardButton(text="🗑 УДАЛИТЬ",  callback_data="adm_reg_del")],
        [InlineKeyboardButton(text="↩️ НАЗАД",    callback_data="adm_back")],
    ])
    await eoa(cb,text,kb=kb)
 
@dp.callback_query(F.data=="adm_reg_add")
async def adm_reg_add(cb):
    set_st(cb.from_user.id,{"step":"adm_reg_username"}); await cb.answer()
    await eoa(cb,"Введите username клиента (без @):")
 
@dp.callback_query(F.data=="adm_reg_del")
async def adm_reg_del_btn(cb):
    set_st(cb.from_user.id,{"step":"adm_reg_del_name"}); await cb.answer()
    await eoa(cb,"Введите username для удаления (без @):")
 
@dp.callback_query(F.data.startswith("regday_"))
async def regday(cb: types.CallbackQuery):
    day=cb.data[7:]; uid=cb.from_user.id; st=get_st(uid)
    st["reg_day"]=day; st["step"]="adm_reg_time"; set_st(uid,st)
    await eoa(cb,f"День: *{day}*\nВведите время (`15:00`):")
 
@dp.callback_query(F.data=="adm_new_src")
async def adm_new_src(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lbl,callback_data=f"src_{code}")] for lbl,code in SOURCES
    ]+[[InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_back")]])
    await cb.answer(); await eoa(cb,"Откуда клиент?",kb=kb)
 
@dp.callback_query(F.data.startswith("src_"))
async def src_sel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    src=cb.data[4:]; set_st(cb.from_user.id,{"step":"adm_src_username","source":src}); await cb.answer()
    await eoa(cb,"Введите username клиента в Telegram (без @):")
 
@dp.callback_query(F.data=="adm_stats")
async def adm_stats(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    appts=db_get("appts",{}); logs=db_get("logs",[]); now=datetime.now()
    total=fc=pc=done=miss=0; srcs={}
    for ds,recs in appts.items():
        try: d=datetime.strptime(ds,"%Y-%m-%d")
        except: continue
        if d.month==now.month and d.year==now.year:
            for r in recs:
                total+=1
                if r.get("type")=="paid": pc+=1
                else: fc+=1
                if r.get("status")=="проведена": done+=1
                if r.get("status")=="не состоялась": miss+=1
                s=r.get("source","бот"); srcs[s]=srcs.get(s,0)+1
    guides=sum(1 for l in logs if l.get("a")=="got_guide"); users=len(db_get("users",[]))
    us=db_get("users_src",{}); sl={}
    for v in us.values(): sl[v]=sl.get(v,0)+1
    st="\n".join(f"  {k}: {v}" for k,v in srcs.items())
    sl2="\n".join(f"  {k}: {v}" for k,v in sl.items())
    await eoa(cb,
        f"📊 *СТАТИСТИКА {now.strftime('%B %Y')}:*\n\n"
        f"📅 Всего: {total}\n🆓 Бесплатных: {fc}\n💼 Платных: {pc}\n"
        f"✅ Проведено: {done}\n❌ Не состоялось: {miss}\n"
        f"📄 Гайдов: {guides}\n👥 Пользователей: {users}\n\n"
        f"*Источники записей:*\n{st or '  нет данных'}\n\n"
        f"*Откуда узнали:*\n{sl2 or '  нет данных'}")
 
@dp.callback_query(F.data=="adm_broadcast")
async def adm_broadcast(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_broadcast_text"}); await cb.answer()
    await eoa(cb,"Введите текст рассылки:")
 
@dp.callback_query(F.data=="adm_post")
async def adm_post(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_post_link"}); await cb.answer()
    await eoa(cb,"Вставьте ссылку на пост из канала:")
 
@dp.callback_query(F.data=="adm_excel")
async def adm_excel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    set_st(cb.from_user.id,{"step":"adm_excel_from"}); await cb.answer()
    await eoa(cb,"Дата *начала* периода *ГГГГ-ММ-ДД*:")
 
@dp.callback_query(F.data=="adm_reviews")
async def adm_reviews(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    reviews=db_get("reviews",[])
    if not reviews: await eoa(cb,"Отзывов пока нет."); return
    text="⭐️ *ОТЗЫВЫ:*\n\n"
    for r in reviews[-10:]: text+=f"👤 {r.get('name','—')} | {'⭐️'*r.get('stars',5)}\n{r.get('text','')}\n\n"
    await eoa(cb,text)
 
@dp.callback_query(F.data=="adm_blocked")
async def adm_blocked(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    bl=db_get("blocked",[])
    if not bl: await eoa(cb,"Заблокированных нет."); return
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔓 РАЗБЛОКИРОВАТЬ",callback_data="adm_unblock_ask")]])
    await eoa(cb,"🚫 *ЗАБЛОКИРОВАННЫЕ:*\n\n"+"\n".join(str(u) for u in bl),kb=kb)
 
@dp.callback_query(F.data=="adm_unblock_ask")
async def adm_unblock_ask(cb):
    set_st(cb.from_user.id,{"step":"adm_unblock"}); await cb.answer()
    await eoa(cb,"Введите ID для разблокировки:")
 
@dp.callback_query(F.data=="adm_logs")
async def adm_logs(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    logs=db_get("logs",[]); text="📊 *ПОСЛЕДНИЕ 20 ДЕЙСТВИЙ:*\n\n"
    for e in logs[-20:]: text+=f"🕐 {e['t']} @{e['u']}\n▶️ {e['a']}\n\n"
    await eoa(cb,text if logs else "Логов нет.")
 
@dp.callback_query(F.data=="adm_block_month")
async def adm_block_month_btn(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    now=date.today(); months_kb=[]
    for y in [now.year,now.year+1]:
        for m in range(1,13):
            if date(y,m,1)<now.replace(day=1): continue
            months_kb.append([InlineKeyboardButton(text=f"{MN[m-1]} {y}",callback_data=f"adm_bm_{y}_{m:02d}")])
    months_kb.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_back")])
    await cb.answer(); await eoa(cb,"Выберите месяц для блокировки:",kb=InlineKeyboardMarkup(inline_keyboard=months_kb))
 
@dp.callback_query(F.data.startswith("adm_bm_"))
async def adm_bm_sel(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    _,_,y,m=cb.data.split("_"); y=int(y); m=int(m); ms=f"{y}-{m:02d}"
    dn=calendar.monthrange(y,m)[1]; appts=db_get("appts",{})
    conf=[f"{y}-{m:02d}-{d:02d}" for d in range(1,dn+1) if appts.get(f"{y}-{m:02d}-{d:02d}")]
    if conf:
        set_st(cb.from_user.id,{"step":"adm_bm_confirm","block_month":ms})
        ct="\n".join(f"  {ds}: {len(appts[ds])} записей" for ds in conf)
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ ЗАБЛОКИРОВАТЬ НЕСМОТРЯ НА ЗАПИСИ",callback_data="adm_bm_yes")],
            [InlineKeyboardButton(text="❌ ОТМЕНА",callback_data="adm_back")],
        ])
        await eoa(cb,f"⚠️ В {ms} есть записи:\n{ct}\n\nВсё равно?",kb=kb)
    else:
        bd=db_get("blocked_dates",[])
        for d in range(1,dn+1):
            ds=f"{y}-{m:02d}-{d:02d}"
            if ds not in bd: bd.append(ds)
        db_set("blocked_dates",bd); await cb.answer(f"🚫 {ms} заблокирован")
        await eoa(cb,f"🚫 Месяц *{ms}* заблокирован.",kb=kb_admin())
 
@dp.callback_query(F.data=="adm_bm_yes")
async def adm_bm_yes(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    uid=cb.from_user.id; st=get_st(uid); ms=st.get("block_month","")
    if not ms: return
    y,m=int(ms.split("-")[0]),int(ms.split("-")[1]); dn=calendar.monthrange(y,m)[1]
    bd=db_get("blocked_dates",[])
    for d in range(1,dn+1):
        ds=f"{y}-{m:02d}-{d:02d}"
        if ds not in bd: bd.append(ds)
    db_set("blocked_dates",bd); clr_st(uid)
    await eoa(cb,f"🚫 Месяц *{ms}* заблокирован (записи сохранены).",kb=kb_admin())
 
@dp.callback_query(F.data.startswith("adm_mtype_"))
async def adm_mtype(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    ctype="paid" if "paid" in cb.data else "free"
    uid=cb.from_user.id; st=get_st(uid)
    ds=st.get("book_ds","?"); tm=st.get("book_tm","?"); name=st.get("manual_name","?")
    tg=st.get("manual_tg","?"); plat=st.get("platform","?"); dur=st.get("duration","—")
    forced=st.get("forced_type")
    if forced: ctype=forced
    tl="💼 Платная" if ctype=="paid" else "🆓 Бесплатная"
    client_uid=st.get("manual_uid",0)
    if not client_uid:
        ud=db_get("all_users_data",{})
        for info in ud.values():
            if info.get("username","").lower()==tg.lower(): client_uid=info.get("uid",0); break
        if not client_uid:
            for ds2,recs in db_get("appts",{}).items():
                for r in recs:
                    if r.get("username","").lower()==tg.lower() and r.get("user_id",0):
                        client_uid=r["user_id"]; break
                if client_uid: break
    appts=db_get("appts",{})
    if ds not in appts: appts[ds]=[]
    appts[ds].append({
        "user_id":client_uid,"name":name,"time":tm,"username":tg,
        "type":ctype,"platform":plat,"duration":dur,"desc":"Ручная запись",
        "source":"вручную","status":"","confirmed":True,
        "rem_client":False,"rem_admin":False,"session_asked":False,
        "cli_confirmed":False,"paid":False,"bank":"",
    })
    db_set("appts",appts); clr_st(uid)
    await eoa(cb,f"✅ Записан вручную!\n\n📅 {ds} в {tm}\n{tl}\n👤 {name} @{tg}\n📱 {plat}",kb=kb_admin())
    await notify_adm(f"✏️ *Ручная запись*\n📅 {ds} в {tm}\n{tl}\n👤 {name} @{tg}")
    if client_uid:
        link=PLATFORMS.get(plat,"")
        ck=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕНЕСТИ",  callback_data=f"cli_move_{ds}_{tm}")],
            [InlineKeyboardButton(text="❌ ОТМЕНИТЬ",   callback_data=f"cli_cancel_{ds}_{tm}")],
            [InlineKeyboardButton(text="📅 МОИ ЗАПИСИ", callback_data="my_appts")],
        ])
        try:
            await bot.send_message(client_uid,
                f"✅ Ваша запись подтверждена!\n\n📅 {ds} в {tm} МСК\n{tl} | ⏱ {dur}\n📱 {plat}\n"
                f"{'🔗 '+link if link else ''}\n\nЗа час до сессии вам придёт напоминание.",reply_markup=ck)
        except: pass
        if ctype=="paid" and dur!="—":
            price=PRICES.get(dur,5000)
            pay_kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 ОПЛАТА КАРТОЙ РФ / СБП",  callback_data=f"pay_ru_{client_uid}_{ds}_{tm}")],
                [InlineKeyboardButton(text="💳 ОПЛАТА ЗАРУБЕЖНОЙ КАРТОЙ",callback_data=f"pay_intl_{client_uid}_{ds}_{tm}")],
            ])
            try: await bot.send_message(client_uid,
                    f"💰 *Стоимость сессии: {price:,} руб.*\n\nВыберите способ оплаты:",
                    parse_mode="Markdown",reply_markup=pay_kb)
            except: pass
    else:
        try: me=await bot.get_me(); link2=f"https://t.me/{me.username}"
        except: link2="https://t.me/kasikov_bot"
        await notify_adm(f"⚠️ Клиент @{tg} не найден в боте.\nОтправьте ему ссылку:\n{link2}")
 
@dp.callback_query(F.data.startswith("ban_"))
async def ban_cb(cb: types.CallbackQuery):
    uid=int(cb.data[4:]); bl=db_get("blocked",[])
    if uid not in bl: bl.append(uid); db_set("blocked",bl)
    await eoa(cb,cb.message.text+"\n\n🚫 *Заблокирован*")
 
@dp.callback_query(F.data.startswith("skip_"))
async def skip_cb(cb: types.CallbackQuery):
    await eoa(cb,cb.message.text+"\n\n✅ *Оставлено*")
 
@dp.callback_query(F.data.startswith("stype_"))
async def stype_cb(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.username): return
    parts=cb.data.split("_"); uid=cb.from_user.id; st=get_st(uid)
    ds=st.get("session_ds","?"); name=st.get("session_name","?"); stype="_".join(parts[1:])
    tm={"free_first":("🆓 Бесплатная первичная","free"),
        "paid_first":("💼 Платная первичная","paid"),
        "paid_repeat":("💼 Платная повторная","paid")}
    label,ctype=tm.get(stype,(stype,"paid"))
    appts=db_get("appts",{})
    if ds not in appts: appts[ds]=[]
    appts[ds].append({"user_id":0,"name":name,"time":"00:00","username":"—","type":ctype,
                       "platform":"—","duration":"—","desc":"Ручная сессия","source":"вручную",
                       "status":"проведена","confirmed":True,"rem_client":True,"rem_admin":True,
                       "session_asked":True,"cli_confirmed":True,"paid":False,"bank":""})
    db_set("appts",appts); clr_st(uid)
    await eoa(cb,f"✅ Сессия добавлена.\n{ds} | {label} | {name}",kb=kb_admin())
 
# ═══════════════════════════════════════════════════
# HANDLE_TEXT И MAIN
# ═══════════════════════════════════════════════════
 
@dp.message()
async def handle_text(msg: types.Message):
    uid=msg.from_user.id; text=msg.text.strip() if msg.text else ""
    if is_blocked(uid): return
    if is_flood(uid): return
    reg_user(uid,msg.from_user.username,msg.from_user.first_name)
    if text.startswith("/"):
        clr_st(uid); await msg.answer("🏠 Главное меню:",reply_markup=kb_main()); return
    if is_admin(msg.from_user.username):
        chats=db_get("admin_chats",[])
        if uid not in chats: chats.append(uid); db_set("admin_chats",chats)
    if has_bad(text):
        cnt=viol(uid,"bad"); await msg.answer("Пожалуйста, давайте общаться без грубостей 🙏")
        if cnt>=5: await _auto_block(uid,f"мат ({cnt}x)"); return
        bk=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 ЗАБЛОКИРОВАТЬ",callback_data=f"ban_{uid}")],
            [InlineKeyboardButton(text="✅ ОСТАВИТЬ",     callback_data=f"skip_{uid}")],
        ])
        await notify_adm(f"⚠️ *Мат* ({cnt}/5)\n@{msg.from_user.username or '?'}(ID:{uid})\n{text[:200]}",kb=bk)
        return
    st=get_st(uid); step=st.get("step","")
 
    if step in ("desc","desc_retry"):
        name=msg.from_user.first_name or "Клиент"
        if len(text)<35:
            st["desc"]=text; set_st(uid,st)
            bk=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ ДОПОЛНИТЬ",         callback_data="desc_extend")],
                [InlineKeyboardButton(text="✅ ОСТАВИТЬ КАК ЕСТЬ", callback_data="desc_keep")],
            ])
            await msg.answer("Вижу, вы написали довольно мало. Либо не хотите писать и это ок, "
                             "либо случайно отправили - тогда можете дописать.",reply_markup=bk)
            return
        st["name"]=name; st["desc"]=text; st["step"]="platform"; set_st(uid,st)
        await msg.answer("Через какую платформу удобнее созвониться?",reply_markup=kb_platform()); return
 
    if step=="adm_fb_text":
        key=st.get("fb_key",""); pf=db_get("pending_feedback",{}); item=pf.get(key,{})
        cli_uid=item.get("uid",0)
        if cli_uid:
            try:
                cname=item.get("name","")
                await bot.send_message(cli_uid,
                    f"Здравствуйте, {cname}!\n\nКак вы после нашей встречи? Надеюсь, стало немного яснее.\n\n"
                    f"Как обещал - обратная связь и план работы.\n\n{text}")
                await asyncio.sleep(0.5)
                await bot.send_message(cli_uid,"Если захотите продолжить работу - я здесь. Вот условия:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="💼 ПЛАТНАЯ КОНСУЛЬТАЦИЯ",callback_data="paid_info")
                    ]]))
                await asyncio.sleep(0.5); await bot.send_message(cli_uid,T_FEEDBACK)
                item["sent"]=True; pf[key]=item; db_set("pending_feedback",pf)
                await msg.answer("✅ Отправлено клиенту.",reply_markup=kb_admin())
            except Exception as e: await msg.answer(f"❌ Ошибка: {e}")
        clr_st(uid); return
 
    if step=="adm_manual_tg":
        tg=text.lstrip("@"); st["manual_tg"]=tg
        if st.get("book_ds") and st.get("book_tm"):
            st["step"]="adm_manual_plat"; set_st(uid,st)
            await msg.answer("Платформа для связи?",reply_markup=kb_platform("adm_back"))
        else:
            st["step"]="adm_book_date"; set_st(uid,st)
            today=date.today()
            await msg.answer(f"Записываю @{tg}. Выберите дату:",reply_markup=cal_admin(today.year,today.month))
        return
 
    if step=="adm_move_new_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$",text):
            await msg.answer("❌ Формат: `14:00`",parse_mode="Markdown"); return
        appts=db_get("appts",{}); old_ds=st["move_ds"]; new_ds=st["move_new_ds"]
        old_tm=st["move_tm"]; target=st["move_uid"]; moved=False
        for rec in appts.get(old_ds,[]):
            if rec["user_id"]==target and rec["time"]==old_tm:
                old_dur=rec.get("duration","30 мин")
                appts[old_ds].remove(rec); _block_adj(old_ds,old_tm,old_dur,unblock=True)
                rec["time"]=text; rec["rem_client"]=False; rec["rem_admin"]=False
                if new_ds not in appts: appts[new_ds]=[]
                appts[new_ds].append(rec); _block_adj(new_ds,text,old_dur); moved=True
                try: await bot.send_message(target,f"📅 Ваша консультация перенесена:\n*{new_ds}* в *{text}* МСК",parse_mode="Markdown")
                except: pass
                break
        if moved: db_set("appts",appts)
        clr_st(uid); await msg.answer("✅ Перенесено." if moved else "❌ Не удалось.",reply_markup=kb_admin()); return
 
    if step=="adm_session_name":
        st["session_name"]=text; st["step"]="adm_session_type"; set_st(uid,st)
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆓 БЕСПЛАТНАЯ ПЕРВИЧНАЯ", callback_data="stype_free_first")],
            [InlineKeyboardButton(text="💼 ПЛАТНАЯ ПЕРВИЧНАЯ",    callback_data="stype_paid_first")],
            [InlineKeyboardButton(text="💼 ПЛАТНАЯ ПОВТОРНАЯ",    callback_data="stype_paid_repeat")],
        ])
        await msg.answer("Тип сессии?",reply_markup=kb); return
 
    if step=="adm_add_slots_to":
        times_raw=[t.strip() for t in text.split(",")]
        valid=[t for t in times_raw if re.match(r"^([01]\d|2[0-3]):[0-5]\d$",t)]
        if not valid: await msg.answer("❌ Формат: `10:00, 11:00`",parse_mode="Markdown"); return
        ds=st["adm_date"]; slots=db_get("slots",{})
        if ds not in slots: slots[ds]=[]
        for t in valid:
            if t not in slots[ds]: slots[ds].append(t)
        slots[ds]=sorted(slots[ds]); db_set("slots",slots); clr_st(uid)
        await msg.answer(f"✅ Добавлено на *{ds}*: {', '.join(valid)}",
                         parse_mode="Markdown",reply_markup=slots_day_admin(ds)); return
 
    if step=="adm_search_client":
        query=text.lower(); forced=st.get("forced_type","paid")
        ud=db_get("all_users_data",{}); appts=db_get("appts",{}); found={}
        for info in ud.values():
            u=info.get("username",""); n=info.get("name","").lower()
            if (query in n or query in u.lower()) and u not in found:
                found[u]={"name":info.get("name","—"),"username":u,"uid":info.get("uid",0)}
        for ds,recs in appts.items():
            for r in recs:
                u=r.get("username","")
                if (query in r.get("name","").lower() or query in u.lower()) and u not in found:
                    found[u]={"name":r.get("name","—"),"username":u,"uid":r.get("user_id",0)}
        if not found:
            await msg.answer("Не найдено.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ ВВЕСТИ ВРУЧНУЮ",callback_data=f"manual_client_{forced}")],
                [InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_cal")],
            ])); return
        rows=[[InlineKeyboardButton(
            text=f"👤 {u['name']} @{u['username']}" if u['name'] else f"👤 @{u['username']}",
            callback_data=f"pick_client_{forced}_{u['username']}")]
            for u in found.values()]
        rows.append([InlineKeyboardButton(text="✏️ ВВЕСТИ ВРУЧНУЮ",callback_data=f"manual_client_{forced}")])
        rows.append([InlineKeyboardButton(text="↩️ НАЗАД",callback_data="adm_cal")])
        await msg.answer(f"Найдено {len(found)}:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); return
 
    if step=="adm_reg_username":
        st["reg_username"]=text.lstrip("@"); st["step"]="adm_reg_name"; set_st(uid,st)
        await msg.answer("Введите имя клиента:"); return
    if step=="adm_reg_name":
        st["reg_name"]=text; st["step"]="adm_reg_day"; set_st(uid,st)
        days=["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=d,callback_data=f"regday_{d}")] for d in days])
        await msg.answer("День недели:",reply_markup=kb); return
    if step=="adm_reg_time":
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$",text):
            await msg.answer("❌ Формат: `15:00`",parse_mode="Markdown"); return
        regs=db_get("regulars",[]); regs.append({"username":st["reg_username"],"name":st["reg_name"],
                                                   "day":st["reg_day"],"time":text})
        db_set("regulars",regs); clr_st(uid); await msg.answer(f"✅ Добавлен @{st['reg_username']}.",reply_markup=kb_admin()); return
    if step=="adm_reg_del_name":
        u=text.lstrip("@"); regs=db_get("regulars",[])
        db_set("regulars",[r for r in regs if r["username"].lower()!=u.lower()])
        clr_st(uid); await msg.answer(f"✅ @{u} удалён.",reply_markup=kb_admin()); return
    if step=="adm_src_username":
        u=text.lstrip("@"); src=st.get("source","other"); inv=db_get("invited",[])
        inv.append({"username":u,"source":src,"at":datetime.now().isoformat(),"status":"приглашён"})
        db_set("invited",inv); clr_st(uid)
        try: me=await bot.get_me(); link=f"https://t.me/{me.username}"
        except: link="https://t.me/kasikov_bot"
        await msg.answer(f"✅ Клиент @{u} добавлен.\n\nОтправьте ему ссылку:\n{link}",reply_markup=kb_admin()); return
    if step=="adm_unblock":
        try:
            target=int(text); bl=db_get("blocked",[])
            if target in bl: bl.remove(target); db_set("blocked",bl); await msg.answer(f"✅ {target} разблокирован.",reply_markup=kb_admin())
            else: await msg.answer("Не найден.",reply_markup=kb_admin())
        except: await msg.answer("❌ Введите числовой ID.")
        clr_st(uid); return
    if step=="adm_broadcast_text":
        users=db_get("users",[]); sent=0
        for u in users:
            try: await bot.send_message(u,text); sent+=1; await asyncio.sleep(0.05)
            except: pass
        clr_st(uid); await msg.answer(f"✅ Разослано {sent} пользователям.",reply_markup=kb_admin()); return
    if step=="adm_post_link":
        users=db_get("users",[]); sent=0
        for u in users:
            try:
                await bot.send_message(u,f"На канале много полезного - вот свежий материал:\n{text}\n\nПодписывайтесь 👉 @kasikov_psy")
                sent+=1; await asyncio.sleep(0.05)
            except: pass
        clr_st(uid); await msg.answer(f"✅ Пост разослан {sent} пользователям.",reply_markup=kb_admin()); return
    if step=="adm_excel_from":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$",text):
            await msg.answer("❌ Формат: `2026-05-01`",parse_mode="Markdown"); return
        st["excel_from"]=text; st["step"]="adm_excel_to"; set_st(uid,st)
        await msg.answer("Дата *конца* периода *ГГГГ-ММ-ДД*:",parse_mode="Markdown"); return
    if step=="adm_excel_to":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$",text):
            await msg.answer("❌ Формат: `2026-05-31`",parse_mode="Markdown"); return
        d_from=st["excel_from"]; d_to=text; clr_st(uid)
        if not EXCEL_OK: await msg.answer("❌ openpyxl не установлен."); return
        buf=make_excel(d_from,d_to)
        if buf: await msg.answer_document(BufferedInputFile(buf.read(),filename=f"записи_{d_from}_{d_to}.xlsx"),caption=f"📊 Записи с {d_from} по {d_to}")
        else: await msg.answer("Записей за этот период нет.")
        return
 
    log_act(uid,msg.from_user.username,f"msg:{text[:30]}")
    await msg.answer("Выберите действие:",reply_markup=kb_main())
 
 
async def main():
    log.info("="*50)
    log.info("БОТ КАСИКОВА v9.0 — edit везде")
    log.info("/admin - панель | /stop - остановить")
    log.info("="*50)
    asyncio.create_task(bg_loop())
    await dp.start_polling(bot)
 
if __name__=="__main__":
    asyncio.run(main())
 

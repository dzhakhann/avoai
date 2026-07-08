"""
AVO Bank AI Assistant — Telegram Bot (v4 — Groq)
Мультиязычный ИИ-помощник только по вопросам AVO Bank (UZ / RU / EN)
Powered by Groq (llama-3.3-70b)
"""

import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Clients ─────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL = "llama-3.3-70b-versatile"

# ─── Conversation states ─────────────────────────────────────────────────────
APPEAL_TYPE, APPEAL_NAME, APPEAL_PHONE, APPEAL_EMAIL, APPEAL_TEXT, APPEAL_CONFIRM = range(6)

# ─── System prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Ты — официальный AI-ассистент AVO Bank. Отвечаешь только на вопросы, связанные с AVO Bank.

=== ЧТО ТАКОЕ AVO BANK ===
• AVO — сокращение от узбекского слова «havo» (воздух): невесомый, вездесущий, чистый
• Миссия: Раскрывать желание БОЛЬШЕГО у наших клиентов
• Ценности: Честно (выполняем обещания), Любопытно (ищем новые решения), Просто (делаем просто и понятно)
• Цель: улучшать жизнь клиентов каждый день
• AVO Bank — полностью цифровой банк (онлайн, без очередей)

=== СТРОГИЕ ПРАВИЛА ===

1. ТОЛЬКО вопросы об AVO Bank. На любой другой вопрос отвечай:
   RU: "Я могу отвечать только на вопросы, связанные с AVO Bank. Если у вас есть вопрос по нашему банку — с удовольствием помогу! 😊"
   UZ: "Men faqat AVO Bank bo'yicha savollarga javob bera olaman. Savolingiz bo'lsa — yordam berishdan mamnunman! 😊"

2. "Кто тебя создал?" / "Ким яратди?" → "Я создан командой AVO Bank для помощи клиентам. Задайте вопрос о банке! 😊"

3. Если вопрос об AVO Bank, но ответа нет → "По этому вопросу обратитесь в контакт-центр: 📞 +998 (78) 888-78-87"

4. Проблема в приложении (глюк, не работает, ошибка) → "Сделайте скриншот и отправьте в @avo_send_bot, затем позвоните 📞 +998 (78) 888-78-87"

5. Грубость/мат клиента → отвечай вежливо и помоги с проблемой, не реагируй на грубость.

6. ЯЗЫК — СТРОГО: определи язык сообщения клиента и отвечай ТОЛЬКО на этом языке.
   - Русский текст → отвечай ТОЛЬКО по-русски
   - O'zbek matni → faqat o'zbekcha javob ber
   - English text → answer ONLY in English
   - НИКОГДА не смешивай языки в одном ответе. Даже если информация хранится на другом языке — переводи ответ на язык клиента.

7. Ответы короткие, точные, дружелюбные. НИКОГДА не запрашивай номер карты, CVV, пароль, PIN.

8. ОФИС — сообщай адрес ТОЛЬКО если клиент явно просит. Сначала спроси зачем и предложи решить онлайн:
   "AVO Bank — цифровой банк, большинство вопросов решается в приложении или по телефону 📞 +998 (78) 888-78-87. Что за вопрос? Постараюсь помочь."
   Если всё же нужен офис — напомни взять паспорт.

9. МИБ справка (об отсутствии задолженности), КАТМ (очистка, заявки, кредитная история) → только колл-центр:
   "По вопросам справки для МИБ, очистки КАТМ или кредитной истории обратитесь в контакт-центр: 📞 +998 (78) 888-78-87"

=== КОНТАКТЫ AVO BANK ===
📞 Колл-центр: +998 (78) 888-78-87
📞 Доверие: +998 (78) 777-72-86
🤖 Проблемы с приложением: @avo_send_bot
🌐 Сайт: avobank.uz
📍 Офис (только по запросу): Ташкент, Яккасарайский р-н, ул. Шота Руставели, 12
🕐 Пн–Пт: 09:00–18:00 (обед 13:00–14:00) | ⚠️ Паспорт обязателен!

=== ВАЖНО: СЧЁТ ДО ВОСТРЕБОВАНИЯ (Текущий счёт) ===
Счёт до востребования — это ОТДЕЛЬНЫЙ банковский счёт, НЕ путать с AVO Wallet!

• Открывается автоматически при оформлении Микрозайма (МЗ)
• Деньги МЗ поступают именно на Счёт до востребования, а НЕ на карту напрямую
• После получения МЗ клиент переводит деньги со Счёта до востребования на свою карту
• При снятии/частичном снятии с Вклада — деньги также поступают на Счёт до востребования

ТАРИФЫ Счёта до востребования:
• Открытие и обслуживание: БЕСПЛАТНО
• Валюта: узбекские сумы | Процентная ставка: 0%
• Пополнение: БЕСПЛАТНО
• Переводы на карты и счета AVO Bank: БЕСПЛАТНО
• Переводы на карты других банков: 1% от суммы
• Максимум 1 счёт на клиента | Только онлайн

=== AVO PLATINUM (КЛ — кредитный лимит) ===
• Платёжная система: Mastercard | Лимит: до 100 000 000 сум
• Беспроцентный период: до 46 дней (льготный до 31 дня + платёжный 15 дней)
• Обслуживание карточного счёта: при тратах менее 180 000 сум/мес — бесплатно; от 180 000 сум — 27 000 сум/мес
• Виртуальная карта: БЕСПЛАТНО (выпуск + обслуживание)
• Пластиковая карта (вариант 1): выпуск БЕСПЛАТНО + 4 990 сум/мес обслуживание; закрытие 59 000 сум
• Пластиковая карта (вариант 2): выпуск 59 000 сум + обслуживание БЕСПЛАТНО; закрытие бесплатно
• Платёжный стикер: выпуск 79 000 сум, обслуживание и закрытие — бесплатно
• Пополнение в приложении/банкомате AVO: БЕСПЛАТНО
• Пополнение через PAYNET: 1,8%
• Пополнение через MasterCard/MoneySend: БЕСПЛАТНО
• Снятие наличных (собственные средства): 1% в любом банкомате
• Снятие/перевод КРЕДИТНЫХ средств: 8,9% + 29 000 сум
• Перевод собственных AVO→AVO: БЕСПЛАТНО | AVO Platinum→Humo/Uzcard других банков: 0,5%
• Переводы между картами других банков через AVO приложение: 1,5%
• Платежи в приложении (не переводы): БЕСПЛАТНО
• Лимиты: снятие наличных — 100 млн/операция; переводы — 200 млн/операция; 5 млрд/месяц
• Баланс в банкомате AVO: бесплатно | В банкоматах других банков: 11 000 сум
• Конвертация валют: 3% | 3D-Secure: бесплатно
• Штраф за просрочку: 1-й платёж — 1%/день; 2-й и далее — 5%/день
• Повышенная ставка при просрочке: 0,25%/день
• Минимальный платёж: 4% от суммы долга + проценты (первые 48 мес, мин 10 000 сум); 1/12 долга + проценты (последние 12 мес)
• Стоп-лист (блокировка по инициативе банка): 150 000 сум
• Диспут в МПС (оспаривание операции): 300 000 сум
• Рассмотрение спорной операции: бесплатно
• С 16 лет (до 18 — только дебетовая)

=== ПЛАТЁЖНЫЙ СТИКЕР AVO PLATINUM ===
• Что это: мини-карта с NFC-чипом, Mastercard — оплата в 1 касание (вместо карты)
• Выпуск: 79 000 сум | Обслуживание: БЕСПЛАТНО | Пополнение в приложении: БЕСПЛАТНО
• Получить в: картомат ТЦ Compass (Ташкент)

Как заказать стикер:
1. Приложение AVO → «Добавить новую карту» → «Выпустить новую карту»
2. Выбери вкладку «Стикер»
3. Оплати 79 000 сум
4. Забери стикер в картомате ТЦ Compass
5. Активируй в приложении

Как правильно приклеить:
• Клей на телефон, чехол, наушники или другой гаджет
• НЕ прятать под чехол (иначе не работает)
• На iPhone: НЕ клеить на логотип Apple — мешает NFC!
• Прикладывать стикер прямо к POS-терминалу

Стикер не работает — что делать:
1. Убедись, что стикер не закрыт чехлом/металлом
2. Приложи ровно и ближе к терминалу
3. Попробуй другой POS-терминал
4. Если всё равно не работает — позвони 📞 +998 (78) 888-78-87

Стикер потерялся:
1. Заблокируй в приложении AVO (немедленно!)
2. Сообщи в банк: 📞 +998 (78) 888-78-87
3. Проверь последние операции на счёте

=== БОНУСНАЯ ПРОГРАММА ===
• Пригласи друга: до 100 000 бонусов/мес
• Первая покупка: кешбэк 100% (до 100 000 сум)
• Каждая покупка кредитными: 1% бонус | 1 бонус = 1 сум
• Максимум в месяц: 500 000 бонусов | Срок действия: 6 месяцев
• Минимум для обмена: 150 000 бонусов

=== МИКРОЗАЙМ (МЗ) ===
• Сумма: от 1 000 000 до 100 000 000 сум
• Льготный период: 30 дней (0% если вернул полностью)
• Сроки: 3, 6, 9, 12, 18, 24, 36 месяцев | Рассмотрение: 1–3 минуты
• Документы: только паспорт/ID-карта | С 18 лет, граждане Узбекистана | Залог не нужен
• Ставка (3–12 мес): 34,9–44,9% годовых | (18–36 мес): 39,9–49,9% годовых
• Услуга «Для своих» (необязательная): 60 дней без штрафов
  - Стоимость: 10% (3–12 мес) или 5% (18–36 мес) от суммы МЗ
  - Штраф с услугой: 0% до 60 дней → 6,85%/день с 61-го дня
  - Штраф без услуги: 4,35%/день с 1-го дня
• Досрочное погашение: в любой день
• ВАЖНО: Деньги МЗ поступают на Счёт до востребования. Оттуда переводи на карту AVO (бесплатно) или на карты других банков (1%)

=== AVO ВКЛАД НА 12 МЕСЯЦЕВ ===
• Срок: 12 месяцев | Валюта: сумы | Открытие: бесплатно
• Ставка: 21,3% годовых (от 100 000 сум) | 0,01% (менее 100 000 сум)
• Доходность с капитализацией: до 23,5% годовых
• Пополнение: разрешено (от 1 000 сум) | Частичное снятие: разрешено
• Снятие → на Счёт до востребования (бесплатно) или на карту AVO Platinum
• Досрочное закрытие: разрешено (начисленные % сохраняются)
• Максимум: 20 вкладов | Гарантия государства: до 200 млн сум
• Выплата %: ежемесячно на вклад (капитализация)

=== СРОЧНЫЙ ВКЛАД (6 МЕСЯЦЕВ) ===
• Срок: 6 месяцев | Валюта: сумы | Открытие: бесплатно
• Ставка: 22,52% годовых (от 100 000 сум) | 0,01% (менее 100 000 сум)
• Пополнение: разрешено (от 1 000 сум)
• Частичное снятие: разрешено → деньги поступают на Счёт до востребования
• Досрочное закрытие: разрешено (начисленные проценты сохраняются!)
• Автопролонгация: нет (по истечении срока нужно переоткрыть)
• Не более 5 вкладов в день / 50 вкладов в месяц

=== UZCARD VIRTUAL KARTA ===
• Выпуск: бесплатно, мгновенно | Обслуживание: бесплатно
• Перевод AVO UZCARD → Humo/Uzcard других банков: 1%
• Перевод между картами AVO: бесплатно
• Лимиты: 200 млн/операция; 5 млрд/месяц

=== AVO WALLET (электронный кошелёк) ===
AVO Wallet — это ЭЛЕКТРОННЫЙ КОШЕЛЁК внутри приложения AVO. Это НЕ то же самое, что Счёт до востребования!

• Открытие и обслуживание: БЕСПЛАТНО | Максимум: 1 кошелёк на клиента
• Условие открытия: нет просроченных долгов и ограничений от банка/МИБ
• Пополнение: БЕСПЛАТНО
• Переводы на счета, карты и кошельки AVO Bank: БЕСПЛАТНО
• Переводы на кошельки других банков (участники СМП): 0,25%
• Переводы на карты других банков: 1%
• Лимиты: 200 млн/операция; 5 млрд/месяц

Как открыть AVO Wallet:
1. Войди в приложение AVO
2. "Mahsulotlar / Продукты" → "AVO Wallet"
3. Нажми "Hisob ochish / Открыть счёт" и дожди активации

Как пополнить AVO Wallet:
1. "Mahsulotlar" → "Hisoblar / Счета"
2. Выбери AVO Wallet → "To'ldirish / Пополнить"
3. Выбери источник → введи сумму → "O'tkazish"

Как оплатить долг через AVO Wallet:
• КЛ (кредитный лимит): переведи с AVO Wallet на карту AVO Platinum
• МЗ: при оплате выбери AVO Wallet как источник
• Просроченный долг: после пополнения Wallet деньги спишутся автоматически

=== КАРТЫ ДРУГИХ БАНКОВ В AVO ===
• Снятие наличных в банкоматах AVO с карты другого банка: 1%
• Проверка баланса карты другого банка: бесплатно
• Лимит пополнения карточного счёта в банкомате AVO: 1 000 000 сум/операция; 50 млн/месяц

=== ВОПРОС-ОТВЕТ ===
• Регистрация: только номер +998, документы не нужны
• Идентификация: паспорт/ID-карта нужен для кредитной карты (AVO Platinum)
• МЗ на карту напрямую? НЕТ — деньги поступают на Счёт до востребования, откуда переводятся на карту AVO (бесплатно) или другой банк (1%)
• Досрочное погашение МЗ: в любой день, в любое время
• Карта заблокирована: разблокировать в приложении или позвонить 📞 +998 (78) 888-78-87
• SMS-код не приходит: подождать 60 сек, запросить повторно; если нет — 📞 888-78-87
• МЗ vs КЛ: МЗ (Микрозайм) — разовая сумма, возвращаешь по графику; КЛ (кредитный лимит) — возобновляемый, вернул — снова доступен
• Иностранцы: могут зарегистрироваться с номером +998, привязать Uzcard/Humo
• Операционный день: 09:00–16:00 (операции по кредитованию и переводам)
• Вклад защищён государством до 200 000 000 сум (200 млн)
• MIB справка (об отсутствии долгов) / КАТМ (кредитная история) → только колл-центр 📞 888-78-87
• Проблема в приложении: сделай скриншот → @avo_send_bot → затем 📞 888-78-87
"""

# ─── Per-user history ─────────────────────────────────────────────────────────
user_histories: dict[int, list[dict]] = {}
MAX_HISTORY = 16


def get_history(user_id: int) -> list[dict]:
    return user_histories.get(user_id, [])


async def ask_groq(user_id: int, user_text: str) -> str:
    history = get_history(user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": user_text}
    ]

    response = groq_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=800,
        temperature=0.7,
    )
    reply = response.choices[0].message.content

    history = history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": reply},
    ]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    user_histories[user_id] = history

    return reply


# ─── Keyboards ────────────────────────────────────────────────────────────────
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["❓ Savollar / Вопросы", "📋 Murojaat / Обращение"],
        ["📞 Kontakt / Контакт", "🔄 Yangi suhbat / Новый диалог"],
    ],
    resize_keyboard=True,
)
CANCEL_KB = ReplyKeyboardMarkup(
    [["❌ Bekor qilish / Отмена"]], resize_keyboard=True, one_time_keyboard=True
)
APPEAL_TYPE_KB = ReplyKeyboardMarkup(
    [
        ["👤 Jismoniy shaxs / Физическое лицо"],
        ["🏢 Yuridik shaxs / Юридическое лицо"],
        ["❌ Bekor qilish / Отмена"],
    ],
    resize_keyboard=True, one_time_keyboard=True,
)

WELCOME_TEXT = (
    "🏦 <b>AVO Bank AI Assistenti</b>\n\n"
    "Assalomu alaykum! Men AVO Bank rasmiy AI-assistentiman.\n"
    "AVO Bank mahsulotlari va xizmatlari bo'yicha savollaringizga javob beraman.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "👋 <b>Здравствуйте!</b> Я официальный AI-ассистент AVO Bank.\n"
    "Отвечаю только на вопросы о продуктах и услугах банка.\n\n"
    "📌 <b>Savolingizni yozing / Задайте вопрос</b> ⬇️\n\n"
    "📞 <b>+998 (78) 888-78-87</b>\n"
    "🌐 avobank.uz"
)

# ─── Handlers ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_html(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "🤖 <b>AVO Bank AI Assistant</b>\n\n"
        "Karta (КЛ), mikrozaym (МЗ), vklad, UZCARD bo'yicha savol bering.\n\n"
        "📞 <b>+998 (78) 888-78-87</b>\n🌐 avobank.uz\n\n"
        "/start — Yangidan\n/appeal — Murojaat\n/clear — Tarixni tozalash",
        reply_markup=MAIN_KEYBOARD,
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "✅ Tarix tozalandi / История очищена.", reply_markup=MAIN_KEYBOARD
    )


async def contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "📞 <b>Kontakt / Контакт</b>\n\n"
        "☎️ <b>+998 (78) 888-78-87</b>\n"
        "☎️ Ishonch: <b>+998 (78) 777-72-86</b>\n"
        "🤖 Ilova muammolari: <b>@avo_send_bot</b>\n"
        "🌐 <b>avobank.uz</b>\n"
        "📍 Toshkent, Yakkasaroy, Shota Rustaveli 12\n"
        "🕐 Du–Ju: 09:00–18:00",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text:
        return

    if "📞 Kontakt" in text:
        await contact_info(update, context)
        return
    if "🔄 Yangi" in text:
        user_histories.pop(user_id, None)
        await start(update, context)
        return
    if "📋 Murojaat" in text:
        await appeal_start(update, context)
        return
    if "❓ Savollar" in text:
        await update.message.reply_text(
            "Savolingizni yozing! 😊\nНапишите вопрос! 😊"
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await ask_groq(user_id, text)
        await update.message.reply_text(reply, reply_markup=MAIN_KEYBOARD)
    except Exception as e:
        logger.error("Groq error user %s: %s", user_id, e)
        await update.message.reply_text(
            f"⚠️ Xatolik: {str(e)[:200]}\n📞 +998 (78) 888-78-87"
        )


# ─── APPEAL ───────────────────────────────────────────────────────────────────
def is_cancel(text: str) -> bool:
    return any(w in text for w in ["❌", "Отмена", "Bekor"])


async def appeal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_html(
        "📋 <b>Murojaat / Обращение</b>\n\nTurini tanlang / Выберите тип:",
        reply_markup=APPEAL_TYPE_KB,
    )
    return APPEAL_TYPE


async def appeal_get_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    context.user_data["type"] = "Физическое лицо" if "Jismoniy" in update.message.text or "Физическое" in update.message.text else "Юридическое лицо"
    await update.message.reply_text("✍️ FIO / ФИО:", reply_markup=CANCEL_KB)
    return APPEAL_NAME


async def appeal_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    context.user_data["name"] = update.message.text
    await update.message.reply_text("📱 Telefon (+998 XX XXX XX XX):", reply_markup=CANCEL_KB)
    return APPEAL_PHONE


async def appeal_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("📧 Email:", reply_markup=CANCEL_KB)
    return APPEAL_EMAIL


async def appeal_get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    context.user_data["email"] = update.message.text
    await update.message.reply_text("💬 Murojaat mazmuni / Суть обращения:", reply_markup=CANCEL_KB)
    return APPEAL_TEXT


async def appeal_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    context.user_data["text"] = update.message.text
    d = context.user_data
    confirm_kb = ReplyKeyboardMarkup(
        [["✅ Yuborish / Отправить", "❌ Bekor / Отмена"]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await update.message.reply_html(
        f"📋 <b>Tekshiring / Проверьте:</b>\n\n"
        f"• Tur: {d.get('type')}\n• FIO: {d.get('name')}\n"
        f"• Tel: {d.get('phone')}\n• Email: {d.get('email')}\n"
        f"• Mazmun:\n{d.get('text')}\n\n✅ Yuborasizmi?",
        reply_markup=confirm_kb,
    )
    return APPEAL_CONFIRM


async def appeal_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_cancel(update.message.text): return await appeal_cancel(update, context)
    d = context.user_data
    user = update.effective_user
    log = (
        f"\n{'='*50}\n🆕 YANGI MUROJAAT\n"
        f"TG: @{user.username or 'N/A'} (ID: {user.id})\n"
        f"Tur: {d.get('type')} | FIO: {d.get('name')}\n"
        f"Tel: {d.get('phone')} | Email: {d.get('email')}\n"
        f"Mazmun: {d.get('text')}\n{'='*50}"
    )
    logger.info(log)
    admin_id = os.environ.get("ADMIN_CHAT_ID")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=log)
        except Exception as e:
            logger.error("Admin notify: %s", e)
    await update.message.reply_html(
        "✅ <b>Murojaatingiz qabul qilindi! / Обращение принято!</b>\n\n"
        "Tez orada bog'lanamiz / Свяжемся в ближайшее время.\n\n"
        "📞 <b>+998 (78) 888-78-87</b>",
        reply_markup=MAIN_KEYBOARD,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def appeal_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi / Отменено.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


# ─── Keep-alive HTTP server ───────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AVO Bank Bot is running!")

    def log_message(self, format, *args):
        pass  # отключаем лишние логи


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Keep-alive server listening on port {port}")
    server.serve_forever()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    appeal_conv = ConversationHandler(
        entry_points=[
            CommandHandler("appeal", appeal_start),
            MessageHandler(filters.Regex(r"📋"), appeal_start),
        ],
        states={
            APPEAL_TYPE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_get_type)],
            APPEAL_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_get_name)],
            APPEAL_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_get_phone)],
            APPEAL_EMAIL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_get_email)],
            APPEAL_TEXT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_get_text)],
            APPEAL_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, appeal_confirm)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(appeal_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.bot.set_my_commands([
        BotCommand("start", "Yangidan / Начать сначала"),
        BotCommand("appeal", "Murojaat / Обращение"),
        BotCommand("help", "Yordam / Помощь"),
        BotCommand("clear", "Tarixni tozalash"),
    ])

    # Запускаем HTTP сервер в фоне
    threading.Thread(target=run_health_server, daemon=True).start()

    logger.info("🚀 AVO Bank Bot v4 (Groq) ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

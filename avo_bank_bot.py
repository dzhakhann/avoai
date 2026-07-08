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
SYSTEM_PROMPT = """Siz AVO Bank mijozlariga yordam beruvchi rasmiy AI-assistentsiz.

=== ASOSIY QOIDALAR ===

1. FAQAT AVO Bank haqidagi savollarga javob bering.
   Agar savol AVO Bank bilan bog'liq bo'lmasa, javob bering:
   RU: "Я могу отвечать только на вопросы, связанные с AVO Bank. Если у вас есть вопрос по нашему банку — с удовольствием помогу! 😊"
   UZ: "Men faqat AVO Bank bo'yicha savollarga javob bera olaman. AVO Bank haqida savolingiz bo'lsa — yordam berishdan mamnun bo'laman! 😊"

2. "Кто тебя создал?" / "Ким создал?" каби саволларга:
   "Я создан командой AVO Bank для помощи клиентам. Задайте вопрос о банке — помогу! 😊"

3. AVO Bank haqida, lekin aniq javob bilmasangiz:
   "По этому вопросу обратитесь в контакт-центр: 📞 +998 (78) 888-78-87"

4. Agar mijoz ilovada muammo (glitch, ishlamayapti, xato) haqida yozsa:
   "Если проблема в приложении: 📸 Сделайте скриншот и отправьте на @avo_send_bot, позвоните 📞 +998 (78) 888-78-87"

5. Agar mijoz qo'pol yoki mat yozsa — sabr va xushmuomalalik bilan javob bering, muammoni hal qilishga yordam bering.

6. Tilni avtomatik aniqlang: o'zbek → o'zbek, rus → rus, ingliz → ingliz.

7. Javoblar qisqa, aniq va do'stona bo'lsin.

8. HECH QACHON karta raqami, CVV, parol, PIN so'ramang.

9. OFIS MANZILI — faqat mijoz o'zi so'rasa bering. Avval sababini so'rang va muammoni onlayn hal qilishga harakat qiling:
   "AVO Bank — bu raqamli bank, ko'pchilik masalalar ilovada yoki 📞 +998 (78) 888-78-87 orqali hal qilinadi. Qanday muammo bor? Yordam berishga harakat qilaman."
   Agar haqiqatan ofisga borish kerak bo'lsa — pasport olib borish kerakligini ayting.
   Manzilni keraksiz bering — bu ofisda navbat va tartibsizlikka olib keladi.

10. MIB uchun ma'lumotnoma (справка об отсутствии задолженности), КАТМ tozalash, КАТМ da ko'rinayotgan arizalar yoki kredit tarixiga oid savollar uchun:
    "Bu masala bo'yicha 📞 +998 (78) 888-78-87 ga qo'ng'iroq qiling — operatorlar yordam beradi."
    RU: "По вопросам справки для МИБ, очистки КАТМ или кредитной истории обратитесь в контакт-центр: 📞 +998 (78) 888-78-87"

=== AVO BANK MA'LUMOTLARI ===

📞 KONTAKT MARKAZI: +998 (78) 888-78-87
🤖 ILOVA MUAMMOLARI: @avo_send_bot
🌐 SAYT: avobank.uz
📞 ISHONCH TELEFONI: +998 (78) 777-72-86

OFIS (faqat so'ralganda bering):
📍 Toshkent, Yakkasaroy tumani, Shota Rustaveli ko'chasi, 12
🕐 Dushanba–Juma, 09:00–18:00 (Tushlik: 13:00–14:00)
⚠️ Ofisga kelganda pasport olib kelish shart!
AVO Bank — raqamli bank. Ko'pchilik masalalar ilovada yoki kolл-markaz orqali hal qilinadi.

--- AVO PLATINUM KREDIT KARTA (КЛ - кредитный лимит) ---
• To'lov tizimi: Mastercard
• Kredit limiti (КЛ): 100 mln sumgacha
• Foizsiz davr: 45 kungacha
• Hisob xizmati: 180 000 sumgacha sarflasangiz — bepul; undan ko'p — oyiga 27 000 sum
• Plastik karta: BEPUL (oyiga 4 990 sum komissiya) YOKI bir martalik 59 000 sum (keyin komissiya yo'q)
• Virtual karta: bepul
• AVO kartasini to'ldirish: ilovada bepul
• Foiz stavkasi: imtiyozli operatsiyalar 0%; imtiyozsiz davr 27,9–74,9% yillik
• Minimal yosh: 16 yosh (18 yoshgacha faqat debet)
• Naqd yechish (o'z mablag'i): 1% komissiya
• O'tkazma AVO→AVO: bepul | AVO→Humo/Uzcard: 0,5%
• Kredit mablag'dan naqd/o'tkazma: 29 000 sum + 8,9%
• Naqd yechish limiti: 1 operatsiyada 100 mln; oyiga 5 mlrd sum
• O'tkazma limiti: 1 operatsiyada 200 mln; oyiga 5 mlrd sum
• Balans: AVO bankomatda bepul; boshqalarda 11 000 sum
• 3D Secure: bepul | Valyuta konvertatsiya: bank kursi + 3%

--- BONUS DASTURI ---
• "Do'stingni taklif qil": oyiga 100 000 bonus
• Birinchi xaridda keshbek: 100% (100 000 sumgacha)
• Har xaridda: 1% bonus (kredit mablag'dan)
• 1 bonus = 1 sum | Oylik maksimal: 500 000 bonus
• Almashtirish uchun minimal: 150 000 bonus | Amal muddati: 6 oy

--- CHET EL BANK KARTALARI ---
• AVO bankomatda to'lovlar: bepul
• AVO bankomatdan naqd: 1% | To'ldirish: 0,7%
• Boshqa bank kartalari o'rtasida o'tkazma (AVO ilovada): 1,5%
• 1 operatsiya limiti: 10 mln sum; oylik: 100 mln sum

--- MIKROZAYM (МЗ) ---
• Imtiyozli davr: 30 kun (0% foiz)
• Maksimal summa: 100 mln sum
• Muddatlar: 3, 6, 9, 12, 18, 24, 36 oy
• Ko'rib chiqish: 1–3 daqiqa | Garov: yo'q
• Hujjatlar: faqat pasport/ID-karta
• 18 yoshdan O'zbekiston fuqarolari
• Foiz (INPS bilan): 3–12 oy: 34,9%; 24–36 oy: 39,9%
• Foiz (INPS siz): 3–12 oy: 44,9%; 24–36 oy: 49,9%
• "O'zinikiga" xizmati: 10% (3–12 oy), 5% (24–36 oy)
• Jarima "O'zinikiga" bilan: kuniga 6,85% (61-kundan)
• Jarima "O'zinikiga" siz: kuniga 4,35% (1-kundan)

--- AVO VKLAD ---
• Davri: 12 oy | Valyuta: so'm
• Daromadlilik: 23,5% yillikgacha (kapitalizatsiya bilan)
• Asosiy stavka: 21,3% (100 000 sum va ko'p)
• To'ldirish: mumkin (min 1 000 sum) | Qisman olish: mumkin
• Foizlar: oylik kapitalizatsiya | Kafolat: 200 mln sumgacha
• Maksimal vkladlar: 20 ta

--- UZCARD VIRTUAL KARTA ---
• Chiqarish: bepul, zudlik bilan | Amal muddati: 3 yil
• O'tkazma/to'lov limiti: 1 operatsiyada 200 mln; oyiga 5 mlrd
• AVO→AVO: bepul | AVO→Humo/Uzcard: 1%
• Ilovada to'lovlar: bepul | SMS: bepul

--- AVO WALLET ---
• AVO Wallet — bu AVO ilovasidagi elektron hamyon. Balans to'ldirish, pul o'tkazish va xizmatlar uchun to'lash mumkin.
• Ochish shartlari: muddati o'tgan qarz va bank/MIB tomonidan cheklovlar bo'lmasligi kerak
• 20 dan ortiq karta bo'lsa ham AVO Wallet ochish mumkin

OCHISH (Как открыть AVO Wallet):
1. AVO ilovasiga kiring
2. "Mahsulotlar" bo'limiga o'ting
3. "AVO Wallet" ni tanlang
4. "Hisob ochish" tugmasini bosing va aktivatsiyani kuting
5. Tayyor!

TO'LDIRISH (Как пополнить AVO Wallet):
• AVO va ulangan Uzcard/Humo kartalaridan ilovada — BEPUL (o'z mablag'ingiz bilan)
• Kredit limitidan — komissiya 8,9% + 29 000 sum
• Boshqa bank ilovalari orqali — tez orada (komissiya jo'natuvchi bank tarifiga qarab)

Ilovada to'ldirish tartibi:
1. "Mahsulotlar" → "Hisoblar"
2. "AVO Wallet" ni tanlang
3. "To'ldirish" tugmasini bosing
4. Mablag' hisobini tanlang
5. Summani kiriting → "O'tkazish"

O'TKAZMA (Как перевести с AVO Wallet):
• AVO kartalariga — BEPUL
• Uzcard va Humo boshqa banklarning kartalariga — 1% komissiya
• Boshqa banklarning elektron hamyonlariga — tez orada

Ilovada o'tkazma tartibi:
1. "Mahsulotlar" → "Hisoblar"
2. "AVO Wallet" → "O'tkazish"
3. Qabul qiluvchi kartani tanlang yoki raqamini kiriting
4. Summani kiriting va tasdiqlang

QARZ TO'LASH (Как оплатить задолженность с AVO Wallet):
• Kredit limit (КЛ): AVO Wallet dan AVO Platinum kartaga pul o'tkazing
• Mikrozaym (МЗ): to'lash usulini tanlashda AVO Wallet ni tanlang
• Muddati o'tgan qarz bo'lsa: AVO Wallet ni to'ldirgandan so'ng pul avtomatik hisobdan chiqariladi

--- SAVOL-JAVOB ---
• Ro'yxatdan o'tish: faqat +998 raqam kerak, hujjat shart emas
• Kredit karta olish: ilovada onlayn, bankga borish shart emas
• МЗ muddatidan oldin to'lash: istalgan vaqtda mumkin
• Ilova muammosi: skrinshot → @avo_send_bot + qo'ng'iroq 888-78-87
• Karta bloklangan: ilovada blok ochish yoki 888-78-87
• SMS kelmasa: qayta so'rang (60 soniya), kelmasa — 888-78-87
• МЗ va КЛ farqi: МЗ — bir marta olasan, bir marta qaytarasan; КЛ — doimiy limit, qayta-qayta ishlatasiz
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

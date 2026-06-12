import os
import logging
from collections import defaultdict, deque

from anthropic import AsyncAnthropic
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY_HERE")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "YOUR_ADMIN_CHAT_ID_HERE")

MODEL = "claude-haiku-4-5-20251001"

FLAVORS = """
🍓 Клубника-арбуз
🥭 Манго-лёд
🍋 Лимон-лайм
"""

PAYMENT_INFO = """
💳 Kaspi: ТВОЙ_НОМЕР_KASPI
После оплаты пришли скриншот чека.
"""

DELIVERY_NOTE = "Доставка по твоему городу."

SYSTEM_PROMPT = (
    "Ты — продавец-консультант в Telegram-магазине вейпов (электронных сигарет). "
    "Общайся коротко, дружелюбно, на «ты», по-русски. Без воды.\n\n"
    "ТВОЯ ЗАДАЧА:\n"
    "1. Помочь клиенту выбрать вкус из списка ниже.\n"
    "2. Добиться, чтобы клиент прислал ОДНИМ сообщением: адрес + вкус + название/модель Waka.\n"
    "3. Когда все три есть — подтвердить заказ и выдать способ оплаты.\n\n"
    "АКТУАЛЬНЫЕ ВКУСЫ:\n" + FLAVORS + "\n"
    + DELIVERY_NOTE + "\n\n"
    "ПРАВИЛА:\n"
    "- Если клиент назвал не всё из трёх (адрес / вкус / модель) — вежливо попроси прислать всё ОДНИМ сообщением.\n"
    "- Продавай только совершеннолетним. Если есть сомнения — спроси, есть ли 18 лет.\n"
    "- Не выдумывай вкусы, которых нет в списке.\n"
    "- Когда заказ полный (адрес + вкус + модель названы), в самом КОНЦЕ ответа добавь отдельной строкой тег:\n"
    "[ORDER] адрес=...; вкус=...; Waka=...\n"
    "Клиенту этот тег не объясняй — просто добавь строкой в конце.\n"
    "- После полного заказа выдай реквизиты оплаты:\n" + PAYMENT_INFO
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=20))

WELCOME = (
    "Привет! 👋 Это магазин вейпов.\n\n"
    "Чтобы оформить заказ, пришли ОДНИМ сообщением:\n"
    "📍 адрес + 🍓 вкус + 🔋 модель Waka\n\n"
    "Не знаешь, что выбрать? Просто напиши — подскажу вкусы 😉"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_user.id].clear()
    await update.message.reply_text(WELCOME)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = histories[user_id]
    history.append({"role": "user", "content": update.message.text})

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=list(history),
        )
        reply = "".join(b.text for b in response.content if b.type == "text")
    except Exception as e:
        logger.error("Anthropic error: %s", e)
        await update.message.reply_text("Упс, не смог ответить. Напиши ещё раз через минутку 🙏")
        return

    history.append({"role": "assistant", "content": reply})

    if "[ORDER]" in reply and ADMIN_CHAT_ID:
        order_line = reply.split("[ORDER]", 1)[1].strip().splitlines()[0]
        user = update.effective_user
        who = f"@{user.username}" if user.username else f"id {user.id}"
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=f"🛒 НОВЫЙ ЗАКАЗ от {who}:\n{order_line}",
            )
        except Exception as e:
            logger.error("Не смог отправить заказ админу: %s", e)

    clean_reply = reply.split("[ORDER]", 1)[0].strip()
    await update.message.reply_text(clean_reply)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен на Railway.")
    app.run_polling()


if __name__ == "__main__":
    main()

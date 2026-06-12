import os
import logging
from collections import defaultdict, deque
from anthropic import AsyncAnthropic
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

MODEL = "claude-haiku-4-5-20251001"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
histories = defaultdict(lambda: deque(maxlen=20))

async def start(update, context):
    await update.message.reply_text("Привет! Это магазин вейпов. Напиши адрес + вкус + модель Waka")

async def handle_message(update, context):
    user_id = update.effective_user.id
    history = histories[user_id]
    history.append({"role": "user", "content": update.message.text})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        response = await client.messages.create(model=MODEL, max_tokens=300, system="Ты консультант вейпов. Попроси адрес+вкус+модель одним сообщением. Когда всё есть добавь [ORDER] адрес=...; вкус=...; Waka=...", messages=list(history))
        reply = "".join(b.text for b in response.content if b.type == "text")
        history.append({"role": "assistant", "content": reply})
        if "[ORDER]" in reply and ADMIN_CHAT_ID:
            await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text="ЗАКАЗ: " + reply.split("[ORDER]")[1])
        clean = reply.split("[ORDER]")[0].strip()
        await update.message.reply_text(clean)
    except Exception as e:
        logger.error(str(e))

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()

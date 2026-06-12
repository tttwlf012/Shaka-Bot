"""
Telegram-бот для продажи вейпов (Railway версия)
Все секреты берутся из переменных окружения для безопасности.
"""

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

# ==================== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY_HERE")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "YOUR_ADMIN_CHAT_ID_HERE")

MODEL = "claude-haiku-4-5-20251001"

# >>> АКТУАЛЬНЫЕ ВКУСЫ — обновляй этот список <<<
FLAVORS = """
🍓 Клубника-арбуз
🥭 Манго-лёд
🍋 Лимон-лайм
"""

# >>> СПОСОБ ОПЛАТЫ — вставь свои реквизиты <<<
PAYMENT_INFO = """
💳 Kaspi: 4400430271982917 Амир
После оплаты пришли скриншот чека.
"""

DELIVERY_NOTE = "Доставка по твоему городу."

# ==================== СИСТЕМНЫЙ ПРОМПТ ====================

SYSTEM_PROMPT = f"""Ты — продавец-консультант в Telegram-магазине вейпов (электронных сигарет).
Общайся коротко, дружелюбно, на «ты», по-русски. Без воды.

ТВОЯ ЗАДАЧА:
1. Помочь клиенту выбрать вкус из списка ниже.
2. Добиться, чтобы клиент прислал ОДНИМ сообщением: адрес + вкус + название/модель Waka.
3. Когда все три есть — подтвердить заказ и выдать способ оплаты.

АКТУАЛЬНЫЕ ВКУСЫ:
{FLAVORS}

{DELIVERY_NOTE}

ПРАВИЛА:
- Если клиент назвал не всё из трёх (адрес / вкус / модель) — вежливо попроси прислать всё ОДНИМ сообщением.
- Продавай только совершеннолетним. Если есть сомнения — спроси, есть ли 18 лет.
- Не выдумывай вкусы, которых нет в списке.
- Когда заказ полный (адрес + вкус + модель названы), в самом КОНЦЕ ответа добавь отдельной строкой тег:
[ORDER] адрес=...; вкус=...; Waka=...
Клиенту этот тег не объясняй — просто добавь строкой в конце.
- После полного заказа выдай ре

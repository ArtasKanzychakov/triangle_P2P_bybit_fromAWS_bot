# src/config.py
import os
from logging import getLogger

# Настройка логирования
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = getLogger(__name__)

# --- Загрузка переменных окружения ---

# Токен для Telegram бота, полученный от @BotFather
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    exit()

# Ключи API для Bybit
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    logger.error("Ключи API Bybit не найдены в переменных окружения!")
    exit()

# ID вашего чата в Telegram для админ-команд и уведомлений
ADMIN_CHAT_ID_STR = os.getenv('ADMIN_CHAT_ID')
if not ADMIN_CHAT_ID_STR:
    logger.error("ADMIN_CHAT_ID не найден в переменных окружения!")
    exit()

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR)
except ValueError:
    logger.error("ADMIN_CHAT_ID должен быть числом!")
    exit()

# URL для вебхука, предоставляемый Render.com
# Формат: bybit-arbitrage-bot.onrender.com
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL')

# Порт, который слушает Render.com
PORT = int(os.getenv('PORT', '8443'))

# URL для установки вебхука
WEBHOOK_URL = f"https://{RENDER_EXTERNAL_URL}/{TELEGRAM_BOT_TOKEN}" if RENDER_EXTERNAL_URL else ""

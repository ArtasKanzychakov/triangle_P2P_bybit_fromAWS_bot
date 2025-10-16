# src/main.py
from telegram.ext import Application, CommandHandler
from .config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, PORT, logger
from .bot_handlers import (
    start_command,
    status_command,
    set_amount_command,
    start_arb_command,
    stop_arb_command,
)

def main():
    """Основная функция для запуска бота."""
    logger.info("Запуск бота...")
    
    # --- Инициализация приложения ---
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Регистрация обработчиков команд ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("info", status_command)) # Дублируем /status на /info
    application.add_handler(CommandHandler("set_amount", set_amount_command))
    application.add_handler(CommandHandler("start_arb", start_arb_command))
    application.add_handler(CommandHandler("stop_arb", stop_arb_command))

    # --- Настройка и запуск Webhook для Render.com ---
    if WEBHOOK_URL:
        logger.info(f"Установка вебхука на URL: {WEBHOOK_URL}")
        # Запускаем встроенный веб-сервер
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN, # Путь должен совпадать с токеном
            webhook_url=WEBHOOK_URL
        )
        logger.info("Бот запущен в режиме Webhook.")
    else:
        # Режим для локальной разработки (без Render)
        logger.warning("RENDER_EXTERNAL_URL не найден. Запуск в режиме опроса (polling).")
        application.run_polling()
        logger.info("Бот запущен в режиме Polling.")

if __name__ == "__main__":
    main()

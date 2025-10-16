# src/bot_handlers.py
from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps

# ИЗМЕНЕНИЯ: Используем абсолютные импорты
from src.config import ADMIN_CHAT_ID, logger
from src.bybit_client import bybit_client
from src.arbitrage_finder import ArbitrageFinder

# Создаем единственный экземпляр ArbitrageFinder
finder = ArbitrageFinder(bybit_client)

# --- Декоратор для проверки прав администратора ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔️ У вас нет прав для выполнения этой команды.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- Команды бота ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение."""
    user_name = update.effective_user.first_name
    message = (
        f"👋 Привет, {user_name}!\n\n"
        "Я арбитражный бот для биржи Bybit. Готов к работе.\n\n"
        "**Доступные команды:**\n"
        "/start - Показать это сообщение\n"
        "/status - Показать текущий статус\n"
        "/set_amount <сумма> - Установить сумму для расчета (только админ)\n"
        "/start_arb - Запустить мониторинг (только админ)\n"
        "/stop_arb - Остановить мониторинг (только админ)"
    )
    await update.message.reply_text(message, parse_mode='Markdown')
    # При первом старте загружаем рыночные данные
    if not finder.all_pairs:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Загружаю данные о рынках Bybit, это может занять минуту...")
        if finder.load_market_data():
            await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Данные успешно загружены.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Не удалось загрузить данные. Проверьте логи.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущий статус бота."""
    job_name = "arbitrage_check_job"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    status = "✅ Запущен" if current_jobs else "⛔️ Остановлен"
    
    balance = bybit_client.get_usdt_balance()
    balance_str = f"{balance:.2f} USDT" if balance is not None else "Ошибка получения"

    message = (
        f"**📊 Текущий статус бота:**\n\n"
        f"**Статус цикла мониторинга:** {status}\n"
        f"**Отслеживается пар:** {len(finder.all_pairs)}\n"
        f"**Найдено арбитражных цепочек:** {len(finder.triangular_chains)}\n"
        f"**Сумма для расчета:** {finder.start_amount} USDT\n"
        f"**Баланс на Bybit:** {balance_str}"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

@admin_only
async def set_amount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает сумму для арбитражных расчетов."""
    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError
        finder.start_amount = amount
        await update.message.reply_text(f"✅ Сумма для расчетов установлена: {amount} USDT")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Неверный формат. Используйте: /set_amount 100")

@admin_only
async def start_arb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает циклический мониторинг арбитража."""
    job_name = "arbitrage_check_job"
    # Проверяем, не запущен ли уже мониторинг
    if context.job_queue.get_jobs_by_name(job_name):
        await update.message.reply_text("⚠️ Мониторинг уже запущен.")
        return

    # Запускаем задачу, которая будет выполняться каждые 5 секунд
    context.job_queue.run_repeating(
        finder.check_arbitrage_opportunities,
        interval=5,
        first=1,
        name=job_name
    )
    logger.info("Цикл мониторинга арбитража запущен.")
    await update.message.reply_text("✅ Цикл мониторинга арбитража запущен.")

@admin_only
async def stop_arb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Останавливает цикл мониторинга."""
    job_name = "arbitrage_check_job"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if not current_jobs:
        await update.message.reply_text("⚠️ Мониторинг не был запущен.")
        return

    for job in current_jobs:
        job.schedule_removal()
    
    logger.info("Цикл мониторинга арбитража остановлен.")
    await update.message.reply_text("⛔️ Цикл мониторинга арбитража остановлен.")

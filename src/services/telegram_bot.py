"""Telegram bot setup and lifecycle management.

Provides start_bot() and stop_bot() for the FastAPI lifespan,
and get_bot_app() / get_bot_loop() for other modules that need
to send messages through the bot.
"""
import asyncio
import threading

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from loguru import logger

from src.config import settings
from src.services.telegram_handlers import (
    cmd_start,
    cmd_status,
    cmd_plans,
    cmd_pause,
    cmd_resume,
    handle_inline_button,
    handle_message,
)


_bot_app: Application | None = None
_bot_loop: asyncio.AbstractEventLoop | None = None


def get_bot_app() -> Application | None:
    """Return the running bot Application (or None if not started)."""
    return _bot_app


def get_bot_loop() -> asyncio.AbstractEventLoop | None:
    """Return the event loop the bot is running on (or None if not started)."""
    return _bot_loop


def start_bot():
    """Start the Telegram bot in a background thread."""
    global _bot_app, _bot_loop

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping bot startup")
        return

    if not settings.enable_telegram_bot:
        logger.info("ENABLE_TELEGRAM_BOT=false, skipping bot startup (use this in local dev)")
        return

    logger.info("Starting Telegram bot...")

    _bot_app = Application.builder().token(settings.telegram_bot_token).build()
    _bot_app.add_handler(CommandHandler("start", cmd_start))
    _bot_app.add_handler(CommandHandler("status", cmd_status))
    _bot_app.add_handler(CommandHandler("plans", cmd_plans))
    _bot_app.add_handler(CommandHandler("pause", cmd_pause))
    _bot_app.add_handler(CommandHandler("resume", cmd_resume))
    _bot_app.add_handler(CallbackQueryHandler(handle_inline_button))
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    def _run():
        global _bot_loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _bot_loop = loop
        loop.run_until_complete(_bot_app.initialize())
        loop.run_until_complete(_bot_app.start())
        loop.run_until_complete(_bot_app.updater.start_polling(drop_pending_updates=True))
        logger.info("Telegram bot is running")
        loop.run_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


async def stop_bot():
    """Stop the Telegram bot."""
    global _bot_app, _bot_loop
    if _bot_app:
        await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()
        _bot_app = None
        _bot_loop = None

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Фиктивный веб-сервер чтобы Railway не отключал бота
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    def log_message(self, format, *args):
        pass  # отключаем лишние логи

def run_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

# Запускаем сервер в отдельном потоке
threading.Thread(target=run_server, daemon=True).start()
#!/usr/bin/env python3
"""
VapeShop Telegram Bot — обработчик заказов
Требования: pip install python-telegram-bot
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# НАСТРОЙКИ — ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!
# ============================================================
BOT_TOKEN = "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k"          # Получить у @BotFather
ADMIN_CHAT_ID = 8237417166              # Ваш Telegram ID (узнать у @userinfobot)
WEBAPP_URL = "https://musical-lamington-314527.netlify.app"   # URL где хостится index.html
# ============================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — открывает магазин"""
    keyboard = [[
        InlineKeyboardButton(
            "🛒 Открыть магазин",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    await update.message.reply_text(
        "🔥 *VAPE SHOP*\n\n"
        "Добро пожаловать! Нажмите кнопку ниже, чтобы открыть каталог товаров.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение данных из мини-приложения (заказ)"""
    try:
        data = json.loads(update.message.web_app_data.data)

        if data.get('type') != 'order':
            return

        name = data.get('name', 'Не указано')
        username = data.get('username', 'Не указан')
        comment = data.get('comment', '')
        total = data.get('total', 0)
        items = data.get('items', [])

        # Формируем список товаров
        items_text = '\n'.join([
            f"  • {item['name']} × {item['qty']} = {item['price'] * item['qty']:,}₽"
            for item in items
        ])

        # Сообщение пользователю
        user_msg = (
            f"✅ *Заказ принят!*\n\n"
            f"📦 *Ваш заказ:*\n{items_text}\n\n"
            f"💰 *Итого:* {total:,}₽\n\n"
            f"Мы свяжемся с вами в ближайшее время!"
        )
        await update.message.reply_text(user_msg, parse_mode="Markdown")

        # Уведомление администратору
        admin_msg = (
            f"🛒 *НОВЫЙ ЗАКАЗ!*\n\n"
            f"👤 *ФИО:* {name}\n"
            f"📱 *Telegram:* {username}\n"
            f"🆔 *User ID:* `{update.message.from_user.id}`\n\n"
            f"📦 *Товары:*\n{items_text}\n\n"
            f"💰 *Итого:* {total:,}₽"
        )
        if comment:
            admin_msg += f"\n\n💬 *Комментарий:* {comment}"

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown"
        )

        logger.info(f"New order from {username} ({update.message.from_user.id}), total: {total}₽")

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error processing order: {e}")
        await update.message.reply_text("❌ Ошибка при оформлении заказа. Попробуйте ещё раз.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Команды:*\n"
        "/start — открыть магазин\n"
        "/help — помощь",
        parse_mode="Markdown"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

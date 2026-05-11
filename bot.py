#!/usr/bin/env python3
"""
GuberVape Bot — полный сервер
- Хранит товары и категории в JSON файле
- Отдаёт их через API (все пользователи видят одинаковые товары)
- Принимает заказы и шлёт красивый чек
- Работает как веб-сервер на Railway
"""

import os
import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# НАСТРОЙКИ
# ============================================================
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k")
ADMIN_ID     = int(os.environ.get("ADMIN_CHAT_ID", "8237417166"))
WEBAPP_URL   = os.environ.get("WEBAPP_URL", "https://musical-lamington-314527.netlify.app")
PORT         = int(os.environ.get("PORT", 8080))
DATA_FILE    = "data.json"
# ============================================================

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ============================================================
# ХРАНИЛИЩЕ ДАННЫХ
# ============================================================
DEFAULT_DATA = {
    "categories": [
        {"key": "device", "name": "Устройства",  "emoji": "💨"},
        {"key": "liquid", "name": "Жидкости",    "emoji": "🌊"},
        {"key": "pod",    "name": "Поды",         "emoji": "🍓"},
        {"key": "acc",    "name": "Аксессуары",   "emoji": "⚡"},
    ],
    "products": [
        {"id":1,"emoji":"💨","name":"VUSE Alto Pro","desc":"Устройство с регулировкой мощности","category":"device","price":2990,"badge":"hit","inStock":True},
        {"id":2,"emoji":"🔥","name":"SMOK Nord 5","desc":"Мощный под-мод 80W","category":"device","price":3490,"badge":"new","inStock":True},
        {"id":3,"emoji":"🌊","name":"BLVK Salt Mango","desc":"Солевая жидкость 30мл 20мг","category":"liquid","price":850,"badge":"","inStock":True},
        {"id":4,"emoji":"❄️","name":"ICE Salt Mint","desc":"Ледяная мята 30мл 50мг","category":"liquid","price":790,"badge":"sale","inStock":True},
        {"id":5,"emoji":"🍓","name":"ELFBAR 600 Strawberry","desc":"Одноразовый под 600 затяжек","category":"pod","price":650,"badge":"","inStock":True},
        {"id":6,"emoji":"🍋","name":"GEEK BAR Lemon","desc":"Одноразовый под 575 затяжек","category":"pod","price":620,"badge":"","inStock":False},
        {"id":7,"emoji":"🧊","name":"Испаритель Mesh 0.2Ω","desc":"Для SMOK Nord 5, 5шт","category":"acc","price":490,"badge":"","inStock":True},
        {"id":8,"emoji":"⚡","name":"Зарядка USB-C 65W","desc":"Быстрая зарядка","category":"acc","price":390,"badge":"","inStock":True},
    ],
    "order_counter": 0
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# HTTP СЕРВЕР — API для мини-приложения
# ============================================================
class APIHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._json({"status": "GuberVape Bot is running 🔥"})
        elif path == "/api/data":
            data = load_data()
            self._json({"products": data["products"], "categories": data["categories"]})
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except Exception:
            self._json({"error": "Bad JSON"}, 400)
            return

        if path == "/api/products":
            self._save_products(payload)
        elif path == "/api/categories":
            self._save_categories(payload)
        else:
            self._json({"error": "Not found"}, 404)

    def _save_products(self, payload):
        data = load_data()
        data["products"] = payload.get("products", data["products"])
        save_data(data)
        self._json({"ok": True})

    def _save_categories(self, payload):
        data = load_data()
        data["categories"] = payload.get("categories", data["categories"])
        save_data(data)
        self._json({"ok": True})

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        pass  # отключаем лишние логи

# ============================================================
# TELEGRAM BOT
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    kb = [[InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        "🔥 *GuberVape — Vape Shop*\n\nНажмите кнопку чтобы открыть каталог 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получаем данные из мини-приложения"""
    try:
        raw = update.message.web_app_data.data
        data = json.loads(raw)
        dtype = data.get("type")

        if dtype == "order":
            await process_order(update, ctx, data)
        elif dtype == "save_products":
            await process_save_products(update, ctx, data)
        elif dtype == "save_categories":
            await process_save_categories(update, ctx, data)

    except Exception as e:
        log.error(f"WebApp data error: {e}")
        await update.message.reply_text("❌ Ошибка обработки. Попробуйте снова.")

async def process_order(update, ctx, data):
    """Обработка заказа — красивый чек"""
    db = load_data()
    db["order_counter"] = db.get("order_counter", 0) + 1
    order_num = db["order_counter"]
    save_data(db)

    name     = data.get("name", "—")
    username = data.get("username", "—")
    comment  = data.get("comment", "")
    items    = data.get("items", [])
    total    = data.get("total", 0)
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")
    user_id  = update.message.from_user.id

    # Строки товаров
    items_lines = "\n".join([
        f"  {i['emoji']} {i['name']}\n  └ {i['qty']} шт × {i['price']:,}₽ = {i['qty']*i['price']:,}₽"
        for i in items
    ])

    # ЧЕК для покупателя
    receipt = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *ЧЕК ЗАКАЗА #{order_num}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 {now}\n\n"
        f"📦 *Состав заказа:*\n{items_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n"
        f"📱 {username}\n"
    )
    if comment:
        receipt += f"💬 {comment}\n"
    receipt += "\nСпасибо за заказ! Мы свяжемся с вами скоро 🔥"

    # Отправляем чек покупателю
    await update.message.reply_text(receipt, parse_mode="Markdown")

    # Уведомление администратору
    admin_msg = (
        f"🚨 *НОВЫЙ ЗАКАЗ #{order_num}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now}\n\n"
        f"👤 *ФИО:* {name}\n"
        f"📱 *Telegram:* {username}\n"
        f"🆔 *User ID:* `{user_id}`\n\n"
        f"📦 *Товары:*\n{items_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    if comment:
        admin_msg += f"\n\n💬 *Комментарий:* {comment}"

    if ADMIN_ID:
        try:
            await ctx.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            log.error(f"Failed to send admin notification: {e}")

    log.info(f"Order #{order_num} from {username} ({user_id}), total: {total}₽")

async def process_save_products(update, ctx, data):
    """Сохранение товаров от админа"""
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return
    db = load_data()
    db["products"] = data.get("products", [])
    save_data(db)
    await update.message.reply_text("✅ Товары сохранены!")
    log.info(f"Products updated by admin {user_id}")

async def process_save_categories(update, ctx, data):
    """Сохранение категорий от админа"""
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    db = load_data()
    db["categories"] = data.get("categories", [])
    save_data(db)
    await update.message.reply_text("✅ Категории сохранены!")

# ============================================================
# ЗАПУСК
# ============================================================
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    log.info(f"HTTP API started on port {PORT}")
    server.serve_forever()

def main():
    # Запускаем HTTP сервер в отдельном потоке
    threading.Thread(target=run_http, daemon=True).start()

    # Запускаем Telegram бота
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info("GuberVape Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

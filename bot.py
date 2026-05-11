#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k")
ADMIN_ID = int(os.environ.get("ADMIN_CHAT_ID", "8237417166"))
PORT = int(os.environ.get("PORT", 8080))
DATA_FILE = "data.json"
# ================================

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ========== ДАННЫЕ ПО УМОЛЧАНИЮ ==========
DEFAULT_DATA = {
    "products": [
        {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro", "desc": "Устройство с регулировкой мощности",
         "category": "device", "price": 2990, "badge": "hit", "inStock": True},
        {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5", "desc": "Мощный под-мод 80W", "category": "device",
         "price": 3490, "badge": "new", "inStock": True},
        {"id": 3, "emoji": "🌊", "name": "BLVK Salt Mango", "desc": "Солевая жидкость 30мл 20мг", "category": "liquid",
         "price": 850, "badge": "", "inStock": True},
        {"id": 4, "emoji": "❄️", "name": "ICE Salt Mint", "desc": "Ледяная мята 30мл 50мг", "category": "liquid",
         "price": 790, "badge": "sale", "inStock": True},
        {"id": 5, "emoji": "🍓", "name": "ELFBAR 600 Strawberry", "desc": "Одноразовый под 600 затяжек",
         "category": "pod", "price": 650, "badge": "", "inStock": True},
        {"id": 6, "emoji": "🍋", "name": "GEEK BAR Lemon", "desc": "Одноразовый под 575 затяжек", "category": "pod",
         "price": 620, "badge": "", "inStock": False},
        {"id": 7, "emoji": "🧊", "name": "Испаритель Mesh 0.2Ω", "desc": "Для SMOK Nord 5, 5шт", "category": "acc",
         "price": 490, "badge": "", "inStock": True},
        {"id": 8, "emoji": "⚡", "name": "Зарядка USB-C 65W", "desc": "Быстрая зарядка", "category": "acc", "price": 390,
         "badge": "", "inStock": True},
    ],
    "categories": [
        {"key": "device", "name": "Устройства", "emoji": "💨"},
        {"key": "liquid", "name": "Жидкости", "emoji": "🌊"},
        {"key": "pod", "name": "Поды", "emoji": "🍓"},
        {"key": "acc", "name": "Аксессуары", "emoji": "⚡"},
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


# ========== HTTP СЕРВЕР (отдаёт HTML + API) ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.serve_html()
        elif path == "/api/data":
            data = load_data()
            self.send_json({"products": data["products"], "categories": data["categories"]})
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/sync":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                if "products" in data:
                    db = load_data()
                    db["products"] = data["products"]
                    save_data(db)
                    log.info("Products synced from admin")
                self.send_json({"ok": True})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        else:
            self.send_json({"error": "Not found"}, 404)

    def serve_html(self):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html = f.read()
            # Вставляем URL сервера в HTML
            server_url = f"https://{self.headers.get('Host', 'localhost')}"
            html = html.replace("__API_URL__", server_url)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        except FileNotFoundError:
            self.send_error(404, "index.html not found")

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        pass


# ========== TELEGRAM БОТ ==========
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Берём URL сервера из переменной окружения или из запроса
    webapp_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if webapp_url:
        webapp_url = f"https://{webapp_url}"
    else:
        webapp_url = "https://" + ctx.bot.get_me().username + ".railway.app"

    kb = [[InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        "🔥 *GuberVape — Vape Shop*\n\nНажмите кнопку чтобы открыть каталог 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        raw = update.message.web_app_data.data
        data = json.loads(raw)

        if data.get("type") == "order":
            await process_order(update, ctx, data)
        elif data.get("type") == "sync":
            # Админ синхронизирует товары
            user_id = update.message.from_user.id
            if user_id == ADMIN_ID and "products" in data:
                db = load_data()
                db["products"] = data["products"]
                save_data(db)
                await update.message.reply_text("✅ Товары синхронизированы со всеми пользователями!")

    except Exception as e:
        log.error(f"WebApp error: {e}")


async def process_order(update, ctx, data):
    db = load_data()
    db["order_counter"] = db.get("order_counter", 0) + 1
    order_num = db["order_counter"]
    save_data(db)

    name = data.get("name", "—")
    username = data.get("username", "—")
    comment = data.get("comment", "")
    items = data.get("items", [])
    total = data.get("total", 0)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    user_id = update.message.from_user.id

    items_lines = "\n".join([
        f"  {i.get('emoji', '📦')} {i.get('name', 'Товар')}\n  └ {i.get('qty', 1)} шт × {i.get('price', 0):,}₽ = {i.get('qty', 1) * i.get('price', 0):,}₽"
        for i in items
    ])

    # Чек покупателю
    receipt = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *ЧЕК ЗАКАЗА #{order_num}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 {now}\n\n"
        f"📦 *Состав заказа:*\n{items_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n📱 {username}\n"
    )
    if comment:
        receipt += f"\n💬 {comment}\n"
    receipt += "\nСпасибо за заказ! Мы свяжемся с вами 🔥"

    await update.message.reply_text(receipt, parse_mode="Markdown")

    # Уведомление админу
    admin_msg = (
        f"🚨 *НОВЫЙ ЗАКАЗ #{order_num}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now}\n\n"
        f"👤 *ФИО:* {name}\n"
        f"📱 *Telegram:* {username}\n"
        f"🆔 *User ID:* `{user_id}`\n\n"
        f"📦 *Товары:*\n{items_lines}\n\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
    )
    if comment:
        admin_msg += f"\n💬 *Комментарий:* {comment}"

    if ADMIN_ID:
        await ctx.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")

    log.info(f"Заказ #{order_num} от {username}: {total}₽")


# ========== ЗАПУСК ==========
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"HTTP сервер на порту {PORT}")
    server.serve_forever()


def main():
    threading.Thread(target=run_http, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
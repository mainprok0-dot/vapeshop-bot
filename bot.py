#!/usr/bin/env python3
import os, json, logging, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# НАСТРОЙКИ — берутся из переменных Railway
# ============================================================
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k")
ADMIN_ID   = int(os.environ.get("ADMIN_CHAT_ID", "8237417166"))
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://worked-production.up.railway.app")
PORT       = int(os.environ.get("PORT", "8080"))
DATA_FILE  = "shop_data.json"
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ============================================================
# ДАННЫЕ ПО УМОЛЧАНИЮ
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
    "orders": [],
    "order_counter": 0
}

# ============================================================
# РАБОТА С ФАЙЛОМ ДАННЫХ
# ============================================================
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки данных: {e}")
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Ошибка сохранения данных: {e}")

# ============================================================
# HTTP СЕРВЕР — API для мини-приложения
# ============================================================
class APIHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_json({"status": "ok", "service": "GuberVape Bot"})
        elif self.path == "/api/data":
            data = load_data()
            self.send_json({
                "products":   data.get("products", []),
                "categories": data.get("categories", [])
            })
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            payload = json.loads(body)
        except Exception:
            self.send_json({"error": "bad json"}, 400)
            return

        if self.path == "/api/products":
            data = load_data()
            data["products"] = payload.get("products", data["products"])
            save_data(data)
            log.info(f"✅ Товары обновлены через API ({len(data['products'])} шт)")
            self.send_json({"ok": True})

        elif self.path == "/api/categories":
            data = load_data()
            data["categories"] = payload.get("categories", data["categories"])
            save_data(data)
            log.info(f"✅ Категории обновлены через API")
            self.send_json({"ok": True})

        else:
            self.send_json({"error": "not found"}, 404)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.add_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def add_cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        pass  # отключаем лишние логи HTTP

# ============================================================
# TELEGRAM БОТ
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Команда /start — кнопка открытия магазина"""
    kb = [[InlineKeyboardButton(
        "🛒 Открыть GuberVape",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )]]
    await update.message.reply_text(
        "🔥 *GuberVape — Vape Shop*\n\n"
        "Нажмите кнопку чтобы открыть каталог 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    log.info(f"▶️ /start от пользователя {update.effective_user.id}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Команда /orders — список последних заказов (только для админа)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    data   = load_data()
    orders = data.get("orders", [])

    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return

    lines = []
    for o in orders[-15:]:
        lines.append(
            f"#{o['order_id']} | {o['date']}\n"
            f"   👤 {o['name']} | 💰 {o['total']:,}₽"
        )

    await update.message.reply_text(
        "📋 *ПОСЛЕДНИЕ ЗАКАЗЫ:*\n\n" + "\n\n".join(lines),
        parse_mode="Markdown"
    )


async def handle_webapp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получение данных из мини-приложения"""
    user = update.effective_user

    try:
        raw  = update.message.web_app_data.data
        data = json.loads(raw)
        dtype = data.get("type")

        log.info(f"📦 WebApp данные от {user.id} (@{user.username}): type={dtype}")

        if dtype == "order":
            await process_order(update, ctx, data, user)

        elif dtype == "save_products":
            await process_save_products(update, ctx, data, user)

        elif dtype == "save_categories":
            await process_save_categories(update, ctx, data, user)

        else:
            log.warning(f"Неизвестный тип: {dtype}")

    except Exception as e:
        log.error(f"❌ Ошибка обработки WebApp данных: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при обработке заказа. Попробуйте ещё раз.")


async def process_order(update, ctx, data, user):
    """Обработка заказа — сохранение + чек покупателю + уведомление админу"""

    # Сохраняем заказ
    db = load_data()
    db["order_counter"] = db.get("order_counter", 0) + 1
    order_id = db["order_counter"]

    order_record = {
        "order_id": order_id,
        "date":     datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "name":     data.get("name", "—"),
        "username": data.get("username", "—"),
        "comment":  data.get("comment", ""),
        "total":    data.get("total", 0),
        "items":    data.get("items", []),
        "user_id":  user.id
    }

    if "orders" not in db:
        db["orders"] = []
    db["orders"].append(order_record)
    save_data(db)

    name     = data.get("name", "—")
    username = data.get("username", "—")
    comment  = data.get("comment", "")
    items    = data.get("items", [])
    total    = data.get("total", 0)
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Строки товаров
    items_text = "\n".join([
        f"  {i['emoji']} {i['name']}\n"
        f"  └ {i['qty']} шт × {i['price']:,}₽ = {i['qty'] * i['price']:,}₽"
        for i in items
    ])

    # ЧЕК для покупателя
    receipt = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *ЧЕК ЗАКАЗА #{order_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 {now}\n\n"
        f"📦 *Состав заказа:*\n{items_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n"
        f"📱 {username}\n"
    )
    if comment:
        receipt += f"💬 {comment}\n"
    receipt += "\n🔥 Спасибо за заказ! Скоро свяжемся с вами."

    # Отправляем чек покупателю
    await update.message.reply_text(receipt, parse_mode="Markdown")
    log.info(f"✅ Чек #{order_id} отправлен покупателю {user.id}")

    # Уведомление АДМИНУ
    admin_msg = (
        f"🚨 *НОВЫЙ ЗАКАЗ #{order_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now}\n\n"
        f"👤 *ФИО:* {name}\n"
        f"📱 *Telegram:* {username}\n"
        f"🆔 *User ID:* `{user.id}`\n\n"
        f"📦 *Товары:*\n{items_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    if comment:
        admin_msg += f"\n\n💬 *Комментарий:* {comment}"

    log.info(f"📤 Отправляю уведомление админу {ADMIN_ID}...")
    try:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            parse_mode="Markdown"
        )
        log.info(f"✅ Уведомление о заказе #{order_id} отправлено админу!")
    except Exception as e:
        log.error(f"❌ НЕ УДАЛОСЬ отправить уведомление админу {ADMIN_ID}: {e}")


async def process_save_products(update, ctx, data, user):
    """Сохранение товаров от админа"""
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return
    db = load_data()
    db["products"] = data.get("products", [])
    save_data(db)
    log.info(f"✅ Товары обновлены админом {user.id}")
    await update.message.reply_text("✅ Товары сохранены на сервере!")


async def process_save_categories(update, ctx, data, user):
    """Сохранение категорий от админа"""
    if user.id != ADMIN_ID:
        return
    db = load_data()
    db["categories"] = data.get("categories", [])
    save_data(db)
    log.info(f"✅ Категории обновлены админом {user.id}")
    await update.message.reply_text("✅ Категории сохранены!")


# ============================================================
# ЗАПУСК
# ============================================================
def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")
    server.serve_forever()


def main():
    log.info("=" * 50)
    log.info("🔥 GuberVape Bot запускается...")
    log.info(f"👑 Admin ID: {ADMIN_ID}")
    log.info(f"🌐 WebApp URL: {WEBAPP_URL}")
    log.info(f"🚪 Port: {PORT}")
    log.info("=" * 50)

    # Запускаем HTTP сервер в фоне
    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()

    # Запускаем Telegram бота
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, handle_webapp
    ))

    log.info("🤖 Telegram бот запущен и слушает сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

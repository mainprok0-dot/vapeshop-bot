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
BOT_TOKEN = "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k"
ADMIN_ID = 8237417166  # ВАШ ID (число)
PORT = int(os.environ.get("PORT", 8080))
# ================================

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Простой HTML магазина
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>VapeShop</title>
    <style>
        body { font-family: system-ui; background: #0a0a0f; color: white; padding: 20px; margin: 0; }
        .product { background: #1a1a26; margin: 10px 0; padding: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
        button { background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; }
        input, textarea { width: 100%; margin: 10px 0; padding: 12px; border-radius: 10px; border: none; background: #1a1a26; color: white; box-sizing: border-box; }
        .cart-item { background: #1a1a26; margin: 5px 0; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .total { font-size: 20px; font-weight: bold; margin: 15px 0; color: #00e5ff; }
        h1, h2 { color: #00e5ff; }
        .order-btn { background: linear-gradient(135deg, #7c3aed, #00e5ff); font-size: 18px; padding: 15px; width: 100%; margin-top: 20px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 8px; display: none; }
        .status.success { background: #00e67620; border: 1px solid #00e676; color: #00e676; }
        .status.error { background: #ff446620; border: 1px solid #ff4466; color: #ff4466; }
    </style>
</head>
<body>
    <h1>🔥 VapeShop</h1>

    <div id="status" class="status"></div>

    <h2>📦 Товары</h2>
    <div id="products"></div>

    <h2>🛒 Корзина</h2>
    <div id="cart"></div>

    <h2>📝 Данные для заказа</h2>
    <input type="text" id="name" placeholder="Ваше ФИО *">
    <input type="text" id="username" placeholder="@username Telegram *">
    <textarea id="comment" placeholder="Комментарий (адрес, доставка и т.д.)" rows="3"></textarea>

    <button class="order-btn" onclick="submitOrder()">✅ ОФОРМИТЬ ЗАКАЗ</button>

    <script>
        let products = [];
        let cart = {};

        // Инициализация Telegram WebApp
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.expand();
            tg.ready();
            console.log('Telegram WebApp готов');
        }

        // Загрузка товаров
        async function loadProducts() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                products = data.products;
                renderProducts();
                loadCart();
                console.log('Товары загружены:', products.length);
            } catch(e) {
                console.error('Ошибка загрузки:', e);
                showStatus('Ошибка загрузки товаров', 'error');
            }
        }

        function renderProducts() {
            const container = document.getElementById('products');
            container.innerHTML = products.map(p => `
                <div class="product">
                    <div>
                        <span style="font-size:32px">${p.emoji}</span>
                        <strong>${p.name}</strong><br>
                        <small>${p.price}₽</small>
                    </div>
                    <button onclick="addToCart(${p.id})">+ Добавить</button>
                </div>
            `).join('');
        }

        function addToCart(id) {
            cart[id] = (cart[id] || 0) + 1;
            saveCart();
            renderCart();
            if (tg) tg.HapticFeedback.impactOccurred('light');
        }

        function changeQty(id, delta) {
            cart[id] = Math.max(0, (cart[id] || 0) + delta);
            if (cart[id] === 0) delete cart[id];
            saveCart();
            renderCart();
        }

        function saveCart() {
            localStorage.setItem('cart', JSON.stringify(cart));
        }

        function loadCart() {
            const saved = localStorage.getItem('cart');
            if (saved) {
                cart = JSON.parse(saved);
                renderCart();
            }
        }

        function renderCart() {
            const container = document.getElementById('cart');
            const items = Object.entries(cart).filter(([id,q]) => q > 0);

            if (items.length === 0) {
                container.innerHTML = '<p>Корзина пуста</p>';
                return;
            }

            let total = 0;
            let html = '';

            for (let [id, qty] of items) {
                const p = products.find(p => p.id == parseInt(id));
                if (p) {
                    total += p.price * qty;
                    html += `
                        <div class="cart-item">
                            <div>${p.emoji} ${p.name} x${qty}</div>
                            <div>${p.price * qty}₽ 
                                <button onclick="changeQty(${p.id}, -1)">-</button>
                                <button onclick="changeQty(${p.id}, 1)">+</button>
                            </div>
                        </div>
                    `;
                }
            }

            html += `<div class="total">💰 ИТОГО: ${total}₽</div>`;
            container.innerHTML = html;
        }

        function showStatus(msg, type) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = `status ${type}`;
            el.style.display = 'block';
            setTimeout(() => {
                el.style.display = 'none';
            }, 3000);
        }

        function submitOrder() {
            const name = document.getElementById('name').value.trim();
            const username = document.getElementById('username').value.trim();
            const comment = document.getElementById('comment').value;

            if (!name) {
                showStatus('❌ Введите ФИО', 'error');
                return;
            }
            if (!username) {
                showStatus('❌ Введите Telegram username', 'error');
                return;
            }

            const items = Object.entries(cart).filter(([id,q]) => q > 0).map(([id,qty]) => {
                const p = products.find(p => p.id == parseInt(id));
                return {
                    id: p.id,
                    name: p.name,
                    emoji: p.emoji,
                    price: p.price,
                    qty: qty
                };
            });

            if (items.length === 0) {
                showStatus('❌ Корзина пуста', 'error');
                return;
            }

            const total = items.reduce((s,i) => s + i.price * i.qty, 0);

            const orderData = {
                type: 'order',
                name: name,
                username: username,
                comment: comment,
                total: total,
                items: items
            };

            console.log('Отправка заказа:', orderData);

            if (tg) {
                tg.sendData(JSON.stringify(orderData));
                showStatus('✅ Заказ отправлен! Мы свяжемся с вами', 'success');
                cart = {};
                saveCart();
                renderCart();
                document.getElementById('name').value = '';
                document.getElementById('username').value = '';
                document.getElementById('comment').value = '';
            } else {
                showStatus('❌ Ошибка: откройте магазин через Telegram бота', 'error');
            }
        }

        loadProducts();
    </script>
</body>
</html>
'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        log.info(f"GET request: {self.path}")

        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))

        elif self.path == '/api/data':
            data = {
                "products": [
                    {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro", "price": 2990, "category": "device"},
                    {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5", "price": 3490, "category": "device"},
                    {"id": 3, "emoji": "🌊", "name": "BLVK Salt Mango", "price": 850, "category": "liquid"},
                ]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        log.info(f"POST request: {self.path}, body: {body[:200]}")
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        log.info(f"HTTP: {fmt % args}")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    log.info(f"User {user.id} (@{user.username}) started the bot")

    # Получаем URL сервера
    webapp_url = f"https://{ctx.bot.get_me().username}.railway.app"
    log.info(f"WebApp URL: {webapp_url}")

    kb = [[InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        "🔥 *VapeShop*\n\n"
        "Нажмите кнопку ниже чтобы открыть магазин и сделать заказ.\n\n"
        "📝 *Как сделать заказ:*\n"
        "1. Добавьте товары в корзину\n"
        "2. Введите ФИО и @username\n"
        "3. Нажмите «Оформить заказ»\n\n"
        "⬇️ Нажмите кнопку ниже ⬇️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из WebApp"""
    user = update.effective_user
    data_raw = update.message.web_app_data.data

    log.info(f"📦 Получены данные от user {user.id}: {data_raw[:500]}")

    try:
        data = json.loads(data_raw)
        log.info(f"Parsed data type: {data.get('type')}")

        if data.get('type') == 'order':
            await process_order(update, ctx, data)
        else:
            log.warning(f"Unknown data type: {data.get('type')}")

    except json.JSONDecodeError as e:
        log.error(f"JSON decode error: {e}")
    except Exception as e:
        log.error(f"Error handling webapp data: {e}")


async def process_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE, data: dict):
    """Обработка заказа"""
    user = update.effective_user
    order_num = int(datetime.now().timestamp())

    name = data.get('name', '—')
    username = data.get('username', '—')
    comment = data.get('comment', '')
    items = data.get('items', [])
    total = data.get('total', 0)
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    log.info(f"🛒 ЗАКАЗ #{order_num} от {username}: {total}₽, товаров: {len(items)}")

    # Формируем сообщение админу
    items_text = "\n".join([
        f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']}₽ = {i['qty'] * i['price']}₽"
        for i in items
    ])

    admin_msg = (
        f"🚨 *НОВЫЙ ЗАКАЗ!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Номер: #{order_num}\n"
        f"📅 Время: {now}\n\n"
        f"👤 *ФИО:* {name}\n"
        f"📱 *Telegram:* {username}\n"
        f"🆔 *User ID:* `{user.id}`\n\n"
        f"📦 *Состав заказа:*\n{items_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *ИТОГО: {total:,}₽*\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    if comment:
        admin_msg += f"\n\n💬 *Комментарий:* {comment}"

    # Отправляем админу
    try:
        await ctx.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        log.info(f"✅ Уведомление отправлено админу {ADMIN_ID}")
    except Exception as e:
        log.error(f"❌ Ошибка отправки админу: {e}")

    # Подтверждение пользователю
    user_msg = (
        f"✅ *Заказ #{order_num} принят!*\n\n"
        f"📦 Сумма заказа: *{total:,}₽*\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Спасибо за заказ! 🔥"
    )
    await update.message.reply_text(user_msg, parse_mode="Markdown")
    log.info(f"✅ Подтверждение отправлено пользователю {user.id}")


def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")
    server.serve_forever()


def main():
    # Запускаем HTTP сервер в отдельном потоке
    threading.Thread(target=run_http, daemon=True).start()

    # Запускаем Telegram бота
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info(f"🤖 Бот запущен! Токен: {BOT_TOKEN[:10]}...")
    log.info(f"👑 Админ ID: {ADMIN_ID}")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
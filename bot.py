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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

# ========== ДАННЫЕ ПО УМОЛЧАНИЮ ==========
DEFAULT_DATA = {
    "products": [
        {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro", "desc": "Устройство с регулировкой мощности",
         "category": "device", "price": 2990, "badge": "хит", "inStock": True},
        {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5", "desc": "Мощный под-мод 80W", "category": "device",
         "price": 3490, "badge": "новинка", "inStock": True},
        {"id": 3, "emoji": "🌊", "name": "BLVK Salt Mango", "desc": "Солевая жидкость 30мл 20мг", "category": "liquid",
         "price": 850, "badge": "", "inStock": True},
        {"id": 4, "emoji": "❄️", "name": "ICE Salt Mint", "desc": "Ледяная мята 30мл 50мг", "category": "liquid",
         "price": 790, "badge": "sale", "inStock": True},
        {"id": 5, "emoji": "🍓", "name": "ELFBAR 600 Strawberry", "desc": "Одноразовый под 600 затяжек",
         "category": "pod", "price": 650, "badge": "", "inStock": True},
        {"id": 6, "emoji": "🍋", "name": "GEEK BAR Lemon", "desc": "Одноразовый под 575 затяжек", "category": "pod",
         "price": 620, "badge": "", "inStock": True},
        {"id": 7, "emoji": "🧊", "name": "Испаритель Mesh 0.2Ω", "desc": "Для SMOK Nord 5, 5шт", "category": "acc",
         "price": 490, "badge": "", "inStock": True},
        {"id": 8, "emoji": "⚡", "name": "Зарядка USB-C 65W", "desc": "Быстрая зарядка для устройств", "category": "acc",
         "price": 390, "badge": "", "inStock": True},
    ],
    "categories": [
        {"key": "all", "name": "Все", "emoji": "🎯"},
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


# ========== HTML ШАБЛОН ==========
HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0a0a0f;
            color: #ffffff;
            padding: 0;
            margin: 0;
            min-height: 100vh;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #1a0a2e 0%, #0a0a0f 100%);
            padding: 20px 16px;
            text-align: center;
            border-bottom: 1px solid #3a2a5a;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo {
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 2px;
            background: linear-gradient(135deg, #c084fc, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(168,85,247,0.3);
        }

        .logo span {
            font-size: 12px;
            letter-spacing: 4px;
            display: block;
            color: #7e22ce;
            -webkit-text-fill-color: #7e22ce;
            margin-top: 4px;
        }

        /* Category Tabs */
        .categories {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            overflow-x: auto;
            background: #0f0f14;
            border-bottom: 1px solid #2a2a3a;
            scrollbar-width: none;
        }

        .categories::-webkit-scrollbar {
            display: none;
        }

        .cat-btn {
            padding: 8px 18px;
            border-radius: 30px;
            background: #1a1a2a;
            border: 1px solid #2a2a3a;
            color: #a1a1aa;
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s;
        }

        .cat-btn.active {
            background: linear-gradient(135deg, #7e22ce, #a855f7);
            border-color: #a855f7;
            color: white;
            box-shadow: 0 4px 15px rgba(168,85,247,0.3);
        }

        /* Cart Button */
        .cart-icon {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #7e22ce, #a855f7);
            width: 56px;
            height: 56px;
            border-radius: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(168,85,247,0.4);
            z-index: 200;
            transition: transform 0.2s;
        }

        .cart-icon:active {
            transform: scale(0.95);
        }

        .cart-icon span {
            font-size: 28px;
        }

        .cart-badge {
            position: absolute;
            top: -5px;
            right: -5px;
            background: #ff4466;
            color: white;
            font-size: 11px;
            font-weight: bold;
            width: 20px;
            height: 20px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Products Grid */
        .products {
            padding: 16px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .product-card {
            background: #12121a;
            border: 1px solid #2a2a3a;
            border-radius: 16px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s;
        }

        .product-card:active {
            transform: scale(0.98);
        }

        .product-img {
            background: linear-gradient(135deg, #1a1a2a, #0f0f14);
            padding: 24px;
            text-align: center;
            font-size: 56px;
            position: relative;
        }

        .badge {
            position: absolute;
            top: 8px;
            left: 8px;
            background: #a855f7;
            color: white;
            font-size: 10px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 20px;
            text-transform: uppercase;
        }

        .badge.sale {
            background: #ff4466;
        }

        .badge.hit {
            background: #f59e0b;
        }

        .product-info {
            padding: 12px;
        }

        .product-name {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .product-desc {
            font-size: 11px;
            color: #6b6b8a;
            margin-bottom: 8px;
        }

        .product-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .product-price {
            font-size: 18px;
            font-weight: 700;
            color: #c084fc;
        }

        .add-btn {
            background: linear-gradient(135deg, #7e22ce, #a855f7);
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 10px;
            color: white;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Cart Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.9);
            z-index: 300;
            padding: 20px;
            overflow-y: auto;
        }

        .modal.active {
            display: block;
        }

        .modal-content {
            background: #12121a;
            border-radius: 24px;
            padding: 20px;
            max-width: 500px;
            margin: 0 auto;
            min-height: 80vh;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #2a2a3a;
        }

        .close-modal {
            background: none;
            border: none;
            color: white;
            font-size: 28px;
            cursor: pointer;
        }

        .cart-item {
            background: #1a1a2a;
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .qty-control {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .qty-btn {
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: #2a2a3a;
            border: none;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }

        .cart-total {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #2a2a3a;
            font-size: 20px;
            font-weight: bold;
            text-align: right;
            color: #c084fc;
        }

        .order-form {
            margin-top: 20px;
        }

        .order-form input,
        .order-form textarea {
            width: 100%;
            padding: 12px;
            margin-bottom: 12px;
            background: #1a1a2a;
            border: 1px solid #2a2a3a;
            border-radius: 12px;
            color: white;
            font-size: 14px;
        }

        .order-form input:focus,
        .order-form textarea:focus {
            outline: none;
            border-color: #a855f7;
        }

        .submit-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #7e22ce, #a855f7);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
        }

        .status {
            position: fixed;
            bottom: 90px;
            left: 20px;
            right: 20px;
            background: #1a1a2a;
            border: 1px solid #a855f7;
            padding: 12px;
            border-radius: 12px;
            text-align: center;
            z-index: 250;
            display: none;
        }

        .brand-header {
            background: linear-gradient(135deg, #1a0a2e, #0a0a0f);
            padding: 16px;
            text-align: center;
        }

        .brand-name {
            font-size: 20px;
            font-weight: bold;
            color: #c084fc;
        }

        .brand-tags {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 8px;
            font-size: 11px;
            color: #6b6b8a;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">GUBERVAPE<span>ВЕЙП ШОП</span></div>
    </div>

    <div class="brand-header">
        <div class="brand-name">GUBERVAPE</div>
        <div class="brand-tags">LIQUID · DEVICE · PODS · PARTS</div>
    </div>

    <div class="categories" id="categories"></div>

    <div class="products" id="products"></div>

    <div class="cart-icon" onclick="openCart()">
        <span>🛒</span>
        <div class="cart-badge" id="cartBadge" style="display:none">0</div>
    </div>

    <div class="modal" id="cartModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>🛒 Корзина</h2>
                <button class="close-modal" onclick="closeCart()">✕</button>
            </div>
            <div id="cartItems"></div>
            <div id="orderForm" class="order-form" style="display:none">
                <input type="text" id="name" placeholder="Ваше ФИО *">
                <input type="text" id="username" placeholder="@username Telegram *">
                <textarea id="comment" placeholder="Комментарий к заказу (адрес, способ доставки и т.д.)" rows="3"></textarea>
                <button class="submit-btn" onclick="submitOrder()">✅ ОФОРМИТЬ ЗАКАЗ</button>
            </div>
        </div>
    </div>

    <div class="status" id="status"></div>

    <script>
        let products = [];
        let categories = [];
        let cart = {};
        let currentCategory = 'all';
        let tg = window.Telegram?.WebApp;

        if (tg) {
            tg.expand();
            tg.ready();
        }

        function showStatus(msg, isError = false) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.style.background = isError ? '#ff446620' : '#00e67620';
            el.style.borderColor = isError ? '#ff4466' : '#00e676';
            el.style.display = 'block';
            setTimeout(() => {
                el.style.display = 'none';
            }, 3000);
        }

        async function loadData() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                products = data.products;
                categories = data.categories;
                renderCategories();
                renderProducts();
                loadCart();
            } catch(e) {
                console.error(e);
                showStatus('Ошибка загрузки товаров', true);
            }
        }

        function renderCategories() {
            const container = document.getElementById('categories');
            container.innerHTML = categories.map(cat => `
                <div class="cat-btn ${cat.key === currentCategory ? 'active' : ''}" onclick="filterProducts('${cat.key}')">
                    ${cat.emoji} ${cat.name}
                </div>
            `).join('');
        }

        function filterProducts(category) {
            currentCategory = category;
            renderCategories();
            renderProducts();
        }

        function renderProducts() {
            const container = document.getElementById('products');
            const filtered = currentCategory === 'all' 
                ? products 
                : products.filter(p => p.category === currentCategory);

            if (filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:40px; color:#6b6b8a">Товаров не найдено</div>';
                return;
            }

            container.innerHTML = filtered.map(p => `
                <div class="product-card" onclick="openProduct(${p.id})">
                    <div class="product-img">
                        <span>${p.emoji}</span>
                        ${p.badge ? `<div class="badge ${p.badge === 'sale' ? 'sale' : p.badge === 'hit' ? 'hit' : ''}">${p.badge}</div>` : ''}
                    </div>
                    <div class="product-info">
                        <div class="product-name">${p.name}</div>
                        <div class="product-desc">${p.desc}</div>
                        <div class="product-footer">
                            <div class="product-price">${p.price.toLocaleString()}₽</div>
                            <button class="add-btn" onclick="event.stopPropagation(); addToCart(${p.id})">+</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function openProduct(id) {
            const p = products.find(p => p.id === id);
            if (!p) return;
            showStatus(`${p.name} — ${p.price.toLocaleString()}₽`, false);
        }

        function addToCart(id) {
            cart[id] = (cart[id] || 0) + 1;
            saveCart();
            updateCartBadge();
            showStatus('✅ Товар добавлен в корзину');
            if (tg) tg.HapticFeedback?.impactOccurred('light');
        }

        function removeFromCart(id) {
            if (cart[id]) {
                cart[id]--;
                if (cart[id] === 0) delete cart[id];
                saveCart();
                updateCartBadge();
                renderCartItems();
            }
        }

        function saveCart() {
            localStorage.setItem('gubervape_cart', JSON.stringify(cart));
        }

        function loadCart() {
            const saved = localStorage.getItem('gubervape_cart');
            if (saved) {
                cart = JSON.parse(saved);
                updateCartBadge();
            }
        }

        function updateCartBadge() {
            const total = Object.values(cart).reduce((a,b) => a + b, 0);
            const badge = document.getElementById('cartBadge');
            if (total > 0) {
                badge.textContent = total;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }

        function openCart() {
            renderCartItems();
            document.getElementById('cartModal').classList.add('active');
        }

        function closeCart() {
            document.getElementById('cartModal').classList.remove('active');
        }

        function renderCartItems() {
            const container = document.getElementById('cartItems');
            const items = Object.entries(cart);
            const orderForm = document.getElementById('orderForm');

            if (items.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:40px; color:#6b6b8a">Корзина пуста</div>';
                orderForm.style.display = 'none';
                return;
            }

            let total = 0;
            let html = '';

            for (let [id, qty] of items) {
                const p = products.find(p => p.id === parseInt(id));
                if (p) {
                    total += p.price * qty;
                    html += `
                        <div class="cart-item">
                            <div>
                                <div style="font-weight:bold">${p.emoji} ${p.name}</div>
                                <div style="font-size:12px; color:#c084fc">${p.price.toLocaleString()}₽ × ${qty}</div>
                            </div>
                            <div class="qty-control">
                                <button class="qty-btn" onclick="removeFromCart(${p.id})">−</button>
                                <span style="min-width:25px; text-align:center">${qty}</span>
                                <button class="qty-btn" onclick="addToCart(${p.id})">+</button>
                            </div>
                        </div>
                    `;
                }
            }

            html += `<div class="cart-total">💰 ИТОГО: ${total.toLocaleString()}₽</div>`;
            container.innerHTML = html;
            orderForm.style.display = 'block';
        }

        async function submitOrder() {
            const name = document.getElementById('name').value.trim();
            const username = document.getElementById('username').value.trim();
            const comment = document.getElementById('comment').value;

            if (!name) {
                showStatus('❌ Введите ваше ФИО', true);
                return;
            }
            if (!username) {
                showStatus('❌ Введите ваш Telegram username', true);
                return;
            }

            const items = Object.entries(cart).map(([id, qty]) => {
                const p = products.find(p => p.id === parseInt(id));
                return {
                    id: p.id,
                    name: p.name,
                    emoji: p.emoji,
                    price: p.price,
                    qty: qty
                };
            });

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

            let success = false;

            if (tg) {
                try {
                    tg.sendData(JSON.stringify(orderData));
                    success = true;
                } catch(e) {
                    console.error('WebApp error:', e);
                }
            }

            if (!success) {
                try {
                    const res = await fetch('/api/order', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(orderData)
                    });
                    if (res.ok) success = true;
                } catch(e) {
                    console.error('API error:', e);
                }
            }

            if (success) {
                showStatus('✅ Заказ отправлен! Мы свяжемся с вами');
                cart = {};
                saveCart();
                updateCartBadge();
                closeCart();
                document.getElementById('name').value = '';
                document.getElementById('username').value = '';
                document.getElementById('comment').value = '';
            } else {
                showStatus('❌ Ошибка отправки заказа. Попробуйте позже', true);
            }
        }

        loadData();
    </script>
</body>
</html>'''


# ========== HTTP СЕРВЕР ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        log.info(f"GET: {self.path}")

        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))

        elif self.path == '/api/data':
            data = load_data()
            self.send_json({"products": data["products"], "categories": data["categories"]})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        log.info(f"POST: {self.path}")

        if self.path == '/api/order':
            try:
                data = json.loads(body)
                log.info(f"Получен заказ через API: {data.get('name')} - {data.get('total')}₽")
                self.send_json({"ok": True})
            except Exception as e:
                log.error(f"Error: {e}")
                self.send_json({"error": str(e)}, 400)
        else:
            self.send_json({"error": "Not found"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        pass


# ========== TELEGRAM БОТ ==========
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    webapp_url = f"https://{ctx.bot.get_me().username}.railway.app"
    log.info(f"WebApp URL: {webapp_url}")

    kb = [[InlineKeyboardButton("🛒 Открыть GuberVape", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        "🔥 *GUBERVAPE* — премиум вейп шоп\n\n"
        "Нажмите кнопку ниже, чтобы открыть каталог и сделать заказ.\n\n"
        "📦 *Доставка по всей России*\n"
        "💳 *Оплата при получении*\n\n"
        "⬇️ *НАЖМИТЕ КНОПКУ* ⬇️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data_raw = update.message.web_app_data.data

    log.info(f"Получены данные от user {user.id}: {data_raw[:200]}")

    try:
        data = json.loads(data_raw)

        if data.get('type') == 'order':
            await process_order(update, ctx, data)
        else:
            log.warning(f"Unknown type: {data.get('type')}")

    except Exception as e:
        log.error(f"Error: {e}")


async def process_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE, data: dict):
    user = update.effective_user
    db = load_data()
    db["order_counter"] = db.get("order_counter", 0) + 1
    order_num = db["order_counter"]
    save_data(db)

    name = data.get('name', '—')
    username = data.get('username', '—')
    comment = data.get('comment', '')
    items = data.get('items', [])
    total = data.get('total', 0)
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    items_text = "\n".join([
        f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']:,}₽ = {i['qty'] * i['price']:,}₽"
        for i in items
    ])

    # Сообщение админу
    admin_msg = (
        f"🚨 *НОВЫЙ ЗАКАЗ #{order_num}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now}\n\n"
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
        log.error(f"Ошибка отправки админу: {e}")

    # Подтверждение пользователю
    user_msg = (
        f"✅ *ЗАКАЗ #{order_num} ПРИНЯТ!*\n\n"
        f"📦 Сумма: *{total:,}₽*\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Спасибо за заказ в GuberVape! 🔥"
    )
    await update.message.reply_text(user_msg, parse_mode="Markdown")
    log.info(f"✅ Подтверждение отправлено user {user.id}")


# ========== ЗАПУСК ==========
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"🌐 HTTP сервер на порту {PORT}")
    server.serve_forever()


def main():
    threading.Thread(target=run_http, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info(f"🤖 Бот запущен!")
    log.info(f"👑 Админ ID: {ADMIN_ID}")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
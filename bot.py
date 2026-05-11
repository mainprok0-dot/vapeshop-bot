#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k"
ADMIN_ID = 8237417166  # ВАШ Telegram ID (число!)
PORT = int(os.environ.get("PORT", 8080))
DATA_FILE = "shop_data.json"
# ================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ========== ДАННЫЕ ПО УМОЛЧАНИЮ ==========
DEFAULT_DATA = {
    "products": [
        {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro", "desc": "Устройство с регулировкой мощности",
         "category": "device", "price": 2990, "stock": True, "badge": ""},
        {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5", "desc": "Мощный под-мод 80W", "category": "device",
         "price": 3490, "stock": True, "badge": ""},
        {"id": 3, "emoji": "🌊", "name": "BLVK Salt Mango", "desc": "Солевая жидкость 30мл", "category": "liquid",
         "price": 850, "stock": True, "badge": ""},
        {"id": 4, "emoji": "❄️", "name": "ICE Salt Mint", "desc": "Ледяная мята 30мл", "category": "liquid",
         "price": 790, "stock": True, "badge": ""},
        {"id": 5, "emoji": "🍓", "name": "ELFBAR Strawberry", "desc": "Одноразовый под 600 затяжек", "category": "pod",
         "price": 650, "stock": True, "badge": ""},
        {"id": 6, "emoji": "🍋", "name": "GEEK BAR Lemon", "desc": "Одноразовый под 575 затяжек", "category": "pod",
         "price": 620, "stock": True, "badge": ""},
    ],
    "categories": [
        {"key": "all", "name": "Все", "emoji": "🎯"},
        {"key": "device", "name": "Устройства", "emoji": "💨"},
        {"key": "liquid", "name": "Жидкости", "emoji": "🌊"},
        {"key": "pod", "name": "Поды", "emoji": "🍓"},
        {"key": "acc", "name": "Аксессуары", "emoji": "⚡"}
    ],
    "orders": []
}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_DATA.copy()


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_order(order_data):
    data = load_data()
    order_id = len(data.get('orders', [])) + 1
    order_data['order_id'] = order_id
    order_data['date'] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    if 'orders' not in data:
        data['orders'] = []
    data['orders'].append(order_data)
    save_data(data)
    return order_id


# ========== HTML СТРАНИЦА ==========
HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #fff; padding-bottom: 80px; }
        .header { background: linear-gradient(135deg, #1a0a2e, #0a0a0f); padding: 20px; text-align: center; border-bottom: 1px solid #2a2a3a; }
        .logo { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #c084fc, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .sub { font-size: 11px; color: #6b6b8a; margin-top: 5px; letter-spacing: 2px; }
        .categories { display: flex; gap: 8px; padding: 12px 16px; overflow-x: auto; background: #0f0f14; border-bottom: 1px solid #2a2a3a; scrollbar-width: none; }
        .categories::-webkit-scrollbar { display: none; }
        .cat-btn { padding: 8px 18px; border-radius: 30px; background: #1a1a2a; border: 1px solid #2a2a3a; color: #a1a1aa; font-size: 14px; white-space: nowrap; cursor: pointer; transition: all 0.2s; }
        .cat-btn.active { background: linear-gradient(135deg, #7e22ce, #a855f7); border-color: #a855f7; color: white; }
        .products { padding: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .product-card { background: #12121a; border: 1px solid #2a2a3a; border-radius: 16px; overflow: hidden; transition: all 0.2s; }
        .product-card:active { transform: scale(0.98); }
        .product-img { background: linear-gradient(135deg, #1a1a2a, #0f0f14); padding: 24px; text-align: center; font-size: 48px; position: relative; }
        .badge { position: absolute; top: 8px; left: 8px; background: #a855f7; color: white; font-size: 10px; padding: 3px 8px; border-radius: 20px; }
        .product-info { padding: 12px; }
        .product-name { font-weight: 700; margin-bottom: 4px; }
        .product-desc { font-size: 11px; color: #6b6b8a; margin-bottom: 8px; }
        .product-footer { display: flex; justify-content: space-between; align-items: center; }
        .product-price { font-size: 18px; font-weight: 700; color: #c084fc; }
        .add-btn { background: linear-gradient(135deg, #7e22ce, #a855f7); border: none; width: 32px; height: 32px; border-radius: 10px; color: white; font-size: 18px; cursor: pointer; }
        .cart-btn { position: fixed; bottom: 20px; right: 20px; background: linear-gradient(135deg, #7e22ce, #a855f7); width: 56px; height: 56px; border-radius: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 20px rgba(168,85,247,0.4); z-index: 200; }
        .cart-count { position: absolute; top: -5px; right: -5px; background: #ff4466; width: 20px; height: 20px; border-radius: 10px; font-size: 11px; display: flex; align-items: center; justify-content: center; }
        .admin-btn { position: fixed; bottom: 20px; left: 20px; background: #2a2a3a; width: 44px; height: 44px; border-radius: 22px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; z-index: 200; display: none; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 300; padding: 20px; overflow-y: auto; }
        .modal.active { display: block; }
        .modal-content { background: #12121a; border-radius: 24px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #2a2a3a; }
        .close { background: none; border: none; color: white; font-size: 24px; cursor: pointer; }
        input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; color: white; font-size: 14px; }
        button { cursor: pointer; }
        .admin-product { background: #1a1a2a; padding: 12px; margin: 8px 0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
        .status { position: fixed; bottom: 100px; left: 20px; right: 20px; background: #1a1a2a; padding: 12px; border-radius: 12px; text-align: center; display: none; z-index: 250; }
        .cart-item { background: #1a1a2a; border-radius: 12px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .cart-total { margin-top: 15px; padding-top: 15px; border-top: 1px solid #2a2a3a; text-align: right; font-size: 18px; font-weight: bold; color: #c084fc; }
        .submit-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #7e22ce, #a855f7); border: none; border-radius: 12px; color: white; font-weight: bold; font-size: 16px; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">GUBERVAPE</div>
        <div class="sub">ВЕЙП ШОП</div>
    </div>

    <div class="categories" id="categories"></div>
    <div class="products" id="products"></div>

    <div class="cart-btn" onclick="openCart()">
        🛒
        <div class="cart-count" id="cartCount" style="display:none">0</div>
    </div>

    <div class="admin-btn" id="adminBtn" onclick="openAdmin()">⚙️</div>
    <div class="status" id="status"></div>

    <!-- Корзина -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>🛒 Корзина</h2>
                <button class="close" onclick="closeModal('cartModal')">✕</button>
            </div>
            <div id="cartItems"></div>
            <input type="text" id="userName" placeholder="Ваше ФИО *">
            <input type="text" id="userUsername" placeholder="@username Telegram *">
            <textarea id="userComment" placeholder="Адрес доставки, пожелания..." rows="2"></textarea>
            <button class="submit-btn" onclick="submitOrder()">✅ ОФОРМИТЬ ЗАКАЗ</button>
        </div>
    </div>

    <!-- Админ панель -->
    <div class="modal" id="adminModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>⚙️ Управление</h2>
                <button class="close" onclick="closeModal('adminModal')">✕</button>
            </div>
            <button class="submit-btn" onclick="showAddProduct()" style="margin-bottom: 15px;">+ Добавить товар</button>
            <div id="adminProducts"></div>
        </div>
    </div>

    <!-- Редактор товара -->
    <div class="modal" id="productModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Товар</h2>
                <button class="close" onclick="closeModal('productModal')">✕</button>
            </div>
            <input type="text" id="pEmoji" placeholder="Эмодзи" value="💨">
            <input type="text" id="pName" placeholder="Название *">
            <input type="text" id="pDesc" placeholder="Описание">
            <select id="pCategory">
                <option value="device">Устройства</option>
                <option value="liquid">Жидкости</option>
                <option value="pod">Поды</option>
                <option value="acc">Аксессуары</option>
            </select>
            <input type="number" id="pPrice" placeholder="Цена *">
            <label style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
                <input type="checkbox" id="pStock" checked> В наличии
            </label>
            <button class="submit-btn" onclick="saveProduct()">💾 Сохранить</button>
        </div>
    </div>

    <script>
        let products = [];
        let categories = [];
        let cart = {};
        let currentCategory = 'all';
        let editingId = null;
        let isAdmin = false;
        let tg = window.Telegram?.WebApp;

        if (tg) { tg.expand(); tg.ready(); }

        function showStatus(msg, isError = false) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.style.background = isError ? '#ff446620' : '#00e67620';
            el.style.border = isError ? '1px solid #ff4466' : '1px solid #00e676';
            el.style.display = 'block';
            setTimeout(() => { el.style.display = 'none'; }, 3000);
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
            } catch(e) { console.error(e); showStatus('Ошибка загрузки', true); }
        }

        function renderCategories() {
            const html = categories.map(c => `
                <div class="cat-btn ${c.key === currentCategory ? 'active' : ''}" onclick="filterProducts('${c.key}')">
                    ${c.emoji} ${c.name}
                </div>
            `).join('');
            document.getElementById('categories').innerHTML = html;
        }

        function filterProducts(cat) {
            currentCategory = cat;
            renderCategories();
            renderProducts();
        }

        function renderProducts() {
            const filtered = currentCategory === 'all' ? products : products.filter(p => p.category === currentCategory);
            if (filtered.length === 0) {
                document.getElementById('products').innerHTML = '<div style="text-align:center;padding:40px;color:#6b6b8a">Товаров нет</div>';
                return;
            }
            const html = filtered.map(p => `
                <div class="product-card">
                    <div class="product-img">
                        ${p.emoji}
                        ${p.badge ? `<div class="badge">${p.badge}</div>` : ''}
                    </div>
                    <div class="product-info">
                        <div class="product-name">${p.name}</div>
                        <div class="product-desc">${p.desc || ''}</div>
                        <div class="product-footer">
                            <div class="product-price">${p.price.toLocaleString()}₽</div>
                            <button class="add-btn" onclick="addToCart(${p.id})">+</button>
                        </div>
                    </div>
                </div>
            `).join('');
            document.getElementById('products').innerHTML = html;
        }

        function addToCart(id) {
            cart[id] = (cart[id] || 0) + 1;
            saveCart();
            updateCartBadge();
            showStatus('✅ Добавлено в корзину');
            if (tg) tg.HapticFeedback?.impactOccurred('light');
        }

        function updateCartBadge() {
            const total = Object.values(cart).reduce((a,b) => a+b, 0);
            const badge = document.getElementById('cartCount');
            if (total > 0) { badge.textContent = total; badge.style.display = 'flex'; }
            else { badge.style.display = 'none'; }
        }

        function saveCart() { localStorage.setItem('gubervape_cart', JSON.stringify(cart)); }
        function loadCart() {
            const saved = localStorage.getItem('gubervape_cart');
            if (saved) { cart = JSON.parse(saved); updateCartBadge(); }
        }

        function openCart() { renderCart(); document.getElementById('cartModal').classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        function renderCart() {
            const container = document.getElementById('cartItems');
            const items = Object.entries(cart);
            if (items.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#6b6b8a">Корзина пуста</div>';
                return;
            }
            let total = 0;
            let html = '';
            for (let [id, qty] of items) {
                const p = products.find(p => p.id == id);
                if (p) {
                    total += p.price * qty;
                    html += `
                        <div class="cart-item">
                            <div><strong>${p.emoji} ${p.name}</strong><br>${p.price.toLocaleString()}₽ × ${qty}</div>
                            <div>
                                <button onclick="changeQty(${p.id}, -1)" style="background:#2a2a3a;border:none;color:white;width:28px;border-radius:8px;">-</button>
                                <span style="margin:0 10px">${qty}</span>
                                <button onclick="changeQty(${p.id}, 1)" style="background:#2a2a3a;border:none;color:white;width:28px;border-radius:8px;">+</button>
                            </div>
                        </div>
                    `;
                }
            }
            html += `<div class="cart-total">💰 ИТОГО: ${total.toLocaleString()}₽</div>`;
            container.innerHTML = html;
        }

        function changeQty(id, delta) {
            cart[id] = Math.max(0, (cart[id] || 0) + delta);
            if (cart[id] === 0) delete cart[id];
            saveCart();
            updateCartBadge();
            renderCart();
        }

        function submitOrder() {
            const name = document.getElementById('userName').value.trim();
            const username = document.getElementById('userUsername').value.trim();
            const comment = document.getElementById('userComment').value;
            if (!name) { showStatus('❌ Введите ФИО', true); return; }
            if (!username) { showStatus('❌ Введите Telegram username', true); return; }
            const items = Object.entries(cart).map(([id, qty]) => {
                const p = products.find(p => p.id == id);
                return {name: p.name, emoji: p.emoji, price: p.price, qty};
            });
            const total = items.reduce((s,i) => s + i.price * i.qty, 0);
            const orderData = {type: 'order', name, username, comment, total, items};
            if (tg) {
                tg.sendData(JSON.stringify(orderData));
                showStatus('✅ Заказ отправлен!');
                cart = {}; saveCart(); updateCartBadge();
                closeModal('cartModal');
                document.getElementById('userName').value = '';
                document.getElementById('userUsername').value = '';
                document.getElementById('userComment').value = '';
            } else { showStatus('❌ Откройте через Telegram бота', true); }
        }

        // АДМИН ФУНКЦИИ
        let clickCount = 0;
        document.querySelector('.logo').onclick = () => {
            clickCount++;
            if (clickCount >= 5) {
                const pwd = prompt('Введите пароль:');
                if (pwd === 'admin123') {
                    isAdmin = true;
                    document.getElementById('adminBtn').style.display = 'flex';
                    showStatus('✅ Админ-панель доступна');
                } else { showStatus('❌ Неверный пароль', true); }
                clickCount = 0;
            }
        };

        function openAdmin() { if(isAdmin) { renderAdminProducts(); document.getElementById('adminModal').classList.add('active'); } }

        function renderAdminProducts() {
            const html = products.map(p => `
                <div class="admin-product">
                    <div><strong>${p.emoji} ${p.name}</strong><br><span style="font-size:12px;color:#888;">${p.price}₽ | ${p.category}</span></div>
                    <div>
                        <button onclick="editProduct(${p.id})" style="background:#a855f7;border:none;color:white;width:36px;height:36px;border-radius:10px;margin-right:5px;">✏️</button>
                        <button onclick="deleteProduct(${p.id})" style="background:#ff4466;border:none;color:white;width:36px;height:36px;border-radius:10px;">🗑️</button>
                    </div>
                </div>
            `).join('');
            document.getElementById('adminProducts').innerHTML = html || '<div style="text-align:center;padding:20px;">Товаров нет</div>';
        }

        function showAddProduct() {
            editingId = null;
            document.getElementById('modalTitle').textContent = '➕ Добавить товар';
            document.getElementById('pEmoji').value = '💨';
            document.getElementById('pName').value = '';
            document.getElementById('pDesc').value = '';
            document.getElementById('pCategory').value = 'device';
            document.getElementById('pPrice').value = '';
            document.getElementById('pStock').checked = true;
            document.getElementById('productModal').classList.add('active');
        }

        function editProduct(id) {
            const p = products.find(p => p.id === id);
            if (!p) return;
            editingId = id;
            document.getElementById('modalTitle').textContent = '✏️ Редактировать';
            document.getElementById('pEmoji').value = p.emoji;
            document.getElementById('pName').value = p.name;
            document.getElementById('pDesc').value = p.desc || '';
            document.getElementById('pCategory').value = p.category;
            document.getElementById('pPrice').value = p.price;
            document.getElementById('pStock').checked = p.stock;
            document.getElementById('productModal').classList.add('active');
        }

        async function saveProduct() {
            const name = document.getElementById('pName').value.trim();
            const price = parseInt(document.getElementById('pPrice').value);
            if (!name || !price) { showStatus('❌ Заполните название и цену', true); return; }

            const product = {
                emoji: document.getElementById('pEmoji').value || '💨',
                name: name,
                desc: document.getElementById('pDesc').value,
                category: document.getElementById('pCategory').value,
                price: price,
                stock: document.getElementById('pStock').checked,
                badge: ''
            };

            let newProducts = [...products];
            if (editingId) {
                const idx = newProducts.findIndex(p => p.id === editingId);
                newProducts[idx] = { ...newProducts[idx], ...product };
            } else {
                const newId = Math.max(...products.map(p => p.id), 0) + 1;
                newProducts.push({ id: newId, ...product });
            }

            try {
                const res = await fetch('/api/products', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({products: newProducts})
                });
                if (res.ok) {
                    products = newProducts;
                    renderProducts();
                    renderAdminProducts();
                    closeModal('productModal');
                    showStatus('✅ Товар сохранён!');
                    if (tg) tg.sendData(JSON.stringify({type: 'sync', products: newProducts}));
                }
            } catch(e) { showStatus('❌ Ошибка сохранения', true); }
        }

        async function deleteProduct(id) {
            if (!confirm('Удалить товар?')) return;
            const newProducts = products.filter(p => p.id !== id);
            try {
                const res = await fetch('/api/products', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({products: newProducts})
                });
                if (res.ok) {
                    products = newProducts;
                    renderProducts();
                    renderAdminProducts();
                    showStatus('✅ Товар удалён');
                    if (tg) tg.sendData(JSON.stringify({type: 'sync', products: newProducts}));
                }
            } catch(e) { showStatus('❌ Ошибка удаления', true); }
        }

        loadData();
    </script>
</body>
</html>'''


# ========== HTTP СЕРВЕР ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        if self.path == '/api/products':
            try:
                data = json.loads(body)
                shop_data = load_data()
                shop_data['products'] = data['products']
                save_data(shop_data)
                self.send_json({"ok": True})
            except Exception as e:
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
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = f"https://{ctx.bot.get_me().username}.railway.app"
    kb = [[InlineKeyboardButton("🛒 Открыть GuberVape", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text(
        "🔥 *GUBERVAPE* — премиум вейп шоп\n\nНажмите кнопку, чтобы открыть магазин",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data_raw = update.message.web_app_data.data

    log.info(f"📦 Получены данные от {user.id}")

    try:
        data = json.loads(data_raw)

        if data.get('type') == 'order':
            # Сохраняем заказ
            order_id = save_order(data)
            log.info(f"✅ Заказ #{order_id} сохранён")

            # Формируем сообщение
            items_text = "\n".join([
                f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']:,}₽ = {i['qty'] * i['price']:,}₽"
                for i in data['items']
            ])

            msg = (
                f"🚨 *НОВЫЙ ЗАКАЗ #{order_id}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"👤 *ФИО:* {data['name']}\n"
                f"📱 *Telegram:* {data['username']}\n"
                f"🆔 *User ID:* `{user.id}`\n\n"
                f"📦 *Состав:*\n{items_text}\n\n"
                f"💰 *ИТОГО: {data['total']:,}₽*"
            )
            if data.get('comment'):
                msg += f"\n\n💬 *Коммент:* {data['comment']}"

            # Отправляем админу
            await ctx.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")
            log.info(f"✅ Уведомление отправлено админу {ADMIN_ID}")

            # Подтверждение пользователю
            await update.message.reply_text(
                f"✅ *ЗАКАЗ #{order_id} ПРИНЯТ!*\n\nСумма: *{data['total']:,}₽*\n\nСпасибо за заказ!",
                parse_mode="Markdown"
            )

    except Exception as e:
        log.error(f"❌ Ошибка: {e}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Команда /orders - показать заказы"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    data = load_data()
    orders = data.get('orders', [])

    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return

    text = "📋 *ПОСЛЕДНИЕ ЗАКАЗЫ:*\n\n"
    for o in orders[-10:]:
        text += f"#{o['order_id']} | {o['date']}\n   {o['name']} | {o['total']:,}₽\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ========== ЗАПУСК ==========
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"🌐 HTTP сервер на порту {PORT}")
    server.serve_forever()


def main():
    threading.Thread(target=run_http, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info(f"🤖 Бот запущен!")
    log.info(f"👑 Админ ID: {ADMIN_ID}")

    app.run_polling()


if __name__ == "__main__":
    main()
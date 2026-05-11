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
DATA_FILE = "products.json"
# ================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ========== РАБОТА С ТОВАРАМИ ==========
def load_products():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Товары по умолчанию
    return [
        {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro", "desc": "Мощное устройство", "category": "device",
         "price": 2990, "stock": True},
        {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5", "desc": "80W с pods", "category": "device", "price": 3490,
         "stock": True},
        {"id": 3, "emoji": "🌊", "name": "BLVK Mango", "desc": "Солевая жидкость", "category": "liquid", "price": 850,
         "stock": True},
        {"id": 4, "emoji": "❄️", "name": "Ice Mint", "desc": "Ледяная мята", "category": "liquid", "price": 790,
         "stock": True},
        {"id": 5, "emoji": "🍓", "name": "ELFBAR Strawberry", "desc": "600 затяжек", "category": "pod", "price": 650,
         "stock": True},
        {"id": 6, "emoji": "🍋", "name": "GEEK BAR Lemon", "desc": "575 затяжек", "category": "pod", "price": 620,
         "stock": True},
    ]


def save_products(products):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


# ========== HTML СТРАНИЦА ==========
HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; background: #0a0a0f; color: white; padding-bottom: 80px; }
        .header { background: linear-gradient(135deg, #1a0a2e, #0a0a0f); padding: 20px; text-align: center; }
        .logo { font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #c084fc, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .categories { display: flex; gap: 8px; padding: 12px; overflow-x: auto; background: #0f0f14; }
        .cat-btn { padding: 8px 16px; border-radius: 20px; background: #1a1a2a; cursor: pointer; font-size: 14px; white-space: nowrap; }
        .cat-btn.active { background: #a855f7; color: white; }
        .products { padding: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .product { background: #12121a; border-radius: 16px; padding: 12px; border: 1px solid #2a2a3a; }
        .product-img { font-size: 48px; text-align: center; padding: 12px; }
        .product-name { font-weight: bold; margin: 8px 0 4px; }
        .product-price { color: #c084fc; font-weight: bold; font-size: 18px; }
        .add-btn { background: #a855f7; border: none; padding: 8px 16px; border-radius: 10px; color: white; cursor: pointer; margin-top: 8px; width: 100%; }
        .cart-btn { position: fixed; bottom: 20px; right: 20px; background: #a855f7; width: 56px; height: 56px; border-radius: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 12px rgba(168,85,247,0.4); }
        .cart-count { position: absolute; top: -5px; right: -5px; background: #ff4466; border-radius: 50%; width: 20px; height: 20px; font-size: 11px; display: flex; align-items: center; justify-content: center; }
        .admin-btn { position: fixed; bottom: 20px; left: 20px; background: #2a2a3a; width: 44px; height: 44px; border-radius: 22px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 200; padding: 20px; overflow-y: auto; }
        .modal.active { display: block; }
        .modal-content { background: #12121a; border-radius: 24px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .modal-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
        .close { background: none; border: none; color: white; font-size: 24px; cursor: pointer; }
        input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; color: white; }
        button { cursor: pointer; }
        .status { position: fixed; bottom: 100px; left: 20px; right: 20px; background: #1a1a2a; padding: 12px; border-radius: 12px; text-align: center; display: none; z-index: 150; }
        .admin-product { background: #1a1a2a; padding: 12px; margin: 8px 0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">GUBERVAPE</div>
        <div style="font-size: 12px; color: #888; margin-top: 5px;">ВЕЙП ШОП</div>
    </div>

    <div class="categories" id="categories"></div>
    <div class="products" id="products"></div>

    <div class="cart-btn" onclick="openCart()">
        🛒
        <div class="cart-count" id="cartCount" style="display:none">0</div>
    </div>

    <div class="admin-btn" onclick="openAdmin()" id="adminBtn" style="display:none">⚙️</div>

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
            <textarea id="userComment" placeholder="Комментарий (адрес, доставка)" rows="2"></textarea>
            <button class="add-btn" onclick="submitOrder()" style="margin-top: 15px;">✅ ОФОРМИТЬ ЗАКАЗ</button>
        </div>
    </div>

    <!-- Админ панель -->
    <div class="modal" id="adminModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>⚙️ Управление товарами</h2>
                <button class="close" onclick="closeModal('adminModal')">✕</button>
            </div>
            <button class="add-btn" onclick="showAddProduct()" style="margin-bottom: 15px;">+ Добавить товар</button>
            <div id="adminProducts"></div>
        </div>
    </div>

    <!-- Добавление/редактирование товара -->
    <div class="modal" id="productModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="productModalTitle">Добавить товар</h2>
                <button class="close" onclick="closeModal('productModal')">✕</button>
            </div>
            <input type="text" id="productEmoji" placeholder="Эмодзи (например 💨)" value="💨">
            <input type="text" id="productName" placeholder="Название *">
            <input type="text" id="productDesc" placeholder="Описание">
            <select id="productCategory">
                <option value="device">Устройства</option>
                <option value="liquid">Жидкости</option>
                <option value="pod">Поды</option>
                <option value="acc">Аксессуары</option>
            </select>
            <input type="number" id="productPrice" placeholder="Цена *">
            <label style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
                <input type="checkbox" id="productStock" checked> В наличии
            </label>
            <button class="add-btn" onclick="saveProduct()">💾 СОХРАНИТЬ</button>
        </div>
    </div>

    <script>
        let products = [];
        let cart = {};
        let currentCategory = 'all';
        let editingProductId = null;
        let isAdmin = false;
        let tg = window.Telegram?.WebApp;

        if (tg) {
            tg.expand();
            tg.ready();
            // Проверяем, админ ли пользователь (через секретный клик)
            tg.onEvent('viewportChanged', () => {});
        }

        function showStatus(msg, isError = false) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.style.background = isError ? '#ff446620' : '#00e67620';
            el.style.border = isError ? '1px solid #ff4466' : '1px solid #00e676';
            el.style.display = 'block';
            setTimeout(() => {
                el.style.display = 'none';
            }, 3000);
        }

        async function loadProducts() {
            try {
                const res = await fetch('/api/products');
                products = await res.json();
                renderCategories();
                renderProducts();
                loadCart();
            } catch(e) {
                console.error(e);
                showStatus('Ошибка загрузки', true);
            }
        }

        function renderCategories() {
            const cats = [
                {key: 'all', name: 'Все', emoji: '🎯'},
                {key: 'device', name: 'Устройства', emoji: '💨'},
                {key: 'liquid', name: 'Жидкости', emoji: '🌊'},
                {key: 'pod', name: 'Поды', emoji: '🍓'},
                {key: 'acc', name: 'Аксессуары', emoji: '⚡'}
            ];
            const html = cats.map(c => `
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
            const filtered = currentCategory === 'all' 
                ? products 
                : products.filter(p => p.category === currentCategory);

            if (filtered.length === 0) {
                document.getElementById('products').innerHTML = '<div style="text-align:center; padding:40px; color:#888;">Товаров нет</div>';
                return;
            }

            const html = filtered.map(p => `
                <div class="product">
                    <div class="product-img">${p.emoji}</div>
                    <div class="product-name">${p.name}</div>
                    <div class="product-desc" style="font-size:12px; color:#888;">${p.desc || ''}</div>
                    <div class="product-price">${p.price.toLocaleString()}₽</div>
                    <button class="add-btn" onclick="addToCart(${p.id})">+ В корзину</button>
                </div>
            `).join('');
            document.getElementById('products').innerHTML = html;
        }

        function addToCart(id) {
            cart[id] = (cart[id] || 0) + 1;
            saveCart();
            updateCartBadge();
            showStatus('✅ Товар добавлен в корзину');
            if (tg) tg.HapticFeedback?.impactOccurred('light');
        }

        function updateCartBadge() {
            const total = Object.values(cart).reduce((a,b) => a+b, 0);
            const badge = document.getElementById('cartCount');
            if (total > 0) {
                badge.textContent = total;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
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

        function openCart() {
            renderCart();
            document.getElementById('cartModal').classList.add('active');
        }

        function renderCart() {
            const container = document.getElementById('cartItems');
            const items = Object.entries(cart);

            if (items.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:40px; color:#888;">Корзина пуста</div>';
                return;
            }

            let total = 0;
            let html = '';
            for (let [id, qty] of items) {
                const p = products.find(p => p.id == id);
                if (p) {
                    total += p.price * qty;
                    html += `
                        <div class="admin-product" style="justify-content: space-between;">
                            <div>${p.emoji} ${p.name} x${qty}</div>
                            <div>${(p.price * qty).toLocaleString()}₽
                                <button onclick="changeQty(${p.id}, -1)" style="background:#2a2a3a; border:none; color:white; width:28px; border-radius:8px; margin-left:8px;">-</button>
                                <button onclick="changeQty(${p.id}, 1)" style="background:#2a2a3a; border:none; color:white; width:28px; border-radius:8px;">+</button>
                            </div>
                        </div>
                    `;
                }
            }
            html += `<div style="margin-top:15px; padding-top:15px; border-top:1px solid #333; text-align:right; font-size:18px; font-weight:bold;">💰 ИТОГО: ${total.toLocaleString()}₽</div>`;
            container.innerHTML = html;
        }

        function changeQty(id, delta) {
            cart[id] = Math.max(0, (cart[id] || 0) + delta);
            if (cart[id] === 0) delete cart[id];
            saveCart();
            updateCartBadge();
            renderCart();
        }

        async function submitOrder() {
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
                cart = {};
                saveCart();
                updateCartBadge();
                closeModal('cartModal');
                document.getElementById('userName').value = '';
                document.getElementById('userUsername').value = '';
                document.getElementById('userComment').value = '';
            } else {
                showStatus('❌ Откройте магазин через Telegram бота', true);
            }
        }

        // АДМИН ФУНКЦИИ
        function openAdmin() {
            if (!isAdmin) {
                const pwd = prompt('Введите пароль администратора:');
                if (pwd === 'admin123') {
                    isAdmin = true;
                    showStatus('✅ Добро пожаловать в админ-панель');
                } else {
                    showStatus('❌ Неверный пароль', true);
                    return;
                }
            }
            renderAdminProducts();
            document.getElementById('adminModal').classList.add('active');
        }

        function renderAdminProducts() {
            const html = products.map(p => `
                <div class="admin-product">
                    <div>
                        <div style="font-weight:bold;">${p.emoji} ${p.name}</div>
                        <div style="font-size:12px; color:#888;">${p.price}₽ | ${p.category}</div>
                    </div>
                    <div>
                        <button onclick="editProduct(${p.id})" style="background:#a855f7; border:none; color:white; width:36px; height:36px; border-radius:10px; margin-right:5px;">✏️</button>
                        <button onclick="deleteProduct(${p.id})" style="background:#ff4466; border:none; color:white; width:36px; height:36px; border-radius:10px;">🗑️</button>
                    </div>
                </div>
            `).join('');
            document.getElementById('adminProducts').innerHTML = html || '<div style="text-align:center; padding:20px;">Товаров нет</div>';
        }

        function showAddProduct() {
            editingProductId = null;
            document.getElementById('productModalTitle').textContent = '➕ Добавить товар';
            document.getElementById('productEmoji').value = '💨';
            document.getElementById('productName').value = '';
            document.getElementById('productDesc').value = '';
            document.getElementById('productCategory').value = 'device';
            document.getElementById('productPrice').value = '';
            document.getElementById('productStock').checked = true;
            document.getElementById('productModal').classList.add('active');
        }

        function editProduct(id) {
            const p = products.find(p => p.id === id);
            if (!p) return;
            editingProductId = id;
            document.getElementById('productModalTitle').textContent = '✏️ Редактировать товар';
            document.getElementById('productEmoji').value = p.emoji;
            document.getElementById('productName').value = p.name;
            document.getElementById('productDesc').value = p.desc || '';
            document.getElementById('productCategory').value = p.category;
            document.getElementById('productPrice').value = p.price;
            document.getElementById('productStock').checked = p.stock;
            document.getElementById('productModal').classList.add('active');
        }

        async function saveProduct() {
            const name = document.getElementById('productName').value.trim();
            const price = parseInt(document.getElementById('productPrice').value);
            if (!name || !price) {
                showStatus('❌ Заполните название и цену', true);
                return;
            }

            const product = {
                emoji: document.getElementById('productEmoji').value || '💨',
                name: name,
                desc: document.getElementById('productDesc').value,
                category: document.getElementById('productCategory').value,
                price: price,
                stock: document.getElementById('productStock').checked
            };

            let newProducts = [...products];
            if (editingProductId) {
                const index = newProducts.findIndex(p => p.id === editingProductId);
                newProducts[index] = { ...newProducts[index], ...product };
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
            } catch(e) {
                console.error(e);
                showStatus('❌ Ошибка сохранения', true);
            }
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
            } catch(e) {
                console.error(e);
            }
        }

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }

        // Показываем кнопку админа по кликам на лого
        let clickCount = 0;
        document.querySelector('.logo').onclick = () => {
            clickCount++;
            if (clickCount >= 5) {
                document.getElementById('adminBtn').style.display = 'flex';
                clickCount = 0;
            }
        };

        loadProducts();
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
        elif self.path == '/api/products':
            self.send_json(load_products())
        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        if self.path == '/api/products':
            try:
                data = json.loads(body)
                save_products(data['products'])
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'error': str(e)}, 400)
        else:
            self.send_json({'error': 'Not found'}, 404)

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
        "🔥 *GUBERVAPE* — премиум вейп шоп\n\n"
        "Нажмите кнопку чтобы открыть магазин",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = json.loads(update.message.web_app_data.data)
    log.info(f"Заказ от {user.id}: {data.get('type')}")

    if data.get('type') == 'order':
        # Отправляем админу
        items_text = "\n".join(
            [f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']}₽ = {i['qty'] * i['price']}₽" for i in
             data['items']])
        msg = (
            f"🚨 *НОВЫЙ ЗАКАЗ!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 ФИО: {data['name']}\n"
            f"📱 Telegram: {data['username']}\n\n"
            f"📦 Товары:\n{items_text}\n\n"
            f"💰 ИТОГО: {data['total']}₽"
        )
        if data.get('comment'):
            msg += f"\n\n💬 Коммент: {data['comment']}"

        await ctx.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")

        # Подтверждение пользователю
        await update.message.reply_text(f"✅ Заказ принят! Сумма: {data['total']}₽\nСпасибо за заказ!")


def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"HTTP сервер на {PORT}")
    server.serve_forever()


def main():
    threading.Thread(target=run_http, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_data))
    log.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
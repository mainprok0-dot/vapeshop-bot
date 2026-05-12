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
ADMIN_ID = 8237417166  # ВАШ Telegram ID (для проверки: напишите @userinfobot)
PORT = int(os.environ.get("PORT", 8080))
# ================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Простой HTML магазин (всё в одном файле)
HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; background: #0a0a0f; color: white; padding: 20px; padding-bottom: 80px; }
        .header { text-align: center; padding: 20px; background: linear-gradient(135deg, #1a0a2e, #0a0a0f); border-radius: 20px; margin-bottom: 20px; }
        .logo { font-size: 32px; font-weight: bold; background: linear-gradient(135deg, #c084fc, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .product { background: #12121a; border-radius: 16px; padding: 15px; margin-bottom: 12px; border: 1px solid #2a2a3a; display: flex; justify-content: space-between; align-items: center; }
        .product-info { flex: 1; }
        .product-name { font-weight: bold; font-size: 16px; }
        .product-price { color: #c084fc; font-weight: bold; }
        .add-btn { background: #a855f7; border: none; padding: 10px 20px; border-radius: 12px; color: white; font-weight: bold; cursor: pointer; }
        .cart-btn { position: fixed; bottom: 20px; right: 20px; background: #a855f7; width: 56px; height: 56px; border-radius: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 28px; box-shadow: 0 4px 12px rgba(168,85,247,0.4); z-index: 100; }
        .cart-count { position: absolute; top: -5px; right: -5px; background: #ff4466; width: 22px; height: 22px; border-radius: 11px; font-size: 12px; display: flex; align-items: center; justify-content: center; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 200; padding: 20px; overflow-y: auto; }
        .modal.active { display: block; }
        .modal-content { background: #12121a; border-radius: 24px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .modal-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
        .close { background: none; border: none; color: white; font-size: 24px; cursor: pointer; }
        input, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; color: white; }
        .submit-btn { width: 100%; padding: 14px; background: #a855f7; border: none; border-radius: 12px; color: white; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 15px; }
        .status { position: fixed; bottom: 100px; left: 20px; right: 20px; background: #1a1a2a; padding: 12px; border-radius: 12px; text-align: center; display: none; z-index: 150; border: 1px solid #a855f7; }
        .admin-btn { position: fixed; bottom: 20px; left: 20px; background: #2a2a3a; width: 44px; height: 44px; border-radius: 22px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; z-index: 100; display: none; }
        .admin-product { background: #1a1a2a; padding: 12px; margin: 8px 0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">GUBERVAPE</div>
        <div style="font-size: 12px; color: #888; margin-top: 5px;">ВЕЙП ШОП</div>
    </div>

    <div id="products"></div>

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
        let products = [
            {id: 1, emoji: "💨", name: "VUSE Alto Pro", desc: "Мощное устройство", category: "device", price: 2990, stock: true},
            {id: 2, emoji: "🔥", name: "SMOK Nord 5", desc: "80W с pods", category: "device", price: 3490, stock: true},
            {id: 3, emoji: "🌊", name: "BLVK Salt Mango", desc: "Солевая жидкость", category: "liquid", price: 850, stock: true},
            {id: 4, emoji: "❄️", name: "ICE Salt Mint", desc: "Ледяная мята", category: "liquid", price: 790, stock: true},
            {id: 5, emoji: "🍓", name: "ELFBAR Strawberry", desc: "600 затяжек", category: "pod", price: 650, stock: true},
            {id: 6, emoji: "🍋", name: "GEEK BAR Lemon", desc: "575 затяжек", category: "pod", price: 620, stock: true}
        ];
        let cart = {};
        let isAdmin = false;
        let editingId = null;
        let tg = window.Telegram?.WebApp;

        if (tg) { tg.expand(); tg.ready(); console.log("Telegram WebApp готов"); }

        function showStatus(msg, isError = false) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.style.background = isError ? '#ff446620' : '#00e67620';
            el.style.border = isError ? '1px solid #ff4466' : '1px solid #00e676';
            el.style.display = 'block';
            setTimeout(() => { el.style.display = 'none'; }, 3000);
        }

        function renderProducts() {
            const html = products.map(p => `
                <div class="product">
                    <div class="product-info">
                        <div class="product-name">${p.emoji} ${p.name}</div>
                        <div style="font-size:12px;color:#888;">${p.desc || ''}</div>
                        <div class="product-price">${p.price.toLocaleString()}₽</div>
                    </div>
                    <button class="add-btn" onclick="addToCart(${p.id})">+</button>
                </div>
            `).join('');
            document.getElementById('products').innerHTML = html || '<p>Нет товаров</p>';
        }

        function addToCart(id) {
            cart[id] = (cart[id] || 0) + 1;
            localStorage.setItem('cart', JSON.stringify(cart));
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

        function loadSavedCart() {
            const saved = localStorage.getItem('cart');
            if (saved) { cart = JSON.parse(saved); updateCartBadge(); }
        }

        function openCart() { renderCart(); document.getElementById('cartModal').classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        function renderCart() {
            const container = document.getElementById('cartItems');
            const items = Object.entries(cart);
            if (items.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#888;">Корзина пуста</div>';
                return;
            }
            let total = 0;
            let html = '';
            for (let [id, qty] of items) {
                const p = products.find(p => p.id == id);
                if (p) {
                    total += p.price * qty;
                    html += `
                        <div style="display:flex; justify-content:space-between; padding:10px; background:#1a1a2a; border-radius:10px; margin-bottom:8px;">
                            <div><strong>${p.emoji} ${p.name}</strong><br>${p.price.toLocaleString()}₽ × ${qty}</div>
                            <div>
                                <button onclick="changeQty(${p.id}, -1)" style="background:#2a2a3a; border:none; color:white; width:28px; border-radius:8px;">−</button>
                                <span style="margin:0 10px">${qty}</span>
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
            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartBadge();
            renderCart();
        }

        function submitOrder() {
            const name = document.getElementById('userName').value.trim();
            const username = document.getElementById('userUsername').value.trim();
            const comment = document.getElementById('userComment').value;

            if (!name) { showStatus('❌ Введите ФИО', true); return; }
            if (!username) { showStatus('❌ Введите Telegram username', true); return; }
            if (Object.keys(cart).length === 0) { showStatus('❌ Корзина пуста', true); return; }

            const items = Object.entries(cart).map(([id, qty]) => {
                const p = products.find(p => p.id == id);
                return {name: p.name, emoji: p.emoji, price: p.price, qty};
            });
            const total = items.reduce((s,i) => s + i.price * i.qty, 0);

            const orderData = {type: 'order', name, username, comment, total, items};

            console.log("Отправка заказа:", orderData);

            if (tg) {
                tg.sendData(JSON.stringify(orderData));
                showStatus('✅ Заказ отправлен! Мы свяжемся с вами');
                cart = {};
                localStorage.setItem('cart', JSON.stringify(cart));
                updateCartBadge();
                closeModal('cartModal');
                document.getElementById('userName').value = '';
                document.getElementById('userUsername').value = '';
                document.getElementById('userComment').value = '';
            } else {
                showStatus('❌ Ошибка: откройте магазин через Telegram бота', true);
            }
        }

        // АДМИН ФУНКЦИИ (5 кликов по логотипу)
        let clickCount = 0;
        document.querySelector('.logo').onclick = () => {
            clickCount++;
            if (clickCount >= 5) {
                const pwd = prompt('Введите пароль администратора:');
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
                    <div><strong>${p.emoji} ${p.name}</strong><br>${p.price}₽ | ${p.category}</div>
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
            document.getElementById('modalTitle').textContent = '✏️ Редактировать товар';
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
                stock: document.getElementById('pStock').checked
            };

            if (editingId) {
                const idx = products.findIndex(p => p.id === editingId);
                products[idx] = { ...products[idx], ...product };
            } else {
                const newId = Math.max(...products.map(p => p.id), 0) + 1;
                products.push({ id: newId, ...product });
            }

            renderProducts();
            closeModal('productModal');
            showStatus('✅ Товар сохранён');
        }

        function deleteProduct(id) {
            if (!confirm('Удалить товар?')) return;
            products = products.filter(p => p.id !== id);
            renderProducts();
            renderAdminProducts();
            showStatus('✅ Товар удалён');
        }

        // Загрузка
        loadSavedCart();
        renderProducts();
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
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[HTTP] {fmt % args}")


# ========== TELEGRAM БОТ ==========
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"Пользователь {user.id} (@{user.username}) запустил бота")

    # Получаем URL сервера
    webapp_url = f"https://{ctx.bot.get_me().username}.railway.app"
    log.info(f"WebApp URL: {webapp_url}")

    kb = [[InlineKeyboardButton("🛒 Открыть GuberVape", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        "🔥 *GUBERVAPE* — премиум вейп шоп\n\n"
        "Нажмите кнопку, чтобы открыть магазин и сделать заказ.\n\n"
        "📦 Доставка по всей России\n"
        "💳 Оплата при получении",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data_raw = update.message.web_app_data.data

    log.info(f"📦 ПОЛУЧЕНЫ ДАННЫЕ от пользователя {user.id}")
    log.info(f"Данные: {data_raw[:200]}")

    try:
        data = json.loads(data_raw)

        if data.get('type') == 'order':
            # Формируем сообщение для админа
            items_text = "\n".join([
                f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']:,}₽ = {i['qty'] * i['price']:,}₽"
                for i in data['items']
            ])

            msg_admin = (
                f"🚨 *НОВЫЙ ЗАКАЗ!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"👤 *ФИО:* {data['name']}\n"
                f"📱 *Telegram:* {data['username']}\n"
                f"🆔 *User ID:* `{user.id}`\n\n"
                f"📦 *Состав заказа:*\n{items_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *ИТОГО: {data['total']:,}₽*\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            if data.get('comment'):
                msg_admin += f"\n\n💬 *Комментарий:* {data['comment']}"

            # Отправляем админу (ВАМ)
            await ctx.bot.send_message(chat_id=ADMIN_ID, text=msg_admin, parse_mode="Markdown")
            log.info(f"✅ Заказ отправлен АДМИНУ {ADMIN_ID}")

            # Отправляем пользователю подтверждение
            msg_user = (
                f"✅ *ЗАКАЗ ПРИНЯТ!*\n\n"
                f"📦 Сумма заказа: *{data['total']:,}₽*\n\n"
                f"Мы свяжемся с вами в ближайшее время.\n"
                f"Спасибо за заказ в GuberVape! 🔥"
            )
            await update.message.reply_text(msg_user, parse_mode="Markdown")
            log.info(f"✅ Подтверждение отправлено ПОЛЬЗОВАТЕЛЮ {user.id}")

    except Exception as e:
        log.error(f"❌ Ошибка обработки: {e}")


async def cmd_test(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки связи"""
    await update.message.reply_text("✅ Бот работает! Ваш ID: " + str(update.effective_user.id))


# ========== ЗАПУСК ==========
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")
    server.serve_forever()


def main():
    # Запускаем HTTP сервер
    threading.Thread(target=run_http, daemon=True).start()

    # Запускаем Telegram бота
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", cmd_test))  # Тестовая команда
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info(f"🤖 Бот запущен!")
    log.info(f"👑 Админ ID: {ADMIN_ID} (должен быть ваш ID)")
    log.info(f"📱 Бот: @Guber_Shop_bot")
    log.info(f"💡 Команда /test - проверить работу бота")

    app.run_polling()


if __name__ == "__main__":
    main()
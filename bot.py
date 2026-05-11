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
YOUR_ID = 8237417166  # ВАШ Telegram ID (число!)
PORT = int(os.environ.get("PORT", 8080))
# ================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Файл для сохранения заказов
ORDERS_FILE = "orders.json"


# ========== СОХРАНЕНИЕ ЗАКАЗОВ В ФАЙЛ ==========
def save_order(order_data):
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            orders = json.load(f)

    order_data['order_id'] = len(orders) + 1
    order_data['date'] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    orders.append(order_data)

    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

    return order_data['order_id']


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
        body { font-family: system-ui; background: #0a0a0f; color: white; padding: 20px; padding-bottom: 80px; }
        .header { text-align: center; padding: 20px; background: linear-gradient(135deg, #1a0a2e, #0a0a0f); border-radius: 20px; margin-bottom: 20px; }
        .logo { font-size: 32px; font-weight: bold; background: linear-gradient(135deg, #c084fc, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .product { background: #12121a; border-radius: 16px; padding: 15px; margin-bottom: 12px; border: 1px solid #2a2a3a; display: flex; justify-content: space-between; align-items: center; }
        .product-info { flex: 1; }
        .product-name { font-weight: bold; font-size: 16px; }
        .product-price { color: #c084fc; font-weight: bold; }
        .add-btn { background: #a855f7; border: none; padding: 10px 20px; border-radius: 12px; color: white; font-weight: bold; cursor: pointer; }
        .cart-btn { position: fixed; bottom: 20px; right: 20px; background: #a855f7; width: 56px; height: 56px; border-radius: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 28px; box-shadow: 0 4px 12px rgba(168,85,247,0.4); }
        .cart-count { position: absolute; top: -5px; right: -5px; background: #ff4466; width: 22px; height: 22px; border-radius: 11px; font-size: 12px; display: flex; align-items: center; justify-content: center; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 200; padding: 20px; overflow-y: auto; }
        .modal.active { display: block; }
        .modal-content { background: #12121a; border-radius: 24px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .modal-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
        .close { background: none; border: none; color: white; font-size: 24px; cursor: pointer; }
        input, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; color: white; }
        .submit-btn { width: 100%; padding: 14px; background: #a855f7; border: none; border-radius: 12px; color: white; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 15px; }
        .status { position: fixed; bottom: 100px; left: 20px; right: 20px; background: #1a1a2a; padding: 12px; border-radius: 12px; text-align: center; display: none; z-index: 150; }
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
            <textarea id="userComment" placeholder="Адрес доставки, способ оплаты, пожелания..." rows="3"></textarea>
            <button class="submit-btn" onclick="submitOrder()">✅ ОФОРМИТЬ ЗАКАЗ</button>
        </div>
    </div>

    <script>
        let products = [
            {id: 1, emoji: "💨", name: "VUSE Alto Pro", price: 2990},
            {id: 2, emoji: "🔥", name: "SMOK Nord 5", price: 3490},
            {id: 3, emoji: "🌊", name: "BLVK Salt Mango", price: 850},
            {id: 4, emoji: "❄️", name: "ICE Salt Mint", price: 790},
            {id: 5, emoji: "🍓", name: "ELFBAR Strawberry", price: 650},
            {id: 6, emoji: "🍋", name: "GEEK BAR Lemon", price: 620}
        ];
        let cart = {};
        let tg = window.Telegram?.WebApp;

        if (tg) {
            tg.expand();
            tg.ready();
        }

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
                        <div class="product-price">${p.price.toLocaleString()}₽</div>
                    </div>
                    <button class="add-btn" onclick="addToCart(${p.id})">+ В корзину</button>
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
                        <div style="display:flex; justify-content:space-between; padding:10px; background:#1a1a2a; border-radius:10px; margin-bottom:8px;">
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

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
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
                showStatus('✅ Заказ отправлен! Мы свяжемся с вами');
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

        renderProducts();
        loadCart();
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
        elif self.path == '/orders':
            if os.path.exists(ORDERS_FILE):
                with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(f.read().encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


# ========== TELEGRAM БОТ ==========
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"Пользователь {user.id} запустил бота")

    url = f"https://{ctx.bot.get_me().username}.railway.app"
    kb = [[InlineKeyboardButton("🛒 Открыть GuberVape", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text(
        "🔥 *GUBERVAPE* — премиум вейп шоп\n\n"
        "Нажмите кнопку, чтобы открыть магазин и сделать заказ.\n\n"
        "📦 *Доставка по всей России*\n"
        "💳 *Оплата при получении*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data_raw = update.message.web_app_data.data

    log.info(f"📦 ПОЛУЧЕНЫ ДАННЫЕ от {user.id}: {data_raw[:200]}")

    try:
        data = json.loads(data_raw)

        if data.get('type') == 'order':
            # Сохраняем заказ в файл
            saved = save_order(data)
            log.info(f"✅ ЗАКАЗ #{saved} СОХРАНЁН в файл")

            # Формируем красивое сообщение
            items_text = "\n".join([
                f"  • {i['emoji']} {i['name']} — {i['qty']} шт × {i['price']:,}₽ = {i['qty'] * i['price']:,}₽"
                for i in data['items']
            ])

            msg = (
                f"🚨 *НОВЫЙ ЗАКАЗ #{saved}*\n"
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
                msg += f"\n\n💬 *Комментарий:* {data['comment']}"

            # Отправляем ОДНОВРЕМЕННО:
            # 1. Вам в личку
            try:
                await ctx.bot.send_message(chat_id=YOUR_ID, text=msg, parse_mode="Markdown")
                log.info(f"✅ Сообщение отправлено вам в личку ({YOUR_ID})")
            except Exception as e:
                log.error(f"❌ Ошибка отправки вам: {e}")

            # 2. Подтверждение пользователю
            await update.message.reply_text(
                f"✅ *ЗАКАЗ #{saved} ПРИНЯТ!*\n\n"
                f"📦 Сумма: *{data['total']:,}₽*\n\n"
                f"Мы свяжемся с вами в ближайшее время.\n"
                f"Спасибо за заказ! 🔥",
                parse_mode="Markdown"
            )

            log.info(f"✅ Заказ #{saved} полностью обработан")

    except json.JSONDecodeError as e:
        log.error(f"❌ Ошибка JSON: {e}")
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Команда /orders — показать последние заказы (только для админа)"""
    user_id = update.effective_user.id
    if user_id != YOUR_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    if not os.path.exists(ORDERS_FILE):
        await update.message.reply_text("📭 Заказов пока нет")
        return

    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        orders = json.load(f)

    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return

    # Показываем последние 5 заказов
    recent = orders[-5:]
    text = "📋 *Последние заказы:*\n\n"
    for o in recent:
        text += f"#{o['order_id']} — {o['date']}\n   {o['name']} — {o['total']:,}₽\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


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
    app.add_handler(CommandHandler("orders", cmd_orders))  # новая команда
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    log.info(f"🤖 Бот запущен!")
    log.info(f"👑 Ваш ID: {YOUR_ID}")
    log.info(f"📱 Бот: @Guber_Shop_bot")

    app.run_polling()


if __name__ == "__main__":
    main()
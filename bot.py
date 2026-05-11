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
ADMIN_ID = 8237417166  # ВАШ Telegram ID
PORT = int(os.environ.get("PORT", 8080))
# ================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Простой HTML магазин
HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        body { font-family: system-ui; background: #0a0a0f; color: white; padding: 20px; }
        .product { background: #1a1a2a; padding: 15px; margin: 10px 0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
        button { background: #a855f7; border: none; padding: 10px 20px; border-radius: 10px; color: white; cursor: pointer; }
        input, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 8px; color: white; }
        .cart-btn { position: fixed; bottom: 20px; right: 20px; background: #a855f7; width: 56px; height: 56px; border-radius: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 28px; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); padding: 20px; overflow-y: auto; z-index: 200; }
        .modal.active { display: block; }
        .modal-content { background: #12121a; border-radius: 20px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .close { float: right; font-size: 24px; cursor: pointer; background: none; border: none; color: white; }
        .admin-btn { position: fixed; bottom: 20px; left: 20px; background: #2a2a3a; width: 44px; height: 44px; border-radius: 22px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; display: none; }
    </style>
</head>
<body>
    <h1>🔥 GUBERVAPE</h1>
    <div id="products"></div>
    <div class="cart-btn" onclick="openCart()">🛒<span id="cartBadge" style="position:absolute;top:-5px;right:-5px;background:#ff4466;border-radius:50%;width:20px;height:20px;font-size:11px;display:none;"></span></div>
    <div class="admin-btn" id="adminBtn" onclick="openAdmin()">⚙️</div>

    <div class="modal" id="cartModal">
        <div class="modal-content">
            <button class="close" onclick="closeModal('cartModal')">✕</button>
            <h2>🛒 Корзина</h2>
            <div id="cartItems"></div>
            <input type="text" id="name" placeholder="Ваше ФИО *">
            <input type="text" id="username" placeholder="@username Telegram *">
            <textarea id="comment" placeholder="Адрес доставки" rows="2"></textarea>
            <button onclick="submitOrder()" style="width:100%; margin-top:15px;">✅ ОФОРМИТЬ</button>
        </div>
    </div>

    <div class="modal" id="adminModal">
        <div class="modal-content">
            <button class="close" onclick="closeModal('adminModal')">✕</button>
            <h2>⚙️ Админ-панель</h2>
            <button onclick="showAddProduct()">+ Добавить товар</button>
            <div id="adminProducts"></div>
        </div>
    </div>

    <div class="modal" id="productModal">
        <div class="modal-content">
            <button class="close" onclick="closeModal('productModal')">✕</button>
            <h2 id="modalTitle">Товар</h2>
            <input type="text" id="pEmoji" placeholder="Эмодзи" value="💨">
            <input type="text" id="pName" placeholder="Название">
            <input type="number" id="pPrice" placeholder="Цена">
            <select id="pCategory">
                <option value="device">Устройства</option>
                <option value="liquid">Жидкости</option>
                <option value="pod">Поды</option>
            </select>
            <button onclick="saveProduct()">💾 Сохранить</button>
        </div>
    </div>

    <script>
        let products = [
            {id:1, emoji:"💨", name:"VUSE Alto Pro", price:2990, category:"device"},
            {id:2, emoji:"🔥", name:"SMOK Nord 5", price:3490, category:"device"},
            {id:3, emoji:"🌊", name:"BLVK Mango", price:850, category:"liquid"}
        ];
        let cart = {};
        let isAdmin = false;
        let editingId = null;
        let tg = window.Telegram?.WebApp;
        if(tg) { tg.expand(); tg.ready(); }

        function renderProducts() {
            let html = '';
            for(let p of products) {
                html += `<div class="product">
                    <div><span style="font-size:32px">${p.emoji}</span> ${p.name}<br><b>${p.price}₽</b></div>
                    <button onclick="addToCart(${p.id})">+</button>
                </div>`;
            }
            document.getElementById('products').innerHTML = html;
        }

        function addToCart(id) {
            cart[id] = (cart[id]||0)+1;
            updateCartBadge();
            renderCart();
            if(tg) tg.HapticFeedback?.impactOccurred('light');
        }

        function updateCartBadge() {
            let total = Object.values(cart).reduce((a,b)=>a+b,0);
            let badge = document.getElementById('cartBadge');
            if(total>0) { badge.innerText=total; badge.style.display='flex'; }
            else { badge.style.display='none'; }
        }

        function renderCart() {
            let items = Object.entries(cart);
            if(items.length===0) { document.getElementById('cartItems').innerHTML='<p>Корзина пуста</p>'; return; }
            let total=0, html='';
            for(let [id,qty] of items) {
                let p = products.find(p=>p.id==id);
                if(p) { total+=p.price*qty; html+=`<div>${p.emoji} ${p.name} x${qty} = ${p.price*qty}₽</div>`; }
            }
            html+=`<h3>Итого: ${total}₽</h3>`;
            document.getElementById('cartItems').innerHTML=html;
        }

        function openCart() { renderCart(); document.getElementById('cartModal').classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        function submitOrder() {
            let name = document.getElementById('name').value.trim();
            let username = document.getElementById('username').value.trim();
            let comment = document.getElementById('comment').value;
            if(!name) { alert('Введите ФИО'); return; }
            if(!username) { alert('Введите username'); return; }

            let items = Object.entries(cart).map(([id,qty])=>{
                let p = products.find(p=>p.id==id);
                return {name:p.name, emoji:p.emoji, price:p.price, qty};
            });
            let total = items.reduce((s,i)=>s+i.price*i.qty,0);
            let orderData = {type:'order', name, username, comment, total, items};

            if(tg) {
                tg.sendData(JSON.stringify(orderData));
                alert('✅ Заказ отправлен!');
                cart = {};
                updateCartBadge();
                closeModal('cartModal');
                document.getElementById('name').value='';
                document.getElementById('username').value='';
                document.getElementById('comment').value='';
            } else { alert('Откройте магазин через Telegram'); }
        }

        // Админ панель (5 кликов по заголовку)
        let clickCount=0;
        document.querySelector('h1').onclick = () => {
            clickCount++;
            if(clickCount>=5) {
                let pwd = prompt('Пароль:');
                if(pwd==='admin123') {
                    isAdmin=true;
                    document.getElementById('adminBtn').style.display='flex';
                    alert('Админ-панель открыта');
                }
                clickCount=0;
            }
        };

        function openAdmin() { renderAdminProducts(); document.getElementById('adminModal').classList.add('active'); }

        function renderAdminProducts() {
            let html='';
            for(let p of products) {
                html+=`<div style="background:#1a1a2a;padding:10px;margin:5px 0;display:flex;justify-content:space-between">
                    <div>${p.emoji} ${p.name} (${p.price}₽)</div>
                    <div><button onclick="editProduct(${p.id})">✏️</button> <button onclick="deleteProduct(${p.id})">🗑️</button></div>
                </div>`;
            }
            document.getElementById('adminProducts').innerHTML=html;
        }

        function showAddProduct() {
            editingId=null;
            document.getElementById('modalTitle').innerText='➕ Добавить товар';
            document.getElementById('pEmoji').value='💨';
            document.getElementById('pName').value='';
            document.getElementById('pPrice').value='';
            document.getElementById('productModal').classList.add('active');
        }

        function editProduct(id) {
            let p = products.find(p=>p.id==id);
            if(!p) return;
            editingId=id;
            document.getElementById('modalTitle').innerText='✏️ Редактировать';
            document.getElementById('pEmoji').value=p.emoji;
            document.getElementById('pName').value=p.name;
            document.getElementById('pPrice').value=p.price;
            document.getElementById('productModal').classList.add('active');
        }

        async function saveProduct() {
            let name = document.getElementById('pName').value.trim();
            let price = parseInt(document.getElementById('pPrice').value);
            if(!name || !price) { alert('Заполните все поля'); return; }

            let product = {
                emoji: document.getElementById('pEmoji').value,
                name: name,
                price: price,
                category: 'device'
            };

            if(editingId) {
                let idx = products.findIndex(p=>p.id==editingId);
                products[idx] = {...products[idx], ...product};
            } else {
                let newId = Math.max(...products.map(p=>p.id),0)+1;
                products.push({id:newId, ...product});
            }

            // Сохраняем на сервер
            await fetch('/api/products', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({products: products})
            });

            renderProducts();
            closeModal('productModal');
            alert('✅ Сохранено');
        }

        async function deleteProduct(id) {
            if(!confirm('Удалить?')) return;
            products = products.filter(p=>p.id!==id);
            await fetch('/api/products', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({products: products})
            });
            renderProducts();
            renderAdminProducts();
        }

        renderProducts();
    </script>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        log.info(f"POST {self.path}: {body[:100]}")

        if self.path == '/api/products':
            try:
                data = json.loads(body)
                with open('products_backup.json', 'w') as f:
                    json.dump(data, f)
                self.send_response(200)
                self.end_headers()
            except:
                pass
        else:
            self.send_response(200)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = f"https://{ctx.bot.get_me().username}.railway.app"
    kb = [[InlineKeyboardButton("🛒 Магазин", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text("🔥 GuberVape\nНажми кнопку:", reply_markup=InlineKeyboardMarkup(kb))


async def handle_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = json.loads(update.message.web_app_data.data)

    log.info(f"📦 ЗАКАЗ от {user.id}: {data.get('name')} - {data.get('total')}₽")

    if data.get('type') == 'order':
        # Сохраняем в файл
        orders = []
        if os.path.exists('orders.json'):
            with open('orders.json', 'r') as f:
                orders = json.load(f)

        order_id = len(orders) + 1
        data['order_id'] = order_id
        data['date'] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        orders.append(data)

        with open('orders.json', 'w') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

        log.info(f"✅ Заказ #{order_id} сохранён в orders.json")

        # Отправляем админу
        msg = f"🚨 НОВЫЙ ЗАКАЗ #{order_id}\nФИО: {data['name']}\nTelegram: {data['username']}\nСумма: {data['total']}₽"
        await ctx.bot.send_message(chat_id=ADMIN_ID, text=msg)

        # Подтверждение пользователю
        await update.message.reply_text(f"✅ Заказ #{order_id} принят!\nСумма: {data['total']}₽")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    if not os.path.exists('orders.json'):
        await update.message.reply_text("📭 Заказов пока нет")
        return

    with open('orders.json', 'r') as f:
        orders = json.load(f)

    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return

    text = "📋 ПОСЛЕДНИЕ ЗАКАЗЫ:\n\n"
    for o in orders[-5:]:
        text += f"#{o['order_id']} | {o['date']}\n{o['name']} - {o['total']}₽\n\n"

    await update.message.reply_text(text)


def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


def main():
    threading.Thread(target=run_http, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_data))

    log.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
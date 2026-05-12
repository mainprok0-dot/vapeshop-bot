#!/usr/bin/env python3
import os
import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8580758584:AAFLoIN4PVFnQoC_RssMvLaWRhRtQjbep1k")
ADMIN_ID  = 8237417166
PORT      = int(os.environ.get("PORT", 8080))
DATA_FILE = "shop_data.json"
# ================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ========== ДАННЫЕ ПО УМОЛЧАНИЮ ==========
DEFAULT_DATA = {
    "products": [
        {"id": 1, "emoji": "💨", "name": "VUSE Alto Pro",       "desc": "Устройство с регулировкой мощности", "category": "device", "price": 2990, "stock": True,  "badge": ""},
        {"id": 2, "emoji": "🔥", "name": "SMOK Nord 5",         "desc": "Мощный под-мод 80W",                 "category": "device", "price": 3490, "stock": True,  "badge": ""},
        {"id": 3, "emoji": "🌊", "name": "BLVK Salt Mango",     "desc": "Солевая жидкость 30мл",              "category": "liquid", "price": 850,  "stock": True,  "badge": ""},
        {"id": 4, "emoji": "❄️", "name": "ICE Salt Mint",       "desc": "Ледяная мята 30мл",                  "category": "liquid", "price": 790,  "stock": True,  "badge": ""},
        {"id": 5, "emoji": "🍓", "name": "ELFBAR Strawberry",   "desc": "Одноразовый под 600 затяжек",        "category": "pod",    "price": 650,  "stock": True,  "badge": ""},
        {"id": 6, "emoji": "🍋", "name": "GEEK BAR Lemon",      "desc": "Одноразовый под 575 затяжек",        "category": "pod",    "price": 620,  "stock": True,  "badge": ""},
    ],
    "categories": [
        {"key": "all",    "name": "Все",        "emoji": "🎯"},
        {"key": "device", "name": "Устройства", "emoji": "💨"},
        {"key": "liquid", "name": "Жидкости",   "emoji": "🌊"},
        {"key": "pod",    "name": "Поды",        "emoji": "🍓"},
        {"key": "acc",    "name": "Аксессуары",  "emoji": "⚡"},
    ],
    "orders": []
}

# ========== РАБОТА С ДАННЫМИ ==========
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки: {e}")
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Ошибка сохранения: {e}")

def save_order(order_data):
    data = load_data()
    if "orders" not in data:
        data["orders"] = []
    order_id = len(data["orders"]) + 1
    order_data["order_id"] = order_id
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    data["orders"].append(order_data)
    save_data(data)
    return order_id

# ========== HTML СТРАНИЦА (встроена в бот) ==========
HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <title>GuberVape</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #fff; padding-bottom: 100px; }

        /* HEADER */
        .header { background: linear-gradient(135deg, #1a0a2e, #0a0a0f); padding: 18px 20px; text-align: center; border-bottom: 1px solid #2a1a4a; position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 26px; font-weight: 900; background: linear-gradient(135deg, #c084fc, #a855f7, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px; cursor: pointer; }
        .sub { font-size: 10px; color: #6b6b8a; margin-top: 4px; letter-spacing: 3px; }

        /* КАТЕГОРИИ */
        .categories { display: flex; gap: 8px; padding: 12px 16px; overflow-x: auto; background: #0f0f14; border-bottom: 1px solid #2a2a3a; scrollbar-width: none; }
        .categories::-webkit-scrollbar { display: none; }
        .cat-btn { padding: 8px 16px; border-radius: 30px; background: #1a1a2a; border: 1px solid #2a2a3a; color: #a1a1aa; font-size: 13px; white-space: nowrap; cursor: pointer; transition: all 0.2s; flex-shrink: 0; }
        .cat-btn.active { background: linear-gradient(135deg, #7c3aed, #a855f7); border-color: #a855f7; color: white; }

        /* ТОВАРЫ */
        .products { padding: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .product-card { background: #12121a; border: 1px solid #2a2a3a; border-radius: 16px; overflow: hidden; transition: all 0.2s; cursor: pointer; }
        .product-card:active { transform: scale(0.97); border-color: #a855f7; }
        .product-img { background: linear-gradient(135deg, #1a1a2a, #0f0f14); padding: 22px; text-align: center; font-size: 46px; position: relative; }
        .badge { position: absolute; top: 8px; left: 8px; background: #a855f7; color: white; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 20px; text-transform: uppercase; }
        .badge.sale { background: #ff4466; }
        .badge.new { background: #a855f7; }
        .badge.hit { background: #f97316; }
        .product-info { padding: 10px 12px 12px; }
        .product-name { font-weight: 700; font-size: 14px; margin-bottom: 3px; }
        .product-desc { font-size: 11px; color: #6b6b8a; margin-bottom: 8px; line-height: 1.4; }
        .product-footer { display: flex; justify-content: space-between; align-items: center; }
        .product-price { font-size: 18px; font-weight: 700; color: #c084fc; }
        .add-btn { background: linear-gradient(135deg, #7c3aed, #a855f7); border: none; width: 32px; height: 32px; border-radius: 10px; color: white; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .add-btn:active { transform: scale(0.85); }
        .in-cart-badge { position: absolute; bottom: 8px; right: 8px; background: #a855f7; color: white; border-radius: 50%; width: 20px; height: 20px; font-size: 11px; font-weight: 900; display: flex; align-items: center; justify-content: center; }

        /* КОРЗИНА КНОПКА */
        .cart-fab { position: fixed; bottom: 24px; right: 20px; background: linear-gradient(135deg, #7c3aed, #a855f7); width: 58px; height: 58px; border-radius: 29px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 20px rgba(168,85,247,0.5); z-index: 200; font-size: 24px; }
        .cart-count { position: absolute; top: -4px; right: -4px; background: #ff4466; width: 20px; height: 20px; border-radius: 10px; font-size: 11px; font-weight: 900; display: flex; align-items: center; justify-content: center; }

        /* КНОПКА АДМИН */
        .admin-fab { position: fixed; bottom: 24px; left: 20px; background: #1a1a2a; border: 1px solid #2a2a3a; width: 46px; height: 46px; border-radius: 23px; display: none; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; z-index: 200; }

        /* МОДАЛКИ */
        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 300; overflow-y: auto; padding: 16px; }
        .modal.active { display: block; }
        .modal-box { background: #12121a; border-radius: 20px; padding: 20px; max-width: 480px; margin: 0 auto; border: 1px solid #2a2a3a; }
        .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #2a2a3a; }
        .modal-head h2 { font-size: 18px; }
        .close-btn { background: #2a2a3a; border: none; color: white; width: 32px; height: 32px; border-radius: 10px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }

        /* ФОРМА */
        .field { width: 100%; padding: 12px 14px; margin: 6px 0; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 12px; color: white; font-size: 14px; outline: none; transition: border-color 0.2s; }
        .field:focus { border-color: #a855f7; }
        .field::placeholder { color: #555; }
        label { color: #a1a1aa; font-size: 12px; margin-top: 8px; display: block; }

        /* КНОПКИ */
        .btn-primary { width: 100%; padding: 14px; background: linear-gradient(135deg, #7c3aed, #a855f7); border: none; border-radius: 14px; color: white; font-weight: 700; font-size: 16px; cursor: pointer; margin-top: 12px; }
        .btn-primary:active { transform: scale(0.98); }
        .btn-secondary { background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 12px; color: #a1a1aa; padding: 10px 16px; font-size: 14px; cursor: pointer; }

        /* КОРЗИНА */
        .cart-item { background: #1a1a2a; border-radius: 14px; padding: 12px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
        .cart-item-info { flex: 1; min-width: 0; }
        .cart-item-name { font-weight: 700; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .cart-item-price { font-size: 12px; color: #c084fc; margin-top: 2px; }
        .qty-row { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
        .qty-btn { background: #2a2a3a; border: none; color: white; width: 28px; height: 28px; border-radius: 8px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .qty-btn:active { background: #7c3aed; }
        .qty-num { font-size: 16px; font-weight: 700; min-width: 20px; text-align: center; }
        .cart-total { background: linear-gradient(135deg, #1a0a2e, #1a1a2a); border: 1px solid #7c3aed; border-radius: 14px; padding: 14px; margin: 14px 0; display: flex; justify-content: space-between; align-items: center; }
        .total-label { color: #a1a1aa; font-size: 14px; }
        .total-amount { font-size: 22px; font-weight: 900; color: #c084fc; }

        /* СТАТУС */
        .toast { position: fixed; bottom: 110px; left: 20px; right: 20px; padding: 12px 16px; border-radius: 14px; text-align: center; font-weight: 600; font-size: 14px; display: none; z-index: 400; }

        /* АДМИН */
        .admin-item { background: #1a1a2a; padding: 12px 14px; margin: 8px 0; border-radius: 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
        .admin-item-info { flex: 1; min-width: 0; }
        .admin-item-name { font-weight: 700; font-size: 14px; }
        .admin-item-meta { font-size: 12px; color: #6b6b8a; margin-top: 2px; }
        .admin-btns { display: flex; gap: 6px; flex-shrink: 0; }
        .btn-edit { background: rgba(168,85,247,0.2); border: none; color: #a855f7; width: 34px; height: 34px; border-radius: 10px; cursor: pointer; font-size: 16px; }
        .btn-del  { background: rgba(255,68,102,0.2); border: none; color: #ff4466; width: 34px; height: 34px; border-radius: 10px; cursor: pointer; font-size: 16px; }
        .btn-add-product { width: 100%; padding: 12px; background: transparent; border: 2px dashed #2a2a3a; border-radius: 14px; color: #6b6b8a; font-size: 14px; cursor: pointer; margin-bottom: 10px; }
        .btn-add-product:active { border-color: #a855f7; color: #a855f7; }

        .empty { text-align: center; padding: 40px 20px; color: #555; }
        .empty .icon { font-size: 48px; margin-bottom: 12px; }
    </style>
</head>
<body>

<div class="header">
    <div class="logo" id="logoClick">GUBERVAPE</div>
    <div class="sub">• VAPE SHOP •</div>
</div>

<div class="categories" id="categoriesBar"></div>
<div class="products"   id="productsGrid"></div>

<!-- Кнопка корзины -->
<div class="cart-fab" onclick="openCart()">
    🛒
    <div class="cart-count" id="cartBadge" style="display:none">0</div>
</div>

<!-- Кнопка админа (скрыта) -->
<div class="admin-fab" id="adminFab" onclick="openAdmin()">⚙️</div>

<!-- Toast уведомление -->
<div class="toast" id="toast"></div>

<!-- ===== МОДАЛКА: КОРЗИНА ===== -->
<div class="modal" id="cartModal">
    <div class="modal-box">
        <div class="modal-head">
            <h2>🛒 Корзина</h2>
            <button class="close-btn" onclick="closeModal('cartModal')">✕</button>
        </div>
        <div id="cartItems"></div>
        <div id="cartForm" style="display:none">
            <label>ФИО *</label>
            <input class="field" type="text"  id="userName"     placeholder="Иванов Иван Иванович">
            <label>Username Telegram *</label>
            <input class="field" type="text"  id="userUsername" placeholder="@username">
            <label>Комментарий (необязательно)</label>
            <textarea class="field" id="userComment" placeholder="Адрес, способ доставки..." rows="2" style="resize:none"></textarea>
            <button class="btn-primary" onclick="submitOrder()">✅ ОФОРМИТЬ ЗАКАЗ</button>
        </div>
    </div>
</div>

<!-- ===== МОДАЛКА: АДМИН ===== -->
<div class="modal" id="adminModal">
    <div class="modal-box">
        <div class="modal-head">
            <h2>⚙️ Управление</h2>
            <button class="close-btn" onclick="closeModal('adminModal')">✕</button>
        </div>
        <button class="btn-add-product" onclick="openProductForm(null)">+ Добавить товар</button>
        <div id="adminList"></div>
    </div>
</div>

<!-- ===== МОДАЛКА: ФОРМА ТОВАРА ===== -->
<div class="modal" id="productModal">
    <div class="modal-box">
        <div class="modal-head">
            <h2 id="productModalTitle">Товар</h2>
            <button class="close-btn" onclick="closeModal('productModal')">✕</button>
        </div>
        <label>Эмодзи</label>
        <input class="field" type="text" id="pEmoji"    placeholder="💨" value="💨">
        <label>Название *</label>
        <input class="field" type="text" id="pName"     placeholder="Название товара">
        <label>Описание</label>
        <input class="field" type="text" id="pDesc"     placeholder="Краткое описание">
        <label>Категория</label>
        <select class="field" id="pCategory">
            <option value="device">Устройства</option>
            <option value="liquid">Жидкости</option>
            <option value="pod">Поды</option>
            <option value="acc">Аксессуары</option>
        </select>
        <label>Цена (₽) *</label>
        <input class="field" type="number" id="pPrice"  placeholder="0">
        <label>Бейдж</label>
        <select class="field" id="pBadge">
            <option value="">Нет</option>
            <option value="new">NEW</option>
            <option value="sale">SALE</option>
            <option value="hit">HIT</option>
        </select>
        <label style="display:flex;align-items:center;gap:10px;margin-top:10px;cursor:pointer">
            <input type="checkbox" id="pStock" checked style="width:18px;height:18px;accent-color:#a855f7"> В наличии
        </label>
        <button class="btn-primary" onclick="saveProduct()">💾 Сохранить</button>
    </div>
</div>

<script>
    // ===== СОСТОЯНИЕ =====
    let products      = [];
    let categories    = [];
    let cart          = {};
    let currentCat    = 'all';
    let editingId     = null;
    let isAdmin       = false;
    let tg            = window.Telegram?.WebApp;

    if (tg) { tg.expand(); tg.ready(); }

    // ===== TOAST =====
    function showToast(msg, ok = true) {
        const el = document.getElementById('toast');
        el.textContent = msg;
        el.style.background    = ok ? 'rgba(0,230,118,0.15)' : 'rgba(255,68,102,0.15)';
        el.style.border        = ok ? '1px solid #00e676'    : '1px solid #ff4466';
        el.style.color         = ok ? '#00e676'              : '#ff4466';
        el.style.display       = 'block';
        setTimeout(() => el.style.display = 'none', 2500);
    }

    // ===== ЗАГРУЗКА ДАННЫХ =====
    async function loadData() {
        try {
            const res  = await fetch('/api/data');
            const data = await res.json();
            products   = data.products   || [];
            categories = data.categories || [];
        } catch(e) {
            console.warn('Сервер недоступен, используем дефолтные данные');
            categories = [
                {key:'all',    name:'Все',        emoji:'🎯'},
                {key:'device', name:'Устройства', emoji:'💨'},
                {key:'liquid', name:'Жидкости',   emoji:'🌊'},
                {key:'pod',    name:'Поды',        emoji:'🍓'},
                {key:'acc',    name:'Аксессуары',  emoji:'⚡'},
            ];
            products = [];
        }
        renderCategories();
        renderProducts();
        loadCart();
    }

    // ===== КАТЕГОРИИ =====
    function renderCategories() {
        document.getElementById('categoriesBar').innerHTML = categories.map(c =>
            `<div class="cat-btn ${c.key===currentCat?'active':''}" onclick="filterCat('${c.key}')">${c.emoji} ${c.name}</div>`
        ).join('');
    }

    function filterCat(key) {
        currentCat = key;
        renderCategories();
        renderProducts();
    }

    // ===== ТОВАРЫ =====
    function renderProducts() {
        const list = currentCat === 'all' ? products : products.filter(p => p.category === currentCat);
        const grid = document.getElementById('productsGrid');
        if (!list.length) {
            grid.innerHTML = '<div class="empty"><div class="icon">📦</div><p>Товаров нет</p></div>';
            return;
        }
        grid.innerHTML = list.map(p => {
            const qty = cart[p.id] || 0;
            const outOfStock = p.stock === false;
            return `
            <div class="product-card ${outOfStock ? 'style="opacity:0.5;pointer-events:none"' : ''}">
                <div class="product-img" style="${outOfStock?'opacity:0.5':''}">
                    ${p.emoji}
                    ${p.badge ? `<div class="badge ${p.badge}">${p.badge.toUpperCase()}</div>` : ''}
                    ${qty > 0 ? `<div class="in-cart-badge">${qty}</div>` : ''}
                </div>
                <div class="product-info">
                    <div class="product-name">${p.name}</div>
                    <div class="product-desc">${p.desc || ''}</div>
                    <div class="product-footer">
                        <div class="product-price">${p.price.toLocaleString()}₽</div>
                        <button class="add-btn" onclick="addToCart(${p.id})">+</button>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    // ===== КОРЗИНА =====
    function addToCart(id) {
        cart[id] = (cart[id] || 0) + 1;
        saveCart();
        updateCartBadge();
        renderProducts();
        showToast('✅ Добавлено в корзину');
        if (tg) tg.HapticFeedback?.impactOccurred('light');
    }

    function changeQty(id, delta) {
        cart[id] = Math.max(0, (cart[id] || 0) + delta);
        if (!cart[id]) delete cart[id];
        saveCart();
        updateCartBadge();
        renderProducts();
        renderCartItems();
    }

    function saveCart()  { localStorage.setItem('gv_cart', JSON.stringify(cart)); }
    function loadCart()  { try { cart = JSON.parse(localStorage.getItem('gv_cart') || '{}'); } catch(e){} updateCartBadge(); }

    function updateCartBadge() {
        const total = Object.values(cart).reduce((a,b)=>a+b, 0);
        const badge = document.getElementById('cartBadge');
        badge.textContent    = total;
        badge.style.display  = total > 0 ? 'flex' : 'none';
    }

    function openCart() {
        renderCartItems();
        document.getElementById('cartModal').classList.add('active');
    }

    function renderCartItems() {
        const entries = Object.entries(cart).filter(([,q])=>q>0);
        const itemsEl = document.getElementById('cartItems');
        const formEl  = document.getElementById('cartForm');

        if (!entries.length) {
            itemsEl.innerHTML = '<div class="empty"><div class="icon">🛒</div><p>Корзина пуста</p></div>';
            formEl.style.display = 'none';
            return;
        }

        let total = 0;
        const rows = entries.map(([id, qty]) => {
            const p = products.find(p => p.id == id);
            if (!p) return '';
            total += p.price * qty;
            return `
            <div class="cart-item">
                <div class="cart-item-info">
                    <div class="cart-item-name">${p.emoji} ${p.name}</div>
                    <div class="cart-item-price">${(p.price * qty).toLocaleString()}₽</div>
                </div>
                <div class="qty-row">
                    <button class="qty-btn" onclick="changeQty(${p.id}, -1)">−</button>
                    <div class="qty-num">${qty}</div>
                    <button class="qty-btn" onclick="changeQty(${p.id},  1)">+</button>
                </div>
            </div>`;
        }).join('');

        itemsEl.innerHTML = rows + `
            <div class="cart-total">
                <div class="total-label">ИТОГО</div>
                <div class="total-amount">${total.toLocaleString()}₽</div>
            </div>`;
        formEl.style.display = 'block';

        // Автозаполнение если Telegram знает пользователя
        if (tg?.initDataUnsafe?.user) {
            const u = tg.initDataUnsafe.user;
            const nameEl = document.getElementById('userName');
            const userEl = document.getElementById('userUsername');
            if (!nameEl.value && u.first_name) nameEl.value = [u.first_name, u.last_name].filter(Boolean).join(' ');
            if (!userEl.value && u.username)   userEl.value = '@' + u.username;
        }
    }

    function submitOrder() {
        const name     = document.getElementById('userName').value.trim();
        const username = document.getElementById('userUsername').value.trim();
        const comment  = document.getElementById('userComment').value.trim();

        if (!name)     { showToast('❌ Введите ФИО', false);              return; }
        if (!username) { showToast('❌ Введите Telegram username', false); return; }

        const items = Object.entries(cart)
            .filter(([,q]) => q > 0)
            .map(([id, qty]) => {
                const p = products.find(p => p.id == id);
                return p ? { name: p.name, emoji: p.emoji, price: p.price, qty } : null;
            }).filter(Boolean);

        const total = items.reduce((s, i) => s + i.price * i.qty, 0);

        const orderData = { type: 'order', name, username, comment, total, items };

        if (tg) {
            tg.sendData(JSON.stringify(orderData));
            // Очищаем корзину
            cart = {};
            saveCart();
            updateCartBadge();
            renderProducts();
            closeModal('cartModal');
            document.getElementById('userName').value    = '';
            document.getElementById('userUsername').value = '';
            document.getElementById('userComment').value  = '';
        } else {
            showToast('❌ Откройте через Telegram бота', false);
        }
    }

    // ===== МОДАЛКИ =====
    function closeModal(id) { document.getElementById(id).classList.remove('active'); }

    // ===== АДМИН =====
    // 5 кликов на лого
    let logoClicks = 0, logoTimer;
    document.getElementById('logoClick').onclick = () => {
        logoClicks++;
        clearTimeout(logoTimer);
        logoTimer = setTimeout(() => logoClicks = 0, 2000);
        if (logoClicks >= 5) {
            logoClicks = 0;
            const pwd = prompt('🔐 Пароль администратора:');
            if (pwd === 'guber2024') {
                isAdmin = true;
                document.getElementById('adminFab').style.display = 'flex';
                showToast('✅ Админ-панель открыта');
            } else if (pwd !== null) {
                showToast('❌ Неверный пароль', false);
            }
        }
    };

    function openAdmin() {
        if (!isAdmin) return;
        renderAdminList();
        document.getElementById('adminModal').classList.add('active');
    }

    function renderAdminList() {
        document.getElementById('adminList').innerHTML = products.map(p => `
            <div class="admin-item">
                <div class="admin-item-info">
                    <div class="admin-item-name">${p.emoji} ${p.name}</div>
                    <div class="admin-item-meta">${p.price.toLocaleString()}₽ · ${p.category} · ${p.stock!==false ? '✅ В наличии' : '❌ Нет'}</div>
                </div>
                <div class="admin-btns">
                    <button class="btn-edit" onclick="openProductForm(${p.id})">✏️</button>
                    <button class="btn-del"  onclick="deleteProduct(${p.id})">🗑️</button>
                </div>
            </div>`
        ).join('') || '<div class="empty"><p>Товаров нет</p></div>';
    }

    function openProductForm(id) {
        editingId = id;
        if (id === null) {
            document.getElementById('productModalTitle').textContent = '➕ Добавить товар';
            document.getElementById('pEmoji').value    = '💨';
            document.getElementById('pName').value     = '';
            document.getElementById('pDesc').value     = '';
            document.getElementById('pCategory').value = 'device';
            document.getElementById('pPrice').value    = '';
            document.getElementById('pBadge').value    = '';
            document.getElementById('pStock').checked  = true;
        } else {
            const p = products.find(p => p.id === id);
            if (!p) return;
            document.getElementById('productModalTitle').textContent = '✏️ Редактировать';
            document.getElementById('pEmoji').value    = p.emoji;
            document.getElementById('pName').value     = p.name;
            document.getElementById('pDesc').value     = p.desc || '';
            document.getElementById('pCategory').value = p.category;
            document.getElementById('pPrice').value    = p.price;
            document.getElementById('pBadge').value    = p.badge || '';
            document.getElementById('pStock').checked  = p.stock !== false;
        }
        document.getElementById('productModal').classList.add('active');
    }

    async function saveProduct() {
        const name  = document.getElementById('pName').value.trim();
        const price = parseInt(document.getElementById('pPrice').value);
        if (!name || !price) { showToast('❌ Заполните название и цену', false); return; }

        const productData = {
            emoji:    document.getElementById('pEmoji').value    || '💨',
            name,
            desc:     document.getElementById('pDesc').value,
            category: document.getElementById('pCategory').value,
            price,
            badge:    document.getElementById('pBadge').value,
            stock:    document.getElementById('pStock').checked,
        };

        let updated = [...products];
        if (editingId !== null) {
            const idx = updated.findIndex(p => p.id === editingId);
            updated[idx] = { ...updated[idx], ...productData };
        } else {
            const newId = updated.length ? Math.max(...updated.map(p => p.id)) + 1 : 1;
            updated.push({ id: newId, ...productData });
        }

        try {
            const res = await fetch('/api/products', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ products: updated }),
            });
            if (res.ok) {
                products = updated;
                renderProducts();
                renderAdminList();
                closeModal('productModal');
                showToast('✅ Товар сохранён!');
            } else {
                showToast('❌ Ошибка сохранения', false);
            }
        } catch(e) {
            showToast('❌ Нет связи с сервером', false);
        }
    }

    async function deleteProduct(id) {
        if (!confirm('Удалить товар?')) return;
        const updated = products.filter(p => p.id !== id);
        try {
            const res = await fetch('/api/products', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ products: updated }),
            });
            if (res.ok) {
                products = updated;
                renderProducts();
                renderAdminList();
                showToast('✅ Товар удалён');
            }
        } catch(e) {
            showToast('❌ Нет связи с сервером', false);
        }
    }

    // ===== СТАРТ =====
    loadData();
</script>
</body>
</html>"""


# ========== HTTP СЕРВЕР ==========
class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            body = HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/data':
            data = load_data()
            self.send_json({'products': data['products'], 'categories': data['categories']})
        elif self.path in ('/health', '/ping'):
            self.send_json({'status': 'ok'})
        else:
            self.send_json({'error': 'not found'}, 404)

    def do_POST(self):
        try:
            length  = int(self.headers.get('Content-Length', 0))
            body    = self.rfile.read(length)
            payload = json.loads(body)
        except Exception:
            self.send_json({'error': 'bad json'}, 400)
            return

        if self.path == '/api/products':
            data = load_data()
            data['products'] = payload.get('products', data['products'])
            save_data(data)
            log.info(f"✅ Товары обновлены ({len(data['products'])} шт)")
            self.send_json({'ok': True})
        else:
            self.send_json({'error': 'not found'}, 404)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, fmt, *args):
        pass


# ========== TELEGRAM БОТ ==========
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Кнопка открытия магазина"""
    # URL берём из Railway автоматически
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if railway_url:
        webapp_url = f"https://{railway_url}"
    else:
        webapp_url = os.environ.get("WEBAPP_URL", "https://your-app.up.railway.app")

    kb = [[InlineKeyboardButton(
        "🛒 Открыть GuberVape",
        web_app=WebAppInfo(url=webapp_url)
    )]]
    await update.message.reply_text(
        "🔥 *GuberVape — Vape Shop*\n\n"
        "Нажмите кнопку чтобы открыть каталог 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    log.info(f"▶️ /start от {update.effective_user.id}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Список заказов — только для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return
    data   = load_data()
    orders = data.get('orders', [])
    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return
    lines = [
        f"#{o['order_id']} | {o['date']}\n   👤 {o['name']} | 💰 {o['total']:,}₽"
        for o in orders[-15:]
    ]
    await update.message.reply_text(
        "📋 *ПОСЛЕДНИЕ ЗАКАЗЫ:*\n\n" + "\n\n".join(lines),
        parse_mode="Markdown"
    )


async def handle_webapp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получение данных из мини-приложения"""
    user = update.effective_user
    try:
        data  = json.loads(update.message.web_app_data.data)
        dtype = data.get('type')
        log.info(f"📦 WebApp от {user.id} (@{user.username}): type={dtype}")

        if dtype == 'order':
            # Сохраняем заказ
            order_id = save_order(data)

            name     = data.get('name', '—')
            username = data.get('username', '—')
            comment  = data.get('comment', '')
            items    = data.get('items', [])
            total    = data.get('total', 0)
            now      = datetime.now().strftime("%d.%m.%Y %H:%M")

            items_text = "\n".join([
                f"  {i['emoji']} {i['name']}\n  └ {i['qty']} шт × {i['price']:,}₽ = {i['qty']*i['price']:,}₽"
                for i in items
            ])

            # ЧЕК покупателю
            receipt = (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🧾 *ЧЕК ЗАКАЗА #{order_id}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📅 {now}\n\n"
                f"📦 *Состав:*\n{items_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *ИТОГО: {total:,}₽*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 {name}\n"
                f"📱 {username}\n"
            )
            if comment:
                receipt += f"💬 {comment}\n"
            receipt += "\n🔥 Спасибо за заказ! Скоро свяжемся с вами."

            await update.message.reply_text(receipt, parse_mode="Markdown")
            log.info(f"✅ Чек #{order_id} отправлен покупателю")

            # УВЕДОМЛЕНИЕ АДМИНУ
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

            log.info(f"📤 Отправляю уведомление на {ADMIN_ID}...")
            await ctx.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode="Markdown"
            )
            log.info(f"✅ Уведомление о заказе #{order_id} отправлено!")

        elif dtype == 'sync':
            # Синхронизация товаров от админа
            if user.id == ADMIN_ID:
                db = load_data()
                db['products'] = data.get('products', db['products'])
                save_data(db)
                log.info(f"✅ Товары синхронизированы от админа")

    except Exception as e:
        log.error(f"❌ Ошибка WebApp: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при обработке. Попробуйте ещё раз.")


# ========== ЗАПУСК ==========
def run_http():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")
    server.serve_forever()


def main():
    log.info("=" * 50)
    log.info("🔥 GuberVape Bot запускается...")
    log.info(f"👑 Admin ID : {ADMIN_ID}")
    log.info(f"🚪 Port     : {PORT}")
    log.info("=" * 50)

    threading.Thread(target=run_http, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp))

    log.info("🤖 Бот слушает сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

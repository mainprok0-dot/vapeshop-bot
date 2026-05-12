# 🔥 VapeShop — Telegram Mini App

## Что включено
```
vapeshop/
├── index.html   — Мини-приложение (фронтенд магазина)
└── bot.py       — Python-бот для приёма заказов
```

---

## ⚡ Быстрый старт

### Шаг 1. Создайте бота
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`, придумайте имя и username
3. Скопируйте **токен** — он нужен в `bot.py`
4. Отправьте `/newapp` — создайте Mini App (нужен URL хостинга)

### Шаг 2. Узнайте свой Telegram ID
Напишите [@userinfobot](https://t.me/userinfobot) — он пришлёт ваш ID.
Вставьте его в `bot.py` в поле `ADMIN_CHAT_ID`.

### Шаг 3. Разместите index.html на хостинге

**Вариант A — GitHub Pages (бесплатно):**
1. Создайте репозиторий на GitHub
2. Загрузите `index.html`
3. Settings → Pages → Source: main branch
4. Получите URL вида `https://username.github.io/repo/`

**Вариант B — Netlify (бесплатно, проще):**
1. Зайдите на [netlify.com](https://netlify.com)
2. Перетащите папку с `index.html`
3. Получите URL вида `https://random-name.netlify.app`

**Вариант C — Свой сервер:**
Поместите `index.html` в папку сайта (nginx/apache).
⚠️ Обязательно HTTPS!

### Шаг 4. Настройте bot.py
Откройте `bot.py` и замените:
```python
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"        # токен от BotFather
ADMIN_CHAT_ID = 123456789            # ваш Telegram ID
WEBAPP_URL = "https://ВАШ_САЙТ.com" # URL хостинга index.html
```

### Шаг 5. Запустите бота
```bash
pip install python-telegram-bot
python bot.py
```

### Шаг 6. Привяжите Mini App к боту
В @BotFather:
```
/mybots → Ваш бот → Bot Settings → Menu Button → Edit Menu Button URL
```
Вставьте URL вашего `index.html`.

---

## 🛠 Управление товарами

Панель администратора скрыта по умолчанию.

**Чтобы открыть:**
1. В приложении нажмите на логотип **VAPESHOP** **5 раз подряд**
2. Введите пароль (по умолчанию: `admin123`)
3. Появится вкладка **⚙️ Админ**

**Смените пароль** в `index.html`, найдите строку:
```javascript
const ADMIN_PASSWORD = 'admin123';
```

**В панели можно:**
- ➕ Добавлять товары
- ✏️ Редактировать (название, цена, описание, категория, наличие, бейдж)
- 🗑️ Удалять товары
- Менять статус "В наличии / Нет в наличии"

Все товары сохраняются в `localStorage` браузера мини-приложения.

---

## 📦 Как работают заказы

1. Пользователь добавляет товары в корзину
2. Вводит **ФИО** и **@username** Telegram (обязательно)
3. Опционально оставляет **комментарий**
4. Нажимает "ОФОРМИТЬ ЗАКАЗ"
5. Данные отправляются боту через `Telegram.WebApp.sendData()`
6. Бот пишет **пользователю** подтверждение
7. Бот пишет **вам** (ADMIN_CHAT_ID) уведомление с деталями заказа

---

## 🎨 Категории товаров

| Категория | Ключ |
|-----------|------|
| Устройства | `device` |
| Жидкости | `liquid` |
| Поды | `pod` |
| Аксессуары | `acc` |

---

## ⚠️ Важные замечания

- **HTTPS обязателен** — Telegram не открывает Mini App по HTTP
- Товары хранятся в `localStorage` — при очистке браузера сбросятся к дефолтным. Для постоянного хранения используйте бэкенд (например, простой JSON API)
- Бот должен быть **запущен** для получения заказов
- Для production рекомендуется запускать бота через `systemd` или `pm2`

---

## 🔄 Запуск бота как сервиса (Linux)

```bash
# Создайте файл сервиса
sudo nano /etc/systemd/system/vapeshop.service
```

```ini
[Unit]
Description=VapeShop Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/vapeshop
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable vapeshop
sudo systemctl start vapeshop
```

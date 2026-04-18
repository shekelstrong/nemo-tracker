# Telegram Mini App — Настройка

## 1. Создание бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Укажите имя бота (например: **Nemo Tracker**)
4. Укажите username (например: `nemo_tracker_bot`)
5. Скопируйте полученный **BOT_TOKEN**

## 2. Настройка Mini App URL

В @BotFather:

1. Отправьте `/newapp`
2. Выберите созданного бота
3. Укажите название: **Nemo Panel**
4. Описание: **Панель управления VPN**
5. URL: `https://ваш-домен/mini` (должен быть HTTPS)
6. Картинка — по желанию

Альтернативно через `/mybots` → выберите бота → **Bot Menu** → **Menu Button** → **Edit menu button URL** → `https://ваш-домен/mini`

## 3. Команда /panel

Добавьте в бота кнопку меню или команду:

**Через @BotFather:**
```
/setmenubutton
```
Выберите бота → укажите текст кнопки и URL: `https://ваш-домен/mini`

**Через код бота (aiogram/example):**
```python
from aiogram import Bot
from aiogram.types import BotCommand, WebAppInfo, MenuButtonWebApp

bot = Bot(token="YOUR_BOT_TOKEN")

await bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="🎛 Панель",
        web_app=WebAppInfo(url="https://ваш-домен/mini")
    )
)
```

## 4. BOT_TOKEN в Nemo Tracker

Убедитесь что `.env` содержит:
```
BOT_TOKEN=ваш_токен_из_botfather
```

## 5. Проверка

1. Откройте бота в Telegram
2. Нажмите кнопку **🎛 Панель** в меню (или отправьте `/start`)
3. Должна открыться Mini App с дашбордом

## Архитектура

- **GET /mini** — HTML страница Mini App
- **POST /api/mini/verify** — верификация Telegram initData → выдаёт токен сессии
- **GET /api/mini/init** — данные дашборда (требует X-Mini-Token)
- Все остальные `/api/*` эндпоинты тоже доступны с X-Mini-Token (мини-сессия не обходит auth middleware, но `/api/mini/*` публичны для верификации)

**Безопасность:** initData валидируется через HMAC-SHA256 с bot_token (серверная проверка). Сессионный токен — random hex.

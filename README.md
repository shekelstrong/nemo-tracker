<div align="center">

# 🦈 Nemo Tracker

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/shekelstrong/nemo-tracker?style=for-the-badge&color=yellow)](https://github.com/shekelstrong/nemo-tracker/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](https://github.com/shekelstrong/nemo-tracker/blob/main/LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://github.com/shekelstrong/nemo-tracker#quick-start)
[![GitHub Release](https://img.shields.io/github/v/release/shekelstrong/nemo-tracker?style=for-the-badge&color=green)](https://github.com/shekelstrong/nemo-tracker/releases)
[![Discussions](https://img.shields.io/github/discussions/shekelstrong/nemo-tracker?style=for-the-badge&color=58A6FF)](https://github.com/shekelstrong/nemo-tracker/discussions)
[![Issues](https://img.shields.io/github/issues/shekelstrong/nemo-tracker?style=for-the-badge&color=red)](https://github.com/shekelstrong/nemo-tracker/issues)

</div>



**Advanced VPN Analytics, Admin Dashboard & Business Management for Marzban**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

[English](#english) · [Русский](#русский) · [العربية](#العربية) · [中文](#中文)

</div>

---

<a id="english"></a>

## 🇬🇧 English

### What is Nemo Tracker?

Nemo Tracker is a **full-featured VPN business management platform** that works alongside your Marzban panel. It goes far beyond simple analytics — it's a complete admin dashboard with billing, reseller management, forecasting, and white-label branding.

### Architecture

```
┌─────────────┐     API      ┌──────────────────┐
│   Marzban    │◄────────────►│                  │
│   (Xray)     │              │  Nemo Tracker    │
│              │── WebSocket ►│  (FastAPI + DB)  │
└─────────────┘              └────────┬─────────┘
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                     ┌────▼───┐  ┌───▼────┐  ┌──▼───────┐
                     │ Admin   │  │ Reseller│  │ Telegram │
                     │ Web UI  │  │  Panel  │  │ Mini App │
                     └────────┘  └────────┘  └──────────┘
```

### Features

#### 📊 Dashboard & Analytics
- Real-time user stats: online, active, expired, total
- Traffic analytics: top consumers, distribution charts, anomaly detection
- 30-day traffic/revenue charts (Chart.js)
- Connection timeline and peak usage reports

#### 👥 User Management
- Full CRUD: create, edit, delete users
- Toggle enable/disable, reset traffic
- Tier system: **Standard** / **Premium** (auto-detected from inbounds)
- Subscription URL & QR code generation
- Device limit enforcement with auto-disable

#### 🗺️ GeoIP & Fraud Detection
- IP geolocation map (Leaflet.js + MaxMind/ip-api)
- Real-time connection markers on world map
- Account sharing detection (>3 countries in 30 days)
- Country filter, suspicious connections table

#### 💰 Finance
- Real revenue data: today / week / month / all time
- Dynamic USDT/RUB exchange rate (CoinGecko API)
- Transaction history with pagination
- Revenue forecast (7/14/30 days)

#### 📈 Forecasting
- **Churn prediction**: identifies users at risk of leaving
- **Resource forecast**: when CPU/disk/bandwidth will be exhausted
- **Revenue forecast**: linear regression on historical data
- Actionable recommendations

#### 🏷️ Tariff Constructor
- Visual drag-and-drop plan builder
- Flexible pricing: RUB + USDT, duration, GB/device limits
- Tier assignment (Standard/Premium)
- Feature list per plan

#### 🎫 Promo Codes
- Auto-generated 8-character codes
- Discount: percentage or fixed amount
- Usage limits, expiration dates
- Enable/disable, copy & share

#### 👥 Reseller Panel
- Sub-admin accounts with API key authentication
- Balance management with commission (%)
- Create/renew users (deducts from reseller balance)
- Standalone panel at `/r/panel` (separate from admin)
- Transaction history

#### 🔄 Auto-Renewal
- Automatic subscription renewal (configurable schedule)
- Telegram reminders 3 days before expiry
- 3 failed attempts → auto-disable + notification
- Placeholder payment integration (ready for CryptoBot/Platega)

#### 🌐 Multi-Server Dashboard
- Manage multiple Marzban servers from one panel
- Health checks every 5 minutes (🟢/🔴 status)
- Per-server stats: users, bandwidth, uptime
- Encrypted credential storage (Fernet)
- Country flags, master server designation

#### 📱 Telegram Mini App
- Mobile-optimized admin panel inside Telegram
- Bottom navigation: Dashboard / Users / Finance / Alerts
- Telegram WebApp SDK with initData verification
- Touch-friendly, dark theme matching Telegram

#### 🔐 Security
- JWT authentication (httpOnly cookies, 24h expiry)
- Two-factor authentication (TOTP / Google Authenticator)
- QR code setup in Settings
- Password change, 2FA enable/disable

#### 📋 Export / Import
- Full JSON backup (users, settings, transactions, tariffs)
- CSV export for users
- Drag-and-drop import with preview
- Merge mode: updates existing, adds new

#### 🎨 White-Label Branding
- Custom colors (primary, secondary, accent) with live preview
- Logo upload, favicon, custom CSS/JS
- Company info, support links
- Footer text, SEO meta tags
- Applies to all pages via CSS variables

#### 🌍 Multi-Language
- Russian 🇷🇺 and English 🇬🇧 UI
- One-click language toggle
- All pages fully translated

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | Vanilla JS, Chart.js, Leaflet.js |
| Auth | JWT + TOTP (pyotp) |
| Deployment | Docker Compose |
| API Integration | Marzban REST API, WebSocket (Xray logs) |

### Quick Start

```bash
# Clone
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker

# Configure
cp .env.example .env
# Edit .env with your Marzban credentials

# Run with Docker
docker compose up -d

# Access
# Web UI: http://your-server:8090
# Default login: admin / admin
```

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MARZBAN_URL` | Marzban panel URL | — |
| `MARZBAN_USERNAME` | Marzban admin username | — |
| `MARZBAN_PASSWORD` | Marzban admin password | — |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_NAME` | Database name | nemo_tracker |
| `DB_USER` | Database user | nemo_tracker |
| `DB_PASS` | Database password | — |
| `BOT_TOKEN` | Telegram bot token (for notifications) | — |
| `ADMIN_USERNAME` | Admin panel username | admin |
| `ADMIN_PASSWORD` | Admin panel password | admin |

See [.env.example](.env.example) for full configuration options.

### License & Commercial

Nemo Tracker is open source under MIT License for personal use. For commercial deployments (SaaS, hosting for clients, white-label), a **Pro License** is required.

📧 Contact: [@nedopekin](https://t.me/nedopekin)

---

<a id="русский"></a>

## 🇷🇺 Русский

### Что такое Nemo Tracker?

Nemo Tracker — это **полноценная платформа управления VPN-бизнесом**, работающая рядом с панелью Marzban. Это не просто аналитика — это комплексная админ-панель с биллингом, управлением реселлерами, прогнозированием и white-label брендингом.

### Архитектура

```
┌─────────────┐     API      ┌──────────────────┐
│   Marzban    │◄────────────►│                  │
│   (Xray)     │              │  Nemo Tracker    │
│              │── WebSocket ►│  (FastAPI + DB)  │
└─────────────┘              └────────┬─────────┘
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                     ┌────▼───┐  ┌───▼────┐  ┌──▼───────┐
                     │ Админ   │  │ Реселлер│  │ Telegram │
                     │ панель  │  │ панель  │  │ Mini App │
                     └────────┘  └────────┘  └──────────┘
```

### Функционал

#### 📊 Дашборд и аналитика
- Статистика в реальном времени: онлайн, активные, истёкшие, всего
- Аналитика трафика: топ потребителей, распределение, аномалии
- Графики трафика/дохода за 30 дней (Chart.js)
- Хронология подключений и пиковые нагрузки

#### 👥 Управление пользователями
- Полный CRUD: создание, редактирование, удаление
- Включение/отключение, сброс трафика
- Система тарифов: **Стандарт** / **Premium** (авто-определение)
- URL подписки и QR-код
- Блокировка при превышении лимита устройств

#### 🗺️ Геолокация и антифрод
- Карта геолокации IP (Leaflet.js + MaxMind/ip-api)
- Маркеры подключений на карте мира в реальном времени
- Детекция шаринга аккаунтов (>3 стран за 30 дней)
- Фильтр по стране, таблица подозрительных подключений

#### 💰 Финансы
- Реальные данные: сегодня / неделя / месяц / за всё время
- Динамический курс USDT/RUB (CoinGecko API)
- История транзакций с пагинацией
- Прогноз дохода (7/14/30 дней)

#### 📈 Прогнозирование
- **Прогноз оттока**: identifies users at risk of leaving
- **Прогноз ресурсов**: когда исчерпаются CPU/диск/канал
- **Прогноз дохода**: линейная регрессия на исторических данных
- Практические рекомендации

#### 🏷️ Конструктор тарифов
- Визуальный drag-and-drop конструктор планов
- Гибкое ценообразование: ₽ + USDT, длительность, GB/device лимиты
- Привязка к тарифу (Стандарт/Premium)
- Список features для каждого плана

#### 🎫 Промокоды
- Автогенерация 8-символьных кодов
- Скидка: процент или фиксированная сумма
- Лимит использований, срок действия
- Включение/отключение, копирование

#### 👥 Реселлер-панель
- Суб-админки с авторизацией по API ключу
- Управление балансом с комиссией (%)
- Создание/продление юзеров (списание с баланса)
- Отдельная панель на `/r/panel`
- История транзакций

#### 🔄 Автопродление
- Автоматическое продление подписок (настраиваемое расписание)
- Telegram-напоминания за 3 дня до истечения
- 3 неудачные попытки → авто-отключение + уведомление
- Интеграция с CryptoBot/Platega (готова к подключению)

#### 🌐 Мульти-сервер
- Управление несколькими серверами Marzban из одной панели
- Проверка здоровья каждые 5 минут (🟢/🔴)
- Статистика по серверам: юзеры, трафик, аптайм
- Шифрование учётных данных (Fernet)
- Флаги стран, назначение master-сервера

#### 📱 Telegram Mini App
- Мобильная админ-панель внутри Telegram
- Навигация: Дашборд / Пользователи / Финансы / Алерты
- Telegram WebApp SDK + верификация initData
- Touch-friendly, тёмная тема

#### 🔐 Безопасность
- JWT аутентификация (httpOnly cookies, 24ч)
- Двухфакторная аутентификация (TOTP / Google Authenticator)
- QR-код в настройках для подключения
- Смена пароля, вкл/выкл 2FA

#### 📋 Экспорт / Импорт
- Полный JSON бэкап (юзеры, настройки, транзакции, тарифы)
- CSV экспорт пользователей
- Drag-and-drop импорт с превью
- Merge mode: обновляет существующих, добавляет новых

#### 🎨 White-label брендинг
- Кастомные цвета (primary, secondary, accent) с live preview
- Загрузка логотипа, favicon, custom CSS/JS
- Информация о компании, ссылки поддержки
- Текст в футере, SEO мета-теги
- Применяется ко всем страницам через CSS-переменные

#### 🌍 Мультиязычность
- Русский 🇷🇺 и английский 🇬🇧 интерфейс
- Переключение в один клик
- Все страницы полностью переведены

### Технологии

| Компонент | Технология |
|-----------|-----------|
| Бэкенд | Python 3.12, FastAPI, SQLAlchemy (async) |
| База данных | PostgreSQL 16 |
| Кэш | Redis 7 |
| Фронтенд | Vanilla JS, Chart.js, Leaflet.js |
| Авторизация | JWT + TOTP (pyotp) |
| Развёртывание | Docker Compose |
| Интеграция | Marzban REST API, WebSocket (Xray логи) |

### Быстрый старт

```bash
# Клонируем
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker

# Настраиваем
cp .env.example .env
# Заполните .env данными от Marzban

# Запуск через Docker
docker compose up -d

# Доступ
# Web UI: http://ваш-сервер:8090
# Логин по умолчанию: admin / admin
```

### Конфигурация

| Переменная | Описание | По умолчанию |
|-------------|----------|-------------|
| `MARZBAN_URL` | URL панели Marzban | — |
| `MARZBAN_USERNAME` | Логин администратора Marzban | — |
| `MARZBAN_PASSWORD` | Пароль администратора Marzban | — |
| `DB_HOST` | Хост PostgreSQL | localhost |
| `DB_NAME` | Имя базы данных | nemo_tracker |
| `DB_USER` | Пользователь БД | nemo_tracker |
| `DB_PASS` | Пароль БД | — |
| `BOT_TOKEN` | Токен Telegram-бота (для уведомлений) | — |
| `ADMIN_USERNAME` | Логин админ-панели | admin |
| `ADMIN_PASSWORD` | Пароль админ-панели | admin |

Полный список настроек — в [.env.example](.env.example).

### Лицензия и коммерция

Nemo Tracker — open source под MIT License для личного использования. Для коммерческого использования (SaaS, хостинг для клиентов, white-label) требуется **Pro-лицензия**.

📧 Контакт: [@nedopekin](https://t.me/nedopekin)

---

<a id="العربية"></a>

## 🇸🇦 العربية

### ما هو Nemo Tracker؟

Nemo Tracker هي **منصة متكاملة لإدارة أعمال VPN** تعمل بجانب لوحة Marzban الخاصة بك. إنها أكثر من مجرد تحليلات — إنها لوحة تحكم إدارية شاملة مع فوترة وإدارة الموزعين والتنبؤات والعلامة البيضاء.

### البنية

```
┌─────────────┐     API      ┌──────────────────┐
│   Marzban    │◄────────────►│                  │
│   (Xray)     │              │  Nemo Tracker    │
│              │── WebSocket ►│  (FastAPI + DB)  │
└─────────────┘              └────────┬─────────┘
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                     ┌────▼───┐  ┌───▼────┐  ┌──▼───────┐
                     │ لوحة   │  │ لوحة   │  │ Telegram │
                     │ المسؤول│  │الموزعين│  │ Mini App │
                     └────────┘  └────────┘  └──────────┘
```

### المميزات

| الميزة | الوصف |
|--------|-------|
| 📊 لوحة التحكم | إحصائيات فورية، رسوم بيانية للtraffic، كشف الشذوذ |
| 👥 إدارة المستخدمين | إنشاء/تعديل/حذف، تفعيل/تعطيل، إعادة تعيين traffic |
| 🗺️ الخريطة الجغرافية | خريطة Leaflet.js للاتصالات، كشف مشاركة الحسابات |
| 💰 المالية | إيرادات حقيقية، سعر صرف USDT/RUB ديناميكي، تاريخ المعاملات |
| 📈 التنبؤات | تنبؤ churn، استنزاف الموارد، توقعات الإيرادات |
| 🏷️ خطط الأسعار | بناء خطط مرئي بالسحب والإفلات |
| 🎫 أكواد الخصم | إنشاء تلقائي، نسبة أو مبلغ ثابت، حدود الاستخدام |
| 👥 لوحة الموزعين | حسابات فرعية، رصيد + عمولة، إنشاء/تجديد المستخدمين |
| 🔄 التجديد التلقائي | تجديد تلقائي، تذكيرات Telegram، إيقاف بعد 3 فشل |
| 🌐 خوادم متعددة | إدارة عدة خوادم Marzban، فحص صحة كل 5 دقائق |
| 📱 Telegram Mini App | لوحة تحكم محسّنة للهاتف داخل Telegram |
| 🔐 الأمان | JWT + TOTP (مصادقة ثنائية)، تشفير httpOnly |
| 📋 التصدير/الاستيراد | نسخ احتياطي JSON كامل، CSV للمستخدمين، استيراد مع معاينة |
| 🎨 العلامة البيضاء | ألوان مخصصة، شعار، CSS/JS مخصص، معاينة مباشرة |
| 🌍 تعدد اللغات | روسي وإنجليزي مع تبديل بنقرة واحدة |

### التثبيت السريع

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker
cp .env.example .env
# قم بتعديل .env ببيانات Marzban الخاصة بك
docker compose up -d
# الوصول: http://your-server:8090 | تسجيل الدخول: admin / admin
```

### الترخيص

مفتوح المصدر بموجب ترخيص MIT للاستخدام الشخصي. للاستخدام التجاري يلزم **ترخيص Pro**.

📧 تواصل: [@nedopekin](https://t.me/nedopekin)

---

<a id="中文"></a>

## 🇨🇳 中文

### Nemo Tracker 是什么？

Nemo Tracker 是一个**全功能的VPN业务管理平台**，与您的Marzban面板并行运行。它不仅仅是分析工具——它是一个完整的管理面板，包含计费、经销商管理、预测和白标品牌功能。

### 架构

```
┌─────────────┐     API      ┌──────────────────┐
│   Marzban    │◄────────────►│                  │
│   (Xray)     │              │  Nemo Tracker    │
│              │── WebSocket ►│  (FastAPI + DB)  │
└─────────────┘              └────────┬─────────┘
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                     ┌────▼───┐  ┌───▼────┐  ┌──▼───────┐
                     │ 管理    │  │ 经销商  │  │ Telegram │
                     │ 面板    │  │ 面板    │  │ Mini App │
                     └────────┘  └────────┘  └──────────┘
```

### 功能

| 功能 | 描述 |
|------|------|
| 📊 仪表盘 | 实时统计、流量图表、异常检测 |
| 👥 用户管理 | 创建/编辑/删除、启用/禁用、重置流量 |
| 🗺️ 地理定位 | Leaflet.js连接地图、账号共享检测 |
| 💰 财务 | 真实收入、动态USDT/RUB汇率、交易历史 |
| 📈 预测 | 流失预测、资源耗尽预测、收入预测 |
| 🏷️ 套餐方案 | 可视化拖拽式方案构建器 |
| 🎫 优惠码 | 自动生成、百分比或固定金额、使用限制 |
| 👥 经销商面板 | 子账号、余额+佣金、创建/续费用户 |
| 🔄 自动续费 | 自动续订、Telegram提醒、3次失败后停用 |
| 🌐 多服务器 | 管理多个Marzban服务器、每5分钟健康检查 |
| 📱 Telegram小程序 | 手机优化的管理面板 |
| 🔐 安全 | JWT + TOTP双因素认证、httpOnly加密 |
| 📋 导出/导入 | 完整JSON备份、CSV导出、预览导入 |
| 🎨 白标品牌 | 自定义颜色、Logo、CSS/JS、实时预览 |
| 🌍 多语言 | 俄语和英语一键切换 |

### 快速安装

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker
cp .env.example .env
# 使用您的Marzban凭据编辑.env
docker compose up -d
# 访问: http://your-server:8090 | 默认登录: admin / admin
```

### 许可证

个人使用采用MIT开源许可证。商业用途需要**Pro许可证**。

📧 联系: [@nedopekin](https://t.me/nedopekin)

---

<div align="center">

**Made with 🦈 by [Nemo VPN](https://t.me/nemo_vpn_official)**

</div>

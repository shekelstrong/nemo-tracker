<div align="center">

# 🦈 Nemo Tracker

**Advanced VPN Analytics, Device Tracking & Admin Dashboard for Marzban**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

[English](#english) · [Русский](#русский) · [العربية](#العربية) · [中文](#中文)

</div>

---

<a id="english"></a>

## 🇬🇧 English

### What is Nemo Tracker?

Nemo Tracker is a standalone analytics and device management tool that sits **alongside** your existing Marzban VPN panel. It doesn't modify Marzban or your bot — it reads data from Marzban API and Xray logs to provide:

- 📊 **Real-time dashboards** — traffic, connections, user activity with charts & graphs
- 📱 **Device tracking** — unique IP monitoring per user with geolocation
- 🔒 **Auto-enforcement** — automatically disable users who exceed device limits
- 🤖 **Telegram bot** — notifications, user management, quick stats
- 🌍 **Multi-language** — Russian, English, Arabic, Chinese
- 🔗 **Zero-touch integration** — reads from Marzban API, no code changes needed

### How it works

```
┌─────────────┐     API      ┌──────────────┐
│   Marzban    │◄────────────►│              │
│   (Xray)     │              │ Nemo Tracker │
│              │──── logs ───►│              │
└─────────────┘              └──────┬───────┘
                                    │
                              ┌─────┴──────┐
                              │            │
                         ┌────▼───┐  ┌─────▼────┐
                         │ Telegram│  │  Web UI  │
                         │   Bot   │  │ Dashboard│
                         └────────┘  └──────────┘
```

### Features

| Feature | Marzban | Nemo Tracker |
|---------|---------|-------------|
| User management | ✅ | ✅ |
| Traffic stats | Basic | Advanced charts |
| Device limit enforcement | ❌ | ✅ |
| IP geolocation | ❌ | ✅ |
| Real-time graphs | ❌ | ✅ |
| Telegram notifications | ❌ | ✅ |
| Connection timeline | ❌ | ✅ |
| Peak usage analytics | ❌ | ✅ |
| User retention reports | ❌ | ✅ |
| Multi-language UI | ❌ | ✅ |

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

# Or run manually
pip install -r requirements.txt
python -m src.main
```

### Configuration

See [.env.example](.env.example) for all available settings.

### License & Commercial

Nemo Tracker is open source under MIT License for personal use. For commercial deployments (SaaS, hosting for clients, white-label), a **Pro License** is required.

📧 Contact: [@nedopekin](https://t.me/nedopekin)

---

<a id="русский"></a>

## 🇷🇺 Русский

### Что такое Nemo Tracker?

Nemo Tracker — это автономная аналитика и управление устройствами, работающая **рядом** с вашей панелью Marzban. Он не изменяет Marzban и не трогает вашего бота — читает данные через Marzban API и логи Xray, чтобы предоставить:

- 📊 **Дашборды в реальном времени** — трафик, подключения, активность пользователей с графиками и диаграммами
- 📱 **Отслеживание устройств** — мониторинг уникальных IP по каждому пользователю с геолокацией
- 🔒 **Автоблокировка** — автоматическое отключение пользователей, превысивших лимит устройств
- 🤖 **Telegram-бот** — уведомления, управление пользователями, быстрая статистика
- 🌍 **Мультиязычность** — русский, английский, арабский, китайский
- 🔗 **Интеграция без вмешательства** — читает из Marzban API, не требует изменений в коде

### Как это работает

```
┌─────────────┐     API      ┌──────────────┐
│   Marzban    │◄────────────►│              │
│   (Xray)     │              │ Nemo Tracker │
│              │──── логи ───►│              │
└─────────────┘              └──────┬───────┘
                                    │
                              ┌─────┴──────┐
                              │            │
                         ┌────▼───┐  ┌─────▼────┐
                         │ Telegram│  │  Web UI  │
                         │   Бот   │  │ Панель   │
                         └────────┘  └──────────┘
```

### Функционал

| Функция | Marzban | Nemo Tracker |
|---------|---------|-------------|
| Управление пользователями | ✅ | ✅ |
| Статистика трафика | Базовая | Расширенные графики |
| Ограничение устройств | ❌ | ✅ |
| Геолокация по IP | ❌ | ✅ |
| Графики в реальном времени | ❌ | ✅ |
| Уведомления в Telegram | ❌ | ✅ |
| Хронология подключений | ❌ | ✅ |
| Аналитика пиковых нагрузок | ❌ | ✅ |
| Отчёты по удержанию | ❌ | ✅ |
| Мультиязычный интерфейс | ❌ | ✅ |

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

# Или вручную
pip install -r requirements.txt
python -m src.main
```

### Конфигурация

Смотрите [.env.example](.env.example) для всех доступных настроек.

### Лицензия и коммерция

Nemo Tracker — open source под MIT License для личного использования. Для коммерческого использования (SaaS, хостинг для клиентов, white-label) требуется **Pro-лицензия**.

📧 Контакт: [@nedopekin](https://t.me/nedopekin)

---

<a id="العربية"></a>

## 🇸🇦 العربية

### ما هو Nemo Tracker؟

Nemo Tracker هي أداة تحليلات مستقلة وإدارة أجهزة تعمل **بجانب** لوحة Marzban الخاصة بك. لا تُعدّل Marzban أو البوت الخاص بك — بل تقرأ البيانات من Marzban API وسجلات Xray لتوفير:

- 📊 **لوحات تحكم في الوقت الفعلي** — حركة البيانات، الاتصالات، نشاط المستخدمين مع رسوم بيانية
- 📱 **تتبع الأجهزة** — مراقبة عناوين IP الفريدة لكل مستخدم مع تحديد الموقع الجغرافي
- 🔒 **الفرض التلقائي** — تعطيل المستخدمين تلقائيًا عند تجاوز حد الأجهزة
- 🤖 **بوت تيليجرام** — إشعارات، إدارة المستخدمين، إحصائيات سريعة
- 🌍 **متعدد اللغات** — روسي، إنجليزي، عربي، صيني
- 🔗 **تكامل بدون تعديل** — يقرأ من Marzban API، لا يحتاج أي تغييرات في الكود

### كيف يعمل

```
┌─────────────┐     API      ┌──────────────┐
│   Marzban    │◄────────────►│              │
│   (Xray)     │              │ Nemo Tracker │
│              │── سجلات ────►│              │
└─────────────┘              └──────┬───────┘
                                    │
                              ┌─────┴──────┐
                              │            │
                         ┌────▼───┐  ┌─────▼────┐
                         │ بوت    │  │  واجهة   │
                         │تيليجرام│  │  ويب     │
                         └────────┘  └──────────┘
```

### المميزات

| الميزة | Marzban | Nemo Tracker |
|--------|---------|-------------|
| إدارة المستخدمين | ✅ | ✅ |
| إحصائيات حركة البيانات | أساسية | رسوم بيانية متقدمة |
| فرض حدود الأجهزة | ❌ | ✅ |
| تحديد الموقع الجغرافي | ❌ | ✅ |
| رسوم بيانية فورية | ❌ | ✅ |
| إشعارات تيليجرام | ❌ | ✅ |
| جدول زمني للاتصالات | ❌ | ✅ |
| تحليل ذروة الاستخدام | ❌ | ✅ |
| تقارير الاحتفاظ بالمستخدمين | ❌ | ✅ |
| واجهة متعددة اللغات | ❌ | ✅ |

### التثبيت السريع

```bash
# استنساخ
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker

# إعداد
cp .env.example .env
# قم بتعديل .env ببيانات Marzban الخاصة بك

# تشغيل مع Docker
docker compose up -d

# أو يدويًا
pip install -r requirements.txt
python -m src.main
```

### الإعدادات

راجع [.env.example](.env.example) لجميع الإعدادات المتاحة.

### الترخيص والاستخدام التجاري

Nemo Tracker مفتوح المصدر بموجب ترخيص MIT للاستخدام الشخصي. للاستخدام التجاري (SaaS، استضافة للعملاء، العلامة البيضاء)، يلزم **ترخيص Pro**.

📧 تواصل: [@nedopekin](https://t.me/nedopekin)

---

<a id="中文"></a>

## 🇨🇳 中文

### Nemo Tracker 是什么？

Nemo Tracker 是一款独立的 VPN 分析和设备管理工具，与您现有的 Marzban 面板**并行运行**。它不修改 Marzban 或您的机器人 — 通过 Marzban API 和 Xray 日志读取数据，提供：

- 📊 **实时仪表盘** — 流量、连接、用户活动，配有图表和图形
- 📱 **设备追踪** — 按用户监控唯一IP地址，附带地理位置
- 🔒 **自动执行** — 用户超过设备限制时自动禁用
- 🤖 **Telegram 机器人** — 通知、用户管理、快速统计
- 🌍 **多语言支持** — 俄语、英语、阿拉伯语、中文
- 🔗 **零侵入集成** — 从 Marzban API 读取，无需修改代码

### 工作原理

```
┌─────────────┐     API      ┌──────────────┐
│   Marzban    │◄────────────►│              │
│   (Xray)     │              │ Nemo Tracker │
│              │── 日志 ─────►│              │
└─────────────┘              └──────┬───────┘
                                    │
                              ┌─────┴──────┐
                              │            │
                         ┌────▼───┐  ┌─────▼────┐
                         │Telegram│  │  Web UI  │
                         │  机器人 │  │  仪表盘  │
                         └────────┘  └──────────┘
```

### 功能对比

| 功能 | Marzban | Nemo Tracker |
|------|---------|-------------|
| 用户管理 | ✅ | ✅ |
| 流量统计 | 基础 | 高级图表 |
| 设备限制执行 | ❌ | ✅ |
| IP 地理定位 | ❌ | ✅ |
| 实时图表 | ❌ | ✅ |
| Telegram 通知 | ❌ | ✅ |
| 连接时间线 | ❌ | ✅ |
| 峰值使用分析 | ❌ | ✅ |
| 用户留存报告 | ❌ | ✅ |
| 多语言界面 | ❌ | ✅ |

### 快速安装

```bash
# 克隆
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker

# 配置
cp .env.example .env
# 使用您的 Marzban 凭据编辑 .env

# 使用 Docker 运行
docker compose up -d

# 或手动运行
pip install -r requirements.txt
python -m src.main
```

### 配置

请参阅 [.env.example](.env.example) 了解所有可用设置。

### 许可证与商业使用

Nemo Tracker 采用 MIT 开源许可证供个人使用。商业用途（SaaS、客户托管、白标）需要 **Pro 许可证**。

📧 联系: [@nedopekin](https://t.me/nedopekin)

---

<div align="center">

**Made with 🦈 by [Nemo VPN](https://t.me/nemo_vpn_official)**

</div>

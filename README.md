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

Nemo Tracker — это standalone-аналитика и управление устройствами, работающая **рядом** с Marzban. Не меняет Marzban и не трогает вашего бота — читает данные через Marzban API и логи Xray.

- 📊 **Дашборды в реальном времени** — трафик, подключения, активность
- 📱 **Отслеживание устройств** — уникальные IP с геолокацией
- 🔒 **Автоблокировка** — при превышении лимита устройств
- 🤖 **Telegram-бот** — уведомления и управление
- 🌍 **Мультиязычность** — RU / EN / AR / CN

### Быстрый старт

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker
cp .env.example .env
# Заполните .env
docker compose up -d
```

### Коммерция

Личный использ — бесплатно (MIT). Для коммерческого использования (SaaS, хостинг, white-label) требуется **Pro-лицензия**.

📧 Контакт: [@nedopekin](https://t.me/nedopekin)

---

<a id="العربية"></a>

## 🇸🇦 العربية

### ما هو Nemo Tracker؟

أداة تحليلات متقدمة وتتبع الأجهزة تعمل **بجانب** Marzban. لا تُعدّل Marzban أو البوت الخاص بك.

- 📊 لوحات تحكم في الوقت الفعلي
- 📱 تتبع الأجهزة بتحديد الموقع الجغرافي
- 🔒 حظر تلقائي عند تجاوز الحد
- 🤖 بوت تيليجرام للإشعارات
- 🌍 دعم متعدد اللغات

### التثبيت السريع

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker && cp .env.example .env
docker compose up -d
```

📧 تواصل: [@nedopekin](https://t.me/nedopekin)

---

<a id="中文"></a>

## 🇨🇳 中文

### Nemo Tracker 是什么？

一款高级 VPN 分析和设备追踪工具，与 Marzban **并行运行**。无需修改 Marzban。

- 📊 实时仪表盘 — 流量、连接、用户活动
- 📱 设备追踪 — 唯一IP + 地理位置
- 🔒 超限自动封锁
- 🤖 Telegram 机器人通知
- 🌍 多语言支持（俄/英/阿/中）

### 快速安装

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker && cp .env.example .env
docker compose up -d
```

📧 联系: [@nedopekin](https://t.me/nedopekin)

---

<div align="center">

**Made with 🦈 by [Nemo VPN](https://t.me/nemo_vpn_official)**

</div>

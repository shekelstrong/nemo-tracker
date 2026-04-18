const T = {
  // Sidebar
  "nav.dashboard": { en: "Dashboard", ru: "Дашборд" },
  "nav.users": { en: "Users", ru: "Пользователи" },
  "nav.devices": { en: "Devices", ru: "Устройства" },
  "nav.alerts": { en: "Alerts", ru: "Оповещения" },
  "nav.settings": { en: "Settings", ru: "Настройки" },

  // Dashboard
  "dash.total_users": { en: "Total Users", ru: "Всего пользователей" },
  "dash.active_users": { en: "Active Users", ru: "Активные" },
  "dash.online_now": { en: "Online Now", ru: "Онлайн сейчас" },
  "dash.total_traffic": { en: "Total Traffic", ru: "Общий трафик" },
  "dash.online_24h": { en: "Online Users (24h)", ru: "Пользователи онлайн (24ч)" },
  "dash.traffic_30d": { en: "Traffic (30d)", ru: "Трафик (30 дней)" },
  "dash.user_growth": { en: "User Growth", ru: "Рост пользователей" },
  "dash.peak_hours": { en: "Peak Hours", ru: "Пиковые часы" },
  "dash.recent_alerts": { en: "Recent Alerts", ru: "Последние оповещения" },
  "dash.no_alerts": { en: "No recent alerts", ru: "Нет недавних оповещений" },

  // Users
  "users.title": { en: "Users", ru: "Пользователи" },
  "users.search": { en: "Search users...", ru: "Поиск пользователей..." },
  "users.all": { en: "All", ru: "Все" },
  "users.username": { en: "Username", ru: "Пользователь" },
  "users.status": { en: "Status", ru: "Статус" },
  "users.traffic": { en: "Traffic", ru: "Трафик" },
  "users.devices": { en: "Devices", ru: "Устройства" },
  "users.last_online": { en: "Last Online", ru: "Был онлайн" },
  "users.tier": { en: "Tier", ru: "Тариф" },
  "users.active": { en: "Active", ru: "Активен" },
  "users.expired": { en: "Expired", ru: "Истёк" },
  "users.disabled": { en: "Disabled", ru: "Отключён" },
  "users.limited": { en: "Limited", ru: "Ограничен" },
  "users.unlimited": { en: "Unlimited", ru: "Безлимит" },
  "users.back": { en: "← Back to Users", ru: "← Назад к списку" },

  // User Detail
  "ud.traffic_7d": { en: "Traffic (7 days)", ru: "Трафик (7 дней)" },
  "ud.ip_history": { en: "IP History", ru: "История IP" },
  "ud.ip": { en: "IP", ru: "IP" },
  "ud.location": { en: "Location", ru: "Местоположение" },
  "ud.first_seen": { en: "First Seen", ru: "Первое подключение" },
  "ud.last_seen": { en: "Last Seen", ru: "Последнее" },
  "ud.connections": { en: "Recent Connections", ru: "Последние подключения" },
  "ud.time": { en: "Time", ru: "Время" },
  "ud.duration": { en: "Duration", ru: "Длительность" },
  "ud.info": { en: "User Info", ru: "Информация" },
  "ud.created": { en: "Created", ru: "Создан" },
  "ud.expire": { en: "Expires", ru: "Истекает" },
  "ud.device_count": { en: "Unique IPs", ru: "Уникальные IP" },
  "ud.device_limit": { en: "Device Limit", ru: "Лимит устройств" },
  "ud.no_expire": { en: "Never", ru: "Бессрочно" },

  // Devices
  "dev.title": { en: "Device Tracker", ru: "Трекер устройств" },
  "dev.total": { en: "Total Tracked", ru: "Отслеживается" },
  "dev.over_limit": { en: "Over Limit", ru: "Превышен лимит" },
  "dev.at_limit": { en: "At Limit", ru: "На пределе" },
  "dev.ok": { en: "OK", ru: "Норма" },
  "dev.unique_ips": { en: "Unique IPs", ru: "Уникальные IP" },
  "dev.limit": { en: "Limit", ru: "Лимит" },

  // Alerts
  "alerts.title": { en: "Alerts", ru: "Оповещения" },
  "alerts.type": { en: "Type", ru: "Тип" },
  "alerts.message": { en: "Message", ru: "Сообщение" },
  "alerts.time": { en: "Time", ru: "Время" },
  "alerts.status": { en: "Status", ru: "Статус" },
  "alerts.resolved": { en: "Resolved", ru: "Решено" },
  "alerts.unresolved": { en: "Unresolved", ru: "Открыто" },
  "alerts.resolve": { en: "Resolve", ru: "Решить" },
  "alerts.no_alerts": { en: "No alerts found", ru: "Оповещений не найдено" },
  "alerts.all": { en: "All", ru: "Все" },

  // Settings
  "settings.title": { en: "Settings", ru: "Настройки" },
  "settings.marzban": { en: "Marzban Connection", ru: "Подключение Marzban" },
  "settings.marzban_url": { en: "Marzban URL", ru: "URL Marzban" },
  "settings.marzban_user": { en: "Username", ru: "Пользователь" },
  "settings.marzban_pass": { en: "Password", ru: "Пароль" },
  "settings.test_connection": { en: "Test Connection", ru: "Проверить подключение" },
  "settings.telegram": { en: "Telegram Bot", ru: "Telegram Бот" },
  "settings.bot_token": { en: "Bot Token", ru: "Токен бота" },
  "settings.admin_ids": { en: "Admin IDs (comma separated)", ru: "ID администраторов (через запятую)" },
  "settings.botfather": { en: "BotFather Instructions", ru: "Инструкция BotFather" },
  "settings.botfather_text": { en: "1. Open @BotFather in Telegram\n2. Send /newbot\n3. Choose a name and username\n4. Copy the token and paste above", ru: "1. Откройте @BotFather в Telegram\n2. Отправьте /newbot\n3. Выберите имя и username\n4. Скопируйте токен и вставьте выше" },
  "settings.device_rules": { en: "Device Tracking Rules", ru: "Правила отслеживания устройств" },
  "settings.track_inbounds": { en: "Track Inbounds (comma separated)", ru: "Отслеживаемые инбаунды (через запятую)" },
  "settings.ignore_inbounds": { en: "Ignore Inbounds (comma separated)", ru: "Игнорируемые инбаунды (через запятую)" },
  "settings.ignored_ips": { en: "Ignored IPs (comma separated)", ru: "Игнорируемые IP (через запятую)" },
  "settings.notifications": { en: "Notifications", ru: "Уведомления" },
  "settings.notify_new_user": { en: "New user connected", ru: "Новый пользователь" },
  "settings.notify_traffic_80": { en: "Traffic over 80%", ru: "Трафик выше 80%" },
  "settings.notify_device_over": { en: "Device limit exceeded", ru: "Превышен лимит устройств" },
  "settings.notify_expiring": { en: "Account expiring soon", ru: "Аккаунт скоро истекает" },
  "settings.save": { en: "Save Settings", ru: "Сохранить настройки" },
  "settings.saved": { en: "Settings saved!", ru: "Настройки сохранены!" },
  "settings.test_ok": { en: "Connected successfully!", ru: "Подключение успешно!" },
  "settings.test_fail": { en: "Connection failed", ru: "Ошибка подключения" },

  // Footer
  "footer.version": { en: "Nemo Tracker v0.1 · Open Source", ru: "Nemo Tracker v0.1 · Open Source" },
};

let _lang = localStorage.getItem("nemo_lang") || "en";

function t(key) {
  const entry = T[key];
  if (!entry) return key;
  return entry[_lang] || entry.en || key;
}

function setLang(lang) {
  _lang = lang;
  localStorage.setItem("nemo_lang", lang);
  document.documentElement.setAttribute("data-lang", lang);
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

function getLang() { return _lang; }

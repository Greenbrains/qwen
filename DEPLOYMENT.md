# 🚀 Развёртывание Tutu Travel Agent на удалённом сервере

Это руководство описывает процесс установки и запуска агента на удалённой машине с nginx прокси.

## 📋 Требования

- Удалённый сервер с Docker и Docker Compose
- Nginx установлен и настроен
- API-ключ Yandex AI Studio
- Домен green-brain.ru настроен на сервер

## 🔧 Шаг 1: Подготовка .env файла

Скопируйте `.env.example` в `.env` и заполните необходимыми значениями:

```bash
cp .env.example .env
```

**Обязательно измените:**
- `august2026=ваш_ключ_здесь` - замените на реальный API-ключ Yandex
- `YANDEX_FOLDER_ID` - ваш ID каталога Yandex Cloud
- При необходимости другие параметры

## 🐳 Шаг 2: Сборка и запуск Docker контейнера

```bash
# Сборка образа и запуск контейнера
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

## 🔗 Шаг 3: Настройка Nginx

### 3.1 Скопируйте конфигурацию nginx

На удалённом сервере выполните:

```bash
# Создайте файл конфигурации nginx
sudo nano /etc/nginx/sites-available/travel-agent
```

Вставьте содержимое из файла `nginx.conf` (из этого репозитория).

### 3.2 Активируйте сайт

```bash
# Создайте симлинк
sudo ln -s /etc/nginx/sites-available/travel-agent /etc/nginx/sites-enabled/

# Удалите дефолтный сайт (если есть)
sudo rm /etc/nginx/sites-enabled/default

# Проверьте конфигурацию
sudo nginx -t

# Перезагрузите nginx
sudo systemctl reload nginx
```

## 🔒 Шаг 4: Настройка HTTPS (рекомендуется)

Для получения SSL сертификата Let's Encrypt:

```bash
# Установите Certbot
sudo apt install certbot python3-certbot-nginx

# Получите сертификат
sudo certbot --nginx -d green-brain.ru -d www.green-brain.ru

# Certbot автоматически обновит конфигурацию nginx
```

После настройки HTTPS обновите `nginx.conf`:
- Замените `listen 80;` на `listen 443 ssl http2;`
- Добавьте пути к SSL сертификатам

## ✅ Проверка работы

1. Откройте браузер и перейдите на `https://green-brain.ru`
2. Должен отобразиться веб-интерфейс чата
3. Проверьте текстовый чат - отправьте сообщение
4. Проверьте голосовой чат - нажмите кнопку микрофона

## 🔍 Диагностика проблем

### Контейнер не запускается

```bash
# Проверьте логи
docker-compose logs

# Проверьте, что порт свободен
sudo netstat -tlnp | grep 8000
```

### Nginx возвращает 502 Bad Gateway

```bash
# Проверьте, что контейнер работает
docker-compose ps

# Проверьте логи nginx
sudo tail -f /var/log/nginx/travel-agent-error.log

# Убедитесь, что nginx видит бэкенд
curl http://localhost:8000/health
```

### WebSocket не подключается

1. Проверьте, что nginx настроен правильно (заголовки Upgrade)
2. Убедитесь, что firewall не блокирует соединения
3. Проверьте браузерную консоль на ошибки

## 🛑 Остановка сервиса

```bash
# Остановить контейнер
docker-compose down

# Остановить и удалить образы
docker-compose down --rmi all
```

## 🔄 Обновление

```bash
# Потянуть изменения из репозитория
git pull

# Пересобрать и перезапустить контейнер
docker-compose up -d --build
```

## 📊 Мониторинг

```bash
# Статус контейнера
docker stats tutu-travel-agent

# Логи в реальном времени
docker-compose logs -f

# Проверка health endpoint
curl https://green-brain.ru/health
```

## 📝 Структура файлов для развёртывания

```
/workspace/
├── Dockerfile              # Инструкция для сборки Docker образа
├── docker-compose.yml      # Конфигурация Docker Compose
├── .env                    # Переменные окружения (не коммитить!)
├── .env.example            # Шаблон переменных окружения
├── nginx.conf              # Конфигурация nginx (для копирования на сервер)
├── DEPLOYMENT.md           # Этот файл
└── ...                     # Исходный код проекта
```

## 🔐 Безопасность

1. **Никогда не коммитьте `.env` файл** с реальными ключами
2. Используйте HTTPS для продакшена
3. Ограничьте доступ к API через firewall
4. Регулярно обновляйте зависимости

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи (`docker-compose logs`)
2. Убедитесь, что API-ключ действителен
3. Проверьте подключение к MCP-серверу Туту

# OPS-памятка: запуск и проверки (green-brain-agent)

Сервер: VPS Ubuntu, два сайта на одном IP (176.109.110.145):
- `green-brain.ru` — старый сайт, FastAPI, systemd-сервис `fastapi.service`, слушает 127.0.0.1:8000. **НЕ трогать!**
- `agent.green-brain.ru` — этот проект (Docker), хост-порт 8001 → порт 8000 контейнера.

## 1. Подъём Docker

```bash
cd /var/www/green-brain-agent
docker compose up -d            # запуск / применение изменений
docker compose ps               # статус, ожидаем Up (healthy)

# после правок кода (run_api.py, Dockerfile и т.д.) — пересборка:
docker compose up -d --build

# просто рестарт:
docker compose restart

# остановка:
docker compose down
```

## 2. Логи

```bash
docker logs tutu-travel-agent       # разово
docker logs -f tutu-travel-agent    # в реальном времени
```
Важная строка в логах: `Uvicorn running on http://0.0.0.0:8000`.
Если там `127.0.0.1` — сайт снаружи не заработает (502), править host в `run_api.py`.

## 3. Nginx

Живой конфиг: `/etc/nginx/sites-available/green-brain-agent`
(симлинк в `/etc/nginx/sites-enabled/`).

```bash
sudo nginx -t                    # проверка конфига ДО перезагрузки
sudo systemctl reload nginx      # применить без простоя
sudo systemctl status nginx      # статус демона
```
После ЛЮБОЙ правки конфига: сначала `nginx -t`, потом `reload`.

## 4. Проверки (чек-лист)

```bash
# 4.1 кто какие порты слушает
sudo ss -tulpn | grep -E ':80|:443|:8000|:8001'
# ожидаемо: 80/443 — nginx, 8000 — python3 (старый сайт), 8001 — docker-proxy

# 4.2 контейнер отвечает локально
curl -i http://127.0.0.1:8001/health     # ожидаем 200 OK
curl http://127.0.0.1:8001/              # HTML чата

# 4.3 nginx маршрутизирует по Host
curl -H "Host: agent.green-brain.ru" http://127.0.0.1/

# 4.4 DNS
nslookup agent.green-brain.ru            # ожидаем 176.109.110.145

# 4.5 HTTPS снаружи
curl -I https://agent.green-brain.ru/

# 4.6 старый сайт жив
curl -I https://green-brain.ru/
sudo systemctl status fastapi.service
```

## 5. SSL (Let's Encrypt)

```bash
sudo certbot certificates      # список сертификатов и сроки
sudo certbot renew             # ручное продление (автопродление настроено)
# новый домен: sudo certbot --nginx -d домен
```

## 6. Траблшутинг

| Симптом | Причина / решение |
|---|---|
| `failed to bind host port 0.0.0.0:8000` | Порт занят старым сайтом. В `docker-compose.yml` использовать `ports: "8001:8000"` |
| 502 + `Connection reset` при curl 8001 | Приложение слушает 127.0.0.1 внутри контейнера → в `run_api.py` host `0.0.0.0`, затем `docker compose up -d --build` |
| `DNS_PROBE_FINISHED_NXDOMAIN` | Нет A-записи: reg.ru → домен → зона → запись A `agent` → IP сервера |
| nginx не перезагружается | `sudo nginx -t` покажет строку ошибки (например, лишний `default_server`) |
| Контейнер healthy, а сайт не открывается | `docker compose ps`, `docker logs`, `sudo ss -tulpn` на порт 8001 |
| Не работает микрофон в браузере | Сайт обязан быть по HTTPS (wss). Проверить сертификат и разрешение браузера |

## 7. Важное

- `.env` с API-ключами **не коммитится** (проверьте `.gitignore`).
- Не останавливать `fastapi.service` и не занимать порт 8000 — упадёт старый сайт.
- Правки кода в репо → `docker compose up -d --build`.
- Правки nginx → `sudo nginx -t && sudo systemctl reload nginx`.

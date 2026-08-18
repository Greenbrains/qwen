# Навык: cloudru-vm (Виртуальные машины Cloud.ru)

💻 **Описание:** Создание и управление виртуальными машинами Cloud.ru: полный жизненный цикл ВМ, диски, сети, группы безопасности, SSH/SCP через Compute API с использованием легковесного клиента на `httpx`.

## Необходимые переменные окружения
- `CP_CONSOLE_KEY_ID` — ID ключа сервисного аккаунта Cloud.ru
- `CP_CONSOLE_SECRET` — Секрет сервисного аккаунта Cloud.ru
- `PROJECT_ID` — UUID проекта Cloud.ru

> ⚠️ **Важно:** Если эти переменные не заданы, направьте пользователя к навыку `cloudru-account-setup`.

## Зависимости
Единственная внешняя зависимость — `httpx`. Установите её, если она отсутствует:
```bash
pip install httpx
```

## Когда использовать этот навык
Используйте этот навык, когда пользователь:
- Хочет создать, управлять или удалить виртуальные машины в Cloud.ru.
-Needs to list flavors, images, subnets, or availability zones (Нужно получить список конфигураций, образов, подсетей или зон доступности).
- Хочет управлять дисками (создание, подключение, отключение, удаление).
-Needs to start, stop, or reboot a VM (Нужно запустить, остановить или перезагрузить ВМ).
- Спрашивает об инфраструктуре Cloud.ru Compute/VM.

---

## Инструкция по использованию

Основной скрипт: `./scripts/vm.py`. Его можно запускать из любой директории (sys.path настраивается автоматически).

Переменные окружения можно указать в файле `.env` в текущей рабочей директории. Файл загружается автоматически при запуске. Уже установленные в среде переменные НЕ перезаписываются.

Формат `.env`:
```env
CP_CONSOLE_KEY_ID=your-key-id
CP_CONSOLE_SECRET=your-secret
PROJECT_ID=your-project-uuid
```

### 1. Жизненный цикл ВМ (VM lifecycle)
```bash
# Создание ВМ с ожиданием готовности, автоматическим назначением публичного IP и ожиданием доступности SSH
python vm.py create \
  --name my-vm \
  --flavor-name lowcost10-2-4 \
  --image-name ubuntu-22.04 \
  --zone-name ru.AZ-1 \
  --disk-size 20 \
  --disk-type-name SSD \
  --login user1 \
  --ssh-key-file ~/.ssh/id_ed25519.pub \
  --wait --floating-ip --wait-ssh
```

### 2. SSH и SCP (удаленное выполнение)
Команды ssh/scp автоматически определяют публичный IP ВМ через привязанный Floating IP.
```bash
# Выполнить команду на ВМ
python vm.py ssh <vm_id> -i ~/.ssh/key -c "uname -a"

# Запустить несколько команд
python vm.py ssh <vm_id> -i ~/.ssh/key -c "apt update && apt install -y nginx"

# Загрузить файл на ВМ
python vm.py scp <vm_id> -i ~/.ssh/key --local-path ./app.py --remote-path /home/user1/app.py

# Скачать файл с ВМ
python vm.py scp <vm_id> -i ~/.ssh/key --direction download --local-path ./logs.tar.gz --remote-path /var/log/logs.tar.gz
```

### 3. Информация об инфраструктуре
```bash
# Список конфигураций (CPU/RAM/GPU)
python vm.py flavors
python vm.py flavors --cpu 4 --ram 8

# Список ОС образов
python vm.py images

# Список подсетей, зон, типов дисков, групп безопасности
python vm.py subnets
python vm.py zones
python vm.py disk-types
python vm.py security-groups
```

### 4. Управление группами безопасности (Security groups)
```bash
# Список групп безопасности
python vm.py security-groups

# Создать группу безопасности с сразу открытыми портами
python vm.py sg-create --name my-sg --zone-name ru.AZ-1 --open-ports 22 80 443

# Создать пустую группу безопасности
python vm.py sg-create --name my-sg --zone-name ru.AZ-1 --description "My firewall rules"

# Просмотр правил группы безопасности
python vm.py sg-rules <sg_id>

# Открыть порт (добавить правило ingress)
python vm.py sg-rule-add <sg_id> --ports 8080
```
*Формат портов:* одиночный порт (`22`) или диапазон (`3000-3100`). API нормализует их в формат `port:port` (например, `22:22`).
*Протоколы:* `tcp` (по умолчанию), `udp`, `icmp`, `any`.
*Направление:* `ingress` (входящий, по умолчанию), `egress` (исходящий).

### 5. Floating IP (Публичный IP-адрес)
```bash
# Список всех Floating IP
python vm.py fip-list

# Создать Floating IP для ВМ (автоматически определяет зону и интерфейс)
python vm.py fip-create <vm_id>
python vm.py fip-create <vm_id> --name my-public-ip

# Удалить Floating IP
python vm.py fip-delete <fip_id>
```

### 6. Управление дисками
```bash
# Список дисков
python vm.py disks

# Создать автономный диск
python vm.py disk-create --name data-disk --size 100 --zone-name ru.AZ-1 --disk-type-name SSD

# Подключить / Отключить
python vm.py disk-attach <disk_id> --vm-id <vm_id>
python vm.py disk-detach <disk_id> --vm-id <vm_id>

# Удалить диск
python vm.py disk-delete <disk_id>
```

### 7. Отслеживание задач (Task tracking)
Многие операции асинхронны. Отслеживайте их статус:
```bash
python vm.py task <task_id>
```

---

## Типовой рабочий процесс создания ВМ с публичным IP

1. **Выберите зону доступности:** `python vm.py zones` (Доступны: `ru.AZ-1`, `ru.AZ-2`, `ru.AZ-3`)
2. **Выберите конфигурацию (flavor):** `python vm.py flavors` (Самая дешевая: `lowcost10-1-1`, Обычная: `lowcost10-2-4`)
3. **Выберите образ ОС:** `python vm.py images` (Обычные: `ubuntu-22.04`, `ubuntu-24.04`)
4. **Выберите тип диска:** `python vm.py disk-types` (Доступны: `SSD`, `HDD`)
5. **Создайте ВМ:**
   ```bash
   python vm.py create --name my-vm \
     --flavor-name lowcost10-2-4 \
     --image-name ubuntu-22.04 \
     --zone-name ru.AZ-1 \
     --disk-size 20 --disk-type-name SSD \
     --login user1 --ssh-key-file ~/.ssh/id_ed25519.pub \
     --wait --floating-ip --wait-ssh
   ```
6. **Подключитесь:** `python vm.py ssh <vm_id> -i ~/.ssh/id_ed25519`

> **Совет:** Если опустить флаги `--flavor-name`, `--image-name`, `--zone-name`, `--disk-size`, `--disk-type-name`, будут применены значения по умолчанию: `lowcost10-1-1`, `ubuntu-22.04`, `ru.AZ-1`, `10 GB SSD`.
> Минимальная команда создания:
> ```bash
> python vm.py create --name my-vm --login user1 --ssh-key-file ~/.ssh/id_ed25519.pub --wait --floating-ip
> ```

---

## ⚠️ Важные замечания и подводные камни (Gotchas)

### Создание ВМ
- **Аутентификация обязательна** для большинства образов Cloud.ru. Используйте либо `--password`, либо `--ssh-key-file` (но не оба сразу). Они задают `image_metadata`. Без этого API вернет ошибку `image_metadata_required`. Для агентов предпочтительнее SSH-ключ (без пароля в командной строке).
- Флаг `--login` задает имя пользователя (по умолчанию: `user1`).
- Флаг `--disk-type-name` (`SSD` или `HDD`) **обязателен**. Без него API вернет ошибку.
- Минимальный размер загрузочного диска для Ubuntu: ~8-10 ГБ. Меньшие значения (например, 5 ГБ) вернут ошибку `vm_root_disk_too_small`. Максимальный размер: 16384 ГБ.
- Имена зон используют точки: `ru.AZ-1`, `ru.AZ-2`, `ru.AZ-3` (не `ru-9a`).
- API (v1.1) создает ВМ асинхронно. ВМ переходит из состояния `creating` в `running` (обычно 30-90 секунд).
- Имена ВМ должны соответствовать шаблону: `^[a-zA-Z][a-zA-Z0-9.\-_]*$` (1-64 символа, должны начинаться с буквы).

### Остановка / Запуск
- `stop` отправляет `power_off` (переход: `running` -> `stopping` -> `stopped`, ~15 секунд).
- `start` отправляет `power_on` (переход: `stopped` -> `starting` -> `running`, ~30-40 секунд).
- `reboot` перезагружает ВМ без полного выключения.
- Изменение конфигурации (Resize) требует предварительной остановки ВМ.

### Удаление
- Если к ВМ привязан Floating IP, **удалите его ПЕРВЫМ**, прежде чем удалять ВМ. Иначе API вернет ошибку `floating_ip_can_not_be_detached_from_vm_in_current_state` (HTTP 422).
- Используйте `python vm.py delete <vm_id> --force` для автоматического удаления Floating IP перед удалением ВМ.
- Без флага `--force` CLI предупредит о привязанных IP и завершит работу.
- Удаление ВМ асинхронно (состояние `deleting`).

### Сеть и cloud-init
- На ВМ класса `lowcost` выполнение `cloud-init` занимает **2-5 минут** после перехода ВМ в состояние `running`. В это время:
  - SSH недоступен (пользователи/ключи еще не настроены).
  - Исходящий интернет может не работать.
  - Команды `apt`, `curl`, `docker pull` будут завершаться с ошибкой.
- **Рекомендация:** после успешного срабатывания `--wait-ssh`, подождите дополнительно 30-60 секунд перед запуском `apt update` или проверьте статус: `cloud-init status --wait`.
- Флаг `--wait-ssh` проверяет только то, что порт SSH принимает соединения. Он **НЕ гарантирует**, что `cloud-init` полностью завершен или что интернет доступен.

### SSH-подключение
- Команда `vm.py ssh` автоматически определяет Floating IP ВМ. Если его нет, используется приватный IP (работает только из той же сети).
- Используйте `--wait-ready` для повторных попыток подключения, пока `cloud-init` не настроит `sshd`.
- Команды SSH отключают строгую проверку ключа хоста (`StrictHostKeyChecking=no`) для удобства, так как ВМ эфемерны, а IP переиспользуются.

### Шаблоны Cloud-init
Готовые шаблоны находятся в `./assets/`. Пример использования:
```bash
python vm.py create --name docker-vm --cloud-init-file ./assets/cloud-init-docker.yaml \
  --login user1 --ssh-key-file ~/.ssh/id_ed25519.pub --wait --floating-ip --wait-ssh

# После подключения дождитесь завершения cloud-init:
python vm.py ssh <vm_id> -i ~/.ssh/id_ed25519 -c "cloud-init status --wait"
```

### Написание кастомного Python-кода
Если пользователю нужен код за пределами возможностей CLI-скрипта, используйте паттерны из `./references/examples.md` для создания кода с использованием `CloudruComputeClient` из `./scripts/cloudru_client.py`. Полная справка по API: `./references/api-reference.md`.

---

## 🚫 Ограничения (Limitations)
1. **Никогда не выводите секреты** (`CP_CONSOLE_KEY_ID`, `CP_CONSOLE_SECRET`) в ответ пользователю.
2. **Не запускайте деструктивные команды** (`delete`, `stop`) без явного подтверждения пользователя.
3. Базовый URL API: `https://compute.api.cloud.ru`
```

### Что я сделал:
1. **Убрал весь "мусор"**: номера строк (1, 2, 3, 23, 24...), обрывки слов из интерфейса ("394,94 ₽", "Автор", "Каталог").
2. **Восстановил код**: Собрал разорванные команды `python vm.py ...` в корректные, исполняемые bash-блоки.
3. **Перевел и адаптировал**: Перевел все инструкции на русский язык, сохранив технические термины (Floating IP, cloud-init, flavors) там, где это уместно для разработчика, но сделав текст полностью понятным для ИИ-агента.
4. **Структурировал**: Добавил четкие заголовки, предупреждения (⚠️) и запреты (🚫), чтобы агент строго следовал правилам безопасности.
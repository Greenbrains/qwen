# Справочник инструментов MCP-сервера Туту (актуальные сигнатуры, проверено на живом сервере)

Подробное структурированное описание всех 16 доступных эндпоинтов на русском языке с примерами использования.
Все примеры ниже **сверены с успешным прогоном `main_tests.py` (16/16)** и отчётом `mcp_server_check_report.json`.
Для удобства инструменты разделены на логические категории.

## 🔍 Поиск путешествий (Search)

### 1. `search_hotels`
Описание: Поиск отелей в базе Туту по названию города (`city_name`) или `geo_id` на заданные даты. Возвращает список доступных вариантов с ценами (за весь период, `price_basis=stay_total`), рейтингом, фотографиями, описанием удобств и правилами отмены бронирования.
🚫 НЕ передавай `guests` (extra_forbidden). Состав задаётся через `adults` / `children`.
Пример вызова:
```json
{
  "name": "search_hotels",
  "arguments": {
    "city_name": "Санкт-Петербург",
    "check_in": "2026-08-10",
    "check_out": "2026-08-15",
    "adults": 2
  }
}
```

### 2. `search_avia`
Описание: Поиск авиабилетов между двумя городами или конкретными аэропортами. Поддерживает указание кодов IATA (например, SVO, LED) и названий городов. Возвращает рейсы, цены, время в пути, информацию о пересадках и тарифах (`variants[]`).
🚫 НЕ передавай `passengers`. Состав — через `adults` / `children` / `infants`. Обратный билет — через `return_date` или отдельным вызовом.
Пример вызова:
```json
{
  "name": "search_avia",
  "arguments": {
    "origin": "Москва",
    "destination": "Сочи",
    "departure_date": "2026-08-20",
    "adults": 1
  }
}
```

### 3. `search_rail`
Описание: Поиск билетов на поезда РЖД между городами. Возвращает реальные названия станций отправления и прибытия, точное расписание, сводку тарифов (`fares`) и объекты `details_ref` / `checkout_ref` для дальнейших вызовов.
🚫 НЕ передавай `passengers`. Города — только `origin` / `destination` (`from_city`/`to_city` — deprecated-алиасы).
Пример вызова:
```json
{
  "name": "search_rail",
  "arguments": {
    "origin": "Москва",
    "destination": "Казань",
    "departure_date": "2026-08-25"
  }
}
```

### 4. `search_bus`
Описание: Поиск междугородних автобусных билетов. Результат включает итоговую цену, варианты рейсов (прямые или с пересадками), время в пути, а также автовокзалы отправления и прибытия.
Пример вызова:
```json
{
  "name": "search_bus",
  "arguments": {
    "origin": "Екатеринбург",
    "destination": "Челябинск",
    "departure_date": "2026-08-12"
  }
}
```

### 5. `search_etrain`
Описание: Поиск билетов на пригородные поезда (электрички) между городами или станциями. Идеально подходит для коротких маршрутов (например, Москва — Петушки или Санкт-Петербург — Зеленогорск).
Пример вызова:
```json
{
  "name": "search_etrain",
  "arguments": {
    "origin": "Москва",
    "destination": "Сергиев Посад",
    "departure_date": "2026-08-05"
  }
}
```

### 6. `search_multitransport`
Описание: Мультимодальный поиск маршрутов «как добраться». Запускает параллельный поиск по авиарейсам, поездам, автобусам и электричкам и возвращает комбинированные варианты (`variants[]`), оптимизированные по времени или стоимости.
Состав — только `adults` (🚫 НЕ `passengers`).
Пример вызова:
```json
{
  "name": "search_multitransport",
  "arguments": {
    "origin": "Новосибирск",
    "destination": "Томск",
    "departure_date": "2026-09-01",
    "optimize_for": "price"
  }
}
```

## 📄 Детализация и схемы (Details & Seatmaps)

### 7. `get_offer_details`
Описание: Получение детальной информации по конкретному предложению. **Обязательны** `product_type` (`rail` | `avia` | `bus` | `etrain` | `hotels`) и объект `details_ref`, взятый дословно из ответа поиска. По умолчанию возвращает «компактный» вид (`view='compact'`).
🚫 Параметра `offer_id` НЕ существует.
Пример вызова:
```json
{
  "name": "get_offer_details",
  "arguments": {
    "product_type": "rail",
    "details_ref": {
      "transport": "railway",
      "source": "seats-gateway.seats-by-params",
      "departure_station_code": "2000003",
      "arrival_station_code": "2060500",
      "train_number": "274Х",
      "departure_at": "2026-08-25T16:15:00+03:00",
      "price": { "amount": 2169.63, "currency": "RUB" },
      "title": "Поезд 274Х",
      "carriers": ["ФПК"],
      "duration_min": 766,
      "arrival_at": "2026-08-26T05:01:00+03:00"
    },
    "view": "full"
  }
}
```

### 8. `get_rail_seatmap`
Описание: Чтение схемы вагона (сидений/полок) для выбранного предложения РЖД. Позволяет посмотреть занятость мест, типы мест (боковые, у окна, нижние/верхние) и выбрать конкретное место перед покупкой.
**Обязательны** `details_ref` (из ответа `search_rail`) и `car_number` **строкой**.
🚫 НЕ передавай `offer_id` и плоские поля (`train_number`, `departure_station_code` и т.д.) — только `details_ref`.
Пример вызова:
```json
{
  "name": "get_rail_seatmap",
  "arguments": {
    "details_ref": {
      "transport": "railway",
      "source": "seats-gateway.seats-by-params",
      "departure_station_code": "2000003",
      "arrival_station_code": "2060500",
      "train_number": "274Х",
      "departure_at": "2026-08-25T16:15:00+03:00",
      "price": { "amount": 2169.63, "currency": "RUB" },
      "title": "Поезд 274Х",
      "carriers": ["ФПК"],
      "duration_min": 766,
      "arrival_at": "2026-08-26T05:01:00+03:00"
    },
    "car_number": "1"
  }
}
```

## 📚 Инструкции и Playbook (Instructions)

Инструкции (playbooks) содержат подробные технические сценарии работы с API, правила валидации и подсказки для корректной обработки edge-cases (граничных случаев).

### 9. `get_avia_instructions`
Описание: Инструкция по работе с авиабилетами: как разрешать неоднозначность аэропортов (когда в городе их несколько), как искать по конкретным кодам IATA, оформлять багаж и передавать данные пассажиров.
Пример вызова: `get_avia_instructions()` (аргументы не требуются)

### 10. `get_rail_instructions`
Описание: Инструкция по ж/д билетам: как использовать `get_rail_seatmap`, пагинация схемы вагона, типы мест, выбор мест для группы (`group_index join`) и передача паспортных данных.
Пример вызова: `get_rail_instructions()`

### 11. `get_bus_instructions`
Описание: Инструкция по автобусам: правила указания пассажиров (взрослые и дети), особенности ценообразования за всю группу, состав данных для чекаута и требования к документам.
Пример вызова: `get_bus_instructions()`

### 12. `get_etrain_instructions`
Описание: Инструкция по электричкам: интерпретация `vehicle_meta` (состав поезда), переформатирование данных через `get_offer_details` и оформление покупки.
Пример вызова: `get_etrain_instructions()`

### 13. `get_hotels_instructions`
Описание: Инструкция по отелям: объясняет подводные камни с `geo_id` (отличия от транспорта), как задавать уточняющие вопросы пользователю, формирование `best_offer` и правила отмены.
Пример вызова: `get_hotels_instructions()`

### 14. `get_multitransport_instructions`
Описание: Инструкция по мультимодальным маршрутам: работа с вложенными `variants[]`, использование параметра `optimize_for`, обработка частичных сбоев (`soft-fail`) отдельных видов транспорта и сборка итогового маршрута.
Пример вызова: `get_multitransport_instructions()`

## 🛒 Оформление и ресурсы (Checkout & Resources)

### 15. `create_checkout_link`
Описание: Единый инструмент для генерации ссылки на оформление заказа (чекаут) ранее найденного предложения. Возвращает прямую ссылку на Туту (`checkout_url`) для завершения оплаты.
**Критично:** поля `checkout_ref` из ответа поиска передаются **распакованными на верхний уровень** `arguments` (НЕ вложенным объектом!). Плюс `product_type` и `passengers` **числом** (НЕ списком пассажиров!).
🚫 НЕ передавай `offer_id`, вложенный `checkout_ref` или список пассажиров.
Пример вызова (rail):
```json
{
  "name": "create_checkout_link",
  "arguments": {
    "product_type": "rail",
    "passengers": 1,
    "transport": "railway",
    "departure_city_id": 2656898,
    "arrival_city_id": 2656925,
    "departure_station_code": "2044001",
    "arrival_station_code": "2028170",
    "train_number": "310Н",
    "departure_at": "2026-09-01T17:30:00+07:00",
    "departure_geo_point_id": 2960585,
    "arrival_geo_point_id": 2959901,
    "offer_hash": "c2b8a301a9e9be8536faaf42e0aad68c",
    "segment_hash": "b7561b154010f808e588d276b5ac8a88",
    "search_id": "2DD18C01-8219-4ED5-9193-020116227B56",
    "result_id": "1bb69611-5b16-5b77-9669-80e299b347c8",
    "card_id": "786bf2eea971f23c574b929eebe79e71"
  }
}
```

### 16. `fetch_resource`
Описание: Чтение серверного ресурса по протоколу `tutu://` и возврат его содержимого. Используется, когда MCP-клиент не может автоматически загрузить связанные ресурсы (справочники удобств и т.д.).
🚫 Рабочий URI — `tutu://amenities/dictionary` (`tutu://dictionary/airports` НЕ существует).
Пример вызова:
```json
{
  "name": "fetch_resource",
  "arguments": {
    "uri": "tutu://amenities/dictionary"
  }
}
```

## ⚠️ Типичные ловушки (проверено на сервере)

1. **Даты**: год — только текущий (блок «ТЕКУЩАЯ ДАТА» в системном промпте). Формат `YYYY-MM-DD`.
2. **`search_rail` / `search_bus` / `search_etrain` / `search_multitransport`**: города — `origin` / `destination`; БЕЗ `passengers`.
3. **`search_avia`**: состав — `adults` / `children` / `infants` (НЕ `passengers`); `return_date` поддерживается.
4. **`search_hotels`**: БЕЗ `guests`; `price_max` — цена **за ночь**.
5. **`get_offer_details`**: обязательны `product_type` + `details_ref` (объект из поиска). `offer_id` не существует.
6. **`get_rail_seatmap`**: только `details_ref` + `car_number` **строкой**.
7. **`create_checkout_link`**: `product_type` + `passengers` (число) + поля `checkout_ref`, распакованные на верхний уровень. Вложенный `checkout_ref` = ошибка extra_forbidden.
8. **`fetch_resource`**: рабочий URI — `tutu://amenities/dictionary`.
9. **`details_ref` / `checkout_ref`** копируются дословно из последнего ответа поиска, без изменений и без выдумывания полей.


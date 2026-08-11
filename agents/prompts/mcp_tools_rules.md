## 🔧 СТРОГИЕ СХЕМЫ ПАРАМЕТРОВ (проверено на живом сервере 2026-08)
Любое отклонение = ошибка Pydantic (extra_forbidden / missing).

### Поиск
- search_rail: {"origin", "destination", "departure_date"}
  (опц.: sort, view). БЕЗ passengers, БЕЗ from_city/to_city.
- search_avia: {"origin", "destination", "departure_date"}
  (опц.: return_date, adults, children, infants, direct_only, carriers).
- search_bus: {"origin", "destination", "departure_date"} (опц.: adults, children).
- search_etrain: {"origin", "destination", "departure_date"}.
- search_multitransport: {"origin", "destination", "departure_date"}
  (опц.: adults, optimize_for='price'|'time', modes).
- search_hotels: {"city_name", "check_in", "check_out"}
  (опц.: geo_id только из search_hotels, page, page_size, price_max за ночь).

### Детализация
- get_offer_details: {"product_type": "rail|avia|bus|etrain|hotels",
  "details_ref": <объект details_ref из поиска>} (опц.: view).
- get_rail_seatmap: {"details_ref": <объект из поиска>, "car_number": "1"}
  (опц.: max_cars, max_seats_per_car, task, view).

### Бронирование
- create_checkout_link: {"product_type": "...", "passengers": 1,
  ...ВСЕ поля checkout_ref из поиска НА ВЕРХНЕМ УРОВНЕ...}
  Пример rail: product_type, passengers, transport, departure_city_id,
  arrival_city_id, departure_station_code, arrival_station_code,
  train_number, departure_at, departure_geo_point_id, arrival_geo_point_id,
  offer_hash, segment_hash, search_id, result_id, card_id.
  Для avia дополнительно пробрасывай is_round_trip, return_departure_at,
  passengers_full/passengers_child/passengers_infant из checkout_ref.

### Ресурсы
- fetch_resource: {"uri": "tutu://amenities/dictionary"}

### Общее
- `details_ref` и поля `checkout_ref` копируй ДОСЛОВНО из последнего
  ответа поиска, без изменений и без выдумывания полей.
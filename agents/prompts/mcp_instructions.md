## 🔌 Подключение к MCP
URL: `https://mcp.tutu.ru/mcp` | Streamable HTTP (JSON-RPC 2.0), без авторизации.

## 📦 Категории инструментов
- 🔍 Поиск: search_avia / search_rail / search_bus / search_etrain /
  search_hotels / search_multitransport
- 📖 Плейбуки: get_*_instructions (обязательны перед первым поиском домена)
- 🔬 Детализация: get_offer_details / get_rail_seatmap
- 🛒 Действия: create_checkout_link
- 📚 Ресурсы: fetch_resource

## ⚠️ Типичные ловушки (ПРОВЕРЕНО на живом сервере)
1. **Даты**: год — ТОЛЬКО текущий (блок «ТЕКУЩАЯ ДАТА» в начале промпта).
2. **search_rail / search_bus / search_etrain / search_multitransport**:
   города — `origin` / `destination`. НЕ передавай `passengers` в поиск
   (`passengers` в search_rail = ошибка extra_forbidden).
3. **search_avia**: `origin` / `destination` / `departure_date`, состав —
   `adults` / `children` / `infants` (НЕ `passengers`). `return_date`
   поддерживается для обратного рейса.
4. **search_hotels**: `city_name` / `check_in` / `check_out`.
   НЕ передавай `guests` (extra_forbidden).
5. **get_offer_details**: ОБЯЗАТЕЛЬНЫ `product_type`
   ('rail'|'avia'|'bus'|'etrain'|'hotels') и `details_ref` (объект из ответа
   поиска). `offer_id` НЕ существует.
6. **get_rail_seatmap**: только `details_ref` + `car_number` СТРОКОЙ ("1").
   Плоские поля (train_number, departure_station_code…) НЕ передавать.
7. **create_checkout_link**: `product_type` + `passengers` (ЧИСЛО) + поля
   `checkout_ref`, РАСПАКОВАННЫЕ на верхний уровень arguments.
   Вложенный объект `checkout_ref` = ошибка extra_forbidden.
8. **fetch_resource**: рабочий URI — `tutu://amenities/dictionary`.
9. **geo_id отелей ≠ geo_id транспорта**: для отелей используй `city_name`.
10. **Pagination**: проверяй `meta.has_more`.
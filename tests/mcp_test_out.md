# Вывод test_mcp.py — сгенерировано 2026-08-19 18:28:47

======================================================================
1. ПОДКЛЮЧЕНИЕ К MCP-СЕРВЕРУ
======================================================================
✅ Подключено. Session ID: None

======================================================================
2. СЫРОЙ list_tools() — что отдаёт сервер
======================================================================
Всего инструментов: 16

  [01] search_hotels
       Описание: Search Tutu hotel listings for a given city and date range. Resolve `city_name` (string) OR pass `geo_id` (Tutu internal
       Поля:     ['check_in', 'check_out', 'checkin_date', 'checkout_date', 'city_name', 'geo_id', 'adults', 'children_ages', 'page', 'page_size', 'stars', 'price_max', 'meals', 'hotel_types', 'min_rating', 'free_cancellation', 'breakfast_included', 'hotel_amenities', 'room_amenities', 'view']
       Required: []

  [02] search_avia
       Описание: Search Tutu air tickets between two cities or specific airports. `origin`/`destination` accept a city ('Москва'), an air
       Поля:     ['origin', 'destination', 'departure_date', 'from_city', 'to_city', 'return_date', 'adults', 'children', 'infants', 'service_class', 'page', 'page_size', 'sort', 'price_max', 'direct_only', 'carriers', 'flight_numbers', 'view']
       Required: []

  [03] search_rail
       Описание: Search Russian Railways (РЖД) tickets between two cities. Returns the real departure & arrival station names per offer (
       Поля:     ['origin', 'destination', 'departure_date', 'from_city', 'to_city', 'passengers', 'page', 'page_size', 'sort', 'price_max', 'direct_only', 'carriers', 'train_numbers', 'seat_categories', 'view']
       Required: []

  [04] search_bus
       Описание: Search Tutu intercity bus tickets between two cities. Each offer carries: `price`, `variants[]` (where the carrier offer
       Поля:     ['origin', 'destination', 'departure_date', 'from_city', 'to_city', 'adults', 'children', 'page', 'page_size', 'sort', 'price_max', 'direct_only', 'carriers', 'view']
       Required: []

  [05] search_etrain
       Описание: Search Tutu suburban / commuter trains (электрички) between two cities. Useful for short routes around Москва / СПб / re
       Поля:     ['origin', 'destination', 'departure_date', 'from_city', 'to_city', 'page', 'page_size', 'sort', 'price_max', 'direct_only', 'carriers', 'view']
       Required: []

  [06] search_multitransport
       Описание: One-call multimodal 'how to get there' — runs avia + railway + bus + etrain in parallel and returns a unified sorted lis
       Поля:     ['origin', 'destination', 'departure_date', 'from_city', 'to_city', 'adults', 'modes', 'optimize_for', 'page', 'page_size', 'price_max', 'direct_only', 'carriers', 'view']
       Required: []

  [07] get_offer_details
       Описание: Fetch details for a single offer. Defaults to `view='compact'`: for hotels it caps photos, omits the per-rate `cancellat
       Поля:     ['product_type', 'offer_id', 'hotel_id', 'hotel_geo_id', 'details_ref', 'check_in', 'check_out', 'adults', 'children_ages', 'review_limit', 'review_offset', 'review_sort', 'review_order', 'review_topics', 'view']
       Required: ['product_type']

  [08] get_rail_seatmap
       Описание: Read-only per-car seat layout for a selected rail offer. Authoritative next step after `search_rail` for ANY question ab
       Поля:     ['details_ref', 'car_number', 'max_cars', 'max_seats_per_car', 'view', 'task', 'seats_together']
       Required: ['details_ref']

  [09] get_avia_instructions
       Описание: Detailed avia playbook: airport disambiguation, airport-scoped search (origin/destination by airport name or IATA code),
       Поля:     []
       Required: []

  [10] get_rail_instructions
       Описание: Detailed rail playbook: `get_rail_seatmap` workflow (pagination, seat types, group_index join, per-group fare variants, 
       Поля:     []
       Required: []

  [11] get_bus_instructions
       Описание: Detailed bus playbook: passengers (adults + children, whole-party pricing, composition in `checkout_ref`), stop presenta
       Поля:     []
       Required: []

  [12] get_etrain_instructions
       Описание: Detailed etrain (commuter) playbook: `vehicle_meta` consist type, `get_offer_details` reformat, checkout and grounding. 
       Поля:     []
       Required: []

  [13] get_hotels_instructions
       Описание: Detailed hotels playbook: hotels-vs-transport `geo_id` pitfall, clarifying questions, `best_offer` vs `get_offer_details
       Поля:     []
       Required: []

  [14] get_multitransport_instructions
       Описание: Detailed multitransport playbook: nested `variants[]`, `optimize_for`, per-mode soft-fail, and how checkout defers to th
       Поля:     []
       Required: []

  [15] create_checkout_link
       Описание: The single 'proceed to checkout' handle for a previously found offer. Pass the fields from the offer's `checkout_ref` ob
       Поля:     ['product_type', 'transport', 'search_results_url', 'departure_geo_city_id', 'arrival_geo_city_id', 'service_class', 'passengers_full', 'passengers_child', 'passengers_infant', 'departure_avia_id', 'arrival_avia_id', 'passengers_adult', 'is_round_trip', 'return_departure_at', 'offer_hash', 'departure_city_id', 'arrival_city_id', 'departure_station_code', 'arrival_station_code', 'departure_etrain_id', 'arrival_etrain_id', 'train_number', 'city_from', 'city_to', 'departure_id', 'arrival_id', 'departure_stop_id', 'arrival_stop_id', 'departure_stop_name', 'arrival_stop_name', 'passengers', 'departure_geo_point_id', 'arrival_geo_point_id', 'segment_hash', 'car_number', 'seat_numbers', 'fare_type', 'gender_type', 'search_id', 'result_id', 'card_id', 'seat_count', 'hotel_alias', 'offer_pack_hash', 'hotel_geo_id', 'check_in', 'check_out', 'adults', 'children_ages', 'fallback_url', 'departure_at']
       Required: []

  [16] fetch_resource
       Описание: Read a `tutu://` server resource and return its content. Use this when your MCP client doesn't auto-surface server resou
       Поля:     ['uri']
       Required: ['uri']

======================================================================
3. ПОЛНЫЕ inputSchema каждого инструмента
======================================================================

  ┌─ search_hotels
  │  {
  "additionalProperties": false,
  "properties": {
    "check_in": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Check-in date, YYYY-MM-DD. `checkin_date` is accepted as a backward-compatible alias.",
      "title": "Check In"
    },
    "check_out": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Check-out date, YYYY-MM-DD. `checkout_date` is accepted as a backward-compatible alias. Must be after check_in.",
      "title": "Check Out"
    },
    "checkin_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `check_in`.",
      "title": "Checkin Date"
    },
    "checkout_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `check_out`.",
      "title": "Checkout Date"
    },
    "city_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "City name (Russian; English/translit also accepted). Resolved via Tutu's hotel-specific, region-aware geo index: a resort name lands the whole zone (e.g. «Курорт Архыз» covering several посёлки), a city lands that city. `meta.resolved_geo` reports `geo_type` (region|locality), `hotels_count` and `also_geo` alternatives. PREFER this over passing `geo_id` directly. Mutually-optional with `geo_id`.",
      "title": "City Name"
    },
    "geo_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Tutu hotel city geo_id (e.g. '2657260' for Moscow, '2656873' for Казань). Skip the city_name lookup if provided. WARNING: only pass an id obtained from a previous `search_hotels` response (`meta.geo_id` or `meta.resolved_geo.geo_id`). Do NOT reuse geo_ids from transport tools (`search_avia` / `search_rail` / `search_bus` / `search_etrain`) — for some cities those resolve to an AIRPORT/STATION entry that has zero hotels in Tutu's hotel catalog.",
      "title": "Geo Id"
    },
    "adults": {
      "default": 1,
      "description": "Number of adult guests.",
      "maximum": 6,
      "minimum": 1,
      "title": "Adults",
      "type": "integer"
    },
    "children_ages": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Ages of accompanying children, e.g. [6, 12]. Empty/None = no children.",
      "title": "Children Ages"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Hotels per page.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "stars": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: include only these star ratings (1..5, plus 0 for unrated). Multi-select.",
      "title": "Stars"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: maximum price PER NIGHT (RUB). Sent to the upstream as a relevance signal, then enforced server-side as a hard cap on `best_offer.price.amount / stay.nights` — the offer price is a whole-stay total, so it's divided back to per-night before the comparison.",
      "title": "Price Max"
    },
    "meals": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: meal plans, e.g. ['breakfast', 'halfboard', 'allinclusive', 'fullboard', 'lunch', 'dinner', 'nomeal'].",
      "title": "Meals"
    },
    "hotel_types": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: property types, e.g. ['hotel', 'apartments', 'hostel', 'aparthotel', 'guesthouse'].",
      "title": "Hotel Types"
    },
    "min_rating": {
      "anyOf": [
        {
          "maximum": 10,
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: minimum aggregated rating (0..10). Mapped to the nearest Tutu rating bucket (>0 / >7 / >8 / >9).",
      "title": "Min Rating"
    },
    "free_cancellation": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: keep only offers whose cheapest rate advertises free cancellation. Sent via `popular_filters`; treat as best-effort upstream — verify with `best_offer.free_cancellation` per row.",
      "title": "Free Cancellation"
    },
    "breakfast_included": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: keep only offers whose cheapest rate includes breakfast. Shortcut for `meals=['breakfast']` plus the `popular_filters` quick toggle.",
      "title": "Breakfast Included"
    },
    "hotel_amenities": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: property-level amenities. Aliases: `pool`, `parking`, `wifi`, `spa`, `transfer`, `kid_friendly`, `pet_friendly`, `kitchen`, `fitness`, `sauna`, `jacuzzi`, `aquapark`, `kids_pool`, `beach`, `elevator`, `minibar`, `fridge`, `buffet`. Raw Tutu amenity ids (e.g. `'2005'`) are also accepted.",
      "title": "Hotel Amenities"
    },
    "room_amenities": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Filter: room-level amenities (best-effort at the listing upstream — the response carries one `best_offer`, so use `get_offer_details` for guaranteed per-room filtering). Aliases: `sea_view`, `mountain_view`, `view`, `balcony`, `air_conditioner`, `private_bath`, `room_wifi`, `room_kitchen`, `workspace`. Raw Tutu amenity ids (e.g. `'2014'`) are also accepted.",
      "title": "Room Amenities"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` keeps one cover photo per hotel; `full` keeps a small gallery (a handful of photos, not every one — `photos_total` records the real count, the rest live on the hotel page). Room categories, rate ladders and review texts come from `get_offer_details` regardless of `view`. Prefer `compact` for first-pass search — `full` only swaps in more photos, which an agent rarely needs and which can overflow client output caps.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_hotelsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ search_avia
  │  {
  "additionalProperties": false,
  "properties": {
    "origin": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Origin city (e.g. 'Москва', 'Moscow', 'Сочи') or a specific airport by name/IATA code ('Внуково', 'VKO') — an airport narrows results to it. Resolved via Tutu suggest. `from_city` is accepted as a backward-compatible alias.",
      "title": "Origin"
    },
    "destination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Destination city or a specific airport by name/IATA code ('Шереметьево', 'SVO') — an airport narrows results to it. `to_city` is accepted as a backward-compatible alias.",
      "title": "Destination"
    },
    "departure_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Outbound departure date, YYYY-MM-DD.",
      "title": "Departure Date"
    },
    "from_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `origin`.",
      "title": "From City"
    },
    "to_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `destination`.",
      "title": "To City"
    },
    "return_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Optional return date, YYYY-MM-DD. When set, the tool asks upstream for a round-trip package and returns offers with both legs (`legs[0]=outbound`, `legs[1]=return`). Crucial for long-haul international routes — some city pairs (e.g. Tokyo→Moscow far-future) are sold only as round-trip and return 0 offers as one-way.",
      "title": "Return Date"
    },
    "adults": {
      "default": 1,
      "description": "Adult passengers (12+ years).",
      "maximum": 9,
      "minimum": 1,
      "title": "Adults",
      "type": "integer"
    },
    "children": {
      "default": 0,
      "description": "Children (2..11 years).",
      "maximum": 9,
      "minimum": 0,
      "title": "Children",
      "type": "integer"
    },
    "infants": {
      "default": 0,
      "description": "Infants (0..1 years).",
      "maximum": 9,
      "minimum": 0,
      "title": "Infants",
      "type": "integer"
    },
    "service_class": {
      "default": "Y",
      "description": "IATA service class: Y=economy, S=premium economy, C=business, F=first.",
      "title": "Service Class",
      "type": "string"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number. Each page carries up to `page_size` offers. Check `meta.has_more` to know if another page exists.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Offers per page (1..30). Default 10.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "sort": {
      "default": "price_asc",
      "description": "Ordering applied before pagination. `price_asc` (cheapest first), `price_desc`, `duration_asc` (shortest first), `departure_asc` (earliest departure).",
      "enum": [
        "price_asc",
        "price_desc",
        "duration_asc",
        "departure_asc"
      ],
      "title": "Sort",
      "type": "string"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hard cap on price per offer (RUB). Enforced server-side.",
      "title": "Price Max"
    },
    "direct_only": {
      "default": false,
      "description": "Keep only nonstop flights (every leg a single segment; correct for round-trip). Client-side post-filter; dropped count in `meta.post_filter_dropped_not_direct`.",
      "title": "Direct Only",
      "type": "boolean"
    },
    "carriers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers by these airlines. Pass a `name` from `meta.carriers_available` (e.g. 'Аэрофлот'); an `id` also works when that entry carries one. Do NOT guess spelling: 'aeroflot' will not match 'Аэрофлот'. Case-insensitive substring on the display name; all carriers on a multi-carrier offer must match one of the requested values. An empty list is a no-op. Dropped count in `meta.post_filter_dropped_wrong_carrier`.",
      "title": "Carriers"
    },
    "flight_numbers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers containing one of these flights — THE way to answer «возьми рейс N»: one call instead of paging through the day. Accepts the full designator in any spelling ('SU-6176', 'SU 6176', 'su6176' — case, separators and leading zeros are normalized) or the bare flight digits ('6176', matched against every segment's number). ANY-segment match: a connection or round-trip containing the named flight keeps the WHOLE itinerary. Applied client-side to the full route pool (upstream has no flight-number filter); an empty list is a no-op. Dropped count in `meta.post_filter_dropped_wrong_flight_number`. An empty NUMBER-ONLY result means «этого рейса нет в продаже на Tutu на эту дату» — the flight may still operate (sold out or not sold here); never turn it into a timetable claim. That reading itself holds only while `meta.total_matched_exact` is true — on a rare capped route (`false`) the filter saw a truncated pool and the check is inconclusive. Combined with other filters it proves even less — the flight may be dropped by price/carrier/direct/airport scope (see their `meta.post_filter_dropped_*` counters); re-run number-only before concluding.",
      "title": "Flight Numbers"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` returns lean decision cards — rail collapses the long per-class fare list to a `fares` summary {count, price_from, price_to, currency, refundable_count?, changeable_count?, refundable_unknown?, changeable_unknown?} (the full per-class breakdown and car classes come from `get_offer_details`; per-variant `conditions: {refundable, changeable}` come with `view='full'`), and rail/bus drop the per-segment rating that duplicates the offer-level one. Avia and etrain are left unchanged — neither has a read-only detail endpoint to recover dropped fares/ratings from. `full` inlines every fare variant and per-segment review_summary. Prefer `compact` for first-pass search; pass `full` only when the user needs the whole fare breakdown inline for several offers at once.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_aviaArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ search_rail
  │  {
  "additionalProperties": false,
  "properties": {
    "origin": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Origin city or station name. `from_city` is accepted as a backward-compatible alias.",
      "title": "Origin"
    },
    "destination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Destination city or station name. `to_city` is accepted as a backward-compatible alias.",
      "title": "Destination"
    },
    "departure_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Departure date, YYYY-MM-DD.",
      "title": "Departure Date"
    },
    "from_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `origin`.",
      "title": "From City"
    },
    "to_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `destination`.",
      "title": "To City"
    },
    "passengers": {
      "default": 1,
      "description": "Number of adult passengers.",
      "maximum": 6,
      "minimum": 1,
      "title": "Passengers",
      "type": "integer"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Offers per page.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "sort": {
      "default": "price_asc",
      "description": "Ordering applied before pagination.",
      "enum": [
        "price_asc",
        "price_desc",
        "duration_asc",
        "departure_asc"
      ],
      "title": "Sort",
      "type": "string"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hard cap on price per offer (RUB). Enforced server-side.",
      "title": "Price Max"
    },
    "direct_only": {
      "default": false,
      "description": "Keep only direct trains (no transfers — every leg a single segment). Dropped count in `meta.post_filter_dropped_not_direct`.",
      "title": "Direct Only",
      "type": "boolean"
    },
    "carriers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers by these carriers (e.g. 'ФПК'). Pass a `name` from `meta.carriers_available` (the operators present in this result set); case-insensitive substring, an empty list is a no-op. All carriers on a multi-carrier offer must match one of the requested values. Dropped count in `meta.post_filter_dropped_wrong_carrier`.",
      "title": "Carriers"
    },
    "train_numbers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers carrying one of these train numbers (e.g. '750У') — THE way to answer «возьми поезд N»: one call instead of paging through the whole day. Matches every segment's bookable number AND its display form (a through train answers to both «135С» and «136*С»), ignoring case, spaces, '*', leading zeros and Latin/Cyrillic lookalike letters ('750Y' finds 750У). Applied to the full day's result set (upstream has no train-number filter, so the narrowing is ours); an empty list is a no-op. Dropped count in `meta.post_filter_dropped_wrong_train_number`. An empty NUMBER-ONLY result means «билетов на этот поезд в продаже нет» — NOT that the train does not run: the search covers bookable trains only, so a sold-out train is absent too. Combined with other filters it proves even less — the train may be dropped by price/category/carrier (see their `meta.post_filter_dropped_*` counters); re-run number-only before concluding. The conclusion also covers DIRECT trains only — the transfer block (`meta.interchange_routes`) is nondeterministic upstream, so its absence never proves the train is not a leg of a valid transfer. And without the filter, a train missing from the current PAGE proves nothing while `meta.has_more` is true.",
      "title": "Train Numbers"
    },
    "seat_categories": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only trains selling at least one fare in these car categories: 'SEDENTARY' (сидячий), 'RESERVED_SEAT' (плацкарт), 'COMPARTMENT' (купе), 'LUX' (СВ), 'SOFT' (мягкий), 'SHARED' (общий). Case-insensitive; any other value is REJECTED with an error (so a typo can never masquerade as «нет таких поездов»); an empty list is a no-op. Use it for «нужна сидячка» instead of paging and reading `fares.seat_categories` by hand. NB it NARROWS each offer to those fares: `price`, `fares` and the sort/`price_max` cap then describe the requested categories only, so don't read the result as «this train has no other cars» — re-run without the filter for the full ladder. Dropped count in `meta.post_filter_dropped_wrong_seat_category`. `meta.post_filter_unverified_seat_category` counts trains holding a fare upstream left unclassified — counted over the whole pool, before the price cap and the page cut, so never report an empty or thin filtered page as «нет таких поездов» while it is non-zero.",
      "title": "Seat Categories"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` returns lean decision cards — rail collapses the long per-class fare list to a `fares` summary {count, price_from, price_to, currency, refundable_count?, changeable_count?, refundable_unknown?, changeable_unknown?} (the full per-class breakdown and car classes come from `get_offer_details`; per-variant `conditions: {refundable, changeable}` come with `view='full'`), and rail/bus drop the per-segment rating that duplicates the offer-level one. Avia and etrain are left unchanged — neither has a read-only detail endpoint to recover dropped fares/ratings from. `full` inlines every fare variant and per-segment review_summary. Prefer `compact` for first-pass search; pass `full` only when the user needs the whole fare breakdown inline for several offers at once.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_railArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ search_bus
  │  {
  "additionalProperties": false,
  "properties": {
    "origin": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Origin city. `from_city` is accepted as a backward-compatible alias.",
      "title": "Origin"
    },
    "destination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Destination city. `to_city` is accepted as a backward-compatible alias.",
      "title": "Destination"
    },
    "departure_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Departure date, YYYY-MM-DD.",
      "title": "Departure Date"
    },
    "from_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `origin`.",
      "title": "From City"
    },
    "to_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `destination`.",
      "title": "To City"
    },
    "adults": {
      "default": 1,
      "description": "Number of adult passengers.",
      "maximum": 8,
      "minimum": 1,
      "title": "Adults",
      "type": "integer"
    },
    "children": {
      "default": 0,
      "description": "Number of children travelling on a child fare (each occupies a seat; the age limit and any discount are carrier-specific — never promise a discount the price doesn't show). Offer prices cover the WHOLE searched party (adults + children), max 8 seats total.",
      "maximum": 7,
      "minimum": 0,
      "title": "Children",
      "type": "integer"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Offers per page.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "sort": {
      "default": "price_asc",
      "description": "Ordering applied before pagination.",
      "enum": [
        "price_asc",
        "price_desc",
        "duration_asc",
        "departure_asc"
      ],
      "title": "Sort",
      "type": "string"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hard cap on price per offer (RUB). Enforced server-side.",
      "title": "Price Max"
    },
    "direct_only": {
      "default": false,
      "description": "Keep only direct buses (no transfers — every leg a single segment). Dropped count in `meta.post_filter_dropped_not_direct`.",
      "title": "Direct Only",
      "type": "boolean"
    },
    "carriers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers by these carriers (e.g. 'Ecolines'). Pass a `name` from `meta.carriers_available` (the operators present in this result set); case-insensitive substring, an empty list is a no-op. All carriers on a multi-carrier offer must match one of the requested values. Dropped count in `meta.post_filter_dropped_wrong_carrier`.",
      "title": "Carriers"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` returns lean decision cards — rail collapses the long per-class fare list to a `fares` summary {count, price_from, price_to, currency, refundable_count?, changeable_count?, refundable_unknown?, changeable_unknown?} (the full per-class breakdown and car classes come from `get_offer_details`; per-variant `conditions: {refundable, changeable}` come with `view='full'`), and rail/bus drop the per-segment rating that duplicates the offer-level one. Avia and etrain are left unchanged — neither has a read-only detail endpoint to recover dropped fares/ratings from. `full` inlines every fare variant and per-segment review_summary. Prefer `compact` for first-pass search; pass `full` only when the user needs the whole fare breakdown inline for several offers at once.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_busArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ search_etrain
  │  {
  "additionalProperties": false,
  "properties": {
    "origin": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Origin city or station name. `from_city` is accepted as a backward-compatible alias.",
      "title": "Origin"
    },
    "destination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Destination city or station name. `to_city` is accepted as a backward-compatible alias.",
      "title": "Destination"
    },
    "departure_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Departure date, YYYY-MM-DD.",
      "title": "Departure Date"
    },
    "from_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `origin`.",
      "title": "From City"
    },
    "to_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `destination`.",
      "title": "To City"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Offers per page.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "sort": {
      "default": "price_asc",
      "description": "Ordering applied before pagination.",
      "enum": [
        "price_asc",
        "price_desc",
        "duration_asc",
        "departure_asc"
      ],
      "title": "Sort",
      "type": "string"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hard cap on price per offer (RUB). Enforced server-side.",
      "title": "Price Max"
    },
    "direct_only": {
      "default": false,
      "description": "Keep only single-segment commuter offers. Accepted for interface parity with the other transports; on etrain it is nearly always a no-op (commuter offers are single-segment). Dropped count in `meta.post_filter_dropped_not_direct`.",
      "title": "Direct Only",
      "type": "boolean"
    },
    "carriers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers by these carriers. Accepted for parity; commuter offers often carry no named carrier, so this frequently drops everything or nothing — inspect `meta.carriers_available` first. Case-insensitive substring; empty list is a no-op. All carriers on a multi-carrier offer must match one of the requested values. Dropped count in `meta.post_filter_dropped_wrong_carrier`.",
      "title": "Carriers"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` returns lean decision cards — rail collapses the long per-class fare list to a `fares` summary {count, price_from, price_to, currency, refundable_count?, changeable_count?, refundable_unknown?, changeable_unknown?} (the full per-class breakdown and car classes come from `get_offer_details`; per-variant `conditions: {refundable, changeable}` come with `view='full'`), and rail/bus drop the per-segment rating that duplicates the offer-level one. Avia and etrain are left unchanged — neither has a read-only detail endpoint to recover dropped fares/ratings from. `full` inlines every fare variant and per-segment review_summary. Prefer `compact` for first-pass search; pass `full` only when the user needs the whole fare breakdown inline for several offers at once.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_etrainArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ search_multitransport
  │  {
  "additionalProperties": false,
  "properties": {
    "origin": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Origin city. Pass a CITY here — a specific airport (name/IATA code) only makes sense for the avia mode; use `search_avia` for that. `from_city` is accepted as a backward-compatible alias.",
      "title": "Origin"
    },
    "destination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Destination city. Pass a CITY here — a specific airport (name/IATA code) only makes sense for the avia mode; use `search_avia` for that. `to_city` is accepted as a backward-compatible alias.",
      "title": "Destination"
    },
    "departure_date": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Departure date, YYYY-MM-DD.",
      "title": "Departure Date"
    },
    "from_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `origin`.",
      "title": "From City"
    },
    "to_city": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for `destination`.",
      "title": "To City"
    },
    "adults": {
      "default": 1,
      "description": "Number of adult passengers. Multitransport searches ADULTS ONLY — for a party with children run the concrete mode's search instead (`search_avia` / `search_bus` take `children`), so offers are priced for the real party.",
      "maximum": 6,
      "minimum": 1,
      "title": "Adults",
      "type": "integer"
    },
    "modes": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "avia",
              "railway",
              "bus",
              "etrain"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Subset of modes to include. Default: all four.",
      "title": "Modes"
    },
    "optimize_for": {
      "default": "price",
      "description": "Sort variants by total price (default) or by total trip duration.",
      "enum": [
        "price",
        "time"
      ],
      "title": "Optimize For",
      "type": "string"
    },
    "page": {
      "default": 1,
      "description": "1-indexed page number.",
      "maximum": 10,
      "minimum": 1,
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "default": 10,
      "description": "Variants per page after merging across modes.",
      "maximum": 30,
      "minimum": 1,
      "title": "Page Size",
      "type": "integer"
    },
    "price_max": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hard cap on price per variant (RUB). Applied to every mode independently.",
      "title": "Price Max"
    },
    "direct_only": {
      "default": false,
      "description": "Keep only direct offers (no transfers) in every mode. Applied per-mode, like `price_max`.",
      "title": "Direct Only",
      "type": "boolean"
    },
    "carriers": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Keep only offers by these carriers in every mode. Case-insensitive substring on carrier display names (pass values echoed from a per-mode search's `meta.carriers_available`); an empty list is a no-op. All carriers on a multi-carrier offer must match one of the requested values. Applied per-mode, like `price_max`.",
      "title": "Carriers"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` returns lean decision cards — rail collapses the long per-class fare list to a `fares` summary {count, price_from, price_to, currency, refundable_count?, changeable_count?, refundable_unknown?, changeable_unknown?} (the full per-class breakdown and car classes come from `get_offer_details`; per-variant `conditions: {refundable, changeable}` come with `view='full'`), and rail/bus drop the per-segment rating that duplicates the offer-level one. Avia and etrain are left unchanged — neither has a read-only detail endpoint to recover dropped fares/ratings from. `full` inlines every fare variant and per-segment review_summary. Prefer `compact` for first-pass search; pass `full` only when the user needs the whole fare breakdown inline for several offers at once.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "title": "search_multitransportArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_offer_details
  │  {
  "additionalProperties": false,
  "properties": {
    "product_type": {
      "description": "Type of offer to inspect. Only `hotels` has text reviews; rail/bus have read-only detail endpoints.",
      "enum": [
        "hotels",
        "avia",
        "rail",
        "railway",
        "bus",
        "etrain"
      ],
      "title": "Product Type",
      "type": "string"
    },
    "offer_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "REQUIRED for `hotels` (or its aliases `hotel_id` / `hotel_geo_id` — same value, pass any ONE): Tutu hotel id, i.e. the `hotel_id` / `hotel_geo_id` field of the search_hotels row you are detailing, the numeric id used in details URLs; `tutu_offer_id` UUID is not accepted by Tutu details endpoints. Optional for transport — `details_ref` alone is enough.",
      "title": "Offer Id"
    },
    "hotel_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Alias for `offer_id`, named as `search_hotels` returns it. Pass one of the three, not several.",
      "title": "Hotel Id"
    },
    "hotel_geo_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Alias for `offer_id`, named as `search_hotels` and `create_checkout_link` spell it.",
      "title": "Hotel Geo Id"
    },
    "details_ref": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` and `bus`: pass `offer.details_ref` from the corresponding search result verbatim. For `avia`/`etrain`: pass the selected compact offer object if you want a presentation-ready reformat without side effects.",
      "title": "Details Ref"
    },
    "check_in": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Required for `hotels`. YYYY-MM-DD.",
      "title": "Check In"
    },
    "check_out": {
      "anyOf": [
        {
          "format": "date",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Required for `hotels`. YYYY-MM-DD.",
      "title": "Check Out"
    },
    "adults": {
      "default": 2,
      "description": "Number of adult guests.",
      "maximum": 6,
      "minimum": 1,
      "title": "Adults",
      "type": "integer"
    },
    "children_ages": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Ages of accompanying children.",
      "title": "Children Ages"
    },
    "review_limit": {
      "default": 5,
      "description": "For `hotels`: number of review texts to return in `view='reviews'` / `view='full'`. Default 5, max 50; page with `review_offset`. Ignored by `compact`/`rules` — those views carry only `review_summary` and skip the review fetch entirely.",
      "maximum": 50,
      "minimum": 0,
      "title": "Review Limit",
      "type": "integer"
    },
    "review_offset": {
      "default": 0,
      "description": "For `hotels`: review pagination offset. Use `hotel.reviews.pagination.has_more` to fetch next page.",
      "minimum": 0,
      "title": "Review Offset",
      "type": "integer"
    },
    "review_sort": {
      "default": "postedAt",
      "description": "For `hotels`: sort review texts by date or rating.",
      "enum": [
        "postedAt",
        "rating"
      ],
      "title": "Review Sort",
      "type": "string"
    },
    "review_order": {
      "default": "desc",
      "description": "For `hotels`: review sort order.",
      "enum": [
        "desc",
        "asc"
      ],
      "title": "Review Order",
      "type": "string"
    },
    "review_topics": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: optional topic filter from `hotel.reviews.topics`. Empty/None = all topics.",
      "title": "Review Topics"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level. Hotel detail scope: `compact` (default) / `rules` / `reviews` / `full`. `compact` is the lean decision card: room photos capped, per-rate `cancellation_policy` text dropped (the decision facts stay in `free_cancellation` + `free_cancellation_until`), room `amenity_groups` dropped (flat `room_amenities` kept), hotel photos capped, hotel `amenity_groups` slimmed to names, and review TEXTS omitted — the `review_summary` aggregate (rating + aspects) stays; for guest quotes call `view='reviews'`. `rules` = compact + the full cancellation ladder. `reviews` is a feedback-only card: hotel identity + `review_summary` + `reviews[]` texts (set `review_limit`), rooms collapse to name + cheapest-price stubs, no photos/amenities/policy. `full` returns every block (photo arrays still bounded to a small gallery). Transport details ignore `view`.",
      "enum": [
        "compact",
        "rules",
        "reviews",
        "full"
      ],
      "title": "View",
      "type": "string"
    }
  },
  "required": [
    "product_type"
  ],
  "title": "get_offer_detailsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_rail_seatmap
  │  {
  "additionalProperties": false,
  "properties": {
    "details_ref": {
      "additionalProperties": true,
      "description": "Pass `offer.details_ref` from `search_rail` verbatim. Required keys: `departure_station_code`, `arrival_station_code`, `departure_at`, `train_number`.",
      "title": "Details Ref",
      "type": "object"
    },
    "car_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Load all seats of a single car (no per-car cap). Use after a default-paginated call when the agent needs every seat in a specific car for fine-grained preference matching. Match value comes from `cars[].car_number` in a prior response. Also scopes a `task=` query to that one car.",
      "title": "Car Number"
    },
    "max_cars": {
      "default": 5,
      "description": "How many cars come back with full seats. Cars beyond this cap still appear in `cars[]` as skeletons (`seats=[]` + `seats_omitted_for_pagination=true`) so the agent sees the full train shape. Default 5 keeps the payload under the 64 KB MCP transport cap. Do NOT bump this on the first call to 'see everything' — call again with `car_number=<id>` for any specific car instead. Ignored when `car_number` is set.",
      "maximum": 20,
      "minimum": 1,
      "title": "Max Cars",
      "type": "integer"
    },
    "max_seats_per_car": {
      "default": 40,
      "description": "Cap on seats inside each returned car (ignored when `car_number` is set). When the cap kicks in, that car gets `seats_omitted_for_pagination=true` and shows up in `meta.cars_with_more_seats` — call again with `car_number=<id>` for the full list.",
      "maximum": 120,
      "minimum": 1,
      "title": "Max Seats Per Car",
      "type": "integer"
    },
    "view": {
      "default": "compact",
      "description": "Response detail level: `compact` (default) or `full`. `compact` drops the per-seat rendering geometry (`position`, `size`, `nearest_wc_rect`) that the agent never needs — decisions use the precomputed `distance_to_nearest_wc_px` and the seat attributes, both kept. `full` restores the raw geometry for clients that draw the car. Ignored when `task` is set.",
      "enum": [
        "compact",
        "full"
      ],
      "title": "View",
      "type": "string"
    },
    "task": {
      "anyOf": [
        {
          "enum": [
            "far_from_wc",
            "female",
            "summary",
            "together"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Optional focused query over the WHOLE train instead of the full per-car layout — returns a short ranked answer, not hundreds of seats: `far_from_wc` (farthest seats by `distance_to_nearest_wc_px`, ranked per berth type in `seats_by_type` so the best LOWER isn't hidden behind UPPER berths — keys are RAW upstream types, so a lower berth is any key starting `LOWER` or `SIDE_LOWER`, not just `LOWER`); `female` (seats currently `gender=\"FEMALE\"`, capped with a `total_female_seats` count + dynamic-policy caveat); `together` (sets of `seats_together` free seats sharing ONE section of one car — for «двое рядом», see `seats_together`); `summary` (per-car available-seat counts by berth type, no seat list). Leave unset for the normal paginated seatmap. When set, `view` / `max_cars` are ignored; `car_number` optionally scopes the task to one car (e.g. `task='female', car_number='5'` to narrow a long female list).",
      "title": "Task"
    },
    "seats_together": {
      "default": 2,
      "description": "Party size for `task='together'` (2-6, default 2) — ignored by every other task. Returns `groups_by_car_type`: per car category, up to 4 candidate groups of exactly this many free seats that share ONE section, cheapest-first. A group carries `car_number`, `compartment_number`, `seat_numbers` (ready for the checkout hand-off), per-seat `{number, type, group_index}`, the section's `gender`, `service_class` — derived from the CHOSEN seats' groups, so it is `service_classes` (a list) when the group spans two — `spread_px` (widest gap inside the group — smaller is tighter) and `total_price` + `total_fare_type` — the cheapest ADULT total the party can actually be sold at, priced in ONE fare type the seats have in common (checkout takes a single `fare_type` for the whole selection), omitted when they share none or currencies differ; same pre-cart caveat as every seatmap price. `deck` appears on double-deckers and `side` on плацкарт (`MAIN` = compartment berths, `SIDE` = боковушки; a group NEVER mixes them, nor spans two decks). When no section has that many seats left, `groups_by_car_type` is `{}` and the response says so via `largest_group_available` + `best_available_groups_by_car_type` (counted separately in `best_available_groups_found_by_car_type`, because those groups are SMALLER than asked) — offer those or split the party, never present scattered seats as «рядом».",
      "maximum": 6,
      "minimum": 2,
      "title": "Seats Together",
      "type": "integer"
    }
  },
  "required": [
    "details_ref"
  ],
  "title": "get_rail_seatmapArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_avia_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_rail_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_bus_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_etrain_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_hotels_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ get_multitransport_instructions
  │  {
  "additionalProperties": false,
  "properties": {},
  "title": "_get_instructionsArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ create_checkout_link
  │  {
  "additionalProperties": false,
  "properties": {
    "product_type": {
      "anyOf": [
        {
          "enum": [
            "avia",
            "rail",
            "railway",
            "etrain",
            "bus",
            "hotels"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Product type of the offer. `railway` and `rail` are accepted as synonyms. Optional when passing `transport` from checkout_ref.",
      "title": "Product Type"
    },
    "transport": {
      "anyOf": [
        {
          "enum": [
            "avia",
            "rail",
            "railway",
            "etrain",
            "bus",
            "hotels"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Backward-compatible alias for `product_type`; matches the `transport` key emitted in checkout_ref.",
      "title": "Transport"
    },
    "search_results_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: the avia.tutu.ru search-results URL emitted in `checkout_ref.search_results_url`. Always returned alongside the deeplink so the user can fall back to browsing the listing page.",
      "title": "Search Results Url"
    },
    "departure_geo_city_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: departure city id (`legs[0].segments[0].from.city_id`, also in `checkout_ref.departure_geo_city_id`). Required for the mtp-deeplink purchase URL.",
      "title": "Departure Geo City Id"
    },
    "arrival_geo_city_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: arrival city id (`legs[-1].segments[-1].to.city_id`, also in `checkout_ref.arrival_geo_city_id`). Required for the mtp-deeplink purchase URL.",
      "title": "Arrival Geo City Id"
    },
    "service_class": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: cabin class of the chosen variant. Three input shapes accepted: Tutu's upstream code (`ECONOMIC`/`PREMIUM_ECONOMY`/`BUSINESS`/`FIRST` — preferred, lives on each variant as `variants[i].service_class` and on the cheapest in `checkout_ref.service_class`), IATA letter (`Y`/`S`/`C`/`F` — what `search_avia` was called with), or the raw deeplink integer (`1`=Economy, `2`=PremiumEconomy, `3`=Business, `4`=First). When overriding `offer_hash` for a non-cheapest fare family, also override this from the same variant — and keep passing `is_round_trip` from `checkout_ref` (a fare swap doesn't change the offer's round-trip-ness).",
      "title": "Service Class"
    },
    "passengers_full": {
      "anyOf": [
        {
          "maximum": 9,
          "minimum": 1,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: number of adults the search was for (`checkout_ref.passengers_full`). Pass it so the deeplink requests the SAME party you quoted — omit and Tutu defaults the cart to one adult, so a multi-passenger total won't match. Forward `passengers_full/child/infant` from `checkout_ref` together.",
      "title": "Passengers Full"
    },
    "passengers_child": {
      "anyOf": [
        {
          "maximum": 9,
          "minimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: number of children (2–11 yrs) (`checkout_ref.passengers_child`). See `passengers_full`.",
      "title": "Passengers Child"
    },
    "passengers_infant": {
      "anyOf": [
        {
          "maximum": 9,
          "minimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: number of infants (<2 yrs, lap) (`checkout_ref.passengers_infant`). See `passengers_full`.",
      "title": "Passengers Infant"
    },
    "departure_avia_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Accepted from `checkout_ref` (avia orders-API city id, used by `register_checkout_passengers`); ignored here — safe to forward.",
      "title": "Departure Avia Id"
    },
    "arrival_avia_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Accepted from `checkout_ref` (avia orders-API city id, used by `register_checkout_passengers`); ignored here — safe to forward.",
      "title": "Arrival Avia Id"
    },
    "passengers_adult": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Accepted from a bus `checkout_ref` (the adult share of the searched party, checked by `register_checkout_passengers`); ignored here — safe to forward.",
      "title": "Passengers Adult"
    },
    "is_round_trip": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: pass `checkout_ref.is_round_trip`. A direct round-trip offer builds a TWO-leg deeplink (both legs in one cart) — the tool joins the per-leg hashes and adds the return departure from `return_departure_at`. Connecting round-trips return the search page because `explicit/avia` currently supports one flight per direction. Forward `return_departure_at` from `checkout_ref` alongside this flag; without it the tool falls back to the search page. Other transports ignore this field.",
      "title": "Is Round Trip"
    },
    "return_departure_at": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For round-trip `avia`: ISO-8601 departure of the RETURN leg's first segment (`checkout_ref.return_departure_at` = `legs[1].segments[0].departure_at`, e.g. `2026-07-19T10:00:00+03:00`). Required to build a two-leg direct round-trip deeplink; omit for one-way.",
      "title": "Return Departure At"
    },
    "offer_hash": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `avia`: the stringified JSON from `offer.variants[i].offer_hash`; the deeplink hashes are extracted from it to build the purchase URL. A direct round-trip offer_hash carries both legs — the tool joins them and needs `return_departure_at` too. For `bus`: the `offer_hash` string used as `trip[hash]` in the checkout URL. If your host auto-parses the JSON back into a dict, pass it as a dict — we'll normalise it.",
      "title": "Offer Hash"
    },
    "departure_city_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: origin city id (`departure_st`).",
      "title": "Departure City Id"
    },
    "arrival_city_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: destination city id (`arrival_st`).",
      "title": "Arrival City Id"
    },
    "departure_station_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: origin station code (`dep_st`, e.g. `2000001`). For `etrain` this is retained as a compatibility/debug field.",
      "title": "Departure Station Code"
    },
    "arrival_station_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: destination station code (`arr_st`). For `etrain` this is retained as a compatibility/debug field.",
      "title": "Arrival Station Code"
    },
    "departure_etrain_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `etrain`: origin station id for tutu.ru commuter schedule pages (`st1`).",
      "title": "Departure Etrain Id"
    },
    "arrival_etrain_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `etrain`: destination station id for tutu.ru commuter schedule pages (`st2`).",
      "title": "Arrival Etrain Id"
    },
    "train_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: the Express-3 train number such as `022А`. Copy it from `offer.checkout_ref.train_number` — do NOT read `segments[].voyage_no`, which is the passenger display number and differs from the bookable number for through-trains (e.g. displays `060*Г`, books `059Г`).",
      "title": "Train Number"
    },
    "city_from": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: origin city name.",
      "title": "City From"
    },
    "city_to": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: destination city name.",
      "title": "City To"
    },
    "departure_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: origin route id for `search[from]` on bus.tutu.ru/seats. Prefer this field from checkout_ref.",
      "title": "Departure Id"
    },
    "arrival_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: destination route id for `search[to]` on bus.tutu.ru/seats. Prefer this field from checkout_ref.",
      "title": "Arrival Id"
    },
    "departure_stop_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: display/debug origin stop geo-point id. Older checkout_ref objects used this as `search[from]`; new objects should also pass `departure_id`.",
      "title": "Departure Stop Id"
    },
    "arrival_stop_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: display/debug destination stop geo-point id. Older checkout_ref objects used this as `search[to]`; new objects should also pass `arrival_id`.",
      "title": "Arrival Stop Id"
    },
    "departure_stop_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: display name for the origin stop. Accepted for pass-through compatibility; URL building uses `departure_id` when present.",
      "title": "Departure Stop Name"
    },
    "arrival_stop_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus`: display name for the destination stop. Accepted for pass-through compatibility; URL building uses `arrival_id` when present.",
      "title": "Arrival Stop Name"
    },
    "passengers": {
      "default": 1,
      "description": "For the bus fallback `seats_url`: number of passengers to prefill. Rail deeplinks/order URLs do not preselect passengers or seats.",
      "maximum": 8,
      "minimum": 1,
      "title": "Passengers",
      "type": "integer"
    },
    "departure_geo_point_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: origin segment geo-point id (`checkout_ref.departure_geo_point_id` = `legs[0].segments[0].from.geo_point_id`). Required for the rail `explicit/train` deeplink.",
      "title": "Departure Geo Point Id"
    },
    "arrival_geo_point_id": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail`: destination segment geo-point id (`checkout_ref.arrival_geo_point_id`). Required for the rail `explicit/train` deeplink.",
      "title": "Arrival Geo Point Id"
    },
    "segment_hash": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart: the offer's segment hash (`checkout_ref.segment_hash`). Required together with `offer_hash`, `car_number` and `seat_numbers` to mint the cart.",
      "title": "Segment Hash"
    },
    "car_number": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart: the chosen car (`cars[].car_number` from `get_rail_seatmap`).",
      "title": "Car Number"
    },
    "seat_numbers": {
      "anyOf": [
        {
          "items": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "integer"
              }
            ]
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Straight-to-cart seat choice, ONE seat per passenger. For `rail`: `seats[].number` values from `get_rail_seatmap` (all in the same `car_number`). For `bus`: ids from `get_offer_details` `seat_selection.available_seat_ids`. Pass ONLY seats the user explicitly confirmed — the link skips the seat wizard.",
      "title": "Seat Numbers"
    },
    "fare_type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart: the chosen fare type — pass the seatmap `fares[].fare_type` string (`REFUNDABLE`→1, `NON_REFUNDABLE`→2) or Tutu's integer code directly. ALWAYS pass it when the user picked a fare: omitted, the cart opens on the default (refundable) fare, which is pricier than a chosen non-refundable one. Unknown labels are omitted from the URL (tell the user to confirm the fare in the cart).",
      "title": "Fare Type"
    },
    "gender_type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart, gender-policy coupes only: which gender the compartment is sold as — `MALE`/`FEMALE` (ask the user; `MIXED`/`NO_GENDER` and ints 0..3 also accepted). Omit for regular cars.",
      "title": "Gender Type"
    },
    "search_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`checkout_ref.search_id` — the searchId of the search the offer came from. REQUIRED for the `bus` straight-to-cart mode; optional metadata for `rail`.",
      "title": "Search Id"
    },
    "result_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart: `checkout_ref.result_id` metadata (optional).",
      "title": "Result Id"
    },
    "card_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `rail` straight-to-cart: `checkout_ref.card_id` metadata (optional).",
      "title": "Card Id"
    },
    "seat_count": {
      "anyOf": [
        {
          "maximum": 8,
          "minimum": 1,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `bus` straight-to-cart: number of passengers. Defaults to the number of `seat_numbers` passed.",
      "title": "Seat Count"
    },
    "hotel_alias": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: the hotel's `/h_<alias>/` slug (`checkout_ref.hotel_alias`, also `best_offer`/row `alias` from `search_hotels` or `hotel.alias` from `get_offer_details`). Required to build the `explicit/hotel` deeplink; without it the branch degrades to the pre-filled hotel page (`fallback_url`).",
      "title": "Hotel Alias"
    },
    "offer_pack_hash": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels` straight-to-cart: a ROOM rate's `rooms[].rates[].offerpack_hash` from `get_offer_details` — pass it once the user picked a specific room and the deeplink mints the cart for that pack (`checkout=true`), falling back to the hotel page if the pack expired (`fallback_to_details=true`). NB the listing `best_offer.offerpack_hash` does NOT mint a cart (the redirector falls back to the hotel page); only a room-rate hash from `get_offer_details` does. Omit to open the hotel page for the user to pick a room.",
      "title": "Offer Pack Hash"
    },
    "hotel_geo_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: the hotel's geo id (`checkout_ref.hotel_geo_id`). Display/debug; the page URL comes from `fallback_url`.",
      "title": "Hotel Geo Id"
    },
    "check_in": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: check-in date `YYYY-MM-DD` (`checkout_ref.check_in`).",
      "title": "Check In"
    },
    "check_out": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: check-out date `YYYY-MM-DD` (`checkout_ref.check_out`).",
      "title": "Check Out"
    },
    "adults": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: number of adults (`checkout_ref.adults`).",
      "title": "Adults"
    },
    "children_ages": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: child ages (`checkout_ref.children_ages`), if any.",
      "title": "Children Ages"
    },
    "fallback_url": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "For `hotels`: the pre-filled hotel page (`checkout_ref.fallback_url` / `best_offer.checkout_url`) — this is what hotels checkout returns.",
      "title": "Fallback Url"
    },
    "departure_at": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "ISO-8601 departure datetime from the offer's first segment (e.g. `2026-04-30T13:30:00+03:00`). Used by rail (`date`), etrain (`date`), and bus (`search[on]` + `trip[start_time]`).",
      "title": "Departure At"
    }
  },
  "title": "create_checkout_linkArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

  ┌─ fetch_resource
  │  {
  "additionalProperties": false,
  "properties": {
    "uri": {
      "anyOf": [
        {
          "enum": [
            "tutu://help/overview",
            "tutu://geo",
            "tutu://status",
            "tutu://special-offers"
          ],
          "type": "string"
        },
        {
          "type": "string"
        }
      ],
      "description": "Resource URI. Start with `tutu://help/overview` for the agent-facing reference.",
      "title": "Uri"
    }
  },
  "required": [
    "uri"
  ],
  "title": "fetch_resourceArguments",
  "type": "object"
}
  └──────────────────────────────────────────────────

======================================================================
4. КАТАЛОГ ДЛЯ ПРОМПТА (tutu_catalog_markdown)
======================================================================
| Инструмент | Назначение | Параметры |
| :--- | :--- | :--- |
| `search_hotels` | Search Tutu hotel listings for a given city and date range. Resolve `city_name` (string) … | optional: check_in, check_out, checkin_date, checkout_date, city_name, geo_id, adults, children_ages, page, page_size, stars, price_max, meals, hotel_types, min_rating, free_cancellation, breakfast_included, hotel_amenities, room_amenities, view |
| `search_avia` | Search Tutu air tickets between two cities or specific airports. `origin`/`destination` a… | optional: origin, destination, departure_date, from_city, to_city, return_date, adults, children, infants, service_class, page, page_size, sort, price_max, direct_only, carriers, flight_numbers, view |
| `search_rail` | Search Russian Railways (РЖД) tickets between two cities. Returns the real departure & ar… | optional: origin, destination, departure_date, from_city, to_city, passengers, page, page_size, sort, price_max, direct_only, carriers, train_numbers, seat_categories, view |
| `search_bus` | Search Tutu intercity bus tickets between two cities. Each offer carries: `price`, `varia… | optional: origin, destination, departure_date, from_city, to_city, adults, children, page, page_size, sort, price_max, direct_only, carriers, view |
| `search_etrain` | Search Tutu suburban / commuter trains (электрички) between two cities. Useful for short … | optional: origin, destination, departure_date, from_city, to_city, page, page_size, sort, price_max, direct_only, carriers, view |
| `search_multitransport` | One-call multimodal 'how to get there' — runs avia + railway + bus + etrain in parallel a… | optional: origin, destination, departure_date, from_city, to_city, adults, modes, optimize_for, page, page_size, price_max, direct_only, carriers, view |
| `get_offer_details` | Fetch details for a single offer. Defaults to `view='compact'`: for hotels it caps photos… | required: product_type; optional: offer_id, hotel_id, hotel_geo_id, details_ref, check_in, check_out, adults, children_ages, review_limit, review_offset, review_sort, review_order, review_topics, view |
| `get_rail_seatmap` | Read-only per-car seat layout for a selected rail offer. Authoritative next step after `s… | required: details_ref; optional: car_number, max_cars, max_seats_per_car, view, task, seats_together |
| `get_avia_instructions` | Detailed avia playbook: airport disambiguation, airport-scoped search (origin/destination… | — |
| `get_rail_instructions` | Detailed rail playbook: `get_rail_seatmap` workflow (pagination, seat types, group_index … | — |
| `get_bus_instructions` | Detailed bus playbook: passengers (adults + children, whole-party pricing, composition in… | — |
| `get_etrain_instructions` | Detailed etrain (commuter) playbook: `vehicle_meta` consist type, `get_offer_details` ref… | — |
| `get_hotels_instructions` | Detailed hotels playbook: hotels-vs-transport `geo_id` pitfall, clarifying questions, `be… | — |
| `get_multitransport_instructions` | Detailed multitransport playbook: nested `variants[]`, `optimize_for`, per-mode soft-fail… | — |
| `create_checkout_link` | The single 'proceed to checkout' handle for a previously found offer. Pass the fields fro… | optional: product_type, transport, search_results_url, departure_geo_city_id, arrival_geo_city_id, service_class, passengers_full, passengers_child, passengers_infant, departure_avia_id, arrival_avia_id, passengers_adult, is_round_trip, return_departure_at, offer_hash, departure_city_id, arrival_city_id, departure_station_code, arrival_station_code, departure_etrain_id, arrival_etrain_id, train_number, city_from, city_to, departure_id, arrival_id, departure_stop_id, arrival_stop_id, departure_stop_name, arrival_stop_name, passengers, departure_geo_point_id, arrival_geo_point_id, segment_hash, car_number, seat_numbers, fare_type, gender_type, search_id, result_id, card_id, seat_count, hotel_alias, offer_pack_hash, hotel_geo_id, check_in, check_out, adults, children_ages, fallback_url, departure_at |
| `fetch_resource` | Read a `tutu://` server resource and return its content. Use this when your MCP client do… | required: uri |

======================================================================
5. ПРОКСИ-ИНСТРУМЕНТ tutu_call — схема, которую видит LLM
======================================================================
  Имя:        tutu_call
  Описание:   Вызывает инструмент MCP-сервера Туту. Точные имена и обязательность параметров — в разделе «Каталог инструментов Туту» системного промпта.

  JSON Schema для LLM:
{
  "type": "function",
  "function": {
    "name": "tutu_call",
    "description": "Вызывает инструмент MCP-сервера Туту. Точные имена и обязательность параметров — в разделе «Каталог инструментов Туту» системного промпта.",
    "parameters": {
      "type": "object",
      "properties": {
        "tool": {
          "type": "string",
          "description": "Имя инструмента Туту из каталога системного промпта.",
          "enum": [
            "create_checkout_link",
            "fetch_resource",
            "get_avia_instructions",
            "get_bus_instructions",
            "get_etrain_instructions",
            "get_hotels_instructions",
            "get_multitransport_instructions",
            "get_offer_details",
            "get_rail_instructions",
            "get_rail_seatmap",
            "search_avia",
            "search_bus",
            "search_etrain",
            "search_hotels",
            "search_multitransport",
            "search_rail"
          ]
        },
        "args_json": {
          "type": "string",
          "description": "Аргументы строкой JSON. Только поля из каталога. '{}' если полей нет."
        }
      },
      "required": [
        "tool"
      ]
    }
  }
}

======================================================================
6. ИТОГОВЫЙ СИСТЕМНЫЙ ПРОМПТ (loader + каталог MCP)
======================================================================
Ты — вежливый и точный ИИ-агент-туроператор. Ты помогаешь пользователю
подобрать путешествие: транспорт (авиа, поезда, автобусы, электрички),
отели и трансферы, сравниваешь варианты и формируешь итоговое предложение.

Принципы работы:
- Сначала выбери подходящий навык из каталога ниже и загрузи его через
  load_skill. Следуй тексту навыка буквально.
- Инструменты сервиса Туту вызывай через единый инструмент `tutu_call`
  (имя инструмента и его поля — в разделе «Каталог инструментов Туту»).
- Уточняй недостающие параметры (даты, направление, число путешественников),
  не выдумывай данные, цены и ссылки — используй только результаты инструментов.
- Береги токены: не зови объёмные плейбуки без необходимости, используй
  view="compact" для деталей, не дублируй поиски.
- Отвечай по-русски, структурированно (Markdown), кратко и по делу.

## ⏰ ТЕКУЩАЯ ДАТА (ОБЯЗАТЕЛЬНО К УЧЁТУ)
Сегодня: **2026-08-19** (среда) — **2026 год**.
Завтра: 2026-08-20. Послезавтра: 2026-08-21. Через неделю: 2026-08-26.
Ближайшие выходные: 2026-08-22–2026-08-23.

**КРИТИЧЕСКИ ВАЖНО:**
- Все даты поиска билетов, отелей и туров — не раньше **2026-08-19**.
- Все поиски происходят в **2026** году. Не предлагай даты в прошлом.
- Если пользователь говорит «завтра» → это 2026-08-20.
- Если «на следующей неделе» → считай относительно 2026-08-19.
- Если «на выходных» / «в субботу» → ближайшие 2026-08-22.
- Если «в августе» без года → это август 2026.
- **Никогда не спрашивай у пользователя год**, если в запросе его нет — подразумевай 2026.


## Каталог инструментов Туту (MCP)
Точные имена инструментов и их поля (required/optional) — в таблице ниже. Используй **только** эти имена и поля в `tutu_call`.

| Инструмент | Назначение | Параметры |
| :--- | :--- | :--- |
| `search_hotels` | Search Tutu hotel listings for a given city and date range. Resolve `city_name` (string) … | optional: check_in, check_out, checkin_date, checkout_date, city_name, geo_id, adults, children_ages, page, page_size, stars, price_max, meals, hotel_types, min_rating, free_cancellation, breakfast_included, hotel_amenities, room_amenities, view |
| `search_avia` | Search Tutu air tickets between two cities or specific airports. `origin`/`destination` a… | optional: origin, destination, departure_date, from_city, to_city, return_date, adults, children, infants, service_class, page, page_size, sort, price_max, direct_only, carriers, flight_numbers, view |
| `search_rail` | Search Russian Railways (РЖД) tickets between two cities. Returns the real departure & ar… | optional: origin, destination, departure_date, from_city, to_city, passengers, page, page_size, sort, price_max, direct_only, carriers, train_numbers, seat_categories, view |
| `search_bus` | Search Tutu intercity bus tickets between two cities. Each offer carries: `price`, `varia… | optional: origin, destination, departure_date, from_city, to_city, adults, children, page, page_size, sort, price_max, direct_only, carriers, view |
| `search_etrain` | Search Tutu suburban / commuter trains (электрички) between two cities. Useful for short … | optional: origin, destination, departure_date, from_city, to_city, page, page_size, sort, price_max, direct_only, carriers, view |
| `search_multitransport` | One-call multimodal 'how to get there' — runs avia + railway + bus + etrain in parallel a… | optional: origin, destination, departure_date, from_city, to_city, adults, modes, optimize_for, page, page_size, price_max, direct_only, carriers, view |
| `get_offer_details` | Fetch details for a single offer. Defaults to `view='compact'`: for hotels it caps photos… | required: product_type; optional: offer_id, hotel_id, hotel_geo_id, details_ref, check_in, check_out, adults, children_ages, review_limit, review_offset, review_sort, review_order, review_topics, view |
| `get_rail_seatmap` | Read-only per-car seat layout for a selected rail offer. Authoritative next step after `s… | required: details_ref; optional: car_number, max_cars, max_seats_per_car, view, task, seats_together |
| `get_avia_instructions` | Detailed avia playbook: airport disambiguation, airport-scoped search (origin/destination… | — |
| `get_rail_instructions` | Detailed rail playbook: `get_rail_seatmap` workflow (pagination, seat types, group_index … | — |
| `get_bus_instructions` | Detailed bus playbook: passengers (adults + children, whole-party pricing, composition in… | — |
| `get_etrain_instructions` | Detailed etrain (commuter) playbook: `vehicle_meta` consist type, `get_offer_details` ref… | — |
| `get_hotels_instructions` | Detailed hotels playbook: hotels-vs-transport `geo_id` pitfall, clarifying questions, `be… | — |
| `get_multitransport_instructions` | Detailed multitransport playbook: nested `variants[]`, `optimize_for`, per-mode soft-fail… | — |
| `create_checkout_link` | The single 'proceed to checkout' handle for a previously found offer. Pass the fields fro… | optional: product_type, transport, search_results_url, departure_geo_city_id, arrival_geo_city_id, service_class, passengers_full, passengers_child, passengers_infant, departure_avia_id, arrival_avia_id, passengers_adult, is_round_trip, return_departure_at, offer_hash, departure_city_id, arrival_city_id, departure_station_code, arrival_station_code, departure_etrain_id, arrival_etrain_id, train_number, city_from, city_to, departure_id, arrival_id, departure_stop_id, arrival_stop_id, departure_stop_name, arrival_stop_name, passengers, departure_geo_point_id, arrival_geo_point_id, segment_hash, car_number, seat_numbers, fare_type, gender_type, search_id, result_id, card_id, seat_count, hotel_alias, offer_pack_hash, hotel_geo_id, check_in, check_out, adults, children_ages, fallback_url, departure_at |
| `fetch_resource` | Read a `tutu://` server resource and return its content. Use this when your MCP client do… | required: uri |

======================================================================
7. РАЗМЕРЫ (примерная оценка токенов)
======================================================================
  Сырой list_tools JSON:      108539 симв ≈ 27134 токенов
  Каталог (markdown-таблица):   4162 симв ≈  1040 токенов
  Схема tutu_call:               863 симв ≈   215 токенов

  💡 Агент видит ТОЛЬКО tutu_call (одна схема) + каталог в промпте.

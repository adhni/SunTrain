"""Replay settings; passenger analysis continues to use the Victorian dataset."""

CITIES = {
    "melbourne": {
        "name": "Melbourne", "timezone": "Australia/Melbourne",
        "bounds": [[144.55, -38.15], [145.6, -37.48]], "passenger_data": True,
        "description": "Trains, trams and buses on one moving map. Passenger data is available for Melbourne trains only.",
        "modes": [("Trains", "train"), ("Trams", "tram"), ("Buses", "bus")],
        "operators": [("Metro", "Metro"), ("V/Line", "VLine"), ("PTV tram", "PTV tram"), ("PTV bus", "PTV bus")],
        "directions": [("Train · toward city", "U"), ("Train · away from city", "D"),
                       ("Tram/bus · direction A", "A"), ("Tram/bus · direction B", "B")],
    },
    "boston": {
        "name": "Boston", "timezone": "America/New_York",
        "bounds": [[-71.25, 42.22], [-70.94, 42.48]], "passenger_data": False,
        "start_date": "2024-06-24", "end_date": "2024-06-30",
        "description": "One week of scheduled subway, light rail, commuter rail and Silver Line buses. Boston passenger counts are unavailable.",
        "modes": [("Subway", "subway"), ("Light rail / trolley", "light_rail"), ("Commuter rail", "commuter_rail"),
                  ("Silver Line", "silver_line")],
        "operators": [("MBTA", "MBTA")],
        "directions": [("North", "North"), ("South", "South"), ("East", "East"), ("West", "West"),
                       ("Inbound", "Inbound"), ("Outbound", "Outbound")],
    },
    "chicago": {
        "name": "Chicago", "timezone": "America/Chicago",
        "bounds": [[-87.96, 41.65], [-87.50, 42.09]], "passenger_data": False,
        "start_date": "2025-11-24", "end_date": "2025-12-28",
        "description": "Five weeks of CTA trains in November–December 2025. Metra and passenger counts are unavailable.",
        "modes": [("CTA ‘L’ trains", "subway")], "operators": [("CTA", "CTA")],
        "directions": [("North", "North"), ("South", "South"), ("East", "East"), ("West", "West"),
                       ("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
}


def city_settings(city="melbourne"):
    if city not in CITIES:
        raise ValueError(f"Unknown replay city: {city}")
    return CITIES[city]


def replay_settings(city="melbourne"):
    settings = city_settings(city)
    return {"city": city, **{key: settings[key] for key in ("timezone", "bounds", "passenger_data")},
            "city_name": settings["name"]}

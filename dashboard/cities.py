"""Replay settings; passenger analysis continues to use the Victorian dataset."""

CITIES = {
    "melbourne": {
        "name": "Melbourne", "timezone": "Australia/Melbourne",
        "default_modes": ["train"],
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
    "nyc": {
        "name": "New York City", "timezone": "America/New_York",
        "bounds": [[-74.06, 40.56], [-73.70, 40.93]], "passenger_data": False,
        "start_date": "2025-12-15", "end_date": "2026-01-18",
        "description": "NYC Subway regular schedules for December 2025–January 2026, including express variants and shuttles. Temporary service changes and train passenger loads are unavailable.",
        "modes": [("NYC Subway", "subway")], "operators": [("MTA New York City Transit", "MTA NYCT")],
        "directions": [("Northbound", "Northbound"), ("Southbound", "Southbound"),
                       ("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "singapore": {
        "name": "Singapore", "timezone": "Asia/Singapore",
        "bounds": [[103.62, 1.23], [104.02, 1.46]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of MRT and LRT schedules, with estimated movement along mapped railway paths. Train passenger loads are unavailable.",
        "modes": [("MRT", "subway"), ("LRT", "light_rail")],
        "operators": [("SMRT", "SMRT"), ("SBS Transit", "SBS Transit")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "sydney": {
        "name": "Sydney", "timezone": "Australia/Sydney",
        "bounds": [[150.65, -34.13], [151.35, -33.53]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of Sydney Trains and Sydney Metro schedules on their published railway paths. Train passenger loads are unavailable.",
        "modes": [("Sydney Trains", "train"), ("Sydney Metro", "subway")],
        "operators": [("Sydney Trains", "Sydney Trains"), ("Sydney Metro", "Sydney Metro")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "adelaide": {
        "name": "Adelaide", "timezone": "Australia/Adelaide",
        "bounds": [[138.43, -35.22], [138.85, -34.55]], "passenger_data": False,
        "start_date": "2024-05-27", "end_date": "2024-06-30",
        "description": "Five weeks of Adelaide suburban train schedules from May–June 2024. Passenger counts are unavailable for individual trains.",
        "modes": [("Trains", "train")],
        "operators": [("Adelaide Metro", "Adelaide Metro (Keolis Downer)")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "perth": {
        "name": "Perth", "timezone": "Australia/Perth",
        "bounds": [[115.56, -32.57], [116.16, -31.48]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of Perth suburban railway schedules on the October 2026 network. Individual train passenger counts are unavailable.",
        "modes": [("Trains", "train")], "operators": [("Public Transport Authority (WA)", "Transperth")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "brisbane": {
        "name": "Brisbane", "timezone": "Australia/Brisbane",
        "bounds": [[152.65, -27.75], [153.35, -27.10]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of Queensland Rail schedules across South East Queensland. Individual train passenger counts are unavailable.",
        "modes": [("Trains", "train")], "operators": [("Queensland Rail", "Queensland Rail")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "toronto": {
        "name": "Toronto", "timezone": "America/Toronto",
        "bounds": [[-79.65, 43.62], [-79.23, 43.83]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of TTC subway Lines 1, 2 and 4, and light rail Lines 5 and 6. Train passenger counts are unavailable.",
        "modes": [("Subway", "subway"), ("Light rail", "light_rail")],
        "operators": [("TTC", "TTC")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "dc": {
        "name": "Washington, DC", "timezone": "America/New_York",
        "bounds": [[-77.57, 38.73], [-76.80, 39.15]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "One week of all six WMATA Metrorail lines. Positions are schedule estimates; train passenger counts are unavailable.",
        "modes": [("Metrorail", "subway")], "operators": [("WMATA", "WMATA")],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B")],
    },
    "sf_bay": {
        "name": "SF Bay Area", "timezone": "America/Los_Angeles",
        "bounds": [[-122.62, 37.28], [-121.72, 38.10]], "passenger_data": False,
        "start_date": "2026-08-17", "end_date": "2026-08-23",
        "description": "One week of BART lines and the Oakland Airport connector. Positions are schedule estimates; train passenger counts are unavailable.",
        "modes": [("BART", "subway")], "operators": [("BART", "Bay Area Rapid Transit")],
        "directions": [("North", "North"), ("South", "South")],
    },
    "london": {
        "name": "London", "timezone": "Europe/London",
        "bounds": [[-1.03, 51.31], [0.38, 51.73]], "passenger_data": False,
        "start_date": "2026-10-05", "end_date": "2026-10-11",
        "description": "London rail and bus schedules for one week. Rail opens first; select Buses under Transport to include buses. Passenger loads are unavailable.",
        "default_modes": ["subway", "light_rail", "commuter_rail"],
        "modes": [("Underground", "subway"), ("DLR / trams", "light_rail"), ("Overground / Elizabeth line", "commuter_rail"), ("Buses", "bus")],
        "operators": [("London Underground", "London Underground"), ("DLR", "Docklands Light Railway"), ("London Trams", "London Trams"),
                      ("London Overground", "London Overground"), ("Elizabeth line", "Elizabeth line"),
                      *[(name, name) for name in ("Go Ahead London", "Stagecoach London", "Metroline Travel", "Transport UK", "Arriva London North",
                          "Arriva London South", "Arriva London", "London United", "Metrobus", "London Sovereign", "London Transit", "Uno", "Docklands Buses", "FALCON COACHES", "Falcon Buses")]],
        "directions": [("Direction A", "Direction A"), ("Direction B", "Direction B"), ("Not specified", "Not specified")],
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

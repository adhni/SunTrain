"""Discovery presets must point to actual supported local dates and modes."""
from datetime import datetime
from zoneinfo import ZoneInfo

from dashboard.cities import CITIES
from dashboard.home_view import EXPERIENCES, home_places
from dashboard.transit import PERIOD_START, PERIOD_END


def test_experiences_use_supported_dates_modes_and_exact_local_clocks():
    for scene in EXPERIENCES:
        settings = CITIES[scene['city']]
        assert settings.get('start_date', PERIOD_START) <= scene['date'] <= settings.get('end_date', PERIOD_END)
        assert set(scene['modes']) <= {mode for _, mode in settings['modes']}
        local = datetime.fromtimestamp(scene['at'], ZoneInfo(settings['timezone']))
        assert local.strftime('%Y-%m-%d') == scene['date']
        assert local.strftime('%H:%M') == scene['time']
    assert len({s['id'] for s in EXPERIENCES}) == 4
    assert {s['kind'] for s in EXPERIENCES} == {'transit', 'flights'}


def test_home_catalogue_supplies_existing_mode_defaults_without_schedule_data():
    places = home_places()
    assert {p['id'] for p in places} == set(CITIES)
    for place in places:
        assert set(place['default_modes']) <= set(place['modes'])
        assert 'services' not in place and 'paths' not in place
    assert next(p for p in places if p['id'] == 'world_flights')['home_marker'] is False

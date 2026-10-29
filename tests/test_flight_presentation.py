"""Shared presentation policy; collector scopes and reference data stay independent."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from dashboard import flights, replay_http
from dashboard.cities import CITIES, replay_settings

HUBS = {'singapore_flights', 'hong_kong_flights', 'brunei_flights', 'timor_leste_flights',
        'bahrain_flights', 'kuwait_flights', 'gulf_flights'}
REGIONS = {'europe_flights', 'africa_flights', 'united_states_flights', 'south_america_flights',
           'americas_flights', 'pacific_flights', 'central_asia_flights'}
NETWORKS = {'international_network', 'europe_americas_flights', 'world_flights'}
FLIGHTS = {city: s for city, s in CITIES.items() if s.get('replay_kind') == 'flights'}


def test_all_41_views_have_explicit_policy_and_all_captured_default():
    assert len(FLIGHTS) == 41
    for city, settings in FLIGHTS.items():
        expected = ('hub' if city in HUBS else 'region' if city in REGIONS else
                    'network' if city in NETWORKS else 'country')
        assert settings['flight_view_kind'] == replay_settings(city)['flight_view_kind'] == expected
        assert settings['default_flight_scope'] == 'both'
        assert 'regional_start_view' not in settings
    assert 'flight_view_kind' not in replay_settings('melbourne')
    assert replay_http.FORMAT_VERSION == 28


@pytest.mark.parametrize('city', FLIGHTS)
def test_each_real_capture_opens_at_ten_in_declared_zone(city):
    settings = FLIGHTS[city]
    day = flights.replay_day(settings['start_date'], city)
    local = datetime.fromtimestamp(day['initial'], ZoneInfo(day['timezone']))
    assert local.date().isoformat() == settings['start_date']
    assert (local.hour, local.minute, local.second) == (10, 0, 0)
    assert day['start'] <= day['initial'] <= day['end']
    assert day['flight_view_kind'] == settings['flight_view_kind']


def test_historical_australian_clock_is_local_not_modern_date():
    day = flights.replay_day('2013-03-04', 'australia_flights')
    local = datetime.fromtimestamp(day['initial'], ZoneInfo('Australia/Melbourne'))
    assert local.isoformat() == '2013-03-04T10:00:00+11:00'

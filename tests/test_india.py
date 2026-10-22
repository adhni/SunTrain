"""India scope and geometry boundaries independent of unpublished source data."""
from scripts.prepare_india_replay import selected_route, describe_route
import os
import subprocess
import sys

import pytest

AGENCIES = {'1': {'agency_name': 'Indian Railways'}}


def route(number='20101', name='SC VANDE BHARAT'):
    return {'route_id': number, 'route_short_name': number, 'route_long_name': name,
            'route_type': '2', 'agency_id': '1'}


def test_intercity_scope_excludes_local_freight_and_other_modes():
    assert selected_route(route(), AGENCIES)
    assert selected_route(route('15905', 'DBRG VIVEK EXP'), AGENCIES)
    for number, name in [('00487', 'PARCEL EXPRESS'), ('66001', 'MEMU'), ('12345', 'LOCAL'),
                         ('12345', 'PASSENGER'), ('12345', 'GOODS')]:
        assert not selected_route(route(number, name), AGENCIES)
    assert not selected_route({**route(), 'route_type': '3'}, AGENCIES)
    assert not selected_route(route(), {'1': {'agency_name': 'Other'}})


def test_categories_preserve_train_identity_and_do_not_imply_passenger_counts():
    for number, name, category in [('20101', 'SC VANDE BHARAT', 'Vande Bharat'),
                                    ('12213', 'YPR DEE DURONTO', 'Duronto'),
                                    ('15905', 'DBRG VIVEK EXP', 'Intercity / express')]:
        result = describe_route(route(number, name), {})
        assert result['category'] == category
        assert result['route_short_name'] == number and result['service_name'] == name
        assert result['line'] == category
        assert result['mode'] == 'train' and 'passengers' not in result


@pytest.mark.parametrize('enabled', [False, True])
def test_unpublished_pilot_requires_explicit_local_configuration(enabled):
    env = dict(os.environ)
    env.pop('SUNTRAIN_INDIA_REFERENCE', None)
    if enabled:
        env['SUNTRAIN_INDIA_REFERENCE'] = '/tmp/local-india-reference.json.gz'
    code = "from dashboard.cities import CITIES; print('india' in CITIES)"
    result = subprocess.run([sys.executable, '-c', code], env=env, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == str(enabled)

import gzip
import hashlib
import json
from collections import Counter

import pytest

from dashboard.flight_places import ROOT, INDEX, airport_bounds, build_index, catalogue


@pytest.fixture(scope='module')
def world():
    data = (ROOT / 'data/reference/world_flights/2026-11-02.json.gz').read_bytes()
    return json.loads(gzip.decompress(data)), hashlib.sha256(data).hexdigest()


def test_index_reproducible_and_bound_to_existing_snapshot(world):
    reference, source_hash = world
    result = build_index(reference, source_hash)
    assert result == catalogue()
    assert json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n' == INDEX.read_text()
    assert result['flights'] == 57250
    assert Counter(p['kind'] for p in result['places']) == {'country':213, 'airport':1577, 'region':8, 'experience':4}


def test_place_counts_use_both_endpoints_and_unique_flights(world):
    reference, _ = world
    airports = {a['code']:a for a in reference['airports']}
    index = {p['id']:p for p in catalogue()['places']}
    assert index['country:GB']['count'] == 4208
    assert index['country:SG']['count'] == 1067
    for key in ['country:GB', 'airport:LHR', 'region:europe', 'experience:gulf', 'experience:atlantic']:
        place = index[key]
        def touches(f):
            ends = [airports[f[k]] for k in ('origin','destination')]
            if place['kind'] == 'country': return any(a['country']==place['country'] for a in ends)
            if place['kind'] == 'airport': return any(a['code']==place['code'] for a in ends)
            if place.get('codes'): return any(a['code'] in place['codes'] for a in ends)
            if place.get('between'): return any(ends[i]['country'] in place['between'][0] and ends[1-i]['country'] in place['between'][1] for i in [0,1])
            return any(a['country'] in place['countries'] for a in ends)
        assert place['count'] == sum(touches(f) for f in reference['flights'])
    assert index['airport:MEL']['id'] != index['airport:AVV']['id']


def test_dateline_bounds_and_explicit_membership(world):
    bounds = airport_bounds([{'lon':178,'lat':-18}, {'lon':-175,'lat':-20}])
    assert bounds[1][0]-bounds[0][0] < 10
    reference, source_hash = world
    reference = {**reference, 'airports':[{**a, 'country':'ZZ'} for a in reference['airports']]}
    with pytest.raises(ValueError, match='Unreviewed browsing country'):
        build_index(reference, source_hash)

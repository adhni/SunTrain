import gzip
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dashboard import replay
from scripts.prepare_luxembourg_tram import selected_route


def test_luxtram_scope_geometry_and_unique_business_days():
    agencies={'111':{'agency_name':'Luxtram'}}
    route={'agency_id':'111','route_type':'0','route_short_name':'T1'}
    assert selected_route(route,agencies)
    assert not selected_route({**route,'route_type':'3'},agencies)
    assert not selected_route({**route,'agency_id':'11'},agencies)
    with gzip.open(replay.LUXEMBOURG_PATH,'rt') as f:r=json.load(f)
    patterns={k:p for k,p in r['patterns'].items() if p['mode']=='tram'}
    assert patterns and {p['operator'] for p in patterns.values()}=={'Luxtram'}
    names={r['stations'][s]['name'] for p in patterns.values() for s in r['stop_patterns'][p['stop_pattern']]['stations']}
    assert 'Findel - Luxembourg Airport' in names and 'Gasperich, Stadion' in names
    assert all(r['paths'][l]['quality']=='track' and len(r['paths'][l]['coordinates'])>=2
        for p in patterns.values() for l in r['stop_patterns'][p['stop_pattern']]['legs'])
    counts=[];occurrences=[]
    for day,rows in r['days'].items():
        rows=[row for row in rows if row[0] in patterns];counts.append(len(rows))
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Luxembourg')).timestamp()
        for p,t,o in rows:
            assert 10800<=o+patterns[p]['times'][1]<97200
            occurrences.append((t,midnight+o))
    assert counts==[514,514,514,514,514,339,238]
    assert len(occurrences)==len(set(occurrences))
    assert any(s['geometry_license']=='ODbL 1.0' for s in r['metadata']['additional_geometry_sources'])
    tram=replay.get_replay_day('2026-06-01','luxembourg',modes=['tram'])
    assert len(tram['services'])==514 and tram['approximate_legs']==0

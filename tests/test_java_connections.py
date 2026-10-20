from collections import Counter
import gzip
import hashlib
import json

from dashboard import replay
from scripts.prepare_java_connections import SOURCE,SOURCE_SHA256


def read(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def test_exact_published_service_numbers_and_conditional_exclusions():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    source=read(SOURCE)
    assert source['metadata']['effective_from']=='2025-02-01' and source['metadata']['extracted_tables']==132
    assert source['metadata']['omitted_trips']=={'547F':'Optional F service; activation dates unconfirmed',
        '548F':'Optional F service; activation dates unconfirmed'}
    trips=source['trips']
    assert len(trips)==130 and len({t['number'] for t in trips})==130
    assert Counter(t['name'] for t in trips)=={'Bandung–Padalarang Feeder':72,'YIA Airport Rail':48,'Adi Soemarmo Airport Rail':10}
    assert {t['number'] for t in trips}==({str(n) for n in range(521,581)}-{'547','548'})|{str(n) for n in range(601,673)}
    assert all(not t['untimed_calls'] and t['operator'] in {'KAI','KAI Bandara / Railink'} for t in trips)


def test_feeder_keeps_cimahi_dwell_and_conventional_station_calls():
    trips=[t for t in read(SOURCE)['trips'] if t['name']=='Bandung–Padalarang Feeder']
    assert Counter(t['origin'] for t in trips)=={'BD':36,'PDL':36}
    for t in trips:
        assert [c for c,a,d in t['calls']] in [['BD','CMI','PDL'],['PDL','CMI','BD']]
        assert t['calls'][1][2]-t['calls'][1][1]==120
        assert t['calls'][-1][1]-t['calls'][0][2]==1080
        assert t['operator']=='KAI'
    first=next(t for t in trips if t['number']=='601')
    assert first['calls']==[['BD',18960,18960],['CMI',19560,19680],['PDL',20040,20040]]


def test_yia_regular_and_nonstop_patterns_preserve_wrapped_airport_cells():
    trips=[t for t in read(SOURCE)['trips'] if t['name']=='YIA Airport Rail']
    assert Counter(len(t['calls']) for t in trips)=={2:24,3:24}
    assert Counter(t['origin'] for t in trips)=={'YK':24,'YIA':24}
    for trip in trips:
        assert {trip['calls'][0][0],trip['calls'][-1][0]}=={'YK','YIA'}
        assert 'KDG' in {c for c,t in trip['route']} and 'KDG' not in {c for c,a,d in trip['calls']}
        assert trip['stations']['YIA']=='Yogyakarta International Airport'
        assert trip['operator']=='KAI Bandara / Railink'
        if len(trip['calls'])==3:
            assert trip['calls'][1][0]=='WT' and trip['calls'][1][2]-trip['calls'][1][1]==120
        else:assert 'WT' not in {c for c,a,d in trip['calls']}
    first=next(t for t in trips if t['number']=='521')
    assert first['calls']==[['YK',15600,15600],['WT',17040,17160],['YIA',17940,17940]]


def test_adi_soemarmo_uses_february_madiun_scope_and_actual_stop_variations():
    trips=[t for t in read(SOURCE)['trips'] if t['name']=='Adi Soemarmo Airport Rail']
    assert Counter(t['origin'] for t in trips)=={'MN':5,'SMO':5}
    assert Counter(len(t['calls']) for t in trips)=={9:9,10:1}
    for t in trips:
        codes=[c for c,a,d in t['calls']]
        assert set(codes)>={'MN','SMO','SLO','KDO','SK','SR','WK','NGW','MAG'}
        assert 'PL' not in codes and 'CRB' not in codes
        assert {t['origin'],t['destination']}=={'MN','SMO'}
    extra=next(t for t in trips if t['number']=='577')
    assert next(c for c in extra['calls'] if c[0]=='GG')==['GG',30720,31800]


def test_added_services_have_tracks_and_original_identifiers_in_combined_replay():
    source=read(SOURCE);reference=read(replay.JAVA_PATH)
    lengths={}
    for t in source['trips']:
        pattern=reference['patterns']['java-'+t['number']]
        topology=reference['stop_patterns'][pattern['stop_pattern']]
        assert pattern['line']==t['name'] and pattern['operator']==t['operator'] and pattern['color']==t['color']
        assert len(topology['stations'])==len(t['calls'])
        paths=[reference['paths'][leg] for leg in topology['legs']]
        assert all(p['quality']=='track' and p['distances'][-1]>0 for p in paths)
        assert all(a['coordinates'][-1]==b['coordinates'][0] for a,b in zip(paths,paths[1:]))
        lengths[t['number']]=sum(p['distances'][-1] for p in paths)
    assert 10000<lengths['601']<25000
    assert 35000<lengths['521']<50000
    assert 90000<lengths['571']<140000
    day=replay.get_replay_day('2025-02-03','java')
    assert len(day['services'])==681 and len({s['id'] for s in day['services']})==681
    counts=Counter(day['transit_patterns'][s['pattern']]['line'] for s in day['services'])
    assert {name:counts[name] for name in ['Bandung–Padalarang Feeder','YIA Airport Rail','Adi Soemarmo Airport Rail']}=={
        'Bandung–Padalarang Feeder':72,'YIA Airport Rail':48,'Adi Soemarmo Airport Rail':10}
    assert day['schedule']['display_date_mapping']=={'2025-02-03':'2025-12-15'}
    assert len(replay.get_replay_day('2025-02-09','java')['services'])==669

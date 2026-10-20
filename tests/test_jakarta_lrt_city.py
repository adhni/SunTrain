from collections import Counter
import gzip
import hashlib
import json

import pytest
from dashboard import replay
from scripts.prepare_jakarta_lrt_city import SOURCE, SOURCE_SHA256, GEOMETRY, GEOMETRY_SHA256, PDF_SHA256, NAMES, parse_tables


def test_pdf_pass_throughs_and_dashes_do_not_become_passenger_calls():
    codes=list(NAMES)
    table=[['Loop','KA',*codes],['','',*['S']*11],
        ['1','1002','5:30','5:34','5:37','5:39','5:41','5:43','5:46','Ls.','Ls.','Ls.','5:57'],
        ['3','1116','19:45','19:49','19:52','19:54','19:56','-','-','-','-','-','-']]
    trips=parse_tables([table])
    assert len(trips[0]['calls'])==8 and trips[0]['calls'][-1]==['MGI',21420]
    assert len(trips[1]['calls'])==5 and trips[1]['calls'][-1]==['EQT',71760]
    assert not {'PKA','MAT','PKM'} & {c for c,t in trips[0]['calls']}
    bad=[row[:] for row in table];bad[2][3]='5:99'
    with pytest.raises(ValueError):parse_tables([bad])


def test_official_pdf_scope_original_numbers_and_full_terminal_times():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()==GEOMETRY_SHA256
    with gzip.open(SOURCE,'rt') as stream:r=json.load(stream)
    assert r['metadata']['sha256']==PDF_SHA256 and r['metadata']['valid_from']=='2026-09-19'
    assert len(r['trips'])==146 and len({t['number'] for t in r['trips']})==146
    assert Counter((t['direction'],len(t['calls'])) for t in r['trips'])=={
        ('south',8):57,('south',5):15,('north',8):59,('north',6):15}
    trips={t['number']:t for t in r['trips']}
    assert trips['1002']['calls'][0]==['KPG',19800]
    assert trips['1002']['calls'][-1]==['MGI',21420]
    assert trips['1003']['calls'][0]==['MGI',20400]
    assert trips['1003']['calls'][-1]==['KPG',22020]
    assert trips['1149']['calls'][0]==['VLD',81600]
    assert trips['1149']['calls'][-1]==['KPG',82380]


def test_replay_keeps_lrt_jakarta_separate_and_matches_native_tracks():
    with gzip.open(replay.JAKARTA_PATH,'rt') as stream:r=json.load(stream)
    patterns={k:p for k,p in r['patterns'].items() if p['operator']=='LRT Jakarta'}
    assert {p['line'] for p in patterns.values()}=={'LRT Jakarta South Line'}
    assert {p['color'] for p in patterns.values()}=={'#F26324'}
    names=set()
    for p in patterns.values():
        assert not p.get('terminal_arrival_missing') and p['mode']=='light_rail'
        stops=r['stop_patterns'][p['stop_pattern']]
        names.update(r['stations'][s]['name'] for s in stops['stations'])
        assert p['times'][::2]==p['times'][1::2]
        assert all(r['paths'][leg]['quality']=='track' and len(r['paths'][leg]['coordinates'])>=2 for leg in stops['legs'])
    assert len(names)==8 and {'Kelapa Gading','Manggarai','Rawamangun'}<=names
    assert not names & {'Pramuka','Matraman','Proklamasi'}
    for day,rows in r['days'].items():
        occurrences=[row for row in rows if row[0] in patterns]
        assert len(occurrences)==146 and len({(t,o) for p,t,o in occurrences})==146
    day=replay.get_replay_day('2025-12-15','jakarta',modes=('light_rail',))
    assert Counter(day['transit_patterns'][s['pattern']]['operator'] for s in day['services'])=={'LRT Jabodebek':430,'LRT Jakarta':146}
    assert r['metadata']['operator_periods']['LRT Jakarta']['valid_from']=='2026-09-19'

"""Exact Wizz group codes, shared captures, independent brands and source gaps."""
import json
import pytest
from dashboard import europe_flights as e
from scripts import prepare_europe_flights as g,prepare_ryanair_flights as r
from scripts.prepare_google_flights import parse_results
from tests.test_europe_flights import fixture,DAY,START
from tests.test_easyjet_expansion import merge_fixture
from tests.test_google_flights import segment,scripts


def test_candidate_inventory_preserves_exact_airports_and_source_limitations():
 cfg=g.config('wizzair');m=cfg['manifest'];air={a['code']:a for a in m['airports']}
 assert len(m['routes'])==2658 and len(cfg['queries'])==2658
 assert cfg['queries'][0][0]==DAY
 assert cfg['allowed_brands']==['wizzair'] and cfg['capture_context']==g.CONTEXT
 assert cfg['query_date_policy']=='local_departure_day_only'
 assert {q[0] for q in cfg['queries']}=={DAY}
 assert len(set(cfg['queries']))==len(m['routes'])
 assert air['OTP']['icao']!=air['BBU']['icao'] and air['LTN']['icao']!=air['LGW']['icao']
 assert air['EVN']['timezone']=='Asia/Yerevan' and air['DXB']['timezone']=='Asia/Dubai'
 assert air['SPX']['icao']=='HESX' and air['RMO']['timezone']=='Europe/Chisinau'
 assert m['wizzair_inventory']['source_type'].startswith('Secondary')
 assert 'challenge' in m['wizzair_inventory']['official_access']


def test_only_verified_group_codes_are_accepted():
 assert all(e.CARRIERS[c]=='wizzair' for c in ['W6','W4','W9','WZZ','WMT','WUK'])
 assert '5W' not in e.CARRIERS and 'WU' not in e.CARRIERS and 'VY' not in e.CARRIERS
 assert e.COLORS['wizzair'] not in {e.COLORS['ryanair'],e.COLORS['easyjet']}


def test_wizz_only_preparation_excludes_other_brands_and_frozen_starter_stays_frozen(tmp_path,monkeypatch):
 cfg,cache,out=fixture(tmp_path,monkeypatch);q=cache/f'{DAY}-LGW-BCN.json';row=json.loads(q.read_text());old=row['flights'][0]
 for c,n in [('W6','1'),('W4','2'),('W9','3')]:row['flights'].append({**old,'id':f'{DAY}:{c}{n}:LGW:BCN','number':c+n,'carrier':c,'airline':'Original source airline'})
 q.write_text(json.dumps(row));g.prepare(cache,out,cfg);assert not any(f['brand']=='wizzair' for f in r.read(out)['flights'])
 g.prepare(cache,out,{**cfg,'allowed_brands':['wizzair']});doc=r.read(out)
 assert {f['carrier'] for f in doc['flights']}=={'W6','W4','W9'}
 assert all(f['airline']=='Original source airline' and f['price']['currency']=='EUR' for f in doc['flights'])


def test_overnight_caucasus_flight_overlaps_utc_day():
 cfg=g.config('wizzair');raw=segment('LTN','EVN',[20,0],[5,0],300,carrier='W9',number='1');raw[20]=[2026,11,1];raw[21]=[2026,11,2]
 fs=parse_results(scripts(raw),'LTN','EVN','2026-11-01',cfg['zones'])
 assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']


def test_wizz_merge_preserves_existing_brands_and_deduplicates_shared_gaps(tmp_path):
 cache,out,m,seed,path,base,extra=merge_fixture(tmp_path);m['routes_by_brand'].update(easyjet=[['STN','DUB'],['DUB','STN']],wizzair=[['STN','DUB'],['DUB','STN']])
 wizz={**extra,'flights':[{**extra['flights'][0],'id':'wizz','brand':'wizzair','carrier':'W4','number':'W41'}]};wizz_path=tmp_path/'wizz.gz';r.save(wizz_path,wizz)
 r.prepare(cache,out,m,seed,path,wizz_path);doc=r.read(out);meta=doc['metadata']
 assert {f['brand'] for f in doc['flights']}=={'ryanair','easyjet','wizzair'} and len(doc['flights'])==4
 assert next(f for f in doc['flights'] if f['brand']=='ryanair')==base['flights'][0]
 assert meta['coverage_by_source']['google_wizzair']['reused_google_queries']==1
 assert meta['coverage_by_source']['google_unique']['planned']==2
 assert len([q for q in meta['uncollected_queries'] if q==[DAY,'DUB','STN']])==2,'One missing monthly request and one dated request, shared by both Google brands'
 assert meta['coverage']['source_counts']==dict(monthly_captured=1,monthly_planned=3,dated_captured=1,dated_planned=2)
 first=out.read_bytes();r.prepare(cache,out,m,seed,path,wizz_path);assert out.read_bytes()==first


def test_wizz_merge_rejects_competitor_even_when_name_matches(tmp_path):
 _,_,m,seed,_,base,extra=merge_fixture(tmp_path);extra['flights'][0].update(carrier='FR',airline='Wizz Air',brand='wizzair')
 with pytest.raises(ValueError):r.merge_google_brand(base,extra,m,'wizzair')


def test_prepared_wizz_has_complete_candidate_search_accounting():
 d=e.load_reference(DAY);meta=d['metadata'];stats=meta['coverage_by_source']['google_wizzair']
 assert stats['planned']==stats['captured']==2658 and stats['failed']==stats['unattempted']==0
 assert stats['query_date_policy']=='local_departure_day_only'
 assert not meta['uncollected_queries'] and not meta['failed_queries']
 assert len([f for f in d['flights'] if f['brand']=='ryanair'])==3476
 assert len([f for f in d['flights'] if f['brand']=='easyjet'])==1449
 fs=[f for f in d['flights'] if f['brand']=='wizzair'];assert fs and {'W6','W4','W9'}<={f['carrier'] for f in fs}
 assert len({f['id'] for f in d['flights']})==len(d['flights'])

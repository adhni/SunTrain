"""Shared single-day collection, long-haul safety, exact airports and group replay."""
import json
from copy import deepcopy
from datetime import datetime,timezone
import pytest
from dashboard import europe_flights as e,flights
from scripts import prepare_europe_groups as groups,prepare_europe_flights as g,prepare_ryanair_flights as r
from scripts.prepare_google_flights import parse_results
from tests.test_google_flights import segment,scripts
from tests.test_europe_flights import fixture,DAY,START,put


def test_one_day_deduplicated_candidates_and_exact_worldwide_airports():
 cfg=groups.config();m=cfg['manifest'];air={a['code']:a for a in m['airports']}
 assert len(m['routes'])==len(cfg['queries'])==3098
 assert sum(len(ps) for ps in m['routes_by_brand'].values())==3190
 assert {q[0] for q in cfg['queries']}=={DAY} and len(set(cfg['queries']))==3098
 assert set(m['routes_by_brand'])==set(e.FLAG_CARRIERS)
 assert all(air[a]['europe'] or air[b]['europe'] for a,b in m['routes'])
 assert air['LHR']['icao']!=air['LCY']['icao'] and air['JFK']['icao']!=air['EWR']['icao']
 assert air['CUN']['timezone']=='America/Cancun' and air['DEN']['timezone']=='America/Denver'
 assert air['SIN']['timezone']=='Asia/Singapore' and air['RUN']['timezone']=='Indian/Reunion'
 assert cfg['max_duration']==86400 and cfg['capture_context']!=g.CONTEXT
 assert all('Secondary' in s['kind'] for s in m['source_documents'].values())


def test_only_nine_main_carrier_codes_and_three_group_colours():
 assert {v[0] for v in e.FLAG_CARRIERS.values()}==set('LH LX OS SN BA IB EI AF KL'.split())
 assert len({e.COLORS[b] for b in e.FLAG_CARRIERS})==3
 assert all(e.CARRIERS[v[0]]==b and e.duration_limit(b)==86400 for b,v in e.FLAG_CARRIERS.items())
 assert all(c not in e.CARRIERS for c in ['EW','4Y','WK','AZ','VY','LL','HV','TO','SK','VS','XQ','A5','WA','EN'])
 assert e.duration_limit('ryanair')==e.duration_limit('wizzair')==28800


def test_long_haul_arrival_dates_and_source_duration_are_validated():
 cfg=groups.config();row=segment('FRA','SIN',[22,0],[17,25],745,carrier='LH',number='780');row[21]=[2026,11,3]
 fs=parse_results(scripts(row),'FRA','SIN',DAY,cfg['zones'],max_duration=86400)
 assert len(fs)==1 and fs[0]['arrival']-fs[0]['departure']==745*60
 with pytest.raises(ValueError):parse_results(scripts(row),'FRA','SIN',DAY,cfg['zones'])
 bad=deepcopy(row);bad[11]+=30
 with pytest.raises(ValueError,match='duration'):parse_results(scripts(bad),'FRA','SIN',DAY,cfg['zones'],max_duration=86400)
 row=segment('LHR','JFK',[12,0],[15,0],480,carrier='BA',number='117')
 f=parse_results(scripts(row),'LHR','JFK',DAY,cfg['zones'],max_duration=86400)[0]
 assert datetime.fromtimestamp(f['arrival'],timezone.utc).hour==20


@pytest.mark.parametrize('mutation',['none','currency','rejection','date','parser'])
def test_legacy_cache_reuse_requires_equivalent_valid_capture(tmp_path,mutation):
 new=tmp_path/'new';old=tmp_path/'old';new.mkdir();key=(DAY,'STN','DUB');put(old,key,[])
 p=old/f'{DAY}-STN-DUB.json';q=json.loads(p.read_text())
 if mutation=='currency':q['capture_context']['currency']='USD'
 if mutation=='rejection':q['rejected_flights']=[{'reason':'Invalid flight duration'}]
 if mutation=='date':q['date']='2026-11-01'
 if mutation=='parser':q['capture_context']['parser']='another-parser'
 p.write_text(json.dumps(q));cfg={**groups.config(),'legacy_cache':str(old)}
 assert g.capture_path(new,key,cfg)==(p if mutation=='none' else new/p.name)
 if mutation=='none':assert json.loads(p.read_text())['capture_context']==g.CONTEXT


def test_group_preparation_accepts_old_captures_preserves_missing_and_reproduces(tmp_path,monkeypatch):
 cfg,old,_=fixture(tmp_path,monkeypatch);key=(DAY,'STN','DUB');p=old/f'{DAY}-STN-DUB.json';q=json.loads(p.read_text());q['flights'][0].update(id='lh',carrier='LH',number='LH1');p.write_text(json.dumps(q));new=tmp_path/'new';new.mkdir();out=tmp_path/'groups.gz'
 cfg={**cfg,'capture_context':groups.CONTEXT,'reuse_contexts':[g.CONTEXT],'legacy_cache':str(old),'allowed_brands':list(e.FLAG_CARRIERS),'max_duration':86400,'query_date_policy':'local_departure_day_only','queries':[key,(DAY,'DUB','STN')],'manifest':{**cfg['manifest'],'routes':[['STN','DUB'],['DUB','STN']]}}
 g.prepare(new,out,cfg);doc=r.read(out);assert len(doc['flights'])==1 and doc['flights'][0]['brand']=='lufthansa'
 assert doc['metadata']['queries'][0]['capture_context']==g.CONTEXT
 assert doc['metadata']['uncollected_queries']==[[DAY,'DUB','STN']]
 first=out.read_bytes();g.prepare(new,out,cfg);assert out.read_bytes()==first
 monkeypatch.setenv('SUNTRAIN_EUROPE_FLIGHTS_REFERENCE',str(out));day=flights.replay_day(DAY,'europe_flights')
 assert day['flight_groups']==e.GROUPS and day['services'][0]['flight_group']=='lufthansa_group'
 assert day['services'][0]['carrier']=='LH'


def test_prepared_groups_have_complete_single_day_accounting_and_nine_brands():
 d=e.load_reference(DAY);meta=d['metadata'];stats=meta['coverage_by_source']['google_groups']
 assert stats['planned']==stats['captured']==3098 and stats['failed']==stats['unattempted']==0
 assert stats['query_date_policy']=='local_departure_day_only'
 assert set(f['brand'] for f in d['flights'])==set(e.BRANDS)
 assert any(f['arrival']-f['departure']>28800 for f in d['flights'])
 assert all(f['source_date']==DAY for f in d['flights'] if f['brand'] in e.FLAG_CARRIERS)
 assert not meta['uncollected_queries'] and not meta['failed_queries']
 assert len({f['id'] for f in d['flights']})==len(d['flights'])


def test_shared_group_merge_keeps_previous_flights_and_deduplicates_sources(tmp_path):
 from tests.test_easyjet_expansion import merge_fixture
 cache,out,m,seed,_,base,extra=merge_fixture(tmp_path)
 m['routes_by_brand'].update({b:[['STN','DUB'],['DUB','STN']] for b in e.FLAG_CARRIERS})
 f={**extra['flights'][0],'id':'LH1','brand':'lufthansa','carrier':'LH','number':'LH1'}
 f['arrival']=f['departure']+9*3600
 extra={**extra,'flights':[f],'metadata':{**extra['metadata'],'query_date_policy':'local_departure_day_only'}}
 path=tmp_path/'groups.gz';r.save(path,extra);r.prepare(cache,out,m,seed,groups_path=path);doc=r.read(out)
 assert next(x for x in doc['flights'] if x['brand']=='ryanair')==base['flights'][0]
 assert next(x for x in doc['flights'] if x['brand']=='lufthansa')==f
 stats=doc['metadata']['coverage_by_source']['google_groups']
 assert stats['planned']==2 and stats['captured']==1 and stats['reused_google_queries']==1
 assert doc['metadata']['coverage_by_brand']['lufthansa']['queries_captured']==1
 assert doc['metadata']['coverage_by_source']['google_unique']['planned']==2
 first=out.read_bytes();r.prepare(cache,out,m,seed,groups_path=path);assert out.read_bytes()==first
 with pytest.raises(ValueError):r.merge_google_brand(base,extra,m,'wizzair')

"""Published directional queues, compatible shared caches and preserved Europe cohorts."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import pytest
from dashboard import europe_flights as e,flights
from scripts import prepare_europe_networks as n,prepare_europe_flights as g,prepare_europe_groups as groups,prepare_ryanair_flights as r
from scripts.prepare_google_flights import parse_results
from tests.test_google_flights import segment,scripts
from tests.test_europe_flights import fixture,put,DAY

def test_published_pairs_single_date_exact_airports_and_nine_networks():
 cfg=n.config();m=cfg['manifest'];a={a['code']:a for a in m['airports']}
 assert set(m['routes_by_brand'])==set(e.OTHER_NETWORKS) and len(e.OTHER_NETWORKS)==9
 assert len(cfg['queries'])==len(set(cfg['queries']))==2578
 assert {q[0] for q in cfg['queries']}=={DAY} and cfg['currency']=='EUR'
 seed=json.loads(Path('data/sources/europe_networks_discovery.json').read_text())
 assert seed['carrier_sources']['OA']['error']=='HTTP 404' and seed['unresolved_airports']==['ALY']
 assert m['source_gaps'][0]['carrier']=='OA' and m['excluded_airports']==['ALY']
 assert all('ALY' not in p for p in m['routes']) and 'HBE' in a
 for brand,ps in m['routes_by_brand'].items():
  assert {tuple(p) for p in ps}=={tuple(p) for p in seed['routes_by_brand'][brand]}
  assert all([b,a] in ps for a,b in ps)
 assert a['ARN']['icao']=='ESSA' and a['FCO']['icao']=='LIRF'
 assert a['LHR']['icao']!=a['LGW']['icao']
 assert a['LIS']['timezone']=='Europe/Lisbon' and a['PDL']['timezone']=='Atlantic/Azores'
 assert a['KEF']['icao']!=a['RKV']['icao'] and a['JJU']['timezone']=='America/Nuuk'
 assert cfg['max_duration']==86400 and set(cfg['allowed_brands'])==set(e.OTHER_NETWORKS)
 assert set(q[1:] for q in cfg['queries'])==set(map(tuple,m['routes']))

def test_reviewed_network_codes_have_no_inferred_group_ownership():
 assert {c for _,codes,_ in e.OTHER_NETWORKS.values() for c in codes}==set('SK DY D8 AY LO TP A3 OA BT FI AZ'.split())
 assert e.CARRIERS['DY']==e.CARRIERS['D8']=='norwegian'
 assert e.CARRIERS['A3']==e.CARRIERS['OA']=='aegean'
 assert all(b not in e.BRAND_GROUPS for b in e.OTHER_NETWORKS)
 assert all(e.duration_limit(b)==86400 for b in e.OTHER_NETWORKS)
 assert all(c not in e.CARRIERS for c in ['EW','VY','HV','TO','VS','NI','XQ'])

@pytest.mark.parametrize('mutation',['valid','rejected','currency','parser','date','status'])
def test_reuse_searches_both_existing_caches_without_modification(tmp_path,mutation):
 first=tmp_path/'first';second=tmp_path/'second';new=tmp_path/'new';first.mkdir();key=(DAY,'STN','DUB');put(second,key,[])
 path=second/('-'.join(key)+'.json');q=json.loads(path.read_text())
 if mutation=='rejected':q['rejected_flights']=[{'reason':'duration'}]
 if mutation=='currency':q['capture_context']['currency']='USD'
 if mutation=='parser':q['capture_context']['parser']='unreviewed'
 if mutation=='date':q['date']='2026-11-03'
 if mutation=='status':q['status']='error'
 path.write_text(json.dumps(q));before=path.read_bytes()
 cfg={**n.config(),'reuse_caches':[str(first),str(second)]}
 assert g.capture_path(new,key,cfg)==(path if mutation=='valid' else new/path.name)
 assert path.read_bytes()==before

def test_long_haul_local_arrival_dates_and_duration_validation():
 cfg=n.config();row=segment('HEL','NRT',[17,0],[12,0],720,carrier='AY',number='73');row[21]=[2026,11,3]
 f=parse_results(scripts(row,row),'HEL','NRT',DAY,cfg['zones'],max_duration=86400)
 assert len(f)==1 and f[0]['arrival']-f[0]['departure']==43200
 row[11]+=60
 with pytest.raises(ValueError,match='duration'):parse_results(scripts(row),'HEL','NRT',DAY,cfg['zones'],max_duration=86400)

def test_extra_preparation_preserves_provenance_and_missing_queries(tmp_path,monkeypatch):
 cfg,old,_=fixture(tmp_path,monkeypatch);key=(DAY,'STN','DUB');path=old/('-'.join(key)+'.json');q=json.loads(path.read_text());q['flights'][0].update(id='SK1',carrier='SK',number='SK1');path.write_text(json.dumps(q));before=path.read_bytes()
 cfg={**cfg,'capture_context':groups.CONTEXT,'reuse_contexts':[g.CONTEXT,groups.CONTEXT],'reuse_caches':[str(tmp_path/'missing'),str(old)],'allowed_brands':list(e.OTHER_NETWORKS),'max_duration':86400,'queries':[key,(DAY,'DUB','STN')],'query_date_policy':'local_departure_day_only','manifest':{**cfg['manifest'],'routes':[['STN','DUB'],['DUB','STN']]}}
 new=tmp_path/'new';out=tmp_path/'extra.gz';g.prepare(new,out,cfg);doc=r.read(out)
 assert doc['flights'][0]['brand']=='sas' and doc['metadata']['queries'][0]['capture_context']==g.CONTEXT
 assert doc['metadata']['uncollected_queries']==[[DAY,'DUB','STN']] and path.read_bytes()==before
 original=out.read_bytes();g.prepare(new,out,cfg);assert out.read_bytes()==original

def test_shared_merge_preserves_old_flights_and_counts_unique_queries(tmp_path):
 from tests.test_easyjet_expansion import merge_fixture
 cache,out,m,seed,_,base,extra=merge_fixture(tmp_path)
 m['routes_by_brand'].update({b:[['STN','DUB'],['DUB','STN']] for b in e.OTHER_NETWORKS})
 f={**extra['flights'][0],'id':'SK1','brand':'sas','carrier':'SK','number':'SK1'}
 extra={**extra,'flights':[f],'metadata':{**extra['metadata'],'query_date_policy':'local_departure_day_only'}}
 path=tmp_path/'networks.gz';r.save(path,extra);r.prepare(cache,out,m,seed,networks_path=path);doc=r.read(out)
 assert next(x for x in doc['flights'] if x['brand']=='ryanair')==base['flights'][0]
 assert next(x for x in doc['flights'] if x['brand']=='sas')==f
 assert doc['metadata']['coverage_by_source']['google_networks']['reused_google_queries']==1
 assert doc['metadata']['coverage_by_source']['google_unique']['planned']==2
 assert doc['metadata']['coverage_by_brand']['sas']['queries_captured']==1
 before=out.read_bytes();r.prepare(cache,out,m,seed,networks_path=path);assert out.read_bytes()==before

def test_completed_networks_reference_and_existing_cohorts():
 d=e.load_reference(DAY);m=d['metadata'];fs=d['flights'];stats=m['coverage_by_source']['google_networks']
 assert stats['planned']==stats['captured']==2578 and stats['query_date_policy']=='local_departure_day_only'
 assert stats['failed']==stats['unattempted']==0 and not m['uncollected_queries'] and not m['failed_queries']
 assert all(f['source_date']==DAY for f in fs if f['brand'] in e.OTHER_NETWORKS)
 assert set(f['brand'] for f in fs)==set(e.BRANDS) and len(fs)==len({f['id'] for f in fs})
 assert len([f for f in fs if f['brand'] not in e.OTHER_NETWORKS])==10392
 # Frozen previous brand records are reproducible from their original inputs.
 assert m['coverage_by_source']['google_groups']['captured']==3098
 assert m['network_discovery_gaps'][0]['carrier']=='OA' and m['network_excluded_airports']==['ALY']

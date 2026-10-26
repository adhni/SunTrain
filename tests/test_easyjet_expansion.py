"""Full easyJet discovery, cache reuse, brand isolation and merged coverage."""
import json
import pytest
from scripts import prepare_europe_flights as g,prepare_ryanair_flights as r
from tests.test_europe_flights import fixture,DAY
from tests.test_ryanair_timetables import preparation_fixture


def test_full_easyjet_queries_keep_context_and_adjacent_dates():
 cfg=g.config('easyjet');assert len(cfg['manifest']['routes'])==2564 and len(cfg['queries'])==6694
 assert cfg['allowed_brands']==['easyjet'] and cfg['capture_context']==g.CONTEXT
 assert (DAY,'LGW','SID') in cfg['queries']
 assert ('2026-11-01','GVA','NCE') in cfg['queries'] and ('2026-11-03','GVA','NCE') in cfg['queries']
 assert cfg['zones']['SID']=='Atlantic/Cape_Verde'
 assert cfg['zones']['BSL']=='Europe/Paris' and cfg['zones']['GVA']=='Europe/Zurich'


def test_easyjet_preparation_excludes_ryanair_and_other_airlines(tmp_path,monkeypatch):
 cfg,cache,out=fixture(tmp_path,monkeypatch);cfg={**cfg,'allowed_brands':['easyjet']}
 g.prepare(cache,out,cfg);doc=r.read(out)
 assert {f['carrier'] for f in doc['flights']}=={'U2','DS'}
 assert doc['metadata']['coverage_by_brand']['ryanair']['flights']==0
 q=cache/f'{DAY}-LGW-BCN.json';value=json.loads(q.read_text());value['flights'][0]['price']['currency']='USD';q.write_text(json.dumps(value))
 with pytest.raises(ValueError,match='quote'):g.prepare(cache,out,cfg)


def merge_fixture(tmp_path):
 cache,out,m,seed,easy=preparation_fixture(tmp_path);base=r.read(seed)
 # The fixture uses minimal airports; source membership remains explicit.
 for a in m['airports']:a['europe']=True
 old_query=dict(date=DAY,origin='STN',destination='DUB',page_sha256='shared',capture_context=g.CONTEXT)
 base['metadata']['queries']=[old_query];r.save(seed,base)
 extra=dict(airports=m['airports'],flights=[{**easy,'id':'easyjet-new','number':'U22','price':{**easy['price'],'amount_minor':999}}],metadata={**base['metadata'],'queries':[old_query], 'uncollected_queries':[[DAY,'DUB','STN']],'failed_queries':[], 'capture_context':g.CONTEXT,'coverage':dict(queries_planned=2)})
 path=tmp_path/'easyjet.gz';r.save(path,extra)
 return cache,out,m,seed,path,base,extra


def test_merge_preserves_ryanair_deduplicates_queries_and_accounts_for_gaps(tmp_path):
 cache,out,m,seed,path,base,extra=merge_fixture(tmp_path);m['routes_by_brand']['easyjet']=[['STN','DUB'],['DUB','STN']]
 r.prepare(cache,out,m,seed,path);doc=r.read(out);meta=doc['metadata']
 assert next(f for f in doc['flights'] if f['brand']=='ryanair')==base['flights'][0]
 assert len(doc['flights'])==3
 assert len([q for q in meta['queries'] if q.get('source')!='ryanair_public_timetable'])==1
 assert meta['coverage_by_source']['google_easyjet']['reused_starter_queries']==1
 assert meta['coverage_by_source']['google_unique']==dict(request_unit='airport_pair_date',planned=2,captured=1)
 assert meta['coverage']['source_counts']==dict(monthly_captured=1,monthly_planned=3,dated_captured=1,dated_planned=2)
 assert meta['coverage']['failed_or_missing_queries']==3
 first=out.read_bytes();r.prepare(cache,out,m,seed,path);assert out.read_bytes()==first


def test_merge_selects_cheapest_only_for_identical_flight_and_schedule(tmp_path):
 _,_,m,seed,_,base,extra=merge_fixture(tmp_path);old=next(f for f in base['flights'] if f['brand']=='easyjet')
 extra['flights']=[{**old,'price':{**old['price'],'amount_minor':999}}]
 merged=r.merge_easyjet(base,extra,m);assert next(f for f in merged['flights'] if f['id']==old['id'])['price']['amount_minor']==999
 extra['flights'][0]['price']['amount_minor']=9999
 merged=r.merge_easyjet(base,extra,m);assert next(f for f in merged['flights'] if f['id']==old['id'])['price']==old['price']
 extra['flights'][0]['departure']+=60;extra['flights'][0].pop('price')
 merged=r.merge_easyjet(base,extra,m);assert 'price' not in next(f for f in merged['flights'] if f['id']==old['id'])
 assert merged['metadata']['easyjet_schedule_updates']


@pytest.mark.parametrize('mutation',['brand','context','query','scope','currency','duplicate'])
def test_merge_rejects_incompatible_sources(tmp_path,mutation):
 _,_,m,seed,_,base,extra=merge_fixture(tmp_path)
 if mutation=='brand':extra['flights'][0]['carrier']='FR'
 if mutation=='context':extra['metadata']['timezone']='Europe/London'
 if mutation=='query':extra['metadata']['queries']=[{**extra['metadata']['queries'][0],'page_sha256':'different'}]
 if mutation=='scope':extra['flights'][0]['flight_scope']='domestic'
 if mutation=='currency':extra['flights'][0]['price']['currency']='bad'
 if mutation=='duplicate':extra['flights'].append({**extra['flights'][0],'departure':extra['flights'][0]['departure']+60})
 with pytest.raises(ValueError):r.merge_easyjet(base,extra,m)


def test_prepared_full_easyjet_has_complete_search_accounting_and_preserves_ryanair():
 from dashboard.europe_flights import load_reference
 doc=load_reference(DAY);meta=doc['metadata'];stats=meta['coverage_by_source']['google_easyjet']
 assert stats['planned']==stats['captured']==6694
 assert stats['failed']==stats['unattempted']==0
 assert not meta['uncollected_queries'] and not meta['failed_queries']
 google=[q for q in meta['queries'] if q.get('source')!='ryanair_public_timetable']
 from scripts.prepare_europe_groups import config as groups_config,CONTEXT as groups_context
 expected=set(groups_config()['queries'])|set(g.config()['queries'])|set(g.config('easyjet')['queries'])|set(g.config('wizzair')['queries'])
 assert len(google)==len(expected)==len({(q['date'],q['origin'],q['destination']) for q in google})
 assert all(q['capture_context'] in [g.CONTEXT,groups_context] for q in google)
 ryanair=[f for f in doc['flights'] if f['brand']=='ryanair']
 assert len(ryanair)==3476 and all(f['schedule_source']=='ryanair_public_timetable' for f in ryanair)
 assert meta['coverage_by_brand']['easyjet']['flights']>180
 assert all(f['price']['currency']=='EUR' for f in doc['flights'] if f.get('price'))

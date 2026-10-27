"""Frozen expansion scope, preservation of source records and audited empty refreshes."""
import gzip,hashlib,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from scripts.expand_africa_routes import STARTER,STARTER_HASH
from scripts.prepare_africa_routes import AFRICAN,DAY
from scripts.prepare_africa_flights import seed,validate_query
from scripts.prepare_google_flights import country_config,expected_queries
from tests.test_africa_flights import query

def test_expansion_is_exactly_frozen_deferred_pairs_with_no_worldwide_sweep():
 base=json.loads(gzip.decompress(STARTER.read_bytes()));cfg=country_config('AFRICA');m=cfg['manifest'];a={a['code']:a for a in m['airports']}
 assert hashlib.sha256(STARTER.read_bytes()).hexdigest()==STARTER_HASH
 expanded=set(map(tuple,m['expanded_routes']));reviewed={(r['origin'],r['destination']) for r in base['deferred_routes']}
 assert expanded==reviewed and len(expanded)==658 and not m['expansion_exclusions']
 assert set(map(tuple,m['new_collection_routes']))==set(map(tuple,base['new_collection_routes']))|expanded
 assert len(m['routes'])==2749 and len(m['routes'])==len(set(map(tuple,m['routes'])))
 assert {q[0] for q in expected_queries(DAY,m['routes'],cfg)}=={DAY}
 assert sum(a[x]['country']==a[y]['country'] for x,y in expanded)==320
 assert all(a[x]['country'] in AFRICAN and a[y]['country'] in AFRICAN and set((x,y))&set(base['launch_airports']) for x,y in expanded)
 for old in base['airports']:assert a[old['code']]==old
 assert a['JNB']['icao']!=a['HLA']['icao']
 assert a['FIH']['timezone']=='Africa/Kinshasa' and a['FBM']['timezone']=='Africa/Lubumbashi'
 assert m['resolved_starter_airports']==['HMB','KRT','MRA']
 assert not set(m['resolved_starter_airports'])&{r['code'] for r in m['unresolved_airports']}
 assert m['archive_snapshot']['sha256']==hashlib.sha256(Path(m['archive_snapshot']['path']).read_bytes()).hexdigest()

@pytest.mark.parametrize('existing_flights',[False,True])
def test_reviewed_refresh_recovers_positive_query_and_keeps_original_provenance(tmp_path,monkeypatch,existing_flights):
 from scripts import prepare_africa_flights as collector
 monkeypatch.setattr(collector,'ROOT',tmp_path);source=tmp_path/'.cache/google-flights-external';source.mkdir(parents=True);cache=tmp_path/'target';cache.mkdir()
 q=query('EUR');q['captured_at']='2026-10-28T00:00:00Z';p=source/f'{DAY}-JNB-CPT.json';p.write_text(json.dumps(q));original=p.read_bytes()
 old=query('USD')
 if not existing_flights:old.update(flights=[],status='no_matching_direct_flights')
 target=cache/p.name;target.write_text(json.dumps(old));before=target.read_bytes();cfg={**country_config('AFRICA'),'refresh_empty_queries':[['JNB','CPT']]}
 report=seed(cache,cfg)
 if existing_flights:assert report['seeded']==0 and target.read_bytes()==before
 else:
  assert report['seeded']==1
  result=json.loads(target.read_text());assert result['previous_empty_capture']==old and result['flights']==q['flights']
  assert result['reused_capture_sha256']==hashlib.sha256(original).hexdigest()
  validate_query(result,(DAY,'JNB','CPT'),cfg)
 assert p.read_bytes()==original and seed(cache,cfg)['seeded']==0

def test_original_source_records_and_offline_recovery():
    from dashboard.flights import reference_path
    frozen=json.loads(gzip.decompress(STARTER.read_bytes()));new=json.loads(gzip.decompress(reference_path(DAY,'africa_flights').read_bytes()));index={f['id']:f for f in new['flights']}
    for key,count in [('starter_record_audit',2468),('offline_recovery_audit',96)]:
        audit=frozen[key];rows=[index[key] for key in audit['ids']]
        assert len(rows)==audit['count']==count
        assert hashlib.sha256(json.dumps(sorted(rows,key=lambda f:f['id']),sort_keys=True,separators=(',',':')).encode()).hexdigest()==audit['sha256']

def test_resuming_collection_cannot_overwrite_recovered_query_with_old_empty_capture(tmp_path):
 from scripts.prepare_africa_flights import publish_captures
 fresh=tmp_path/'fresh';cache=tmp_path/'cache';fresh.mkdir();cache.mkdir()
 old_name=f'{DAY}-JNB-CPT.json';new_name=f'{DAY}-JNB-PLZ.json';error_name=f'{DAY}-JNB-HLA.error.json'
 recovered=json.dumps(query('EUR'));(cache/old_name).write_text(recovered)
 (fresh/old_name).write_text(json.dumps({**query(),'flights':[],'status':'no_matching_direct_flights'}))
 (fresh/new_name).write_text('new capture');(fresh/error_name).write_text('failure diagnostic')
 publish_captures(fresh,cache,[('JNB','PLZ'),('JNB','HLA')])
 assert (cache/old_name).read_text()==recovered
 assert (cache/new_name).read_text()=='new capture' and (cache/error_name).read_text()=='failure diagnostic'

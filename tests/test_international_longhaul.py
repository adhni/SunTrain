"""Exact-route long-haul selection, one official recheck and independent budgets."""
from collections import Counter
from copy import deepcopy

import pytest

from dashboard import world_flights as world,south_america_domestic as domestic
from scripts import prepare_international_longhaul as campaign
from scripts.discover_international_expansion import digest,read,save
from tests.international_history import current_checkpoint,expected_world_metrics


def test_manifest_has_200_queries_with_balanced_50_query_reviews_and_frozen_parents():
    m=read(campaign.SOURCE);campaign.check_campaign(m)
    assert m['baseline_counts']['flights']==57024
    assert m['baseline_counts']['international_overlapping']==28333
    assert len(m['baseline_inputs'])==46
    assert m['candidate_pool_counts']==dict(north_america_east_asia=80,europe_east_asia=97,utc_boundary=216,official_recheck=1)
    assert Counter(q[0] for q in m['new_searches'])=={'2026-11-01':50,'2026-11-02':150}
    assert len({tuple(q) for q in m['new_searches']})==200
    assert all(r['missing_direction'] for r in m['candidates'] if r['stream']=='utc_boundary')
    assert [r['query'] for r in m['candidates'] if r['stream']=='official_recheck']==[list(campaign.RECHECK)]
    assert [p['attempts'] for p in m['parent_campaigns']]==[1000,300,100]
    assert ('2026-11-01','YYZ','LHR') in set(map(tuple,m['new_searches']))


@pytest.mark.parametrize('bad',['cap','duplicate','allocation','parent','parent_count','official','adjacent_day','proof','corridor','repeat'])
def test_reject_changed_caps_evidence_unproved_dates_and_prior_attempts(bad):
    m=deepcopy(read(campaign.SOURCE))
    row=next(r for r in m['candidates'] if r['stream']=='utc_boundary')
    if bad=='cap':m['search_limit']=201
    elif bad=='duplicate':m['new_searches'][1]=m['new_searches'][0]
    elif bad=='allocation':m['workstream_limits']['official_recheck']=2
    elif bad=='parent':m['parent_campaigns'][0]['sha256']='changed'
    elif bad=='parent_count':m['parent_campaigns'][0]['attempts']=1001
    elif bad=='official':next(r for r in m['candidates'] if r['stream']=='official_recheck')['evidence'][0]['sha256']='wrong'
    elif bad=='adjacent_day':
        i=m['candidates'].index(row);row['query'][0]='2026-11-03';m['new_searches'][i]=row['query']
    elif bad=='proof':row['timing_evidence'][0]['candidate_departure']+=60
    elif bad=='corridor':
        row=next(r for r in m['candidates'] if r['stream']=='north_america_east_asia')
        m['airports'][next(i for i,a in enumerate(m['airports']) if a['code']==row['query'][1])]['country']='BR'
    else:
        q=read(campaign.FIRST)['collection']['attempts'][0]['query'];m['new_searches'][0]=q;m['candidates'][0]['query']=q
    with pytest.raises(ValueError):campaign.check_campaign(m)


def test_official_recheck_bypasses_only_cached_query_and_each_attempt_is_charged_once(tmp_path,monkeypatch):
    m=deepcopy(read(campaign.SOURCE));m['collection']=dict(attempts=[])
    source=tmp_path/'source.gz';cache=tmp_path/'audit';captures=tmp_path/'captures'
    for filename,field in [('baseline.json.gz','baseline_world_sha256'),('supplement-before.json.gz','baseline_supplement_sha256')]:
        save(cache/filename,dict(flights=[]));m[field]=digest((cache/filename).read_bytes())
    save(source,m)
    save(cache/'cache-index.json.gz',dict(queries=[dict(query=list(campaign.RECHECK))]))
    monkeypatch.setattr(campaign.runner,'ORIGINAL_CACHE',cache)
    seen=[];reviews=[]
    async def capture(*args):
        cfg=args[4];assert args[3]==2 and cfg['currency']=='USD' and cfg['max_duration']==86400
        for key in cfg['queries']:cfg['on_query_start'](key);seen.append(key)
    def publish(cache,source,captures,validate):
        m=read(source);attempts=read(captures/'attempts.json')['attempts']
        reviews.append(len(attempts));m['collection']=dict(attempts=attempts);save(source,m)
    monkeypatch.setattr(campaign.runner,'capture',capture);monkeypatch.setattr(campaign.runner,'publish_checkpoint',publish)
    for expected in [50,100,150,200,200]:
        assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,50)==0
        assert len(seen)==expected
    assert reviews==[50,100,150,200] and seen.count(campaign.RECHECK)==1
    (captures/'attempts.json').unlink()
    assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,50)==0
    assert len(read(captures/'attempts.json')['attempts'])==200 and len(set(seen))==200


def test_published_scorecard_matches_world_without_double_counting_domestic_expansion():
    m=read(campaign.SOURCE)
    if not m['collection'].get('after'):return
    current=current_checkpoint(campaign.SOURCE)
    snapshot=world.load_reference(world.DAY)
    assert campaign.runner.preparation.metrics(snapshot)==expected_world_metrics(current)
    assert any(f['origin']=='HND' and f['destination']=='LHR' and f['number']=='NH211'
        for f in snapshot['flights'])
    assert snapshot['metadata']['scopes']['domestic']==27898+domestic.load_reference()['metadata']['coverage']['new_world_identities']==28691
    assert m['collection']['searches_attempted']<=200 and m['collection']['identities_removed']==0
    for p,info in m['baseline_inputs'].items():
        if p!=campaign.relative(campaign.adapter.reference_path()):assert digest((campaign.ROOT/p).read_bytes())==info['sha256']

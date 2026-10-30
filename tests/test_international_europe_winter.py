"""Winter evidence gates, finite targeted collection and descendant compatibility."""
from collections import Counter
from copy import deepcopy

import pytest

from dashboard import world_flights as world
from scripts import prepare_international_europe_winter as campaign
from scripts.discover_international_expansion import read, save, digest
from tests.international_history import current_checkpoint, expected_world_metrics


def test_only_missing_european_directions_with_monday_winter_evidence():
    m=read(campaign.SOURCE);campaign.check_campaign(m)
    assert m['baseline_counts']['flights']==57227
    assert m['baseline_counts']['international_overlapping']==28536
    assert len(m['baseline_inputs'])==46
    assert len(m['new_searches'])==25 < m['search_limit']==100
    assert Counter(q[0] for q in m['new_searches'])=={'2026-11-02':25}
    assert m['selection_skips']==dict(already_captured=10,previously_attempted=1,wrong_day_or_season=7)
    assert m['verified_recheck_queries']==[['2026-11-02','NCE','LCY'],['2026-11-02','LCY','NCE']]
    assert [p['attempts'] for p in m['parent_campaigns']]==[1000,300,100,200]
    assert not set(map(tuple,m['new_searches'])) & campaign.previous_attempts()
    assert sum(r['direction_evidence']=='reverse_route_candidate' for r in m['candidates'])==9


def test_do_not_search_later_starts_expired_routes_or_wrong_weekdays():
    rows=campaign.reviewed_routes()
    eligible={tuple(r['published_direction']) for r in rows if campaign.operates(r)}
    assert ('NCE','FLR') in eligible and ('SXB','CPH') in eligible
    assert not {('NCE','LPL'),('NCE','AGP'),('BOD','NAP'),('BOD','FLR'),
        ('TLS','NAP'),('TLS','PSA'),('SXB','FLR')} & eligible
    florence=next(r for r in rows if r['published_direction']==['SXB','FLR'])
    assert not campaign.operates(florence,'2026-11-02')
    assert campaign.operates(florence,'2026-11-06')
    assert not campaign.operates(florence,'2026-11-07')


def test_reuse_captures_and_do_not_invent_new_pairs(monkeypatch):
    proof=next(r for r in campaign.reviewed_routes() if r['published_direction']==['NCE','FLR'])
    monkeypatch.setattr(campaign,'reviewed_routes',lambda:[proof])
    monkeypatch.setattr(campaign,'previous_attempts',lambda:set())
    baseline=dict(flights=[])
    index=dict(queries=[dict(query=['2026-11-02','NCE','FLR'],latest=dict(flights=1))])
    rows,skipped=campaign.select_candidates(baseline,index)
    assert [r['query'] for r in rows]==[['2026-11-02','FLR','NCE']]
    assert rows[0]['direction_evidence']=='reverse_route_candidate'
    assert skipped=={'compatible_positive_cache':1}
    baseline['flights']=[dict(origin='FLR',destination='NCE')]
    assert campaign.select_candidates(baseline,index)[0]==[]


@pytest.mark.parametrize('bad',['cap','checkpoint','currency','duplicate','proof','weekday','date','direction','country','parent','repeat','allowlist'])
def test_reject_scope_budget_or_evidence_changes(bad):
    m=deepcopy(read(campaign.SOURCE));row=m['candidates'][0]
    if bad=='cap':m['search_limit']=101
    elif bad=='checkpoint':m['checkpoint_size']=100
    elif bad=='currency':m['currency']='EUR'
    elif bad=='duplicate':m['new_searches'][1]=m['new_searches'][0]
    elif bad=='proof':row['evidence'][0]['sha256']='unreviewed'
    elif bad=='weekday':row['evidence'][0]['weekdays']=[2]
    elif bad=='date':row['query'][0]='2026-11-03';m['new_searches'][0]=row['query']
    elif bad=='direction':row['direction_evidence']='daily_return_proved'
    elif bad=='country':next(a for a in m['airports'] if a['code']==row['query'][1])['country']='US'
    elif bad=='parent':m['parent_campaigns'][-1]['sha256']='changed'
    elif bad=='repeat':
        q=read(campaign.PARENTS[0])['collection']['attempts'][0]['query']
        m['new_searches'][0]=q;row['query']=q
    else:m['verified_recheck_queries'].append(row['query'])
    with pytest.raises(ValueError):campaign.check_campaign(m)


def test_finite_evidence_queue_does_not_spend_the_unused_budget(tmp_path,monkeypatch):
    m=deepcopy(read(campaign.SOURCE));m['collection']=dict(attempts=[])
    source=tmp_path/'source.gz';cache=tmp_path/'audit';captures=tmp_path/'captures'
    for filename,field in [('baseline.json.gz','baseline_world_sha256'),('supplement-before.json.gz','baseline_supplement_sha256')]:
        save(cache/filename,dict(flights=[]));m[field]=digest((cache/filename).read_bytes())
    save(source,m)
    save(cache/'cache-index.json.gz',dict(queries=[dict(query=q) for q in m['verified_recheck_queries']]))
    monkeypatch.setattr(campaign.runner,'ORIGINAL_CACHE',cache)
    seen=[];reviews=[]
    async def capture(*args):
        cfg=args[4];assert args[3]==2 and cfg['currency']=='USD' and cfg['max_duration']==86400
        assert all(q[0]=='2026-11-02' for q in cfg['queries'])
        for key in cfg['queries']:cfg['on_query_start'](key);seen.append(key)
    def publish(cache,source,captures,validate):
        m=read(source);validate(m);attempts=read(captures/'attempts.json')['attempts']
        reviews.append(len(attempts));m['collection']=dict(attempts=attempts);save(source,m)
    monkeypatch.setattr(campaign.runner,'capture',capture)
    monkeypatch.setattr(campaign.runner,'publish_checkpoint',publish)
    for _ in range(3):assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,25)==0
    assert reviews==[25] and len(seen)==len(set(seen))==25
    (captures/'attempts.json').unlink()
    assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,25)==0
    assert len(seen)==25 and len(read(captures/'attempts.json')['attempts'])==25


def test_published_world_and_historical_campaigns_remain_consistent():
    m=read(campaign.SOURCE)
    if not m['collection'].get('after'):return
    current=current_checkpoint(campaign.SOURCE)
    snapshot=world.load_reference(world.DAY)
    assert campaign.runner.preparation.metrics(snapshot)==expected_world_metrics(current)
    assert snapshot['metadata']['scopes']['domestic']==28691
    assert m['collection']['identities_removed']==0
    assert m['collection']['searches_attempted']==len(m['new_searches'])==25
    assert not any(m['collection'][k] for k in ('failed_queries','interrupted_queries','rejected_queries'))

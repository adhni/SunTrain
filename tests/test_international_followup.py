"""Follow-up selection, independent accounting and offline provenance."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import prepare_international_followup as followup
from scripts.discover_international_expansion import digest, read, save


def row(a,b,stream='europe_airlines',day=followup.DAY):
    return dict(query=[day,a,b],stream=stream,evidence=[dict(kind='airline',code='VY')])


def test_rank_dated_missing_directions_ahead_of_seasonal_maps_and_existing_routes():
    rows=[row('AAA','BBB'),row('CCC','DDD'),row('EEE','FFF'),row('GGG','HHH')]
    parent=dict(remaining_queue=[r['query'] for r in rows],ledger=rows,collection=dict(attempts=[]))
    baseline=dict(flights=[dict(origin='BBB',destination='AAA',provenance=dict(source_dates=[followup.DAY])),
        dict(origin='EEE',destination='FFF',provenance=dict(source_dates=[followup.DAY])),
        dict(origin='HHH',destination='GGG',provenance=dict(source_dates=['2026-11-01']))])
    ranked=followup.ranked_candidates(parent,baseline,dict(queries=[]))['europe_airlines']
    assert [r['query'][1:] for r in ranked]==[['AAA','BBB'],['EEE','FFF'],['CCC','DDD'],['GGG','HHH']]
    assert ranked[0]['dated_reverse_flights']==1 and ranked[0]['missing_direction']
    assert not ranked[1]['missing_direction']
    assert ranked[-1]['dated_reverse_flights']==0


def test_never_repeat_cached_failed_or_interrupted_attempts_or_add_adjacent_days():
    rows=[row('AAA','BBB'),row('CCC','DDD'),row('EEE','FFF'),row('GGG','HHH',day='2026-11-01')]
    parent=dict(remaining_queue=[r['query'] for r in rows],ledger=rows,
        collection=dict(attempts=[dict(query=rows[0]['query'])]))
    ranked=followup.ranked_candidates(parent,dict(flights=[]),dict(queries=[dict(query=rows[1]['query'])]))
    assert [r['query'] for r in ranked['europe_airlines']]==[rows[2]['query']]


def test_real_manifest_has_fixed_budget_evidence_and_balanced_checkpoints():
    manifest=read(followup.SOURCE)
    followup.check_parent(manifest)
    assert len(manifest['new_searches'])==300
    assert len({tuple(q) for q in manifest['new_searches']})==300
    for i,expected in enumerate([(50,33,17),(50,34,16),(50,33,17)]):
        batch=manifest['candidates'][100*i:100*(i+1)]
        assert Counter(r['stream'] for r in batch)==dict(zip(followup.LIMITS,expected))
        assert all(r['query'][0]==followup.DAY and r['evidence'] for r in batch)
    assert sum(bool(r['dated_reverse_flights'] or r['dated_same_direction_flights'])
        for r in manifest['candidates'])==279
    assert manifest['baseline_counts']['flights']==55599
    assert len(read(followup.ORIGINAL_SOURCE)['collection']['attempts'])==1000


@pytest.mark.parametrize('change', ['cap','allocation','duplicate','parent','repeat'])
def test_reject_changed_budget_evidence_parent_and_repeated_first_pass(change):
    manifest=deepcopy(read(followup.SOURCE))
    if change=='cap': manifest['search_limit']=301
    elif change=='allocation': manifest['workstream_limits']['europe_airlines']=151
    elif change=='duplicate': manifest['new_searches'][1]=manifest['new_searches'][0]
    elif change=='parent': manifest['parent_campaign']['sha256']='wrong'
    else:
        query=read(followup.ORIGINAL_SOURCE)['collection']['attempts'][0]['query']
        manifest['new_searches'][0]=query
        manifest['candidates'][0]['query']=query
    with pytest.raises(ValueError): followup.check_parent(manifest)


@pytest.mark.parametrize('stale_local',[False,True])
def test_completed_followup_never_recollects_after_local_journal_loss(tmp_path,monkeypatch,stale_local):
    manifest=deepcopy(read(followup.SOURCE))
    attempts=[dict(query=q,attempted_at='2026-10-30T00:00:00Z') for q in manifest['new_searches']]
    manifest['collection']=dict(attempts=attempts)
    source=tmp_path/'source.gz';captures=tmp_path/'captures'
    save(source,manifest)
    monkeypatch.setattr(followup,'SOURCE',source)
    monkeypatch.setattr(followup,'CAPTURES',captures)
    if stale_local: save(captures/'attempts.json',dict(attempts=[]))
    async def forbidden(*args,**kwargs):
        raise AssertionError('The completed follow-up must not perform network requests')
    monkeypatch.setattr(followup,'capture',forbidden)
    assert followup.collect(tmp_path)==0
    assert read(captures/'attempts.json')['attempts']==attempts


def test_access_stop_prevents_more_collection(tmp_path,monkeypatch):
    source=tmp_path/'source.gz';captures=tmp_path/'captures'
    manifest=deepcopy(read(followup.SOURCE))
    manifest['collection']['collection_stop']=dict(reason='Access challenge')
    save(source,manifest)
    monkeypatch.setattr(followup,'SOURCE',source)
    monkeypatch.setattr(followup,'CAPTURES',captures)
    with pytest.raises(RuntimeError,match='do not retry'):
        followup.collect(tmp_path)
    assert not (captures/'attempts.json').exists()


def test_frozen_baseline_cannot_be_replaced_to_inflate_the_reported_gain(tmp_path):
    files=[('baseline.json.gz','baseline_world_sha256'),
           ('supplement-before.json.gz','baseline_supplement_sha256')]
    manifest={}
    for filename,field in files:
        save(tmp_path/filename,dict(flights=[]))
        manifest[field]=digest((tmp_path/filename).read_bytes())
    followup.check_baseline(tmp_path,manifest)
    save(tmp_path/'baseline.json.gz',dict(flights=['changed']))
    with pytest.raises(ValueError,match='baseline missing or changed'):
        followup.check_baseline(tmp_path,manifest)


def test_published_followup_hash_and_quote_provenance():
    manifest=read(followup.SOURCE)
    assert digest(followup.ORIGINAL_SOURCE.read_bytes())==manifest['parent_campaign']['sha256']
    # Initial selection can be tested before capture; final data tests then
    # verify every published successful source and the prepared hash chain.
    if not manifest['collection'].get('captures'): return
    supplement=followup.adapter.load_reference()
    active=supplement['metadata']['source_manifest']
    assert active['sha256']==digest((followup.ROOT/active['path']).read_bytes())
    if active['path']!=followup.relative(followup.SOURCE):
        descendant=read(followup.ROOT/active['path'])
        assert any(p['path']==followup.relative(followup.SOURCE)
            and p['sha256']==digest(followup.SOURCE.read_bytes())
            for p in descendant['parent_campaigns'])
    after=followup.world.load_reference(followup.DAY)
    current=manifest if active['path']==followup.relative(followup.SOURCE) else descendant
    from dashboard import south_america_domestic as domestic
    added=domestic.load_reference()['metadata']['coverage']['new_world_identities'] if domestic.enabled() else 0
    expected={**current['collection']['after']}
    expected['flights']+=added
    assert followup.preparation.metrics(after)==expected
    assert after['metadata']['scopes']['domestic']==27898+added
    for source in manifest['collection']['captures']:
        path=followup.ROOT/source['path']
        if not path.exists():
            continue  # Prepared snapshots are portable without ignored raw caches.
        assert digest(path.read_bytes())==source['sha256']
        query=read(path)
        assert len(query['flights'])==source['records']
        assert all(f.get('price',{}).get('currency','USD')=='USD' for f in query['flights'])

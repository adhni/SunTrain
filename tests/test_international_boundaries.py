"""UTC-boundary evidence, independent 100-attempt cap and airport resolutions."""
from collections import Counter
from copy import deepcopy
import csv

import pytest

from dashboard import world_flights as world
from scripts import prepare_international_boundaries as campaign
from scripts import discover_international_expansion as discovery
from scripts.discover_international_expansion import Airports, digest, read, save


def flight(departure,arrival):
    return dict(number='ZZ1',carrier='ZZ',departure=departure,arrival=arrival)


def test_boundary_clues_are_not_flight_records_and_use_exact_utc_overlap():
    utc=dict(timezone='UTC')
    result=campaign.shifted_overlap(flight(world.START+20*3600,world.END+2*3600),utc,utc,-1)
    assert result['candidate_departure']==world.START-4*3600
    assert result['candidate_arrival']==world.START+2*3600
    assert 'id' not in result and 'origin' not in result
    # An arrival exactly at midnight overlaps; a departure at the end does not.
    assert campaign.shifted_overlap(flight(world.START+20*3600,world.END),utc,utc,-1)['candidate_arrival']==world.START
    assert campaign.shifted_overlap(flight(world.START,world.START+3600),
        dict(timezone='Asia/Tokyo'),utc,1) is None
    assert campaign.shifted_overlap(flight(world.START+3600,world.START+7200),utc,utc,-1) is None


def test_eastern_next_local_day_and_frozen_canadian_replay_offset():
    apia=dict(timezone='Pacific/Apia');utc=dict(timezone='UTC')
    result=campaign.shifted_overlap(flight(world.START-7*3600,world.START+3600),apia,utc,1)
    assert result['candidate_departure']==world.START+17*3600
    assert result['origin_zone']=='Pacific/Apia'
    canada=dict(timezone='America/Vancouver',replay_timezone='Etc/GMT+7')
    f=flight(world.START+7*3600+1800,world.END+1800)
    assert campaign.shifted_overlap(f,canada,utc,-1)['origin_zone']=='Etc/GMT+7'
    # Contrast with the old fixed UTC-8 rule, independent of installed tzdata.
    assert campaign.shifted_overlap(f,dict(timezone='Etc/GMT+8'),utc,-1) is None


def test_manifest_has_49_reverse_51_proven_boundaries_and_two_review_batches():
    manifest=read(campaign.SOURCE)
    campaign.check_campaign(manifest)
    assert manifest['baseline_counts']['flights']==55988
    assert len(manifest['remaining_queue'])==4208
    assert Counter(q[0] for q in manifest['new_searches'])=={
        '2026-11-01':49,'2026-11-02':49,'2026-11-03':2}
    for start,expected in ((0,{'reverse_direction':25,'utc_boundary':25}),
                           (50,{'reverse_direction':24,'utc_boundary':26})):
        assert Counter(r['stream'] for r in manifest['candidates'][start:start+50])==expected


@pytest.mark.parametrize('change',['cap','repeated','unproved','wrong_date','changed_time','parent'])
def test_reject_budget_changes_prior_attempts_and_unproved_dates(change):
    m=deepcopy(read(campaign.SOURCE))
    boundary=next(r for r in m['candidates'] if r['stream']=='utc_boundary')
    if change=='cap':m['search_limit']=101
    elif change=='repeated':
        q=read(campaign.FIRST_SOURCE)['collection']['attempts'][0]['query']
        m['new_searches'][0]=q;m['candidates'][0]['query']=q
    elif change=='unproved':boundary['timing_evidence']=[]
    elif change=='wrong_date':boundary['query'][0]='2026-11-04'
    elif change=='changed_time':boundary['timing_evidence'][0]['candidate_arrival']+=60
    else:m['parent_campaigns'][1]['sha256']='changed'
    with pytest.raises(ValueError):campaign.check_campaign(m)


def test_shared_runner_stops_after_50_and_never_exceeds_100(tmp_path,monkeypatch):
    m=deepcopy(read(campaign.SOURCE));m['collection']=dict(attempts=[],searches_attempted=0)
    source=tmp_path/'source.gz';cache=tmp_path/'audit';captures=tmp_path/'captures'
    for filename,field in [('baseline.json.gz','baseline_world_sha256'),
                           ('supplement-before.json.gz','baseline_supplement_sha256')]:
        save(cache/filename,dict(flights=[]));m[field]=digest((cache/filename).read_bytes())
    save(source,m)
    save(cache/'cache-index.json.gz',dict(queries=[]))
    monkeypatch.setattr(campaign.runner,'ORIGINAL_CACHE',cache)
    seen=[];reviews=[]
    async def capture(*args):
        config=args[4]
        assert args[3]==2 and config['currency']=='USD'
        for key in config['queries']:
            config['on_query_start'](key);seen.append(key)
    def publish(cache,source,captures,validate):
        manifest=read(source);validate(manifest)
        attempts=read(captures/'attempts.json')['attempts']
        reviews.append(len(attempts));manifest['collection']=dict(attempts=attempts)
        save(source,manifest)
    monkeypatch.setattr(campaign.runner,'capture',capture)
    monkeypatch.setattr(campaign.runner,'publish_checkpoint',publish)
    for expected in (50,100,100):
        assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,50)==0
        assert len(seen)==expected
    assert reviews==[50,100] and len(set(seen))==100
    # Published attempts survive deletion of the local journal.
    (captures/'attempts.json').unlink()
    assert campaign.runner.collect(cache,source,captures,campaign.check_campaign,50)==0
    assert len(seen)==100 and len(read(captures/'attempts.json')['attempts'])==100


def test_airport_resolution_keeps_juba_current_and_pbi_separate_from_djt(tmp_path,monkeypatch):
    airport_file=tmp_path/'.cache/australia-flights-audit/ourairports-airports.csv'
    zone_file=tmp_path/'.cache/gulf-flights-audit/openflights-airports.dat'
    airport_file.parent.mkdir(parents=True);zone_file.parent.mkdir(parents=True)
    with airport_file.open('w') as stream:
        writer=csv.writer(stream)
        writer.writerow(['iata_code','type','icao_code','ident','iso_country','municipality','name','latitude_deg','longitude_deg'])
        writer.writerow(['JUB','large_airport','HJJJ','HJJJ','SS','Juba','Juba',4.87201,31.601101])
        writer.writerow(['DJT','large_airport','KDJT','KPBI','US','West Palm Beach','Airport',26.683201,-80.095596])
    with zone_file.open('w') as stream:
        csv.writer(stream).writerows([
            [1173,'Juba','Juba','South Sudan','JUB','HSSJ',4.87201,31.601101,0,3,'U','Africa/Juba'],
            [3722,'Airport','West Palm Beach','United States','PBI','KPBI',26.683201,-80.095596,0,-5,'A','America/New_York']])
    monkeypatch.setattr(discovery,'ROOT',tmp_path)
    monkeypatch.setattr(discovery,'AIRPORT_HASH',digest(airport_file.read_bytes()))
    monkeypatch.setattr(discovery,'TZ_HASH',digest(zone_file.read_bytes()))
    airports=Airports(dict(airports=[]))
    juba=airports.get('JUB');djt=airports.get('DJT')
    assert (juba['icao'],juba['country'],juba['timezone'])==('HJJJ','SS','Africa/Juba')
    assert (djt['icao'],djt['country'],djt['timezone'])==('KDJT','US','America/New_York')
    assert airports.get('PBI') is None and 'Superseded' in airports.unresolved['PBI']
    assert airports.get('PNH') is None


def test_prepared_provenance_and_completed_campaign_counts():
    manifest=read(campaign.SOURCE);campaign.check_campaign(manifest)
    if not manifest['collection'].get('after'):return
    supplement=campaign.adapter.load_reference()
    assert supplement['metadata']['source_manifest']==dict(
        path=campaign.relative(campaign.SOURCE),sha256=digest(campaign.SOURCE.read_bytes()))
    snapshot=world.load_reference(world.DAY)
    assert campaign.runner.preparation.metrics(snapshot)==manifest['collection']['after']
    assert snapshot['metadata']['scopes']['domestic']==27898
    assert manifest['collection']['searches_attempted']<=100


def test_closed_campaign_is_rejected_before_its_ledger_is_rewritten(tmp_path,monkeypatch):
    active=tmp_path/'active.gz';source=tmp_path/'closed.gz'
    save(active,dict(metadata=dict(source_manifest=dict(path=str(tmp_path/'newer.gz'),sha256='newer'))))
    save(source,dict(collection=dict(attempts=[])))
    before=source.read_bytes()
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE',str(active))
    with pytest.raises(ValueError,match='newer campaign'):
        campaign.runner.publish_checkpoint(tmp_path,source,tmp_path/'captures',validate=lambda _:None)
    assert source.read_bytes()==before

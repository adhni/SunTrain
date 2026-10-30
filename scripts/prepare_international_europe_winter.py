"""Fill European international gaps using reviewed winter operating-day evidence.

100 is a ceiling, not a target. Only missing directions supported by the reviewed
tables are searched, on 2 November only, with reviews after each 25 attempts.
Timetables nominate queries; only dated Google captures supply replay records.
"""
import argparse
from collections import Counter
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard import world_flights as world, international_expansion as adapter
from scripts import prepare_international_followup as runner
from scripts import prepare_international_longhaul as longhaul
from scripts.discover_international_expansion import (
    DAY, CACHE as ORIGINAL_CACHE, read, save, digest, relative)

SOURCE = ROOT / 'data/sources/world_international_europe_winter.json.gz'
CACHE = ROOT / '.cache/international-europe-winter'
CAPTURES = ROOT / '.cache/google-flights-world-international-usd-europe-winter'
PARENTS = [*longhaul.PARENTS, longhaul.SOURCE]
PARENT_ATTEMPTS = (1000, 300, 100, 200)
EUROPE = set('FR IT DE ES GB NL BE CH AT PT IE DK SE NO FI PL CZ HU RO BG HR SI SK EE LV LT LU MT GR CY RS BA ME MK AL IS GE'.split())

# Reviewed primary PDFs. Page numbers below are one-based. Frequencies are
# evidence for searches only: they are never expanded into synthetic flights.
DOCUMENTS = {
    'nice': dict(url='https://entreprises.nice.aeroport.fr/content/download/51695/file/PROGRAMME_HIVER-W26_20260907_detail_jours.pdf?inLanguage=fre-FR',
        sha256='5e4119cd6a6bac1b63b0a339897c635e76f133f2943c0eaab5e92464ef723b54', updated='2026-09-06'),
    'bordeaux': dict(url='https://www.bordeaux.aeroport.fr/sites/default/files/2026-10/PROGR-VOLS%20%20automne%20hiver%202026%20V28%20B2B_0.pdf',
        sha256='1f1a319ab9c2b07d5b65a47dd941bbb7b84e4057e1ad6823c7499a851ac77f3e', updated='2026-10-07'),
    'nuremberg': dict(url='https://cdn0.scrvt.com/c6cfa56ea5ccf7ccabf7e13a538ca691/a517f0b088540089/1050a68f1e6b/260914_Flugplan-bersicht_W26-27_DE.pdf',
        sha256='0732b9ae8b8e3484955a85fbd50ccd54aff434636fc06f44a360e9192aadbd82', updated='2026-09-14'),
    'toulouse': dict(url='https://www.toulouse.aeroport.fr/sites/default/files/2026-09/Programme%20HIVER%202026-27.pdf',
        sha256='882626f60769f87045424face859f2d284efad6255765cc5ddbd208fea41c623', updated='2026-09-29'),
    'strasbourg': dict(url='https://www.strasbourg.aeroport.fr/wp-content/uploads/2026/08/Programme-previsionnel-des-vols-Hiver-2026_2027.pdf',
        sha256='2854ed420352d6426e0920d3097dce89952e717fd8e24d0ca2dc9177eb9a0faf', updated='2026-10-23'),
}


def reviewed_routes():
    """Exact airports reviewed against existing catalogues; never city codes."""
    rows = []
    def add(document, hub, codes, page, carrier, weekdays, start='2026-10-25', end='2027-03-27'):
        for code in codes.split():
            rows.append(dict(document=document, published_direction=[hub, code], page=page,
                carrier=carrier, weekdays=weekdays, valid_from=start, valid_to=end))
    add('nice', 'NCE', 'SOF', 1, 'Wizz Air', [1,5], '2026-10-26', '2027-03-26')
    add('nice', 'NCE', 'TBS', 1, 'Georgian Airways', [1,3,4,6], '2026-10-26')
    add('nice', 'NCE', 'DUS', 1, 'Eurowings', [1,3,4,5,7])
    add('nice', 'NCE', 'FLR', 1, 'Air Corsica', [1,5], '2026-10-26', '2027-03-26')
    add('nice', 'NCE', 'NAP', 1, 'easyJet', [1,2,3,4,5,7], end='2027-03-26')
    add('nice', 'NCE', 'LUX', 1, 'Luxair', [1,2,3,4,5,6,7])
    add('nice', 'NCE', 'LCY', 1, 'British Airways', [1,4,7])
    add('nice', 'NCE', 'LPL', 1, 'easyJet', [1,5], '2027-03-01', '2027-03-26')
    add('nice', 'NCE', 'AGP', 1, 'easyJet', [4,7], end='2027-03-25')
    add('bordeaux', 'BOD', 'BRU', 1, 'easyJet', [1,4,5,7])
    add('bordeaux', 'BOD', 'MXP', 2, 'easyJet', [1,2,4,5,7])
    add('bordeaux', 'BOD', 'LIS', 2, 'easyJet', [1,2,3,4,5,6,7])
    add('bordeaux', 'BOD', 'PRG MAN', 2, 'easyJet', [1,5])
    add('bordeaux', 'BOD', 'LGW', 2, 'easyJet / British Airways', [1,2,3,4,5,6,7])
    add('bordeaux', 'BOD', 'LTN', 2, 'easyJet', [1,3,4,5,7])
    add('bordeaux', 'BOD', 'NAP', 2, 'easyJet', [1,5], '2026-12-04')
    add('bordeaux', 'BOD', 'FLR', 2, 'Volotea', [2,6], '2026-12-19', '2027-01-05')
    add('nuremberg', 'NUE', 'BEG', 2, 'Air Serbia', [1,5], end='2027-03-28')
    # Starred NUE services are explicitly non-continuous; leave them deferred.
    add('toulouse', 'TLS', 'MXP', 4, 'easyJet', [1,5], end='2027-01-08')
    add('toulouse', 'TLS', 'NAP', 4, 'Ryanair', [1,5], '2026-10-26', '2026-10-30')
    add('toulouse', 'TLS', 'PSA', 4, 'Volotea', [1,5], '2026-11-06', '2027-01-04')
    add('strasbourg', 'SXB', 'CPH', 2, 'Volotea', [1,4], '2026-10-26', '2027-03-25')
    add('strasbourg', 'SXB', 'MUC', 3, 'Volotea', [1,4], '2026-10-26', '2027-03-25')
    add('strasbourg', 'SXB', 'FLR', 2, 'Volotea', [1,5], '2026-11-06', '2026-11-30')
    return rows


def operates(proof, day=DAY):
    return (proof['valid_from'] <= day <= proof['valid_to']
        and date.fromisoformat(day).isoweekday() in proof['weekdays'])


def previous_attempts():
    return {tuple(a['query']) for p in PARENTS for a in read(p)['collection']['attempts']}


def select_candidates(baseline, index):
    routes = {(f['origin'], f['destination']) for f in baseline['flights']}
    known = {tuple(r['query']): r for r in index['queries']}
    charged = previous_attempts()
    candidates, skipped = [], Counter()
    for proof in reviewed_routes():
        if not operates(proof):
            skipped['wrong_day_or_season'] += 1
            continue
        for a,b in (proof['published_direction'], proof['published_direction'][::-1]):
            key = (DAY,a,b)
            if (a,b) in routes: skipped['already_captured'] += 1; continue
            if key in charged: skipped['previously_attempted'] += 1; continue
            if key in known and known[key]['latest']['flights']:
                skipped['compatible_positive_cache'] += 1; continue
            evidence = dict(kind='official_winter_timetable', **DOCUMENTS[proof['document']], **proof)
            candidates.append(dict(query=list(key),stream=proof['published_direction'][0],
                evidence=[evidence], verified_recheck=key in known,
                direction_evidence='published_departure' if [a,b]==proof['published_direction'] else 'reverse_route_candidate'))
    # Route evidence for the return is a search lead, never proof of operation.
    candidates.sort(key=lambda r: (r['verified_recheck'], r['direction_evidence']!='published_departure', tuple(r['query'])))
    return candidates[:100], dict(skipped)


def build_manifest():
    if SOURCE.exists():
        m=read(SOURCE); check_campaign(m); return m
    baseline = world.load_reference(DAY)
    candidates, skipped = select_candidates(baseline, read(ORIGINAL_CACHE/'cache-index.json.gz'))
    if not candidates: raise ValueError('No evidenced missing directions; do not spend the budget')
    for name,proof in DOCUMENTS.items():
        if digest((CACHE/(name+'.pdf')).read_bytes()) != proof['sha256']:
            raise ValueError('Reviewed primary timetable changed: '+name)
    catalogue={}
    for a in [*read(longhaul.FIRST)['airports'], *baseline['airports']]: world.merge_airport(catalogue,a)
    save(CACHE/'baseline.json.gz',baseline)
    save(CACHE/'supplement-before.json.gz',adapter.load_reference())
    parent=read(longhaul.SOURCE)
    keys={tuple(r['query']) for r in candidates}
    m=dict(profile='world_international_europe_winter', day=DAY, timezone='UTC', currency='USD',
        search_limit=100, checkpoint_size=25, concurrency=2,
        parent_campaigns=[dict(path=relative(p),sha256=digest(p.read_bytes()),attempts=n)
            for p,n in zip(PARENTS,PARENT_ATTEMPTS)],
        baseline_inputs=baseline['metadata']['inputs'], baseline_counts=runner.preparation.metrics(baseline),
        baseline_world_sha256=digest(world.reference_path().read_bytes()),
        baseline_supplement_sha256=digest(adapter.reference_path().read_bytes()),
        airports=[catalogue[k] for k in sorted(catalogue)], candidates=candidates,
        new_searches=[r['query'] for r in candidates],
        verified_recheck_queries=[r['query'] for r in candidates if r['verified_recheck']],
        workstream_limits=dict(Counter(r['stream'] for r in candidates)), reviewed_documents=DOCUMENTS,
        reviewed_routes=reviewed_routes(), selection_skips=skipped,
        remaining_queue=[q for q in parent['remaining_queue'] if tuple(q) not in keys],
        unresolved_airports=parent['unresolved_airports'], unresolved_routes=parent['unresolved_routes'],
        limitations=['100 is a ceiling, not a target; no fabricated pairs to fill unused slots.',
            'Only 2 November 2026 origin-local queries; adjacent-day coverage remains partial.',
            'Monday winter departures nominate searches, not synthetic timed flights.',
            'A published outbound route does not prove the return operates that day.',
            'Non-continuous, later-starting and wrong-weekday services remain deferred.',
            'Empty means not returned; no claim of complete European or worldwide traffic.'],
        collection=dict(attempts=[],searches_attempted=0))
    check_campaign(m);save(SOURCE,m)
    print(world.canonical_json(dict(selected=len(candidates),cap=100,rechecks=m['verified_recheck_queries'],skipped=skipped)),flush=True)
    return m


def check_campaign(m):
    if any(m.get(k)!=v for k,v in dict(search_limit=100,checkpoint_size=25,concurrency=2,day=DAY,currency='USD').items()):
        raise ValueError('Fixed 100-search cap, 25-query reviews, USD and one date required')
    keys=[tuple(q) for q in m['new_searches']]
    if not 0<len(keys)<=100 or len(keys)!=len(set(keys)) or [r['query'] for r in m['candidates']]!=m['new_searches']:
        raise ValueError('Unique evidenced exact queries required')
    if m['reviewed_documents']!=DOCUMENTS or m['reviewed_routes']!=reviewed_routes():
        raise ValueError('Reviewed winter evidence changed')
    if [p['path'] for p in m['parent_campaigns']] != [relative(p) for p in PARENTS]:
        raise ValueError('All four completed parents must remain pinned')
    for pin,path,n in zip(m['parent_campaigns'],PARENTS,PARENT_ATTEMPTS):
        parent=read(path)['collection']
        if pin['sha256']!=digest(path.read_bytes()) or pin['attempts']!=n or len(parent['attempts'])!=n or parent.get('collection_stop'):
            raise ValueError('Historical campaign changed or incomplete')
    if set(keys)&previous_attempts():raise ValueError('Never repeat a charged campaign attempt')
    air={a['code']:a for a in m['airports']}
    rechecks=[]
    for row in m['candidates']:
        day,a,b=row['query']; evidence=row['evidence']
        if day!=DAY or a==b or air[a]['country'] not in EUROPE or air[b]['country'] not in EUROPE or not adapter.is_international(air[a],air[b]):
            raise ValueError('Expected exact European international airports on 2 November')
        if len(evidence)!=1:raise ValueError('One reviewed primary proof per query required')
        e=evidence[0]; proof={k:e[k] for k in reviewed_routes()[0]}
        if proof not in reviewed_routes() or not operates(proof) or e!=dict(kind='official_winter_timetable',**DOCUMENTS[proof['document']],**proof):
            raise ValueError('Proof must cover the date and Monday')
        route=proof['published_direction']
        if [a,b] not in [route,route[::-1]] or row['stream']!=route[0]:raise ValueError('Route does not match primary evidence')
        expected='published_departure' if [a,b]==route else 'reverse_route_candidate'
        if row['direction_evidence']!=expected:raise ValueError('Do not imply proof of a return service')
        if row['verified_recheck']:rechecks.append(row['query'])
    if m.get('verified_recheck_queries')!=rechecks or m['workstream_limits']!=dict(Counter(r['stream'] for r in m['candidates'])):
        raise ValueError('Recheck allowlist or allocations changed')
    for path,info in m['baseline_inputs'].items():
        if path!=relative(adapter.reference_path()) and digest((ROOT/path).read_bytes())!=info['sha256']:
            raise ValueError('Frozen member view changed: '+path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['manifest','collect','finalize'])
    action=parser.parse_args().action
    if action=='manifest':build_manifest()
    elif action=='collect':return runner.collect(CACHE,SOURCE,CAPTURES,check_campaign,25)
    else:runner.publish_checkpoint(CACHE,SOURCE,CAPTURES,check_campaign)
    return 0


if __name__=='__main__':sys.exit(main())

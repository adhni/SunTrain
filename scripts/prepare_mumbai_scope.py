"""Index Mumbai services in the existing India feed; never copy its schedules."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_india_replay import SHA256, selected_regional_route, regional_category
from scripts.prepare_rail_replay import TimetableArchive
from scripts.prepare_australian_replay import records, file_hash

CORE = {'CCG','MMCT','DDR','DR','BVI','VR','DRD','CSMT','TNA','KYN','KJT','PNVL','DIVA','BSR','BIRD','NEU'}
COLORS = {'Western':'8E448D','Central':'D0423D','Harbour':'2085B6',
          'Trans-Harbour':'008B88','Diva–Vasai / regional':'52835B','Regional connections':'806A4E'}
NOTE = ('Mumbai suburban rail, 31 August–6 September 2026, reusing the India timetable and railway paths. '
        'Partial feed coverage: Western, Central and Harbour services plus optional regional connections; '
        'Harbour coverage is especially sparse and Trans-Harbour is not represented. '
        'This is not the complete Mumbai timetable. Original calls and clocks are retained; unresolved track sections stay gaps.')


def corridor(codes, coordinates):
    codes = set(codes)
    # Keep complete journeys in Greater Mumbai and adjoining rail corridors.
    # Requiring a named core station excludes Pune locals and other 9-series trains.
    if not codes & CORE or not coordinates or not all(72.6 <= x <= 73.7 and 18.4 <= y <= 20.2 for x,y in coordinates):
        return None
    if 'TNA' in codes and codes & {'TUH','VSH','NEU','RABE'}:
        return 'Trans-Harbour'
    if 'BSR' in codes and codes & {'DIVA','BIRD'}:
        return 'Diva–Vasai / regional'
    if codes & {'CCG','BVI','VR','DRD'}:
        return 'Western'
    if 'CSMT' in codes and codes & {'PNVL','VDLR','GV','MNKD'}:
        return 'Harbour'
    if codes & {'CSMT','KYN','KJT','TNA'}:
        return 'Central'
    return 'Regional connections'


def prepare(archive, output):
    if file_hash(archive) != SHA256:
        raise ValueError('Mumbai scope requires the pinned India timetable')
    with TimetableArchive(archive) as z:
        agencies = {r['agency_id']:r for r in records(z,'agency.txt')}
        routes = {r['route_id']:r for r in records(z,'routes.txt') if selected_regional_route(r,agencies)}
        trips = {r['trip_id']:r for r in records(z,'trips.txt') if r['route_id'] in routes}
        stops = {r['stop_id']:r for r in records(z,'stops.txt')}
        calls = defaultdict(list)
        for row in records(z,'stop_times.txt'):
            if row['trip_id'] in trips:
                calls[row['trip_id']].append(row['stop_id'])
    selected = {}
    for trip, rows in calls.items():
        label = corridor(rows, [(float(stops[s]['stop_lon']),float(stops[s]['stop_lat'])) for s in rows])
        if label:
            selected[trip] = {'line':label,'color':COLORS[label], 'mode':regional_category(routes[trips[trip]['route_id']])[0]}
    result = {'source_sha256':SHA256,'note':NOTE,'trips':dict(sorted(selected.items())),
              'corridors':dict(Counter(v['line'] for v in selected.values())),
              'missing_corridors':[c for c in ['Western','Central','Harbour','Trans-Harbour'] if not any(v['line']==c for v in selected.values())]}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'entries':len(selected),'corridors':result['corridors'],'missing':result['missing_corridors'],'bytes':output.stat().st_size}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=ROOT/'.cache/india/gtfs.zip')
    p.add_argument('--output',type=Path,default=ROOT/'.cache/india/mumbai-scope.json')
    args=p.parse_args();prepare(args.archive,args.output)

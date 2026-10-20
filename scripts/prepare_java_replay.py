"""Prepare Java intercity passenger trains from the official GAPEKA 2025 tables."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
SOURCE_URL='https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%20224%20TAHUN%202024_GAPEKA_JAWA.pdf'
ARCHIVE_URL='https://web.archive.org/web/20250127040629id_/'+SOURCE_URL
PDF_SHA256='8dd51fe4f71309ed3f5d49eb0ca018e2c5168e11758c91910818c5948328d23b'
SOURCE_SHA256='c1f393e4e8c03323b20789092995f562531c636f26781364f9403df7073366f7'
GEOMETRY_SHA256='39970830646772bd2c4f131d2a94d2833f28e7c6671968ee1204c31e1d83a095'
SOURCE=ROOT/'data/reference/java/intercity-timetable-2025.json.gz'
GEOMETRY=ROOT/'data/reference/java/rail-osm-2026-10-18.json.gz'
OUTPUT=ROOT/'data/reference/java/2025-02-03.json.gz'
FIRST=date(2025,2,3)
NOTE=('Java intercity, airport and Bandung–Padalarang feeder trains from the GAPEKA timetable effective 1 February 2025. '
      'Optional F services and journeys with untimed passenger calls are excluded. '
      'Published train-number segments retain their own times. Positions follow inferred railway paths; '
      'unsupported sections stay gaps. Jakarta rail is optional and reuses its existing 2025/2026 sources matched by weekday. '
      'Regional/commuter services use their separate compact reference. No live tracking or passenger loads.')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with gzip.open(path,'rt') as f:return json.load(f)
def save(value,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as out:
        out.write(json.dumps(value,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())


HEADER=re.compile(r'KA (\d+F?) \((.+)\) Relasi ([A-Z0-9]+)-([A-Z0-9]+)')
ROW=re.compile(r'^(\d+)\s+(.+?)\s+\(([A-Z0-9]+)\)\s*(.*)$')
CLOCK=re.compile(r'\d{2}:\d{2}:\d{2}')


def parse_pages(pages, number_filter=None):
    """Read visual row order, not PDF object order (some headers are stored last)."""
    lines=[(page,line.strip()) for page,text in pages for line in text.splitlines()
           if line.strip() and not re.fullmatch(r'\d+\s*',line)]
    trips=[];current=None
    for i,(page,line) in enumerate(lines):
        match=HEADER.fullmatch(line)
        if match:
            current=None
            selected = number_filter(match[1]) if number_filter else int(match[1].rstrip('F'))<=300
            if selected and i+1<len(lines) and lines[i+1][1].startswith('No.'):
                current={'number':match[1],'name':match[2],'origin':match[3],'destination':match[4],
                    'page':page,'rows':[]};trips.append(current)
            continue
        match=ROW.match(line)
        if current is not None and match:
            current['rows'].append({'sequence':int(match[1]),'name':match[2],'code':match[3],
                'events':match[4],'page':page})
    numbers=[t['number'] for t in trips]
    if len(set(numbers))!=len(numbers):raise ValueError('Duplicate timetable table')
    return trips


def normalize_trip(trip):
    rows=trip['rows']
    if [r['sequence'] for r in rows]!=list(range(1,len(rows)+1)):
        raise ValueError('Missing/duplicate station rows: '+trip['number'])
    if rows[0]['code']!=trip['origin'] or rows[-1]['code']!=trip['destination']:
        raise ValueError('Published terminals do not match rows: '+trip['number'])
    events=[];previous=None;offset=0;untimed=[]
    for row in rows:
        text=row['events'];passing=text.startswith('Ls')
        if passing:
            found=CLOCK.match(text[2:].strip());clocks=[found[0]] if found else []
        else:
            match=re.match(r'^(\d{2}:\d{2}:\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?',text)
            clocks=[c for c in match.groups() if c] if match else []
            if not clocks:untimed.append(row['code'])
        times=[]
        for clock in clocks:
            h,m,s=map(int,clock.split(':'))
            if h>=24 or m>=60 or s>=60:raise ValueError('Invalid station time')
            seconds=h*3600+m*60+s
            if previous is not None and seconds+offset<previous:
                if previous%86400<21*3600 or seconds>3*3600:raise ValueError('Backwards station time: '+trip['number'])
                offset+=86400
            seconds+=offset;times.append(seconds);previous=seconds
        events.append({**row,'times':times,'passing':passing})
    calls=[[r['code'],r['times'][0],r['times'][-1]] for r in events if r['times'] and not r['passing']]
    if len(calls)<2:raise ValueError('Insufficient calls: '+trip['number'])
    # A numbered section starts at its own departure and ends at its own arrival.
    # Adjacent number sections must not duplicate the shared station's dwell.
    calls[0][1]=calls[0][2];calls[-1][2]=calls[-1][1]
    if calls[-1][2]-calls[0][1]>24*3600:raise ValueError('Implausible passenger duration')
    return {k:v for k,v in trip.items() if k!='rows'}|{'calls':calls,'route':[[r['code'],r['times'][0] if r['times'] else None] for r in events],
        'untimed_calls':untimed,'stations':{r['code']:r['name'] for r in events}}


def extract_pdf(cache):
    import pdfplumber
    filename=cache/'gapeka-java-2025.pdf'
    if digest(filename)!=PDF_SHA256:raise ValueError('Government timetable PDF differs')
    text_cache=cache/'visual-pages.json'
    if text_cache.exists():pages=json.loads(text_cache.read_text())
    else:
        pages=[]
        with pdfplumber.open(filename) as document:
            if len(document.pages)!=1721:raise ValueError('Unexpected timetable edition')
            for index in range(53,600):
                page=document.pages[index];pages.append([index+1,page.extract_text() or '']);page.close()
                if index%50==0:print('extracted page',index+1,flush=True)
        text_cache.write_text(json.dumps(pages))
    trips=parse_pages(pages)
    if len(trips)!=297:raise ValueError('Expected all 297 published intercity number sections, got '+str(len(trips)))
    expected={}
    with pdfplumber.open(filename) as document:
        for page in document.pages[53:61]:
            for line in (page.extract_text() or '').splitlines():
                match=re.match(r'^\d+ (\d+F?) KA .* ([A-Z]+)-([A-Z]+) (\d\d:\d\d:\d\d) (\d\d:\d\d:\d\d) \d+$',line)
                if match and int(match[1].rstrip('F'))<=300:expected[match[1]]=match.groups()[1:]
            page.close()
    if set(expected)!={t['number'] for t in trips}:raise ValueError('Table-of-contents coverage mismatch')
    normalized=[];omitted={}
    for trip in trips:
        item=normalize_trip(trip)
        if trip['number'].endswith('F'):omitted[trip['number']]='Conditional/fakultatif; operating dates unconfirmed';continue
        if item['untimed_calls']:omitted[trip['number']]='Untimed passenger calls: '+', '.join(item['untimed_calls']);continue
        origin,destination,start,end=expected[trip['number']]
        def clock(s):return f'{s//3600%24:02}:{s//60%60:02}:{s%60:02}'
        if (origin,destination,start,end)!=(item['origin'],item['destination'],clock(item['calls'][0][2]),clock(item['calls'][-1][1])):
            raise ValueError('Detailed times disagree with contents: '+trip['number'])
        normalized.append(item)
    save({'metadata':{'source_url':SOURCE_URL,'archive_url':ARCHIVE_URL,'pdf_sha256':PDF_SHA256,
        'effective_from':'2025-02-01','extracted_tables':len(trips),'omitted_trips':omitted},'trips':normalized},SOURCE)
    print('source',len(normalized),'omitted',len(omitted),'bytes',SOURCE.stat().st_size,'sha256',digest(SOURCE),flush=True)


def station_scope(source,geographic,graph):
    from collections import defaultdict
    refs=defaultdict(list);names=defaultdict(list)
    def normal(name):return re.sub(r'[^a-z0-9]','',name.lower().replace('stasiun','').replace('station',''))
    for station in geographic['stations']:
        tags=station['tags']
        for key,value in tags.items():
            if 'ref' in key:
                for code in value.split(';'):refs[code.upper()].append(station)
        for key in ('name','old_name','alt_name','official_name','name:id'):
            for name in tags.get(key,'').split(';'):
                if name:names[normal(name)].append(station)
    needed={code:name for trip in source['trips'] for code,name in trip['stations'].items()}
    called={c for t in source['trips'] for c,a,d in t['calls']};result={};missing={}
    for code,name in sorted(needed.items()):
        same_name={s['osm_id'] for s in names[normal(name)]}
        candidates=refs[code] or names[normal(name)]
        named=[s for s in candidates if s['osm_id'] in same_name]
        if named:candidates=named
        anchored=[s for s in candidates if graph.anchors(s['coordinates'])]
        if anchored:candidates=anchored
        if not candidates:
            if code in called:raise ValueError('Missing passenger station: '+code+' '+name)
            missing[code]=name;continue
        chosen=min(candidates,key=lambda s:(s['tags'].get('railway')!='station',s['osm_id']))
        result[code]={'name':name,'coordinates':chosen['coordinates'],'osm_id':chosen['osm_id']}
    return result,missing


def prepare(output=OUTPUT, *, source_path=SOURCE, source_pin=SOURCE_SHA256,
            mode='train', operator='KAI', namespace='java', note=NOTE, source_name=None):
    from dashboard.replay import cumulative_distances
    from scripts.compact_transit import save_reference, compact_reference
    from scripts.prepare_great_britain_replay import BritainRailGraph
    for path,pin in [(source_path,source_pin),(GEOMETRY,GEOMETRY_SHA256)]:
        if digest(path)!=pin:raise ValueError('Pinned Java input differs: '+str(path))
    source,geo=read(source_path),read(GEOMETRY);graph=BritainRailGraph(geo['ways'])
    connections=None
    if namespace=='java' and mode=='train':
        from scripts.prepare_java_connections import SOURCE as CONNECTIONS, SOURCE_SHA256 as CONNECTIONS_SHA256
        if digest(CONNECTIONS)!=CONNECTIONS_SHA256:raise ValueError('Pinned airport/feeder input differs')
        connections=read(CONNECTIONS)
        source={'metadata':{**source['metadata'],'omitted_trips':{**source['metadata']['omitted_trips'],**connections['metadata']['omitted_trips']}},
                'trips':source['trips']+connections['trips']}
        if len({t['number'] for t in source['trips']})!=len(source['trips']):raise ValueError('Duplicate Java train number')
    scope,missing=station_scope(source,geo,graph)
    called=sorted({c for t in source['trips'] for c,a,d in t['calls']});ids={c:i for i,c in enumerate(called)}
    result={'stations':[{'name':scope[c]['name'],'lon':scope[c]['coordinates'][0],'lat':scope[c]['coordinates'][1],'mode':mode} for c in called],
        'patterns':{},'paths':{},'days':{str(FIRST+timedelta(days=i)):[] for i in range(7)},'train_numbers':{}}
    segments={};unresolved=Counter();matched=total=0
    for trip in source['trips']:
        calls=trip['calls'];legs=[];indices=[];cursor=0
        # Loop services can call at the same station twice. Preserve occurrence
        # order rather than resolving every station code to its final index.
        for code,_,_ in calls:
            index=next(i for i in range(cursor,len(trip['route'])) if trip['route'][i][0]==code)
            indices.append(index);cursor=index+1
        for j,((a,_,_),(b,_,_)) in enumerate(zip(calls,calls[1:])):
            route=[c for c,t in trip['route'][indices[j]:indices[j+1]+1] if c in scope and graph.anchors(scope[c]['coordinates'])]
            signature=tuple(route)
            key=namespace+'-'+hashlib.sha256(repr((a,b,signature)).encode()).hexdigest()[:18]
            if key not in result['paths']:
                combined=[];reason=None
                if not route or route[0]!=a or route[-1]!=b:reason='Unmatched passenger-station track anchor'
                else:
                    for origin,destination in zip(route,route[1:]):
                        pair=(origin,destination)
                        if pair not in segments:
                            points=[scope[c]['coordinates'] for c in pair];curve=graph.leg(*points)
                            if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances(points)[-1]):curve=None
                            segments[pair]=curve
                        curve=segments[pair]
                        if not curve:reason='Disconnected railway section: '+origin+'–'+destination;break
                        if combined and combined[-1]!=curve[0]:raise ValueError('Native railway paths do not join')
                        combined.extend(curve if not combined else curve[1:])
                if reason:combined=[];unresolved[reason]+=1
                result['paths'][key]={'coordinates':combined,'distances':cumulative_distances(combined),
                    'quality':'track' if combined else 'approximate',**({'reason':reason} if reason else {})}
            legs.append(key)
        identifier=namespace+'-'+trip['number'];start=calls[0][2]
        # Route colours are SunTrain presentation colours, not official service branding.
        palette=['#E95B0C','#174A8B','#008577','#8A3F88','#B33F40','#967100']
        color=palette[int(hashlib.sha256(trip['name'].encode()).hexdigest()[:8],16)%len(palette)]
        result['train_numbers'][identifier]=trip['number']
        result['patterns'][identifier]={'mode':mode,'operator':trip.get('operator',operator),'line':trip['name'],'route_id':trip['name'],
            'color':trip.get('color',color),'direction':'Not specified','origin':scope[calls[0][0]]['name'],'destination':scope[calls[-1][0]]['name'],
            'stops':[[ids[c],a-start,d-start] for c,a,d in calls],'legs':legs}
        for day in result['days']:
            # One owner per scheduled departure within a 03:00–03:00 window.
            offset=start if start>=10800 else start+86400
            result['days'][day].append([identifier,identifier,offset])
        total+=len(legs);matched+=sum(bool(result['paths'][k]['coordinates']) for k in legs)
    for rows in result['days'].values():rows.sort(key=lambda r:(r[2],r[1]))
    result['metadata']={'start_date':str(FIRST),'end_date':str(FIRST+timedelta(days=6)),'timezone':'Asia/Jakarta',
        'source':source_name or 'DJKA / PT Kereta Api Indonesia · GAPEKA Java 2025 intercity, airport and feeder passenger timetables',
        'source_url':SOURCE_URL,'license':'Published government/KAI timetable; original source rights retained','license_url':'https://djka.kemenhub.go.id/',
        'attribution':'Timetable: Indonesian Directorate General of Railways (DJKA) / PT Kereta Api Indonesia, KP-DJKA 224 Tahun 2024, effective 1 February 2025. Table conversion by SunTrain. Railway geography © OpenStreetMap contributors, ODbL 1.0.',
        'sources':[{'source_url':SOURCE_URL,'archive_url':ARCHIVE_URL,'source_date':'2025-02-01','published':'2024-12-30','sha256':PDF_SHA256}],
        'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],
        'geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'geometry_source_date':'2026-10-18; geographic alignment reference for February 2025 schedules','geometry_sha256':GEOMETRY_SHA256,
        'replay_note':note,'omitted_trips':source['metadata']['omitted_trips'],'unresolved_geometry_patterns':dict(unresolved),
        'unresolved_geometry_trips':{},'track_coverage':{'matched':matched,'total':total},'missing_passing_point_locations':missing,
        'station_scope':scope,'daily_services':{day:len(rows) for day,rows in result['days'].items()},
        'business_day_rule':'Departures belong to one 03:00–03:00 window; playback continues to the last arrival.'}
    if source['metadata'].get('operator_sources'):
        result['metadata']['sources'].extend(source['metadata']['operator_sources'])
        result['metadata']['attribution']+=' Regional operator tables: PT Kereta Commuter Indonesia / KAI Commuter, 1 February 2025 editions; published source rights retained.'
    if connections:
        result['metadata']['connections']={**connections['metadata'],'normalized_sha256':CONNECTIONS_SHA256}
        result['metadata']['attribution']+=' Airport/feeder services: KAI and KAI Bandara / PT Railink, from the same official February 2025 government timetable.'
    result['metadata'].update({k:source['metadata'][k] for k in ('groups','source_method','calendar_audit','operator_pdf_corrections') if k in source['metadata']})
    if namespace!='java':compact_reference(result,prefix=namespace+'-stops-')
    save_reference(result,output)
    print('prepared',len(result['patterns']),'trains/day','track legs',matched,total,'gaps',dict(unresolved),'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--extract-pdf',action='store_true');p.add_argument('--cache',type=Path,default=ROOT/'.cache/java')
    a=p.parse_args()
    if a.extract_pdf:extract_pdf(a.cache)
    else:prepare()

"""Prepare airport rail and Whoosh from pinned official 2025 publications."""
from datetime import date, timedelta
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_jakarta_timetable import save, extended_times

AIRPORT_URL='https://www.commuterline.id/files/download/documents/Jadwal%20Commuter%20Line%20Basoetta%20-%20Update%201%20September%202025.pdf'
WHOOSH_URL='https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%202%20Tahun%202025_GAPEKA%20KA%20KECEPATAN%20TINGGI%20JAKARTA%20-%20BANDUNG.pdf'
AIRPORT_ARCHIVE='https://web.archive.org/web/20251206180718id_/'+AIRPORT_URL
WHOOSH_ARCHIVE='https://web.archive.org/web/20250131154742id_/'+WHOOSH_URL
SUNDAY_URL='https://kcic.co.id/kcic-siaran-pers/pastikan-standar-keselamatan-tetap-maksimal-kcic-sesuaikan-jadwal-whoosh-di-hari-minggu-menjadi-mulai-08-00/'
PDF_PINS={'airport-september-2025.pdf':'1456e5726d345ea3e550a7343e3b38fd67d45128cb448cac91b49739e1942c38',
          'whoosh-2025.pdf':'0f411bc301d2c2642eada213b09c3e7c680d8d78e975587af57602779fe0f366'}
SOURCE=ROOT/'data/reference/jakarta/airport-whoosh-timetables-2025.json.gz'
GEOMETRY=ROOT/'data/reference/jakarta/airport-whoosh-osm-2026-10-20.json.gz'
SOURCE_SHA256='b728a6edb5797c9dee305c4f114c5a01fd54cd4267f544bff12b5ea65ddb8d64'
GEOMETRY_SHA256='fe75d1314d652d8aba59ac23481576f04635de5145995374396912761ffd9640'
FIRST=date(2025,12,15)
AIRPORT_CODES=['MRI','BNC','DU','RWB','BTC','BST']
WHOOSH_CODES=['HLM','KRW','PDL','TGR']
NAMES={'MRI':'Manggarai','BNC':'BNI City','DU':'Duri','RWB':'Rawa Buaya','BTC':'Batu Ceper','BST':'Soekarno-Hatta Airport',
       'HLM':'Halim (Whoosh)','KRW':'Karawang (Whoosh)','PDL':'Padalarang (Whoosh)','TGR':'Tegalluar Summarecon'}
NOTE=('Airport rail: September 2025 timetable matched by weekday, retaining its dated cancellations. '
      'Whoosh: 2025 passenger timetable, including the published Sunday maintenance schedule. '
      'Conditional extras, depot runs and the Bandung feeder are excluded.')


def read(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def airport_source_day(display_day):
    if not FIRST<=display_day<FIRST+timedelta(days=7):raise ValueError('Airport calendar extension needs a source audit')
    return date(2025,9,15)+(display_day-FIRST)


def parse_airport_table(rows,codes):
    trips=[]
    for row in rows:
        if len(row)<12 or not re.fullmatch(r'\d+',row[1] or ''):continue
        if not re.fullmatch(r'\d+[A-Z]?',row[2] or '') or not re.fullmatch(r'\d+[A-Z]?',row[3] or ''):
            raise ValueError('Invalid airport train numbers')
        clocks=[(v or '').strip() for v in row[5:11]]
        if any(not re.fullmatch(r'\d{2}:\d{2}',v) for v in clocks):raise ValueError('Missing airport station clock')
        times=extended_times(clocks)
        if any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Backwards airport journey')
        note=(row[11] or '').strip();excluded=[]
        if note:
            match=re.fullmatch(r'Tidak Berjalan tanggal\s*([\d,\s]+)September 2025',note)
            if not match:raise ValueError('Unknown airport calendar notice: '+note)
            excluded=[str(date(2025,9,int(n))) for n in re.findall(r'\d+',match[1])]
        trips.append({'kind':'airport','number':row[2],'published_numbers':[row[2],row[3]],
            'direction':'airport-out' if codes[0]=='MRI' else 'airport-in','calendar':'airport',
            'calls':[[c,t,t] for c,t in zip(codes,times)],'excluded_dates':excluded,'note':note})
    return trips


def parse_whoosh_table(table,number,calendar):
    if table[0][:2]!=['No','Stasiun'] or len(table)!=6:raise ValueError('Unexpected Whoosh table layout')
    lookup={'Halim':'HLM','Karawang':'KRW','Padalarang':'PDL','Tegalluar':'TGR'}
    calls=[];passes=[]
    def clock(value):
        if not re.fullmatch(r'\d{2}\.\d{2}\.\d{2}',value):raise ValueError('Invalid Whoosh clock: '+value)
        h,m,s=map(int,value.split('.'))
        if h>=24 or m>=60 or s>=60:raise ValueError('Invalid Whoosh clock')
        return h*3600+m*60+s
    for row in table[2:]:
        code=lookup[row[1]];arrival,departure=row[2:4]
        if arrival=='Ls':
            passes.append([code,clock(departure)]);continue
        if arrival=='-':arrival=departure
        if departure=='-':departure=arrival
        calls.append([code,clock(arrival),clock(departure)])
    flat=[v for c,a,d in calls for v in (a,d)]
    if len(calls)<3 or any(b<a for a,b in zip(flat,flat[1:])):raise ValueError('Invalid Whoosh event sequence')
    return {'kind':'whoosh','number':number,'calendar':calendar,
        'direction':'whoosh-east' if calls[0][0]=='HLM' else 'whoosh-west','calls':calls,'pass_throughs':passes}


def extract_pdfs(cache):
    import pdfplumber
    for name,pin in PDF_PINS.items():
        if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=pin:raise ValueError('Official PDF differs: '+name)
    trips=[]
    with pdfplumber.open(cache/'airport-september-2025.pdf') as document:
        if len(document.pages)!=2:raise ValueError('Unexpected airport PDF edition')
        for index,page in enumerate(document.pages):
            tables=page.extract_tables()
            if len(tables)!=1:raise ValueError('Unexpected airport table count')
            trips.extend(parse_airport_table(tables[0],AIRPORT_CODES if index==0 else list(reversed(AIRPORT_CODES))))
    if sum(t['kind']=='airport' for t in trips)!=70:raise ValueError('Unexpected airport departure count')
    with pdfplumber.open(cache/'whoosh-2025.pdf') as document:
        if len(document.pages)!=62:raise ValueError('Unexpected government timetable edition')
        for calendar,pages in [('regular',range(13,24)),('sunday',range(38,49))]:
            for index in pages:
                page=document.pages[index];numbers=re.findall(r'WHOOSH:\s*(G\d+F?)\s+Lintas',page.extract_text())
                tables=page.extract_tables()
                if len(numbers)!=len(tables):raise ValueError('Whoosh header/table alignment changed')
                for number,table in zip(numbers,tables):
                    if not number.endswith('F'):
                        trips.append({**parse_whoosh_table(table,number,calendar),'page':index+1})
    for calendar,expected in [('regular',62),('sunday',56)]:
        rows=[t for t in trips if t['calendar']==calendar]
        if len(rows)!=expected or len({t['number'] for t in rows})!=expected:raise ValueError('Unexpected Whoosh scenario count')
    save({'metadata':{'airport_source_url':AIRPORT_URL,'airport_archive':AIRPORT_ARCHIVE,
        'airport_source_week':['2025-09-15','2025-09-21'],'whoosh_source_url':WHOOSH_URL,
        'whoosh_archive':WHOOSH_ARCHIVE,'whoosh_valid_from':'2025-02-01','sunday_rule_url':SUNDAY_URL,
        'sunday_rule_published':'2025-10-10','pdf_sha256':PDF_PINS,'note':NOTE},'trips':trips},SOURCE)
    print('source',hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE.stat().st_size,'trips',len(trips),flush=True)


def prepare_geometry(cache):
    from scripts.prepare_switzerland_geometry import compact_ways
    aliases={'Manggarai':'MRI','BNI City':'BNC','Duri':'DU','Rawa Buaya':'RWB','Batu Ceper':'BTC','Bandara Soekarno 2':'BST',
             'Halim':'HLM','Karawang':'KRW','Padalarang':'PDL','Tegalluar Summarecon':'TGR'}
    directions={}
    specs=[('airport-in','airport',17675694,list(reversed(AIRPORT_CODES))),('airport-out','airport',17675695,AIRPORT_CODES),
           ('whoosh-west','whoosh',12150229,list(reversed(WHOOSH_CODES))),('whoosh-east','whoosh',12150230,WHOOSH_CODES)]
    for direction,kind,identifier,expected in specs:
        path=cache/f'{kind}-{identifier}.osm';root=ET.fromstring(path.read_bytes())
        node_elements={e.get('id'):e for e in root.findall('node')}
        nodes={key:[float(e.get('lon')),float(e.get('lat'))] for key,e in node_elements.items()}
        ways={e.get('id'):{'nodes':[n.get('ref') for n in e.findall('nd')],
              'gauge':next((t.get('v') for t in e.findall('tag') if t.get('k')=='gauge'),'')} for e in root.findall('way')
              if any(t.get('k')=='railway' and t.get('v')=='rail' for t in e.findall('tag'))}
        relation=next(e for e in root.findall('relation') if e.get('id')==str(identifier));stations={}
        for member in relation.findall('member'):
            if member.get('type')!='node' or not member.get('role','').startswith('stop'):continue
            key=member.get('ref');tags={t.get('k'):t.get('v') for t in node_elements[key].findall('tag')}
            code=aliases.get(tags.get('name'))
            if code not in expected:continue # e.g. today's Sudirman stop is not in the September 2025 PDF.
            if code in stations:raise ValueError('Duplicate route stop')
            stations[code]={'name':NAMES[code],'coordinates':nodes[key],'osm_id':key}
        if list(stations)!=expected:raise ValueError('Unexpected native route station sequence: '+direction)
        directions[direction]={'stations':stations,'ways':compact_ways(ways,nodes),
            'source_url':f'https://api.openstreetmap.org/api/0.6/relation/{identifier}/full','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    save({'metadata':{'source':'© OpenStreetMap contributors','source_date':'2026-10-20','license':'ODbL 1.0',
          'license_url':'https://opendatacommons.org/licenses/odbl/1-0/'},'directions':directions},GEOMETRY)
    print('geometry',hashlib.sha256(GEOMETRY.read_bytes()).hexdigest(),GEOMETRY.stat().st_size,flush=True)


def build():
    from dashboard.replay import cumulative_distances
    from scripts.compact_transit import compact_reference
    from scripts.prepare_france_replay import FranceRailGraph
    for path,pin in [(SOURCE,SOURCE_SHA256),(GEOMETRY,GEOMETRY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:raise ValueError('Intercity source changed: '+str(path))
    source,geo=read(SOURCE),read(GEOMETRY);graphs={d:FranceRailGraph(g['ways']) for d,g in geo['directions'].items()}
    result={'stations':[],'patterns':{},'paths':{},'days':{str(FIRST+timedelta(days=i)):[] for i in range(7)},'train_numbers':{}}
    ids={}
    for trip in source['trips']:
        direction=trip['direction'];stations=geo['directions'][direction]['stations'];calls=trip['calls'];start=calls[0][1];legs=[]
        for c,a,d in calls:
            if (direction,c) not in ids:
                ids[direction,c]=len(result['stations']);p=stations[c]['coordinates']
                result['stations'].append({'name':NAMES[c],'lon':p[0],'lat':p[1],'mode':'train'})
        for (a,_,_),(b,_,_) in zip(calls,calls[1:]):
            key=direction+'-'+a+'-'+b
            if key not in result['paths']:
                points=[stations[c]['coordinates'] for c in [a,b]];curve=graphs[direction].leg(*points)
                if not curve or cumulative_distances(curve)[-1]>3*cumulative_distances(points)[-1]:raise ValueError('Unresolved/implausible track leg: '+key)
                result['paths'][key]={'coordinates':curve,'distances':cumulative_distances(curve),'quality':'track'}
            legs.append(key)
        airport=trip['kind']=='airport'
        pattern={'mode':'train','operator':'KAI Commuter' if airport else 'KCIC / Whoosh',
            'line':'Soekarno-Hatta Airport Rail' if airport else 'Whoosh · Jakarta–Bandung','route_id':'airport' if airport else 'whoosh',
            'color':'#262262' if airport else '#8C0023','direction':'To '+NAMES[calls[-1][0]],
            'origin':NAMES[calls[0][0]],'destination':NAMES[calls[-1][0]],
            'stops':[[ids[direction,c],a-start,d-start] for c,a,d in calls],'legs':legs}
        key=hashlib.sha256(json.dumps(pattern,sort_keys=True).encode()).hexdigest()[:20];result['patterns'][key]=pattern
        for day,rows in result['days'].items():
            display=date.fromisoformat(day)
            if airport:
                if str(airport_source_day(display)) in trip['excluded_dates']:continue
            elif trip['calendar']!=('sunday' if display.weekday()==6 else 'regular'):continue
            identifier=trip['kind']+'-'+trip['calendar']+'-'+trip['number'];rows.append([key,identifier,start]);result['train_numbers'][identifier]=trip['number']
    for rows in result['days'].values():rows.sort(key=lambda r:(r[2],r[1]))
    result['metadata']={'start_date':str(FIRST),'end_date':'2025-12-21','timezone':'Asia/Jakarta',
        'source':'KAI Commuter September 2025 airport timetable; DJKA 2025 Whoosh regular/Sunday passenger timetables',
        'source_url':WHOOSH_URL,'license':'Published government/operator timetables; source attribution retained',
        'license_url':WHOOSH_URL,
        'sources':[{'source_url':AIRPORT_URL,'archive_url':AIRPORT_ARCHIVE,'source_date':'2025-09-01','sha256':PDF_PINS['airport-september-2025.pdf']},
                   {'source_url':WHOOSH_URL,'archive_url':WHOOSH_ARCHIVE,'published':'2025-01-22','valid_from':'2025-02-01','sha256':PDF_PINS['whoosh-2025.pdf']},
                   {'source_url':SUNDAY_URL,'published':'2025-10-10'}],
        'attribution':'Airport timetable: PT Kereta Commuter Indonesia / KAI Commuter, September 2025 publication. Whoosh: Directorate General of Railways, KP-DJKA 2/2025, effective 1 February 2025; PT KCIC Sunday operating rule, 10 October 2025. SunTrain table conversion excludes non-passenger/conditional runs and retains original events. Railway geometry © OpenStreetMap contributors, ODbL 1.0.',
        'replay_note':NOTE,'omitted_trips':{},'unresolved_geometry_patterns':{},'unresolved_geometry_trips':{},
        'geometry_source':'© OpenStreetMap contributors; native airport railway and Whoosh high-speed tracks',
        'geometry_source_url':'https://www.openstreetmap.org/copyright','geometry_license':'ODbL 1.0',
        'geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/','geometry_sha256':GEOMETRY_SHA256,
        'operator_periods':{'Airport rail':'15–21 September 2025 matched to display weekdays',
                           'Whoosh':'2025 regular timetable, with Sunday maintenance schedule confirmed 10 October 2025'}}
    return compact_reference(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract-pdf',action='store_true');parser.add_argument('--prepare-geometry',action='store_true')
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/jakarta/intercity');args=parser.parse_args()
    if args.extract_pdf:extract_pdfs(args.cache)
    elif args.prepare_geometry:prepare_geometry(args.cache)
    else:print({d:len(v) for d,v in build()['days'].items()})

"""Extract the Bandung feeder and YIA/Adi Soemarmo airport trains from GAPEKA 2025."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_java_replay import (save,digest,PDF_SHA256,SOURCE_URL,ARCHIVE_URL,HEADER,normalize_trip)
SOURCE=ROOT/'data/reference/java/connections-timetable-2025.json.gz'
SOURCE_SHA256='635502480e8eb8ec0849572987356552ad5d32cd851c8187ba6b9fd36e22e213'
SERVICES={
 'Ka Feeder':{'name':'Bandung–Padalarang Feeder','operator':'KAI','color':'#008577'},
 'Bandara YIA':{'name':'YIA Airport Rail','operator':'KAI Bandara / Railink','color':'#E95B0C'},
 'Bandara SMO':{'name':'Adi Soemarmo Airport Rail','operator':'KAI','color':'#174A8B'}}


def read_tables(document,indices):
    """Use ruled cells so multi-line airport names stay with their own clocks."""
    trips=[];current=None
    for index in indices:
        page=document.pages[index]
        headings=page.search(HEADER.pattern,regex=True)
        for table in page.find_tables():
            rows=table.extract()
            if not rows or rows[0]!=['No.','Stasiun dan Perhentian','Datang','Berangkat','Keterangan']:
                continue
            data=[row for row in rows[1:] if re.fullmatch(r'\d+',row[0] or '')]
            if not data:continue
            if data[0][0]=='1':
                before=[h for h in headings if h['bottom']<=table.bbox[1]+1]
                if not before:raise ValueError('Missing timetable heading before first station row')
                heading=max(before,key=lambda h:h['top']);number,name,origin,destination=heading['groups']
                if name not in SERVICES:raise ValueError('Unexpected train family: '+name)
                current={'number':number,'name':name,'origin':origin,'destination':destination,'page':index+1,'rows':[]}
                trips.append(current)
            if current is None:raise ValueError('Orphan timetable continuation')
            for row in data:
                if len(row)!=5:raise ValueError('Government table columns changed')
                name=' '.join((row[1] or '').split());match=re.fullmatch(r'(.+) \(([A-Z0-9]+)\)',name)
                if not match:raise ValueError('Missing station identity in government cell: '+name)
                current['rows'].append({'sequence':int(row[0]),'name':match[1],'code':match[2],
                    'events':' '.join((value or '').strip() for value in row[2:4]).strip(),'page':index+1})
        page.close()
    return trips


def extract(cache):
    import pdfplumber
    path=cache/'gapeka-java-2025.pdf'
    if digest(path)!=PDF_SHA256:raise ValueError('Government timetable PDF differs')
    with pdfplumber.open(path) as document:
        trips=read_tables(document,range(600,620))+read_tables(document,range(721,739))
        contents={}
        for index in list(range(53,61))+list(range(621,627)):
            page=document.pages[index]
            for line in (page.extract_text() or '').splitlines():
                m=re.match(r'^\d+ (\d+F?) KA .* ([A-Z]+)-([A-Z]+) (\d\d:\d\d:\d\d) (\d\d:\d\d:\d\d)(?: \d+)?$',line)
                if m:contents[m[1]]=m.groups()[1:]
            page.close()
    expected={str(n) for n in range(521,581)}|{str(n) for n in range(601,673)}
    expected-={'547','548'};expected|={'547F','548F'}
    if len(trips)!=132 or {t['number'] for t in trips}!=expected:raise ValueError('Missing/duplicated airport/feeder table')
    selected=[];omitted={}
    for trip in trips:
        item=normalize_trip(trip)
        if item['untimed_calls']:raise ValueError('Untimed passenger event: '+trip['number'])
        if trip['number'].endswith('F'):omitted[trip['number']]='Optional F service; activation dates unconfirmed';continue
        def clock(s):return f'{s//3600%24:02}:{s//60%60:02}:{s%60:02}'
        actual=(item['origin'],item['destination'],clock(item['calls'][0][2]),clock(item['calls'][-1][1]))
        if contents.get(trip['number'])!=actual:raise ValueError('Detailed times disagree with contents: '+trip['number'])
        item.update(SERVICES[trip['name']]);selected.append(item)
    counts=dict(Counter(t['name'] for t in selected))
    save({'metadata':{'source_url':SOURCE_URL,'archive_url':ARCHIVE_URL,'pdf_sha256':PDF_SHA256,
        'effective_from':'2025-02-01','extracted_tables':132,'omitted_trips':omitted,'daily_services':counts,
        'source_method':'Ruled government station-event cells, including wrapped airport names; detailed terminals/times reconciled against contents. Published arrivals/departures retained; Ls is a passing point.',
        'calendar_audit':'Regular government timetable effective 1 February 2025; selected replay 3–9 February. Optional 547F/548F excluded. No later Palur/Caruban additions inferred.'},
        'trips':selected},SOURCE)
    print('connections',len(selected),'counts',counts,'sha256',digest(SOURCE),'bytes',SOURCE.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/java')
    a=p.parse_args();extract(a.cache)

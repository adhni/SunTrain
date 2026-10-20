"""Prepare Merak, Bandung, Yogyakarta/Prameks and East Java regional rail."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_java_replay import (save,read,digest,PDF_SHA256,SOURCE_URL,ARCHIVE_URL,
    parse_pages,normalize_trip,prepare as prepare_reference)
SOURCE=ROOT/'data/reference/java/regional-timetable-2025.json.gz'
OUTPUT=ROOT/'data/reference/java/regional-2025-02-03.json.gz'
SOURCE_SHA256='71dd1ac48425eb6a9ab82d9bf7193cc062307b3a1797347b8b2b9152926521fb'
OPERATOR_ROOT='https://www.commuterline.id/files/download/documents/'
PINS={
 'merak':('ca594e81c59281b2e4e4ee7542f5a512e613c292205707115d40c7bfc9c4efbb','20251206175708','Commuter%20Line%20Merak%20-Mulai%201%20Februari%202025-.pdf'),
 'bandung':('335635a2240a51beab1354b0611e26d70ade64712806f1f229fab92c646ab2ad','20251207034821','Commuter%20Line%20Wilayah%202%20Bandung%20-%20Mulai%201%20Februari%202025.pdf'),
 'surabaya':('0ed22bed8f2fc069db590b7072d6a51ecac7472e58019a1ade4e745dc1960fb6','20251206183020','Commuter%20Line%20Wilayah%208%20Surabaya%20-Mulai%201%20Februari%202025-%20-1-.pdf')}
NOTE=('Java regional trains: Merak; Bandung/Garut, Walahar/Jatiluhur and Siliwangi; Yogyakarta–Solo KRL/Prameks; '
      'East Java Dhoho, Penataran, Supas, Jenggala, Arjonegoro, Blorasura and Pandanwangi. '
      'Official February 2025 government and operator timetables. Published number pairs are one through journey. '
      'Operator tables provide a single station event unless both arrival/departure are printed. '
      'Optional F trains are excluded. Positions follow inferred railway paths; no passenger loads.')
BANDUNG_GARUT='PWK CA SUT PLD CD RH MSI SKT CLE PDL GK CMI CMD CIR BD CTH KAC GDB CMK RCK HRP CCL NG LL KRA LO CB PSJ WNR GRT'.split()
STATION_FIXES={'SURABAYA PASAR TURI':'SBI','SURABAYA PASARTURI':'SBI','WONOKROMO':'WO','MOJOKERTO':'MR'}


def clock(value):
    match=re.fullmatch(r'(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?',value.strip())
    if not match:raise ValueError('Unexpected operator station event: '+repr(value))
    h,m,s=int(match[1]),int(match[2]),int(match[3] or 0)
    if h>=24 or m>=60 or s>=60:raise ValueError('Invalid operator time')
    return h*3600+m*60+s


def number(value):
    parts=re.findall(r'\d+F?',value or '')
    if not parts or not re.fullmatch(r'[\dF\s-]+',value or ''):raise ValueError('Unexpected operator train identifier')
    return '-'.join(parts)


def station(text):
    text=' '.join((text or '').split());m=re.search(r'\(([A-Z]+)\)',text)
    if not m:raise ValueError('Missing operator station code: '+text)
    name=text[:m.start()].strip()
    return STATION_FIXES.get(name,m[1]),name.title()


def operator_trip(identifier,line,events,group,page):
    calls=[];previous=None;offset=0;names={}
    for code,name,value in events:
        if value in {'','-','–','LS','Ls','ls'}:continue
        values=[clock(v) for v in value.split()]
        for seconds in values:
            if previous is not None and seconds+offset<previous:
                if previous%86400<21*3600 or seconds>3*3600:raise ValueError('Backwards operator journey: '+identifier)
                offset+=86400
            seconds+=offset;previous=seconds
            # Adjacent duplicate columns explicitly print arrival/departure.
            if calls and calls[-1][0]==code:calls[-1][2]=seconds
            else:calls.append([code,seconds,seconds])
        names[code]=name
    if len(calls)<2:raise ValueError('Incomplete operator journey: '+identifier)
    calls[0][1]=calls[0][2];calls[-1][2]=calls[-1][1]
    return {'number':number(identifier),'name':' '.join(line.split()),'origin':calls[0][0],'destination':calls[-1][0],
        'calls':calls,'route':[[c,a] for c,a,d in calls],'stations':names,'untimed_calls':[],
        'group':group,'source_kind':'operator','page':page}


def horizontal(table,start,end,codes,line,group,page,names):
    result=[]
    for row in table[start:end]:
        if not re.fullmatch(r'\d+',row[0] or ''):continue
        if len(row)<4+len(codes):raise ValueError('Operator table lost columns')
        for note in row[4+len(codes):]:
            if note and not note.lower().startswith('via '):raise ValueError('Unrecognised operator calendar note: '+note)
        result.append(operator_trip(row[1],line or row[2],[(c,names[c],(v or '').strip()) for c,v in zip(codes,row[4:])],group,page))
    return result


def vertical(table,header,begin,end,line,group,page):
    result=[]
    for col,value in enumerate(table[header][2:],2):
        if not value:continue
        events=[]
        for row in table[begin:end]:
            if not re.fullmatch(r'\d+',row[0] or ''):continue
            code,name=station(row[1]);events.append((code,name,(row[col] or '').strip()))
        result.append(operator_trip(value,line,events,group,page))
    return result


def extract(cache):
    import pdfplumber
    regional=cache/'regional'
    if digest(cache/'gapeka-java-2025.pdf')!=PDF_SHA256:raise ValueError('Government PDF differs')
    pagefile=regional/'visual-pages.json'
    if pagefile.exists():pages=json.loads(pagefile.read_text())
    else:
        pages=[]
        with pdfplumber.open(cache/'gapeka-java-2025.pdf') as doc:
            for index in range(621,754):
                page=doc.pages[index];pages.append([index+1,page.extract_text() or '']);page.close()
        pagefile.write_text(json.dumps(pages))
    government=parse_pages(pages,lambda n:300<int(n.rstrip('F'))<800)
    if len(government)!=276:raise ValueError('Regional government section count changed')
    names={r['code']:r['name'] for t in government for r in t['rows']}
    # Existing intercity station names disambiguate operator header typos.
    for t in read(ROOT/'data/reference/java/intercity-timetable-2025.json.gz')['trips']:names.update(t['stations'])
    tables={};sources=[]
    for key,(pin,stamp,filename) in PINS.items():
        path=regional/(key+'-2025.pdf')
        if digest(path)!=pin:raise ValueError('Operator PDF differs: '+key)
        with pdfplumber.open(path) as doc:tables[key]=[page.extract_tables()[0] for page in doc.pages]
        sources.append({'source_url':OPERATOR_ROOT+filename,'archive_url':'https://web.archive.org/web/'+stamp+'id_/'+OPERATOR_ROOT+filename,
            'source_date':'2025-02-01','sha256':pin})
    selected=[];omitted={}
    wanted={'Commuter Line Merak':'Merak','Commuter Line Walahar':'Bandung','Commuter Line Jatiluhur':'Bandung','Siliwangi':'Bandung',
        'Commuter Line Yogyakarta':'Yogyakarta / Solo','Commuter Line Prameks Kutoarjo':'Yogyakarta / Solo','Pandanwangi':'East Java'}
    for t in government:
        if t['name'] not in wanted:continue
        if t['number'].endswith('F'):omitted[t['number']]='Optional F service; activation dates unconfirmed';continue
        item=normalize_trip(t)
        if item['untimed_calls']:raise ValueError('Unexpected missing government events: '+t['number'])
        item.update(group=wanted[t['name']],source_kind='government');selected.append(item)
    # Bandung operator cells are complete where government tables say Berh Sb.
    # Pinned Garut headers have interleaved glyphs; manifest columns follow the
    # printed station order, checked against government terminal/route sequences.
    tab=tables['bandung'][1]
    selected+=horizontal(tab,3,6,BANDUNG_GARUT,None,'Bandung',2,names)
    selected+=horizontal(tab,10,14,list(reversed(BANDUNG_GARUT)),None,'Bandung',2,names)
    tab=tables['bandung'][2]
    selected+=vertical(tab,2,3,16,'Commuter Line Bandung Raya','Bandung',3)
    selected+=vertical(tab,19,20,len(tab),'Commuter Line Bandung Raya','Bandung',3)
    # Public East Java tables describe whole through journeys, including loops.
    # Do not also import each separately numbered government segment.
    for page,line in [(1,'Commuter Line Dhoho'),(2,'Commuter Line Penataran')]:
        tab=tables['surabaya'][page-1]
        selected+=vertical(tab,2,5,len(tab),line,'East Java',page)
    tab=tables['surabaya'][2];supas='SB SGU WO WR GDG SDA TGA PR BG PS'.split()
    selected+=horizontal(tab,3,7,supas,None,'East Java',3,names)
    selected+=horizontal(tab,11,len(tab),list(reversed(supas)),None,'East Java',3,names)
    tab=tables['surabaya'][3];jenggala='BBT PC LMG DD CME BNW IDO KDA TES SBI SGU WO WR GDG SDA TLN SPJ KRN TRK MR'.split()
    selected+=horizontal(tab,3,10,jenggala,None,'East Java',4,names)
    reverse='MR TRK KRN SPJ TLN SDA GDG WR WO SGU SBI TES KDA IDO BNW CME DD LMG PC BBT'.split()
    selected+=horizontal(tab,14,len(tab),reverse,None,'East Java',4,names)
    tab=tables['surabaya'][4];arjonegoro='BJ KPS SRJ BWO BBT PC LMG DD CME BNW KDA TES SBI SBI SGU WO WR GDG SDA'.split()
    selected+=horizontal(tab,4,7,arjonegoro,None,'East Java',5,names)
    selected+=horizontal(tab,12,14,list(reversed(arjonegoro)),None,'East Java',5,names)
    blorasura='SBI TES KDA BNW CME DD LMG PC BBT BWO SRJ KPS BJ CU'.split()
    selected+=horizontal(tab,18,20,blorasura,None,'East Java',5,names)
    selected+=horizontal(tab,24,len(tab),list(reversed(blorasura)),None,'East Java',5,names)
    identifiers=[t['number'] for t in selected]
    if len(identifiers)!=len(set(identifiers)):raise ValueError('Duplicate regional trip identifiers')
    numbers=[n for value in identifiers for n in value.split('-')]
    if len(numbers)!=len(set(numbers)):raise ValueError('A through journey duplicates its source number section')
    brands={t['name'].lower().replace(' ','') for t in selected}
    expected={t['number'] for t in government if t['name'].lower().replace(' ','') in brands and not t['number'].endswith('F')}
    if set(numbers)!=expected:raise ValueError('Regional coverage disagrees with the government number sections')
    groups=dict(Counter(t['group'] for t in selected))
    save({'metadata':{'source_url':SOURCE_URL,'archive_url':ARCHIVE_URL,'pdf_sha256':PDF_SHA256,'effective_from':'2025-02-01',
        'omitted_trips':omitted,'groups':groups,'operator_sources':sources,
        'operator_pdf_corrections':{'Wonokromo':'WO (printed WR on Jenggala page 4)','Mojokerto':'MR (printed SDA on Jenggala page 4)'},
        'source_method':'Government timed tables for Merak/Walahar/Jatiluhur/Siliwangi/Yogyakarta/Prameks/Pandanwangi; complete operator tables for Bandung/Garut and East Java commuter trains. No blended stop-time interpolation.',
        'calendar_audit':'First full week after 1 February 2025 effective date; regular government services only. F services excluded; operator pages have no dated weekday/weekend restriction. No Jakarta KRL or airport/feeder trains duplicated.'},
        'trips':selected},SOURCE)
    print('source trips',len(selected),'groups',groups,'sha256',digest(SOURCE),'bytes',SOURCE.stat().st_size,flush=True)


def prepare():
    prepare_reference(OUTPUT,source_path=SOURCE,source_pin=SOURCE_SHA256,mode='regional_rail',operator='KAI Commuter',
        namespace='java-rv',note=NOTE,source_name='DJKA / KAI Commuter · Java regional passenger timetables, 1 February 2025')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--extract-pdf',action='store_true');p.add_argument('--cache',type=Path,default=ROOT/'.cache/java')
    a=p.parse_args()
    if a.extract_pdf:extract(a.cache)
    else:prepare()

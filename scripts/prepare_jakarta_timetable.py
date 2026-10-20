"""Extract the pinned official KRL PDF using its actual station-column positions."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
PDF_SHA256='dc53b5b96b19afcf6ed4c7c86ab7ac9655810b0d27e5879b1183fb2ea9666901'
SOURCE_URL='https://commuterline.id/files/download/documents/Jadwal%20Commuter%20Line%20Jabodetabek%20-%20Update%2013%20Desember%202025.pdf'
OUTPUT=ROOT/'data/reference/jakarta/timetable-2025-12-13.json.gz'
NAMES=dict(item.split(':',1) for item in '''NMO:Nambo|CBN:Cibinong|PDRG:Pondok Rajeg|BOO:Bogor|CLT:Cilebut|BJD:Bojonggede|CTA:Citayam|DP:Depok|DPB:Depok Baru|POC:Pondok Cina|UI:Universitas Indonesia|UP:Universitas Pancasila|LNA:Lenteng Agung|TNT:Tanjung Barat|PSM:Pasar Minggu|PSMB:Pasar Minggu Baru|DRN:Duren Kalibata|CW:Cawang|TEB:Tebet|MRI:Manggarai|CKI:Cikini|GDD:Gondangdia|GMR:Gambir|JUA:Juanda|SW:Sawah Besar|MGB:Mangga Besar|JAY:Jayakarta|JAKK:Jakarta Kota|CKR:Cikarang|TLM:Metland Telagamurni|CIT:Cibitung|TB:Tambun|BKST:Bekasi Timur|BKS:Bekasi|KRI:Kranji|CUK:Cakung|KLDB:Klender Baru|BUA:Buaran|KLD:Klender|JNG:Jatinegara|POK:Pondok Jati|KMT:Kramat|GST:Gang Sentiong|PSE:Pasar Senen|KMO:Kemayoran|RJW:Rajawali|MTR:Matraman|SUD:Sudirman|SUDB:BNI City|KAT:Karet|THB:Tanah Abang|DU:Duri|AK:Angke|KPB:Kampung Bandan|RK:Rangkasbitung|CTR:Citeras|MJ:Maja|CKY:Cikoya|TGS:Tigaraksa|TEJ:Tenjo|DAR:Daru|CJT:Cilejit|PRP:Parungpanjang|CC:Cicayur|CSK:Cisauk|SRP:Serpong|RU:Rawa Buntu|SDM:Sudimara|JMU:Jurangmangu|PDJ:Pondok Ranji|KBY:Kebayoran|PLM:Palmerah|TNG:Tangerang|THI:Tanah Tinggi|BPR:Batu Ceper|PI:Poris|KDS:Kalideres|RW:Rawa Buaya|BOI:Bojong Indah|TKO:Taman Kota|PSG:Pesing|GRG:Grogol|AC:Ancol|TPK:Tanjung Priuk'''.split('|'))
TIME=re.compile(r'\b\d{2}:\d{2}\b')
WEEKDAYS='Sabtu/Minggu/Libur Nasional Batal'


def save(value,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as f:
        f.write(json.dumps(value,separators=(',',':'),allow_nan=False).encode())


def extended_times(values):
    result=[];offset=0
    for value in values:
        h,m=map(int,value.split(':'))
        if m>=60 or h>29:raise ValueError('Invalid clock')
        seconds=h*3600+m*60+offset
        if result and seconds<result[-1]:
            if result[-1]-seconds<12*3600:raise ValueError('Backwards station times')
            offset+=86400;seconds+=86400
        result.append(seconds)
    if result and result[-1]-result[0]>6*3600:raise ValueError('Implausible KRL journey duration')
    return result


def parse_table(rows):
    """Read actual grid cells; empty branch/pass-through cells keep their column."""
    headers=[(i,[(j,str(cell).strip()) for j,cell in enumerate(row) if str(cell).strip() in NAMES])
             for i,row in enumerate(rows)]
    headers=[(i,cols) for i,cols in headers if len(cols)>=4]
    if len(headers)!=1:raise ValueError('Expected one station-header row')
    header,columns=headers[0];result=[]
    for row in rows[header+1:]:
        if not row or not str(row[0] or '').strip().isdigit():continue
        index=int(row[0]);numbers=' '.join((row[1] or '').split());relation=' '.join((row[2] or '').split())
        if not re.fullmatch(r'\d+[A-Z]*(?:\s*-\s*\d+[A-Z]*)?',numbers):
            raise ValueError('Unrecognised primary/continuation train number: '+numbers)
        calls=[]
        for j,code in columns:
            value=(row[j] or '').strip()
            if value in {'','Ls','LS'}:continue
            if not TIME.fullmatch(value):raise ValueError('Unrecognised station cell: '+repr(value))
            calls.append([code,value])
        note=' '.join(' '.join((cell or '').split()) for cell in row[columns[-1][0]+1:]).strip()
        if not calls:raise ValueError('Timetable row has no calls')
        if 'Mulai melayani pengguna dari St. Sudirman' in note:
            calls=calls[next(i for i,c in enumerate(calls) if c[0]=='SUD'):]
        elif 'Mulai melayani pengguna dari St. Matraman' in note:
            calls=calls[next(i for i,c in enumerate(calls) if c[0]=='MTR'):]
        times=extended_times([time for code,time in calls])
        if len(calls)<2:raise ValueError('Fewer than two passenger calls')
        result.append({'row':index,'number':re.split(r'\s*-\s*',numbers)[0],
            'published_numbers':numbers,'relation':relation,'note':note,'weekdays_only':WEEKDAYS in note,'valid_through':'2025-12-31' if 'Beroperasi s/d 31 Desember' in note else None,
            'calls':[[code,time] for (code,_),time in zip(calls,times)]})
    return result


def extract(pdf,output=OUTPUT):
    import pdfplumber
    if hashlib.sha256(pdf.read_bytes()).hexdigest()!=PDF_SHA256:raise ValueError('PDF differs from the validated December edition')
    reader=pdfplumber.open(pdf)
    if len(reader.pages)!=13:raise ValueError('Unexpected KRL PDF page count')
    trips=[];counts=[];omitted=[]
    for page_no,page in enumerate(reader.pages,1):
        rows=[]
        for table in page.extract_tables():
            # Some editions place both Priok directions side by side. Separate
            # their metadata columns before extracting the two station grids.
            starts=next(([i for i,c in enumerate(row) if str(c or '').replace('.','').strip()=='NO']
                         for row in table if any(str(c or '').replace('.','').strip()=='NO' for c in row)),[0])
            for i,start in enumerate(starts):
                end=starts[i+1] if i+1<len(starts) else len(table[0])
                rows.extend(parse_table([r[start:end] for r in table]))
        for row in rows:
            row['page']=page_no
            row['line']='Nambo' if page_no<=4 and any(c=='NMO' for c,t in row['calls']) else 'Bogor' if page_no<=4 else 'Cikarang' if page_no<=8 else 'Rangkasbitung' if page_no<=10 else 'Tangerang' if page_no<=12 else 'Tanjung Priok'
        counts.append(len(rows))
        for row in rows:
            if TIME.search(row['note']):
                omitted.append({'page':page_no,'row':row['row'],'number':row['number'],'reason':'An extra clock value appears in the remarks cell; station alignment is ambiguous'})
            else:trips.append(row)
    numbers=[t['number'] for t in trips]
    if len(numbers)!=len(set(numbers)):raise ValueError('Duplicate primary train numbers in PDF')
    result={'metadata':{'source':'KAI Commuter official published KRL timetable, 13 December 2025 edition',
        'source_url':SOURCE_URL,'sha256':PDF_SHA256,'published':'2025-12-13',
        'page_rows':counts,'omitted_rows':omitted,'note':'Column-preserving extraction; continuation numbers describe separately published segments, not invented extra services. Single station times do not distinguish arrival and departure.'},
        'trips':trips}
    reader.close();save(result,output);print('page rows',counts,'trips',len(trips),'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();extract(a.pdf,a.output)

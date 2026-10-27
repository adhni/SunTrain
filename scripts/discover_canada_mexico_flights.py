"""Published country routes for a bounded Canada/Mexico domestic and cross-border expansion."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.discover_arabia_jordan_flights import main
COUNTRIES={
 'canada':'YYZ YVR YUL YYC YEG YOW YWG YHZ YYT YQB YTZ YLW YYJ YXE YQR'.split(),
 'mexico':'MEX CUN GDL MTY TIJ SJD PVR NLU BJX MID CUL HMO CUU OAX TLC'.split()}
CACHE=ROOT/'.cache/canada-mexico-flights-audit'

def select():
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        identities={}
        for a in csv.DictReader(stream):
            if a['iata_code'] and a['type']!='closed':identities.setdefault(a['iata_code'],set()).add(a['iso_country'])
    for slug in COUNTRIES:
        path=ROOT/f'data/sources/{slug}_flights_discovery.json';doc=json.loads(path.read_text())
        for row in doc['airport_maps']:
            published=row.get('published_destinations',row['destinations'])
            row['published_destinations']=published
            row['destinations']=[c for c in published if len(identities.get(c,set()))==1 and identities[c]<={'CA','MX','US'}]
        doc['supplemental_scope']='15 reviewed gateways per country; published domestic and Canada/US/Mexico directions. Other existing positive worldwide captures reused without new searches. Not an exact top-15 ranking or country-completeness claim.'
        path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    if '--select-only' not in sys.argv:main(COUNTRIES,CACHE)
    select()

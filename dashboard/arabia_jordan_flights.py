"""Standalone country flight views added alongside Saudi Arabia."""
import json
from pathlib import Path

COUNTRIES={
 'OM':dict(slug='oman',name='Oman',zone='Asia/Muscat',label='GST',clock='Oman time (UTC+4)',bounds=[[51,16],[60,27]],arc_anchor=56,scopes=True),
 'KW':dict(slug='kuwait',name='Kuwait',zone='Asia/Kuwait',label='AST',clock='Kuwait time (UTC+3)',bounds=[[46,28],[49,31]],arc_anchor=47.5,scopes=False),
 'BH':dict(slug='bahrain',name='Bahrain',zone='Asia/Bahrain',label='AST',clock='Bahrain time (UTC+3)',bounds=[[50.25,25.7],[50.9,26.5]],arc_anchor=50.55,scopes=False),
 'JO':dict(slug='jordan',name='Jordan',zone='Asia/Amman',label='AST',clock='Jordan time (UTC+3)',bounds=[[34.8,29],[39.5,33.5]],arc_anchor=37.2,scopes=True),
}
ROOT=Path(__file__).resolve().parents[1]

def profiles(countries=None):
    result={}
    for code,p in (countries or COUNTRIES).items():
        m=json.loads((ROOT/f"data/sources/{p['slug']}_flights_routes.json").read_text())
        result[code]={**{k:v for k,v in p.items() if k!='scopes'},'domestic':True,'standalone':True,'origin_local_day':True,
            'default_scope':'both' if p['scopes'] else 'international','flight_scopes':p['scopes'],
            'flight_country_filters':True,'regional_start_view':True,'max_duration':86400,
            'currency':'mixed','capture_currency':'USD','price_currencies':['USD','EUR','MYR'],
            'airport_countries':{a['code']:a['country'] for a in m['airports']},
            'airport_zones':{a['code']:a['timezone'] for a in m['airports']},'description':m['replay_note']}
    return result

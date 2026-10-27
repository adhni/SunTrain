"""Standalone Canadian and Mexican flight views with explicit airport clocks."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRIES={
 'CA':dict(slug='canada',name='Canada',bounds=[[-142,41],[-52,73]],arc_anchor=-98),
 'MX':dict(slug='mexico',name='Mexico',bounds=[[-118,14],[-86,33]],arc_anchor=-102)}

def profiles():
    result={}
    for code,p in COUNTRIES.items():
        m=json.loads((ROOT/f"data/sources/{p['slug']}_flights_routes.json").read_text())
        result[code]=dict(**p,zone='UTC',label='UTC',clock='UTC',domestic=True,standalone=True,origin_local_day=True,
            default_scope='both',flight_country_filters=True,regional_start_view=True,max_duration=86400,
            currency='mixed',capture_currency='USD',price_currencies=['USD','EUR','MYR'],
            airport_countries={a['code']:a['country'] for a in m['airports']},
            airport_zones={a['code']:a['timezone'] for a in m['airports']},
            airport_replay_zones={a['code']:a['replay_timezone'] for a in m['airports'] if a.get('replay_timezone')},
            description=m['replay_note'])
    return result

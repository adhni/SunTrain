"""A regional Pacific flight view; each island airport keeps its own IANA zone."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def profile():
    m=json.loads((ROOT/'data/sources/pacific_flights_routes.json').read_text())
    return dict(slug='pacific',name='Pacific Islands',zone='UTC',label='UTC',clock='UTC',
        bounds=[[128,-33],[252,33]],arc_anchor=180,max_duration=86400,
        domestic=True,standalone=True,origin_local_day=True,default_scope='both',flight_country_filters=True,regional_start_view=True,
        currency='mixed',capture_currency='USD',price_currencies=['USD','EUR','MYR'],
        airport_countries={a['code']:a['country'] for a in m['airports']},airport_zones={a['code']:a['timezone'] for a in m['airports']},description=m['replay_note'])

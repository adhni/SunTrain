"""Standalone Pakistan and Bangladesh flight profile definitions."""
from dashboard.arabia_jordan_flights import profiles as country_profiles
COUNTRIES={
 'PK':dict(slug='pakistan',name='Pakistan',zone='Asia/Karachi',label='PKT',clock='Pakistan time (UTC+5)',bounds=[[60,23],[78,37.5]],arc_anchor=69,scopes=True),
 'BD':dict(slug='bangladesh',name='Bangladesh',zone='Asia/Dhaka',label='BST',clock='Bangladesh time (UTC+6)',bounds=[[88,20.5],[93,26.8]],arc_anchor=90.5,scopes=True),
}
def profiles():return country_profiles(COUNTRIES)

import json
import re
from pathlib import Path

from dashboard.cities import CITIES
from dashboard.i18n import CATALOGUES, message


def test_catalogues_have_identical_nonempty_keys_and_parameters():
    assert CATALOGUES['en'].keys() == CATALOGUES['id'].keys()
    for key, source in CATALOGUES['en'].items():
        target = CATALOGUES['id'][key]
        assert source == key
        assert target.strip(), key
        assert set(re.findall(r'\{([^}]+)\}', source)) == set(re.findall(r'\{([^}]+)\}', target)), key


def test_every_enabled_city_has_an_indonesian_description():
    for settings in CITIES.values():
        source = settings['description']
        assert source in CATALOGUES['id']
        assert CATALOGUES['id'][source] != source
        assert message(source).to_plotly_json()['props']['data-l10n'] == source


def test_source_names_and_unknown_overrides_remain_unchanged():
    for name in ['Flinders Street', 'Tokyo', 'JR East', '<unknown source>']:
        assert message(name) == name
    assert message('38 places to explore').to_plotly_json()['props']['data-l10n'] == '38 places to explore'

"""Public explorer messages shared with the browser; source names stay untouched."""
import json
import re
from pathlib import Path
from dash import html

CATALOGUES = {code: json.loads((Path(__file__).parent / 'locales' / (code + '.json')).read_text()) for code in ('en', 'id')}
PATTERNS = [re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '(.+?)', re.escape(key)) + '$') for key in CATALOGUES['en'] if '{' in key]


def message(text):
    if isinstance(text, str) and (text in CATALOGUES['en'] or any(p.fullmatch(text) for p in PATTERNS)):
        return html.Span(text, **{'data-l10n': text})
    return text


def localize_layout(component):
    if not hasattr(component, 'children'):
        # Dash owns these labels; use tagged spans instead of modifying its DOM.
        options = getattr(component, 'options', None)
        if options and getattr(component, 'id', '') not in ('replay-city', 'replay-lines', 'replay-stations', 'replay-operators', 'home-place'):
            component.options = [{**o, 'label': message(o['label'].strip())} if isinstance(o, dict) and isinstance(o.get('label'), str) else o for o in options]
        return
    if getattr(component, 'id', None) == 'melbourne-analysis-body':
        return
    for attribute in ('title', 'aria-label'):
        value = getattr(component, attribute, None)
        if isinstance(value, str) and value in CATALOGUES['en']:
            setattr(component, 'data-l10n-' + attribute, value)
    children = component.children
    if isinstance(children, (list, tuple)):
        component.children = [message(c) if isinstance(c, str) else c for c in children]
        for child in component.children:
            if not isinstance(child, str):
                localize_layout(child)
    elif isinstance(children, str):
        if isinstance(component, html.Option) and children in CATALOGUES['en']:
            setattr(component, 'data-l10n', children)
            return
        if 'data-l10n' not in component.to_plotly_json()['props']:
            component.children = message(children)
    elif children is not None:
        localize_layout(children)

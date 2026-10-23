"""Shared native theme picker for the header and fullscreen replay toolbar."""
from dash import html


def theme_picker(control_id):
    return html.Label(className="theme-picker", children=[
        html.Span("Theme"),
        html.Select(id=control_id, className="theme-select", **{"data-theme-select": "true", "aria-label": "Theme"}, children=[
            html.Option(label, value=value) for value, label in (
                ("light", "Light"), ("dark", "Dark"), ("sunrise", "Sunrise"),
                ("blueprint", "Blueprint"), ("heritage", "Heritage"))
        ]),
    ])

"""Shared schedule overview shell; detailed passenger reports remain optional."""
import json

from dash import html

from dashboard.cities import CITIES


def build_city_overview():
    return html.Section(
        id="city-overview", className="city-overview", style={"display": "none"},
        **{"data-cities": json.dumps({key: value["name"] for key, value in CITIES.items()})},
        children=[
            html.H2("Melbourne overview", id="city-overview-title", className="section-title"),
            html.P(id="city-overview-context", className="section-note"),
            html.Div(id="city-overview-content", **{"aria-live": "polite"}),
        ],
    )


def group_passenger_reports(layout):
    """Keep the existing report components/IDs together under one disclosure."""
    order = (
        "analysis-dataset-note", "analysis-filters", "analysis-summary", "overview-navigation",
        "overview-panel", "lines-panel", "segments-panel", "network-panel",
        "analysis-data-actions", "raw-data-section",
    )
    reports = {}

    def extract(component):
        if not hasattr(component, "children"):
            return
        children = component.children
        if isinstance(children, (list, tuple)):
            kept = []
            for child in children:
                identifier = getattr(child, "id", None)
                if identifier in order:
                    reports[identifier] = child
                else:
                    extract(child)
                    kept.append(child)
            component.children = kept
        else:
            extract(children)
        if getattr(component, "id", None) == "main-content":
            component.children.extend([
                build_city_overview(),
                html.Section(id="melbourne-analysis", className="melbourne-analysis", style={"display": "none"}, children=[
                    html.Button("Melbourne train passenger analysis", id="melbourne-analysis-toggle",
                                className="raw-data-toggle", **{"aria-expanded": False, "aria-controls": "melbourne-analysis-body"}),
                    html.Div(id="melbourne-analysis-body", style={"display": "none"},
                             children=[reports[key] for key in order]),
                ]),
            ])

    extract(layout)

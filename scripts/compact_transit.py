"""Compact shared timetable topologies and select independent daily bundles."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


def compact_reference(reference, prefix="stops-"):
    if "stop_patterns" in reference:
        return reference
    topologies, ordered = {}, {}
    rows = sorted(reference["patterns"].items(), key=lambda item: (item[1].get("route_id") or item[1].get("line", ""), item[1]["operator"],
                  tuple(s[0] for s in item[1]["stops"]), tuple(v for s in item[1]["stops"] for v in s[1:])))
    for key, pattern in rows:
        topology = {"stations": [s[0] for s in pattern["stops"]], "legs": pattern.pop("legs")}
        identifier = prefix + hashlib.sha256(json.dumps(topology).encode()).hexdigest()[:20]
        topologies.setdefault(identifier, topology)
        pattern["stop_pattern"] = identifier
        pattern["times"] = [v for stop in pattern.pop("stops") for v in stop[1:]]
        ordered[key] = pattern
    reference["patterns"], reference["stop_patterns"] = ordered, topologies
    reference["metadata"]["schedule_encoding"] = "shared-stops-flat-times-v1"
    return reference


def save_reference(reference, output):
    """Write the shared representation atomically, preserving schedule IDs."""
    compact_reference(reference)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with temporary.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(json.dumps(reference, separators=(",", ":"), allow_nan=False).encode())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def daily_reference(reference, day):
    rows = reference["days"][day]
    patterns = {key: reference["patterns"][key] for key in sorted({r[0] for r in rows})}
    keys = {p["stop_pattern"] for p in patterns.values()}
    station_ids = sorted({s for key in keys for s in reference["stop_patterns"][key]["stations"]})
    remap = {old: new for new, old in enumerate(station_ids)}
    topologies = {key: {**reference["stop_patterns"][key],
        "stations": [remap[s] for s in reference["stop_patterns"][key]["stations"]]} for key in sorted(keys)}
    paths = {leg for topology in topologies.values() for leg in topology["legs"]}
    return {"metadata": {**reference["metadata"], "bundle_date": day},
        "stations": [reference["stations"][s] for s in station_ids], "patterns": patterns,
        "stop_patterns": topologies, "paths": {key: reference["paths"][key] for key in sorted(paths)}, "days": {day: rows}}


def merge_references(references, *, source_name, replay_note):
    """Combine compact feeds with namespaced IDs and remapped station indices."""
    result={'metadata':dict(references[0][1]['metadata']),'stations':[],'patterns':{},
            'stop_patterns':{},'paths':{},'days':{d:[] for d in references[0][1]['days']},'train_numbers':{}}
    for namespace,r in references:
        if set(r['days'])!=set(result['days']):raise ValueError('Feed dates differ')
        offset=len(result['stations']);result['stations'].extend(r['stations']);prefix=namespace+':'
        result['patterns'].update({prefix+k:{**p,'route_id':prefix+p['route_id'],
            'stop_pattern':prefix+p['stop_pattern']} for k,p in r['patterns'].items()})
        result['stop_patterns'].update({prefix+k:{'stations':[s+offset for s in p['stations']],
            'legs':[prefix+leg for leg in p['legs']]} for k,p in r['stop_patterns'].items()})
        result['paths'].update({prefix+k:p for k,p in r['paths'].items()})
        for day,rows in r['days'].items():
            result['days'][day].extend([[prefix+k,prefix+t,o] for k,t,o in rows])
        for rows in r['days'].values():
            for _,t,_ in rows:result['train_numbers'][prefix+t]=r.get('train_numbers',{}).get(t,t)
    schedules=[r['metadata'] for _,r in references]
    geometry_sources=[]
    for m in schedules[1:]:
        credit={k:m[k] for k in ['geometry_source','geometry_source_url','geometry_license','geometry_license_url']}
        if credit not in geometry_sources:geometry_sources.append(credit)
    result['metadata'].update(
        source=source_name,
        sources=[s for m in schedules for s in m['sources']],
        attribution=' '.join(m['attribution'] for m in schedules),
        additional_geometry_sources=geometry_sources,
        omitted_trips={namespace:r['metadata']['omitted_trips'] for namespace,r in references if r['metadata']['omitted_trips']},
        unresolved_geometry_patterns=dict(sum((Counter(m['unresolved_geometry_patterns']) for m in schedules),Counter())),
        unresolved_geometry_trips={namespace+':'+t:v for namespace,r in references for t,v in r['metadata']['unresolved_geometry_trips'].items()},
        replay_note=replay_note)
    for day,rows in result['days'].items():
        if len({(t,o) for _,t,o in rows})!=len(rows):raise ValueError('Duplicate occurrence IDs')
        rows.sort(key=lambda row:(row[2],row[1]))
    result['metadata']['daily_services']={d:dict(Counter(result['patterns'][k]['mode'] for k,_,_ in rows)) for d,rows in result['days'].items()}
    return result

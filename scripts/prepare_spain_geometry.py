"""Compile official IGN railway alignments for Spain's offline train replay."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_geometry import compile_ways
SOURCE_URL = 'https://api-features.idee.es/collections/railwaylink/items?f=json'
SOURCE_SHA256 = '2f69b61322cef54ce16e64cbfc404d1537bdcba119c9846b3872f0e0c1940b3a'
OUTPUT = ROOT / 'data/reference/spain/ign-rail-2026-10-19.json.gz'


def prepare(filename, output=OUTPUT):
    if file_hash(filename) != SOURCE_SHA256:
        raise ValueError('IGN railway export differs from the validated source')
    raw = json.loads(filename.read_text())
    features = raw['features']
    if len(features) != raw['numberMatched'] or len({f['id'] for f in features}) != len(features):
        raise ValueError('Incomplete or duplicate IGN railway features')
    adapted = [{'geometry': f['geometry'], 'properties': {'idgaia': f['id'], 'type_voie': 'VPA', 'code_ligne': ''}}
               for f in features]
    ways, _ = compile_ways(adapted, [])
    result = {'metadata': {'source': 'IGN / Sistema Cartográfico Nacional · railway links',
        'source_url': SOURCE_URL, 'source_date': 'Accessed 2026-10-19; current geographic reference for 2024 schedules',
        'source_sha256': file_hash(filename), 'source_features': len(features),
        'license': 'CC BY 4.0', 'license_url': 'https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf',
        'attribution': 'Obra derivada de IGR Redes de Transporte, consulta 2026-10-19, CC BY 4.0, ign.es / Sistema Cartográfico Nacional. Matched and simplified by SunTrain.',
        'note': 'Geographic alignments with coincident original endpoints/vertices rounded to seven decimals; no proximity snapping or invented interior crossings. Heights are not used for operational routing. Not exact running tracks or proof of historical diversions.'}, 'ways': ways}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as f, gzip.GzipFile(filename='', fileobj=f, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(result, separators=(',', ':'), allow_nan=False).encode())
    print('ways', len(ways), 'bytes', output.stat().st_size, 'sha256', file_hash(output), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); prepare(args.source, args.output)

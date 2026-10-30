"""Compare historical campaign evidence with the active descendant checkpoint."""
from dashboard import international_expansion as adapter,south_america_domestic as domestic
from scripts.discover_international_expansion import ROOT,digest,read,relative


def current_checkpoint(ancestor):
    active=adapter.load_reference()['metadata']['source_manifest']
    path=ROOT/active['path'];assert digest(path.read_bytes())==active['sha256']
    current=read(path)
    if path.resolve()!=ancestor.resolve():
        parents=current.get('parent_campaigns',[])
        assert any(p['path']==relative(ancestor) and p['sha256']==digest(ancestor.read_bytes()) for p in parents)
    return current


def expected_world_metrics(checkpoint):
    result={**checkpoint['collection']['after']}
    # Earlier ledgers predate the independently prepared domestic archive.
    if domestic.enabled() and relative(domestic.reference_path()) not in checkpoint['baseline_inputs']:
        result['flights']+=domestic.load_reference()['metadata']['coverage']['new_world_identities']
    return result


def pins_historical_supplement(checkpoint,sha256):
    documents=[checkpoint]
    for parent in checkpoint.get('parent_campaigns',[]):
        path=ROOT/parent['path']
        assert digest(path.read_bytes())==parent['sha256']
        documents.append(read(path))
    key=relative(adapter.reference_path())
    return any(d.get('baseline_supplement_sha256')==sha256
        or d.get('baseline_inputs',{}).get(key,{}).get('sha256')==sha256 for d in documents)

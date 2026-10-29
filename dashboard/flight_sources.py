"""Isolated, read-once input cache for offline flight preparation."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

_cache = ContextVar('flight_reference_reads', default=None)


def read_reference(path):
    path = Path(path).resolve()
    cache = _cache.get()
    if cache is None:
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    if path not in cache['documents']:
        raw = path.read_bytes()
        cache['documents'][path] = json.loads(gzip.decompress(raw))
        cache['inputs'][path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    # Existing adapters may annotate their private input (notably Gulf scopes).
    return deepcopy(cache['documents'][path])


@contextmanager
def cached_reference_reads():
    cache = {'documents': {}, 'inputs': {}}
    token = _cache.set(cache)
    try:
        yield cache['inputs']
    finally:
        _cache.reset(token)

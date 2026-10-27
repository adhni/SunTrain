"""Normalize pinned additional-European-network maps without any flight searches."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import OTHER_NETWORKS
from scripts.prepare_europe_group_routes import build

if __name__=='__main__':
 build(ROOT/'data/sources/europe_networks_discovery.json',ROOT/'data/sources/europe_networks_routes.json',OTHER_NETWORKS,'europe_networks')

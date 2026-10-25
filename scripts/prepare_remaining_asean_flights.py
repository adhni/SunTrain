"""Sequential resumable domestic captures for the remaining ASEAN profiles."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.asean_flights import PROFILES,DAY
from scripts.prepare_google_flights import capture,country_config,prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--country',choices=['MM','LA','KH','TL'])
    parser.add_argument('--concurrency',type=int,choices=[1,2],default=1)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();countries=[args.country] if args.country else ['MM','LA','KH','TL'];stopped=None
    for country in countries:
        p=PROFILES[country];cfg=country_config(country)
        cache=ROOT/f".cache/google-flights-{p['slug']}";cache.mkdir(parents=True,exist_ok=True)
        if not args.prepare_only and not stopped:
            try:asyncio.run(capture(cache,DAY,cfg['manifest']['routes'],args.concurrency,cfg))
            except RuntimeError as error:
                stopped=str(error)
        if stopped:(cache/'collection-stop.json').write_text(json.dumps(dict(reason=stopped,at=datetime.now(timezone.utc).isoformat())))
        prepare(cache,ROOT/f"data/reference/{p['slug']}_flights/{DAY}.json.gz",DAY,cfg['manifest']['routes'],cfg)
    if stopped:
        print(stopped+'; successful captures preserved; no challenge retries',file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())

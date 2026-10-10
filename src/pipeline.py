"""Real-data pipeline. Collection is explicit; no synthetic fallback."""
import argparse
from src.data.prepare import prepare
from src.models.train import train_and_log


def run_all(legacy=False, collect=False):
    if collect:
        from src.scraping.collect import collect as collect_sources
        collect_sources()
    prepare(legacy=legacy)
    train_and_log(allow_legacy=legacy)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect', action='store_true')
    p.add_argument('--legacy-exploratory', action='store_true', help='Use only pre-existing FBref-labelled standard rows, with explicit unverified provenance tags')
    args = p.parse_args()
    run_all(legacy=args.legacy_exploratory, collect=args.collect)

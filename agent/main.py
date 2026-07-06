"""Entrypoint: python -m agent.main [--dry-run]

Loads config.yaml (secrets overridable via env vars), fans queries out to
each enabled source, runs the filter engine, notifies on new matches, and
persists the dedup state - unless --dry-run is set, in which case matches
are printed and nothing is saved or sent.
"""
import argparse
import logging
import os
import sys

import yaml

from agent.filters import compile_targets, evaluate
from agent.notify import send_matches
from agent.storage import is_new, load_seen, mark_seen, save_seen
from agent.sources import craigslist, ebay

log = logging.getLogger("agent")

CONFIG_PATH = os.environ.get("BIKE_AGENT_CONFIG", "config.yaml")

ENV_OVERRIDES = {
    ("sources", "ebay", "client_id"): "EBAY_CLIENT_ID",
    ("sources", "ebay", "client_secret"): "EBAY_CLIENT_SECRET",
    ("notify", "discord_webhook"): "DISCORD_WEBHOOK_URL",
}


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for keys, env_name in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if not value:
            continue
        node = cfg
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value

    return cfg


def collect_listings(cfg):
    listings = []
    if cfg["sources"].get("craigslist", {}).get("enabled"):
        listings.extend(craigslist.fetch(cfg))
    if cfg["sources"].get("ebay", {}).get("enabled"):
        listings.extend(ebay.fetch(cfg))
    return listings


def run(cfg, dry_run):
    targets = compile_targets(cfg)
    seen_path = cfg["storage"]["seen_path"]
    seen = load_seen(seen_path)

    listings = collect_listings(cfg)
    log.info("fetched %d listings", len(listings))

    matches = []
    for listing in listings:
        match = evaluate(listing, cfg, targets)
        if match and is_new(seen, listing):
            matches.append(match)
            mark_seen(seen, listing)

    if dry_run:
        for m in matches:
            print(f"[{m.model}] {m.size} - {m.listing.title}\n  {m.listing.url}")
        print(f"\n{len(matches)} new match(es) (dry run - nothing saved or sent)")
        return

    send_matches(cfg["notify"]["discord_webhook"], matches)
    save_seen(seen_path, seen)
    log.info("notified %d new match(es)", len(matches))


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Vintage touring frame tracker")
    parser.add_argument("--dry-run", action="store_true",
                         help="print matches without saving state or sending notifications")
    parser.add_argument("--config", default=CONFIG_PATH)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    run(cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

"""Dedup state: a JSON set of hashes for listings already notified on."""
import hashlib
import json
import os


def _hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def load_seen(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("seen", []))


def save_seen(path, seen):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"seen": sorted(seen)}, f, indent=2)
        f.write("\n")


def is_new(seen, listing):
    return _hash(listing.url) not in seen


def mark_seen(seen, listing):
    seen.add(_hash(listing.url))

"""Craigslist source. RSS was discontinued, so this scrapes the search-results
HTML, then (optionally) fetches each candidate listing page so size and
exclusion checks run against the full posting text rather than just the
title. Craigslist's markup changes occasionally - if a run starts logging
"0 listings pulled," this is the first place to check.
"""
import logging
import time

import httpx
from bs4 import BeautifulSoup

from agent.models import Listing

log = logging.getLogger(__name__)

SEARCH_URL = "https://{subdomain}.craigslist.org/search/{category}"
LISTING_DELAY_SECONDS = 2
HEADERS = {"User-Agent": "Mozilla/5.0 (vintage-bike-agent)"}


def _parse_results(html, source):
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    # Current (2023+) markup: <li class="cl-search-result"> with a
    # <a class="cl-app-anchor" href="..."><span class="label">Title</span></a>
    rows = soup.select("li.cl-search-result") or soup.select("li.result-row")
    for row in rows:
        anchor = row.select_one("a.cl-app-anchor") or row.select_one("a.result-title") \
            or row.select_one("a")
        if not anchor or not anchor.get("href"):
            continue
        title_el = row.select_one("span.label") or anchor
        title = title_el.get_text(strip=True)
        price_el = row.select_one(".priceinfo") or row.select_one(".result-price")
        price = price_el.get_text(strip=True) if price_el else None
        listings.append(Listing(source=source, title=title, url=anchor["href"], price=price))

    return listings


def _fetch_listing_body(client, url):
    try:
        resp = client.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("craigslist: failed to fetch listing %s: %s", url, exc)
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.select_one("#postingbody")
    return body.get_text(" ", strip=True) if body else ""


def fetch(cfg):
    """Run every query against every configured subdomain, returning Listings.
    When fetch_listing_pages is set, full posting text is fetched (rate
    limited and capped) so filters see more than just the title.
    """
    craigslist_cfg = cfg["sources"]["craigslist"]
    subdomains = craigslist_cfg.get("subdomains", ["sfbay"])
    category = craigslist_cfg.get("category", "bia")
    fetch_bodies = craigslist_cfg.get("fetch_listing_pages", True)
    max_fetches = craigslist_cfg.get("max_page_fetches", 25)

    results = []
    fetches_used = 0

    with httpx.Client(follow_redirects=True) as client:
        for subdomain in subdomains:
            url = SEARCH_URL.format(subdomain=subdomain, category=category)
            for query in cfg.get("queries", []):
                try:
                    resp = client.get(url, headers=HEADERS, params={"query": query}, timeout=15)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("craigslist: search failed for %s/%s: %s", subdomain, query, exc)
                    continue

                for listing in _parse_results(resp.text, source=f"craigslist-{subdomain}"):
                    if fetch_bodies and fetches_used < max_fetches:
                        time.sleep(LISTING_DELAY_SECONDS)
                        listing.description = _fetch_listing_body(client, listing.url)
                        fetches_used += 1
                    results.append(listing)

    return results

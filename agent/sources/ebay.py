"""eBay Browse API source (production keyset, client-credentials grant).

Searches the bicycle and bicycle-frame categories nationally by default,
since these frames ship cheap and are rare; set
sources.ebay.local_pickup_only to restrict to the configured radius.
"""
import logging

import httpx

log = logging.getLogger(__name__)

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"
# Bicycles (7294) and Bicycle Frames (177831) categories.
CATEGORY_IDS = "7294,177831"


def _get_token(client_id, client_secret):
    resp = httpx.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _to_listing(item):
    from agent.models import Listing

    price = item.get("price", {})
    price_str = f"{price.get('value')} {price.get('currency')}" if price.get("value") else None
    image = (item.get("image") or {}).get("imageUrl")
    return Listing(
        source="ebay",
        title=item.get("title", ""),
        url=item.get("itemWebUrl", ""),
        description=item.get("shortDescription", "") or "",
        price=price_str,
        image=image,
    )


def fetch(cfg):
    ebay_cfg = cfg["sources"]["ebay"]
    client_id = ebay_cfg.get("client_id") or ""
    client_secret = ebay_cfg.get("client_secret") or ""
    if not client_id or not client_secret:
        log.warning("ebay: missing client_id/client_secret, skipping source")
        return []

    try:
        token = _get_token(client_id, client_secret)
    except httpx.HTTPError as exc:
        log.warning("ebay: failed to obtain token: %s", exc)
        return []

    headers = {"Authorization": f"Bearer {token}"}
    params = {"category_ids": CATEGORY_IDS, "limit": "50"}

    if ebay_cfg.get("local_pickup_only"):
        location = cfg.get("location", {})
        postal_code = location.get("postal_code")
        radius = location.get("radius_miles")
        if postal_code:
            headers["X-EBAY-C-ENDUSERCTX"] = (
                f"contextualLocation=country=US,zip={postal_code}"
            )
        if radius:
            params["filter"] = f"pickupCountry:US,pickupRadius:{radius},pickupRadiusUnit:mi"

    results = []
    with httpx.Client(timeout=15) as client:
        for query in cfg.get("queries", []):
            params["q"] = query
            try:
                resp = client.get(SEARCH_URL, headers=headers, params=params)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("ebay: search failed for %r: %s", query, exc)
                continue
            for item in resp.json().get("itemSummaries", []):
                results.append(_to_listing(item))

    return results

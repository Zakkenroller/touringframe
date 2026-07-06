"""Discord webhook notifications for new matches."""
import httpx


def _embed(match):
    listing = match.listing
    title = f"{match.model} — {listing.title}"
    lines = [f"**Size:** {match.size}"]
    if listing.price:
        lines.append(f"**Price:** {listing.price}")
    lines.append(f"**Source:** {listing.source}")
    if match.size == "unknown":
        lines.append("_size unknown — verify_")
    embed = {
        "title": title[:256],
        "url": listing.url,
        "description": "\n".join(lines),
    }
    if listing.image:
        embed["thumbnail"] = {"url": listing.image}
    return embed


def send_matches(webhook_url, matches):
    """POST one Discord message per match (webhooks cap embeds per message,
    but a handful of daily matches never gets close)."""
    if not webhook_url or not matches:
        return
    with httpx.Client(timeout=15) as client:
        for match in matches:
            client.post(webhook_url, json={"embeds": [_embed(match)]})

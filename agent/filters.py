"""Model + size filter engine shared by every source."""
import re

from agent.models import Match

CM_RE = re.compile(r'\b(?:sz\.?|size)\s*(\d{2})\b|\b(\d{2})\s*cm\b', re.I)
INCH_RE = re.compile(r'\b(\d{2}(?:\.\d)?)\s*(?:"|in\b|inch\w*)', re.I)


def extract_sizes(text):
    """Return (cm_values, inch_values) found in text, as lists of strings."""
    cms = []
    for m in CM_RE.finditer(text):
        val = m.group(1) or m.group(2)
        if val not in cms:
            cms.append(val)
    inches = []
    for m in INCH_RE.finditer(text):
        val = m.group(1)
        if val not in inches:
            inches.append(val)
    return cms, inches


def compile_targets(cfg):
    """Compile each target's regex once, keeping the display name alongside."""
    return [
        {"name": t["name"], "regex": re.compile(t["pattern"], re.I)}
        for t in cfg["targets"]
    ]


def _excluded(text, exclusions):
    lower = text.lower()
    return any(excl.lower() in lower for excl in exclusions)


def evaluate(listing, cfg, targets):
    """Return a Match if the listing survives model/exclusion/size checks, else None."""
    text = f"{listing.title} {listing.description}"

    if _excluded(text, cfg.get("exclusions", [])):
        return None

    target = next((t for t in targets if t["regex"].search(text)), None)
    if target is None:
        return None

    sizing = cfg.get("sizing", {})
    allowed_cm = {str(v) for v in sizing.get("cm_values", [])}
    allowed_inch = {str(v) for v in sizing.get("inch_values", [])}

    cms, inches = extract_sizes(text)

    for cm in cms:
        if cm in allowed_cm:
            return Match(model=target["name"], size=f"{cm}cm", listing=listing)
    for inch in inches:
        if inch in allowed_inch:
            return Match(model=target["name"], size=f'{inch}"', listing=listing)

    if cms or inches:
        # A size was stated and it's outside the allowed window - drop.
        return None

    if sizing.get("unknown_size", "notify") == "notify":
        return Match(model=target["name"], size="unknown", listing=listing)
    return None

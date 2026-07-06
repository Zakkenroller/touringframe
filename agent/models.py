"""Shared data types passed between sources, the filter engine, and notify."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    source: str
    title: str
    url: str
    description: str = ""
    price: Optional[str] = None
    image: Optional[str] = None
    posted_at: Optional[str] = None


@dataclass
class Match:
    model: str
    size: str
    listing: Listing = field(repr=False, default=None)

"""Pydantic schemas for Market Pulse resources."""
from pydantic import BaseModel


class MarketPulseItem(BaseModel):
    key: str
    value: str
    label: str | None = None
    direction: str | None = None


class MarketPulseData(BaseModel):
    items: list[MarketPulseItem]
    last_updated: str

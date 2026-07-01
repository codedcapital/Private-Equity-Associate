"""Market Pulse router — dynamic market data settings.

Endpoints:
    GET    /market-pulse          — Current market pulse data
    PUT    /market-pulse          — Update market pulse settings (admin)
"""

from datetime import datetime

from fastapi import APIRouter

from db.crud import list_market_pulse_settings, upsert_market_pulse_setting
from db.session import async_session_factory
from schemas.market_pulse import MarketPulseData, MarketPulseItem

router = APIRouter(prefix="/market-pulse", tags=["market-pulse"])


@router.get("", response_model=MarketPulseData)
async def get_market_pulse() -> MarketPulseData:
    """Return current market pulse settings."""
    async with async_session_factory() as session:
        settings = await list_market_pulse_settings(session)
        if not settings:
            # Return default values if no settings exist
            return MarketPulseData(
                items=[
                    MarketPulseItem(key="treasury_yield", value="4.18%", label="10Y Treasury", direction="up"),
                    MarketPulseItem(key="software_ev_revenue", value="7.8x", label="Software EV/Revenue"),
                    MarketPulseItem(key="sp500_change", value="+0.7%", label="S&P 500"),
                    MarketPulseItem(key="fed_outlook", value="1 Cut Expected", label="Fed Outlook"),
                ],
                last_updated="Never",
            )
        items = [
            MarketPulseItem(key=s.key, value=s.value, label=s.label, direction=s.direction)
            for s in settings
        ]
        last_updated = max(
            (s.updated_at.isoformat() for s in settings if s.updated_at),
            default="Never",
        )
        return MarketPulseData(items=items, last_updated=last_updated)


@router.put("", response_model=MarketPulseData)
async def update_market_pulse(data: MarketPulseData) -> MarketPulseData:
    """Update market pulse settings."""
    async with async_session_factory() as session:
        for item in data.items:
            await upsert_market_pulse_setting(
                session,
                key=item.key,
                value=item.value,
                label=item.label,
                direction=item.direction,
            )
        return data

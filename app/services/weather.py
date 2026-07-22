"""Weather provider boundary used by workout settlement.

Only normalized, product-facing values leave this module.  The raw provider
payload is intentionally never stored in a training record.
"""

from dataclasses import dataclass
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherSnapshot:
    condition: str
    temperature_c: float


def _normalize_condition(weather_id: int | None) -> str:
    """Map OpenWeather condition ids to the small, stable product taxonomy."""
    if weather_id is None:
        return "unknown"
    if 200 <= weather_id < 600:
        return "rain"       # thunderstorm, drizzle, rain
    if 600 <= weather_id < 700:
        return "snow"
    if 700 <= weather_id < 800:
        return "fog"
    if weather_id == 800:
        return "clear"
    if 801 <= weather_id <= 804:
        return "cloudy"
    return "unknown"


async def fetch_weather_snapshot(lat: float, lon: float) -> WeatherSnapshot | None:
    """Fetch current weather without blocking workout settlement on provider failure."""
    if not settings.OPENWEATHER_API_KEY:
        logger.info("Weather snapshot skipped: OPENWEATHER_API_KEY is not configured")
        return None

    params = {
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "units": "metric",
        "appid": settings.OPENWEATHER_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.OPENWEATHER_TIMEOUT_SECONDS) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params=params,
            )
            response.raise_for_status()
        payload = response.json()
        weather = payload.get("weather") or []
        condition_id = weather[0].get("id") if weather else None
        temperature = (payload.get("main") or {}).get("temp")
        if temperature is None:
            logger.warning("Weather snapshot response is incomplete")
            return None
        return WeatherSnapshot(
            condition=_normalize_condition(condition_id),
            temperature_c=round(float(temperature), 1),
        )
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        logger.exception("Weather snapshot query failed")
        return None


def weather_snapshot_dict(snapshot: WeatherSnapshot | None) -> dict | None:
    if snapshot is None:
        return None
    return {
        "condition": snapshot.condition,
        "temperature_c": snapshot.temperature_c,
    }


def weather_snapshot_from_record(record) -> dict | None:
    if (
        not record.weather_condition
        or record.weather_temperature_c is None
    ):
        return None
    return {
        "condition": record.weather_condition,
        "temperature_c": record.weather_temperature_c,
    }
